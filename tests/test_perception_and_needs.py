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
