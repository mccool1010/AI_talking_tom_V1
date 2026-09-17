import sys
import types

from needs_service import NeedsService
from tom_state_service import TomStateService


def test_voice_label_needs_confidence(monkeypatch):
    # voice_emotion_service imports transformers; a stub keeps this test light.
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(pipeline=None))
    from voice_emotion_service import pick_emotion
    assert pick_emotion({"angry": 0.58, "neutral": 0.38, "happy": 0.04}, 0.7) == "neutral"
    assert pick_emotion({"angry": 0.95, "neutral": 0.05}, 0.7) == "angry"
    assert pick_emotion({"happy": 0.7, "neutral": 0.3}, 0.7) == "happy"


def test_needs_recover_while_tom_is_alone(user):
    needs = NeedsService(user)
    needs.hunger, needs.sleepiness, needs.social_need = 100, 100, 0
    needs.recover(now=needs.updated_at + 2 * 3600)
    assert (needs.hunger, needs.sleepiness, needs.social_need) == (70, 60, 20)
    needs.recover(now=needs.updated_at + 100 * 3600)
    assert (needs.hunger, needs.sleepiness, needs.social_need) == (0, 0, 100)


def test_recovery_is_persisted_and_applied_on_load(user, mongo):
    needs = NeedsService(user)
    needs.update_hunger(90)
    needs.collection.update_one({"tom_id": user.user_id},
                                {"$set": {"updated_at": needs.updated_at - 3600}})
    reloaded = NeedsService(user)
    assert 74 <= reloaded.hunger <= 76


def test_energy_recovers_over_time(user):
    tom = TomStateService(user)
    tom.update_energy(-100)
    tom.recover(now=tom.updated_at + 1800)
    assert tom.energy == 10
    tom.recover(now=tom.updated_at + 10 * 3600)
    assert tom.energy == 100


def test_speech_envelope_follows_loudness(monkeypatch):
    import numpy as np
    for name in ("sounddevice", "soundfile"):
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace())
    from tts_service import speech_envelope
    sr = 16000
    t = np.arange(sr) / sr
    audio = np.sin(2 * np.pi * 220 * t) * (t < 0.5)  # 0.5 s tone, then silence
    env = speech_envelope(audio, sr, fps=20)
    assert len(env) == 20
    assert min(env[2:9]) > 0.8                    # mouth open while the tone plays
    assert all(v == 0.0 for v in env[16:])        # and closed again in the silence
    assert all(b <= a for a, b in zip(env[10:], env[11:]))  # closes smoothly
    assert speech_envelope(np.zeros(100), sr) == []


def _stt_module(monkeypatch):
    for name in ("sounddevice", "faster_whisper", "scipy", "scipy.io", "scipy.io.wavfile"):
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace(WhisperModel=None, write=None))
    import stt_service
    return stt_service


def test_transcript_filter_drops_noise_and_hallucinations(monkeypatch):
    stt = _stt_module(monkeypatch)
    seg = lambda text, nsp=0.1, lp=-0.3: types.SimpleNamespace(text=text, no_speech_prob=nsp, avg_logprob=lp)
    assert stt.clean_transcript([seg(" So")], speech_seconds=0.4) == ""
    assert stt.clean_transcript([seg(" Thank you.")], speech_seconds=0.6) == ""
    assert stt.clean_transcript([seg(" Thank you.")], speech_seconds=1.5) == "Thank you."
    assert stt.clean_transcript([seg(" I'm fine,"), seg(" really.")], speech_seconds=2.0) == "I'm fine, really."
    assert stt.clean_transcript([seg(" Hello"), seg(" music", nsp=0.9, lp=-1.2)], 1.2) == "Hello"
