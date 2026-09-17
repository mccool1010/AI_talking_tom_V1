import logging
import subprocess

import sounddevice as sd
import soundfile as sf

import config
from interaction_state import InteractionPhase

log = logging.getLogger(__name__)

SYNTH_TIMEOUT_SECONDS = 30


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

    def speak(self, text):
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
                self._godot.send_speak(text)
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
