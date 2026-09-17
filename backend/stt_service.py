import logging
import threading
import time
from collections import deque
from enum import Enum

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from scipy.io.wavfile import write

import config

log = logging.getLogger(__name__)

CHUNK_SIZE = 512              # 32 ms at 16 kHz (Silero VAD's native frame size)
PRE_ROLL_SECONDS = 0.3        # audio kept from before speech was detected
MAX_UTTERANCE_SECONDS = 30
VAD_START_PROB = 0.5
VAD_CONTINUE_PROB = 0.35


class STTLifecycle(Enum):
    """Explicit lifecycle states for the STT service."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class SpeechDetector:
    """
    Decides whether a 16 kHz int16 chunk contains speech. Uses Silero VAD when
    available (robust to background noise), otherwise a volume threshold.
    """

    def __init__(self, use_vad=True, energy_threshold=500):
        self.energy_threshold = energy_threshold
        self.model = None
        if use_vad:
            try:
                import torch
                threads = torch.get_num_threads()
                try:
                    from silero_vad import load_silero_vad
                    self.model = load_silero_vad()
                finally:
                    # Importing silero_vad limits torch to one thread for the
                    # whole process, which made the wav2vec2 emotion model 3x slower.
                    torch.set_num_threads(threads)
                self._torch = torch
            except Exception:
                log.warning("Silero VAD unavailable; falling back to volume threshold", exc_info=True)

    @property
    def uses_vad(self):
        return self.model is not None

    def speech_prob(self, chunk):
        if self.model is None:
            return 1.0 if np.abs(chunk).mean() > self.energy_threshold else 0.0
        audio = self._torch.from_numpy(chunk.reshape(-1).astype(np.float32) / 32768.0)
        return float(self.model(audio, config.STT_SAMPLE_RATE))

    def reset(self):
        if self.model is not None:
            self.model.reset_states()


def load_whisper(model_name, device):
    """Load Whisper on the GPU when possible, falling back to CPU int8."""
    import torch
    threads = torch.get_num_threads()
    try:
        return _load_whisper(model_name, device)
    finally:
        torch.set_num_threads(threads)  # loading lowers torch's global thread count


def _load_whisper(model_name, device):
    candidates = [("cuda", "float16"), ("cpu", "int8")] if device == "auto" else \
        [(device, "float16" if device == "cuda" else "int8")]
    for dev, compute_type in candidates:
        try:
            model = WhisperModel(model_name, device=dev, compute_type=compute_type)
            # CUDA libraries are only loaded on first use, so prove it works now.
            segments, _ = model.transcribe(np.zeros(8000, dtype=np.float32), language="en")
            list(segments)
            log.info("Whisper %s on %s (%s)", model_name, dev, compute_type)
            return model
        except Exception as e:
            log.info("Whisper on %s unavailable: %s", dev, e)
    raise RuntimeError("Could not load Whisper on any device")


class STTService:
    """
    Speech-to-text service with background thread and explicit lifecycle.

    Lifecycle: CREATED -> RUNNING <-> PAUSED -> STOPPED.
    Only listens while interaction_state.can_listen() is True; the main loop
    moves the interaction state on after consuming a transcription.
    """

    def __init__(self, environment, interaction_state):
        self.environment = environment
        self._interaction_state = interaction_state

        self._lifecycle_state = STTLifecycle.CREATED
        self._lifecycle_lock = threading.Lock()
        self._condition = threading.Condition(self._lifecycle_lock)
        self._thread = None

        self.latest_text = None
        self.latest_audio = None
        self._data_lock = threading.Lock()

        self._listening = False      # mic stream open
        self._recording = False      # speech detected
        self._transcribing = False   # Whisper running

        self.sample_rate = config.STT_SAMPLE_RATE
        self.silence_duration = config.STT_SILENCE_SECONDS
        self.recording_path = config.RECORDING_PATH
        config.ensure_runtime_dirs()
        self.detector = SpeechDetector(config.STT_USE_VAD, config.STT_ENERGY_THRESHOLD)
        self.model = load_whisper(config.WHISPER_MODEL, config.WHISPER_DEVICE)

    # ---- lifecycle ----

    def start(self):
        with self._lifecycle_lock:
            if self._lifecycle_state in (STTLifecycle.RUNNING, STTLifecycle.PAUSED):
                return
            self._lifecycle_state = STTLifecycle.RUNNING
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="stt")
        self._thread.start()

    def stop(self):
        with self._lifecycle_lock:
            if self._lifecycle_state == STTLifecycle.STOPPED:
                return
            self._lifecycle_state = STTLifecycle.STOPPED
            self._condition.notify_all()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._clear_data()

    def pause(self):
        with self._lifecycle_lock:
            if self._lifecycle_state == STTLifecycle.RUNNING:
                self._lifecycle_state = STTLifecycle.PAUSED

    def resume(self):
        with self._lifecycle_lock:
            if self._lifecycle_state == STTLifecycle.PAUSED:
                self._lifecycle_state = STTLifecycle.RUNNING
                self._condition.notify_all()

    # ---- accessors ----

    def is_listening(self):
        return self._recording

    def is_mic_open(self):
        return self._listening

    def is_transcribing(self):
        return self._transcribing

    def get_and_clear(self):
        """Atomically take the latest (text, audio), or (None, None)."""
        with self._data_lock:
            text, audio = self.latest_text, self.latest_audio
            self.latest_text = self.latest_audio = None
        return text, audio

    # ---- internals ----

    def _clear_data(self):
        with self._data_lock:
            self.latest_text = self.latest_audio = None

    def _stopped(self):
        with self._lifecycle_lock:
            return self._lifecycle_state == STTLifecycle.STOPPED

    def _listen_loop(self):
        while True:
            with self._lifecycle_lock:
                while self._lifecycle_state == STTLifecycle.PAUSED:
                    self._condition.wait()
                if self._lifecycle_state == STTLifecycle.STOPPED:
                    break

            if not self._interaction_state.can_listen():
                time.sleep(0.1)
                continue

            try:
                text, audio = self._listen()
            except Exception:
                log.exception("Listening failed; retrying in 1 s")
                time.sleep(1)
                continue
            if not text:
                continue

            with self._data_lock:
                self.latest_text, self.latest_audio = text, audio

            # Wait for the main loop to consume the result.
            while not self._stopped():
                with self._data_lock:
                    if self.latest_text is None:
                        break
                time.sleep(0.1)

    def _listen(self):
        """Capture one utterance and transcribe it. Returns (text, audio) or (None, None)."""
        self._listening = True
        self.detector.reset()
        state = {"recording": False, "silent_chunks": 0, "chunks": 0}
        pre_roll = deque(maxlen=max(1, int(PRE_ROLL_SECONDS * self.sample_rate / CHUNK_SIZE)))
        audio_chunks = []
        silence_limit = int(self.silence_duration * self.sample_rate / CHUNK_SIZE)
        max_chunks = int(MAX_UTTERANCE_SECONDS * self.sample_rate / CHUNK_SIZE)
        done = threading.Event()

        def callback(indata, frames, time_info, status):
            if status:
                log.debug("Audio status: %s", status)
            chunk = indata.copy()
            prob = self.detector.speech_prob(chunk)
            if not state["recording"]:
                if prob >= VAD_START_PROB:
                    state["recording"] = True
                    self._recording = True
                    audio_chunks.extend(pre_roll)
                    audio_chunks.append(chunk)
                else:
                    pre_roll.append(chunk)
                return
            audio_chunks.append(chunk)
            state["chunks"] += 1
            state["silent_chunks"] = 0 if prob >= VAD_CONTINUE_PROB else state["silent_chunks"] + 1
            if state["silent_chunks"] > silence_limit or state["chunks"] > max_chunks:
                done.set()

        try:
            with sd.InputStream(callback=callback, channels=1, samplerate=self.sample_rate,
                                dtype="int16", blocksize=CHUNK_SIZE):
                while not done.wait(0.05):
                    if self._stopped() or self.environment.user_left:
                        return None, None
        finally:
            self._listening = False
            if not done.is_set():
                self._recording = False

        audio = np.concatenate(audio_chunks)
        write(self.recording_path, self.sample_rate, audio)

        self._transcribing = True
        try:
            segments, _ = self.model.transcribe(
                audio.reshape(-1).astype(np.float32) / 32768.0, language="en")
            text = "".join(s.text for s in segments).strip()
            log.info("Heard: %s", text)
            return text, audio
        finally:
            self._recording = False
            self._transcribing = False
