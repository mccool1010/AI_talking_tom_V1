import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import numpy as np
import threading
from enum import Enum


class STTLifecycle(Enum):
    """Explicit lifecycle states for the STT service."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class STTService:
    """
    Speech-to-text service with background thread and explicit lifecycle.

    Lifecycle states:
        CREATED -> RUNNING -> PAUSED -> RUNNING -> STOPPED

    The service respects the interaction state machine:
        - Only starts listening when interaction_state.can_listen() is True.
        - The main loop transitions the interaction state after consuming text.

    Thread safety:
        - _lifecycle_state protected by _lifecycle_lock.
        - _condition used for pause/resume signaling (no busy-wait).
        - latest_text / latest_audio protected by _data_lock.
    """

    def __init__(self, environment, interaction_state):
        self.environment = environment
        self._interaction_state = interaction_state

        # Lifecycle
        self._lifecycle_state = STTLifecycle.CREATED
        self._lifecycle_lock = threading.Lock()
        self._condition = threading.Condition(self._lifecycle_lock)
        self._thread = None

        # Shared output data
        self.latest_text = None
        self.latest_audio = None
        self._data_lock = threading.Lock()

        # Internal state flags
        self._listening = False      # True when mic InputStream is open
        self._recording = False      # True when speech detected (volume > threshold)
        self._transcribing = False   # True during Whisper transcription

        print("Loading Whisper...")
        self.model = WhisperModel(
            "base.en",
            device="cpu",
            compute_type="int8"
        )
        self.sample_rate = 16000
        self.threshold = 500
        self.silence_duration = 2
        print("Whisper Ready")

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def start(self):
        """
        Start the STT background thread.

        Only valid from CREATED or STOPPED states.
        Guards against duplicate starts.
        """
        with self._lifecycle_lock:
            if self._lifecycle_state == STTLifecycle.RUNNING:
                print("[STT] Already running")
                return
            if self._lifecycle_state == STTLifecycle.PAUSED:
                print("[STT] Paused — use resume() instead")
                return

            self._lifecycle_state = STTLifecycle.RUNNING
            print("[STT] Starting")

        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True
        )
        self._thread.start()

    def stop(self):
        """
        Stop the STT service and release resources.

        The thread exits cleanly and shared state is cleared.
        """
        with self._lifecycle_lock:
            if self._lifecycle_state == STTLifecycle.STOPPED:
                return
            self._lifecycle_state = STTLifecycle.STOPPED
            self._condition.notify_all()

        print("[STT] Stopping")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        # Clear stale data
        self._clear_data()
        print("[STT] Stopped")

    def pause(self):
        """
        Pause listening. The background thread stays alive but does not
        consume audio until resume() is called.
        """
        with self._lifecycle_lock:
            if self._lifecycle_state != STTLifecycle.RUNNING:
                return
            self._lifecycle_state = STTLifecycle.PAUSED
            print("[STT] Paused")

    def resume(self):
        """
        Resume listening after a pause.
        """
        with self._lifecycle_lock:
            if self._lifecycle_state != STTLifecycle.PAUSED:
                return
            self._lifecycle_state = STTLifecycle.RUNNING
            self._condition.notify_all()
            print("[STT] Resumed")

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def is_listening(self):
        """Return True if the user is actively speaking (speech detected)."""
        return self._recording

    def is_mic_open(self):
        """Return True if the microphone InputStream is open (waiting or recording)."""
        return self._listening

    def is_transcribing(self):
        """Return True if the service is currently transcribing audio."""
        return self._transcribing

    def get_and_clear(self):
        """
        Atomically read and clear the latest transcription result.

        Returns:
            (text, audio) tuple, or (None, None) if no result is available.
        """
        with self._data_lock:
            text = self.latest_text
            audio = self.latest_audio
            self.latest_text = None
            self.latest_audio = None
        return text, audio

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear_data(self):
        """Clear shared output data to prevent stale reads."""
        with self._data_lock:
            self.latest_text = None
            self.latest_audio = None

    def _is_running(self):
        """Check if lifecycle state is RUNNING (no lock — caller must hold)."""
        return self._lifecycle_state == STTLifecycle.RUNNING

    def _listen_loop(self):
        """
        Background loop that continuously listens for speech.

        Respects:
            - Lifecycle state (RUNNING / PAUSED / STOPPED)
            - Interaction state (only listens when can_listen() is True)
        """
        print("[STT] Listen loop started")
        while True:
            # Check lifecycle
            with self._lifecycle_lock:
                if self._lifecycle_state == STTLifecycle.STOPPED:
                    break

                # If paused, wait until resumed or stopped
                while self._lifecycle_state == STTLifecycle.PAUSED:
                    print("[STT] Waiting for resume...")
                    self._condition.wait()
                    if self._lifecycle_state == STTLifecycle.STOPPED:
                        break

                if self._lifecycle_state == STTLifecycle.STOPPED:
                    break

            # Check interaction state — only listen when system is idle
            if not self._interaction_state.can_listen():
                import time
                time.sleep(0.1)
                continue

            # Perform one listening cycle
            text, audio = self._listen()
            if text is None:
                continue

            # Store result atomically
            with self._data_lock:
                self.latest_text = text
                self.latest_audio = audio

            # Wait until the main loop has consumed the result
            # before starting the next listen cycle.
            # The main loop will transition the interaction state,
            # so can_listen() will be False until the turn completes.
            while True:
                with self._lifecycle_lock:
                    if self._lifecycle_state == STTLifecycle.STOPPED:
                        break
                with self._data_lock:
                    if self.latest_text is None:
                        break
                import time
                time.sleep(0.1)

        print("[STT] Listen loop exited")

    def _listen(self):
        """
        Capture and transcribe a single speech utterance.

        Returns:
            (text, audio) tuple, or (None, None) if cancelled.
        """
        self._listening = True
        print("Waiting for speech...")

        audio_chunks = []
        recording = False
        silence_chunks = 0
        chunk_size = 1024

        silence_limit = int(
            self.silence_duration *
            self.sample_rate /
            chunk_size
        )

        def callback(indata, frames, time_info, status):
            if status:
                print(status)
            nonlocal recording
            nonlocal silence_chunks
            nonlocal audio_chunks

            volume = np.abs(indata).mean()

            if not recording:
                if volume > self.threshold:
                    print("Speech detected")
                    recording = True
                    self._recording = True
                    audio_chunks.append(indata.copy())
            else:
                audio_chunks.append(indata.copy())
                if volume < self.threshold:
                    silence_chunks += 1
                else:
                    silence_chunks = 0

        with sd.InputStream(
            callback=callback,
            channels=1,
            samplerate=self.sample_rate,
            dtype="int16",
            blocksize=chunk_size
        ):
            while True:
                # Check if we should abort
                with self._lifecycle_lock:
                    if self._lifecycle_state == STTLifecycle.STOPPED:
                        self._listening = False
                        self._recording = False
                        return None, None

                if self.environment.user_left:
                    print("User left camera. Cancelling listening.")
                    self._listening = False
                    self._recording = False
                    return None, None

                if recording and silence_chunks > silence_limit:
                    break

        print("Speech ended")

        audio = np.concatenate(audio_chunks)

        write(
            "recording.wav",
            self.sample_rate,
            audio
        )

        print("Transcribing...")
        self._transcribing = True
        try:
            segments, info = self.model.transcribe(
                "recording.wav",
                language="en"
            )
            text = ""
            for segment in segments:
                text += segment.text
            return text.strip(), audio
        finally:
            self._listening = False
            self._recording = False
            self._transcribing = False

    def test_volume(self):
        """Debug utility to monitor microphone volume."""
        def callback(indata, frames, time_info, status):
            volume = np.abs(indata).mean()
            print(volume)

        with sd.InputStream(
            callback=callback,
            channels=1,
            samplerate=self.sample_rate,
            dtype="int16"
        ):
            input("Press Enter to stop...\n")
