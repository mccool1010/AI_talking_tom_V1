from datetime import datetime, timedelta

from emotion_memory_service import EmotionMemoryService
from emotion_fusion_service import EmotionFusionService
from interaction_state import InteractionPhase, InteractionState
from memory_decay_service import MemoryDecayService
from needs_service import NeedsService
from personality_profile_service import PersonalityProfileService
from profile_memory_service import ProfileMemoryService
from relationship_service import RelationshipService
from tom_state_service import TomStateService
from user_context_service import UserContextService


def test_signup_login_and_wrong_password():
    uc = UserContextService()
    assert uc.signup("bob", "Bob", "hunter22!")
    assert not uc.signup("bob", "Bob", "other-password")
    assert not uc.login("bob", "wrong")
    assert uc.login("bob", "hunter22!")
    assert uc.get_user_id() == "bob" and uc.is_logged_in()


def test_passwordless_account_needs_explicit_permission():
    uc = UserContextService()
    assert not uc.login("default", "")
    assert uc.login("default", "", allow_passwordless=True)


def test_user_switch_notifies_listeners_and_logout_returns_to_default():
    uc = UserContextService()
    seen = []
    uc.on_user_changed(seen.append)
    uc.signup("bob", "Bob", "hunter22!")
    uc.login("bob", "hunter22!")
    uc.login("bob", "hunter22!")  # same user: no second notification
    uc.logout()
    assert seen == ["bob", "default"]
    assert uc.get_user_name() == "Hari"


def test_failing_listener_does_not_break_switch():
    uc = UserContextService()
    uc.on_user_changed(lambda _: 1 / 0)
    uc.set_user("carol", "Carol")
    assert uc.get_user_id() == "carol"


def test_state_services_reload_on_switch(user):
    uc = UserContextService()
    tom = TomStateService(uc)
    needs = NeedsService(uc)
    rel = RelationshipService(uc)
    personality = PersonalityProfileService(uc)
    for service in (tom, needs, rel, personality):
        uc.on_user_changed(service.switch_user)

    tom.update_energy(-60)
    rel.update_trust(20)
    uc.set_user("bob")
    assert tom.energy == 100 and rel.trust == 50
    uc.set_user("default")
    assert tom.energy == 40 and rel.trust > 50
    assert personality.get_traits()["laziness"] == 30
    assert needs.social_need == 50


def test_emotion_history_saved_for_non_default_user(user):
    EmotionMemoryService(user).get_mood("happy")
    assert EmotionMemoryService(user).history == ["happy"]


def test_fusion_rule():
    fusion = EmotionFusionService()
    assert fusion.get_emotion("happy", "happy") == "happy"
    assert fusion.get_emotion("happy", "angry") == "happy"
    assert fusion.get_emotion("neutral", "angry") == "angry"
    assert fusion.get_emotion("neutral", None) == "neutral"


def test_synthesis_failure_can_complete_turn():
    state = InteractionState()
    for phase in (InteractionPhase.PROCESSING_INPUT, InteractionPhase.GENERATING_RESPONSE,
                  InteractionPhase.PRODUCING_SPEECH, InteractionPhase.TURN_COMPLETE,
                  InteractionPhase.IDLE):
        assert state.transition_to(phase), phase
    assert state.can_listen()


def test_force_idle_recovers_stuck_turn():
    state = InteractionState()
    state.transition_to(InteractionPhase.PROCESSING_INPUT)
    assert not state.can_listen()
    state.force_idle()
    assert state.can_listen()


def test_decay_runs_for_every_user(user):
    alice = ProfileMemoryService(user)
    alice.add_fact("Old fact")
    alice.switch_user("bob")
    alice.add_fact("Bob fact")
    old = (datetime.now() - timedelta(days=30)).isoformat()
    alice.collection.update_many({}, {"$set": {"facts.0.last_accessed": old,
                                               "facts.0.importance": 1}})
    changed = MemoryDecayService().run_for_all(alice.collection)
    assert changed == 2
    assert all(doc["facts"] == [] for doc in alice.collection.find({}))
