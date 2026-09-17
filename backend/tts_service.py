import logging
import subprocess

import numpy as np
import sounddevice as sd
import soundfile as sf

import config
from interaction_state import InteractionPhase

log = logging.getLogger(__name__)

SYNTH_TIMEOUT_SECONDS = 30
ENVELOPE_FPS = 30
ENVELOPE_WINDOW_SECONDS = 0.04
NOISE_GATE = 0.12
ATTACK_SECONDS = 0.02
RELEASE_SECONDS = 0.06


def speech_envelope(data, samplerate, fps=ENVELOPE_FPS):
    """
    How open Tom's mouth should be, 0..1, every 1/fps second.

    RMS over overlapping 40 ms windows, scaled to the line's own loudness,
    gated so pauses close the mouth, and smoothed with a quick attack and a
    slower release so the jaw does not snap between frames.
    """
    audio = np.asarray(data, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    hop = max(1, int(samplerate / fps))
    frames = len(audio) // hop
    if frames == 0:
        return []
    half = max(1, int(samplerate * ENVELOPE_WINDOW_SECONDS / 2))
    padded = np.pad(audio ** 2, (half, half))
    csum = np.concatenate(([0.0], np.cumsum(padded, dtype=np.float64)))
    centers = np.arange(frames) * hop + hop // 2 + half
    rms = np.sqrt((csum[centers + half] - csum[centers - half]) / (2 * half))
    peak = np.percentile(rms, 95)
    if peak <= 1e-6:
        return [0.0] * frames
    level = np.clip(rms / peak, 0.0, 1.0)
    level = np.where(level < NOISE_GATE, 0.0, (level - NOISE_GATE) / (1 - NOISE_GATE)) ** 0.8
    attack = 1 - np.exp(-1 / (fps * ATTACK_SECONDS))
    release = 1 - np.exp(-1 / (fps * RELEASE_SECONDS))
    out, current = [], 0.0
    for v in level:
        current += (attack if v > current else release) * (v - current)
        out.append(round(float(current if current > 0.05 else 0.0), 2))
    return out


class TTSService:
    def __init__(self, interaction_state, stt_service=None):
        self._interaction_state = interaction_state
        self._stt = stt_service
        self._godot = None
        self.piper_path = str(config.PIPER_EXE)
        self.model_path = str(config.PIPER_VOICE)
        self.output_file = str(config.TTS_OUTPUT_PATH)
        config.ensure_runtime_dirs()
        for path in (config.PIPER_EXE, config.PIPER_VOICE):
            if not path.is_file():
                raise FileNotFoundError(f"Piper file missing: {path} (run `git lfs pull`)")
        # Warm the OS file cache so the first real reply is not slower.
        try:
            self.synthesize(".")
        except Exception:
            log.warning("Piper warm-up failed", exc_info=True)

    def set_godot_bridge(self, bridge):
        self._godot = bridge

    def synthesize(self, text):
        """Render `text` to the output WAV. Raises on failure."""
        result = subprocess.run(
            [self.piper_path, "--model", self.model_path, "--output_file", self.output_file],
            input=text, text=True, capture_output=True, timeout=SYNTH_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper failed ({result.returncode}): {result.stderr.strip()[-500:]}")
        return self.output_file

    def speak(self, text, emotion="neutral"):
        """
        Synthesize and play `text`.
        State: PRODUCING_SPEECH -> SPEAKING -> TURN_COMPLETE. STT is paused
        during playback so Tom does not hear himself.
        """
        log.info("Tom says: %s", text)
        self._interaction_state.transition_to(InteractionPhase.PRODUCING_SPEECH)
        try:
            self.synthesize(text)
            data, samplerate = sf.read(self.output_file)
        except Exception:
            log.exception("Speech synthesis failed")
            self._interaction_state.transition_to(InteractionPhase.TURN_COMPLETE)
            return

        if self._stt:
            self._stt.pause()
        try:
            self._interaction_state.transition_to(InteractionPhase.SPEAKING)
            if self._godot:
                self._godot.send_speak(text, emotion=emotion,
                                       envelope=speech_envelope(data, samplerate), fps=ENVELOPE_FPS)
            sd.play(data, samplerate)
            sd.wait()
        except Exception:
            log.exception("Audio playback failed")
        finally:
            self._interaction_state.transition_to(InteractionPhase.TURN_COMPLETE)
            if self._godot:
                self._godot.send_speak_end()
            if self._stt:
                self._stt.resume()
