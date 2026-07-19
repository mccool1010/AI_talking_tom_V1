import subprocess
import soundfile as sf
import sounddevice as sd
import os
from interaction_state import InteractionPhase


class TTSService:
    def __init__(self, interaction_state, stt_service=None):
        print("initializing TTS Engine..........")
        self._interaction_state = interaction_state
        self._stt = stt_service
        self._godot = None  # Set via set_godot_bridge()
        self.piper_path = "C:/tom/AI-Talking-Tom/piper/piper.exe"
        self.model_path = "C:/tom/AI-Talking-Tom/models/tts/en_US-lessac-medium.onnx"
        self.output_file = "output.wav"

        # Pre-warm: run a silent synthesis so the model is cached by the OS
        self._warm_up()
        print("TTS Engine ready.... ")

    def _warm_up(self):
        """Pre-load piper once so subsequent calls are faster."""
        try:
            subprocess.run(
                [self.piper_path, "--model", self.model_path,
                 "--output_file", self.output_file],
                input=".",
                text=True,
                capture_output=True,
                timeout=10
            )
            print("[TTS] Piper pre-warmed")
        except Exception as e:
            print(f"[TTS] Warm-up failed (non-critical): {e}")

    def set_godot_bridge(self, bridge):
        """Attach the Godot bridge for animation sync."""
        self._godot = bridge

    def speak(self, text):
        """
        Generate and play speech for the given text.

        Transitions the interaction state through:
            PRODUCING_SPEECH -> SPEAKING -> TURN_COMPLETE

        Pauses STT during playback to prevent self-hearing.
        """
        print(f"TTS RECEIVED: [{text}]")

        # Transition to PRODUCING_SPEECH (synthesis phase)
        self._interaction_state.transition_to(
            InteractionPhase.PRODUCING_SPEECH
        )

        subprocess.run([
            self.piper_path,
            "--model",
            self.model_path,
            "--output_file",
            self.output_file
        ],
            input=text,
            text=True
        )

        # Pause STT before playing audio (prevent self-hearing)
        if self._stt:
            self._stt.pause()

        # Transition to SPEAKING (playback phase)
        self._interaction_state.transition_to(
            InteractionPhase.SPEAKING
        )

        print("TTS STARTING")
        if self._godot:
            self._godot.send_speak(text)
        data, samplerate = sf.read("output.wav")
        sd.play(data, samplerate)
        sd.wait()

        # Transition to TURN_COMPLETE
        self._interaction_state.transition_to(
            InteractionPhase.TURN_COMPLETE
        )

        print("TTS FINISHED")
        if self._godot:
            self._godot.send_speak_end()

        # Resume STT after playback is done
        if self._stt:
            self._stt.resume()
