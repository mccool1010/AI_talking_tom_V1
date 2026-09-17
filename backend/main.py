import logging
import logging.handlers
import signal
import sys
import time

import config
import db


def setup_logging():
    config.ensure_runtime_dirs()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_DIR / "tom.log", maxBytes=5 << 20, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(config.LOG_LEVEL.upper())
    root.addHandler(console)
    root.addHandler(file_handler)
    for noisy in ("httpx", "urllib3", "ultralytics", "tensorflow", "h5py", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


log = logging.getLogger("tom")

ENV_EVENT_COOLDOWN = 30          # seconds between environment reactions
DECAY_CHECK_INTERVAL = 3600      # seconds between "has the day changed?" checks


class TomApp:
    def __init__(self):
        from brain_manager import BrainManager
        from dashboard_api import start_api
        from emotion_fusion_service import EmotionFusionService
        from emotion_memory_service import EmotionMemoryService
        from environment_service import EnvironmentService
        from event_queue import EventQueue
        from face_emotion_service import FaceEmotionService
        from godot_bridge import GodotBridge
        from idle_behavior_service import IdleBehaviorService
        from idle_event_service import IdleEventService
        from interaction_state import InteractionState
        from internal_thought_service import InternalThoughtService
        from llm_service import LLMService
        from memory_decay_service import MemoryDecayService
        from memory_extraction_service import MemoryExtractionService
        from memory_metadata_service import MemoryMetadataService
        from needs_service import NeedsService
        from personality_balancing_service import PersonalityBalancingService
        from personality_evolution_service import PersonalityEvolutionService
        from personality_profile_service import PersonalityProfileService
        from profile_memory_service import ProfileMemoryService
        from relationship_prompt_service import RelationshipPromptService
        from relationship_service import RelationshipService
        from stt_service import STTService
        from tom_state_service import TomStateService
        from tts_service import TTSService
        from user_context_service import UserContextService
        from voice_emotion_service import VoiceEmotionService

        db.check_connection()

        # Coordination
        self.interaction_state = InteractionState()
        self.event_queue = EventQueue()
        self.user_context = UserContextService()
        self.environment = EnvironmentService()

        # Speech
        log.info("Loading speech models...")
        self.stt = STTService(self.environment, self.interaction_state)
        self.llm = LLMService(self.user_context)
        self.tts = TTSService(self.interaction_state, stt_service=self.stt)

        # Perception
        log.info("Loading perception models...")
        self.face = FaceEmotionService(self.environment)
        self.voice = VoiceEmotionService()
        self.fusion = EmotionFusionService()

        # State and memory
        self.memory = EmotionMemoryService(self.user_context)
        self.tom = TomStateService(self.user_context)
        self.needs = NeedsService(self.user_context)
        self.profile = ProfileMemoryService(self.user_context)
        self.decay = MemoryDecayService()
        self.metadata = MemoryMetadataService()
        self.extractor = MemoryExtractionService()
        self.relationship = RelationshipService(self.user_context)
        self.relationship_prompt = RelationshipPromptService()
        self.thoughts = InternalThoughtService()
        self.idle = IdleBehaviorService()
        self.idle_events = IdleEventService()

        # Personality
        self.personality = PersonalityProfileService(self.user_context)
        self.evolution = PersonalityEvolutionService()
        self.balancing = PersonalityBalancingService()

        # Every per-user service reloads when the dashboard switches user.
        for service in (self.llm, self.memory, self.tom, self.needs, self.profile,
                        self.relationship, self.personality):
            self.user_context.on_user_changed(service.switch_user)

        self.brain = BrainManager(
            interaction_state=self.interaction_state,
            event_queue=self.event_queue,
            idle_service=self.idle,
            idle_event_service=self.idle_events,
            tom_state=self.tom,
            needs_service=self.needs,
            personality_service=self.personality,
        )

        start_api({
            "user_context": self.user_context,
            "tom": self.tom,
            "needs": self.needs,
            "relationship": self.relationship,
            "personality": self.personality,
            "emotion_memory": self.memory,
            "profile": self.profile,
            "llm": self.llm,
            "face": self.face,
        })

        self.godot = GodotBridge()
        self.tts.set_godot_bridge(self.godot)

        self._last_env_event_time = 0
        self._last_decay_check = 0
        self._last_sent_emotion = None
        self._running = False

    # ---- helpers ----

    def _relationship_context(self):
        return self.relationship_prompt.build(
            self.relationship.trust,
            self.relationship.friendship,
            self.relationship.attachment,
            self.user_context.get_user_name(),
        )

    def run_daily_decay(self):
        self._last_decay_check = time.time()
        if not self.metadata.should_decay():
            return
        changed = self.decay.run_for_all(self.profile.collection)
        self.metadata.mark_decay_done()
        log.info("Daily memory decay completed (%d profiles changed)", changed)

    def submit_environment_event(self, event_text, face_emotion):
        """Generate a reaction to an environment change and queue it for speech."""
        now = time.time()
        if now - self._last_env_event_time < ENV_EVENT_COOLDOWN:
            return
        if self.stt.is_listening() or self.stt.is_transcribing():
            return
        self._last_env_event_time = now
        response = self.llm.generate_event(
            event=event_text,
            emotion=face_emotion,
            energy=self.tom.energy,
            friendliness=self.tom.friendliness,
            curiosity=self.tom.curiosity,
            relationship_context=self._relationship_context(),
        )
        self.brain.submit_environment_event(response)

    # ---- conversation turn ----

    def process_conversation_turn(self, text):
        """
        Speech -> response. PROCESSING_INPUT -> GENERATING_RESPONSE, then TTS
        runs the speaking phases. Memory extraction runs after Tom has spoken.
        """
        from interaction_state import InteractionPhase

        self.interaction_state.transition_to(InteractionPhase.PROCESSING_INPUT)
        log.info("User: %s", text)

        retrieved = self.profile.retrieve(text, limit=3)
        memory_text = [m["value"] for m in retrieved]

        voice_emotion = self.voice.get_emotion(str(config.RECORDING_PATH))
        face_emotion = self.face.get_emotion()
        final_emotion = self.fusion.get_emotion(face_emotion, voice_emotion)
        log.info("Emotion face=%s voice=%s -> %s", face_emotion, voice_emotion, final_emotion)

        mood = self.memory.get_mood(final_emotion)
        traits = self.personality.get_traits()
        self.relationship.update_from_conversation(mood)
        self.tom.update_from_conversation(mood, traits)
        self.needs.update_from_conversation(traits)

        internal_thoughts = self.thoughts.generate(
            self.tom.energy,
            self.needs.hunger,
            self.needs.sleepiness,
            self.needs.social_need,
            {"trust": self.relationship.trust, "attachment": self.relationship.attachment},
            memory_text,
            self.user_context.get_user_name(),
        )

        self.interaction_state.transition_to(InteractionPhase.GENERATING_RESPONSE)
        response = self.llm.generate(
            text,
            mood,
            self.tom.energy,
            self.tom.friendliness,
            self.tom.curiosity,
            self.needs.hunger,
            self.needs.sleepiness,
            self.needs.social_need,
            self.profile.get_likes(),
            self.profile.get_dislikes(),
            self.profile.get_facts(),
            self.relationship.trust,
            self.relationship.friendship,
            self.relationship.attachment,
            self._relationship_context(),
            memory_text,
            internal_thoughts,
            self.environment.objects,
            traits,
            user_name=self.user_context.get_user_name(),
        )

        self.tts.speak(response)

        # ---- after the reply has been spoken ----
        try:
            memory_data = self.extractor.extract(text)
            for item in memory_data["likes"]:
                self.profile.add_like(item)
            for item in memory_data["dislikes"]:
                self.profile.add_dislike(item)
            for item in memory_data["facts"]:
                self.profile.add_fact(item)
        except Exception:
            log.exception("Memory extraction failed")

        deltas = self.evolution.evolve(
            mood,
            {"trust": self.relationship.trust,
             "friendship": self.relationship.friendship,
             "attachment": self.relationship.attachment},
            self.memory.history,
            {"hunger": self.needs.hunger,
             "sleepiness": self.needs.sleepiness,
             "social_need": self.needs.social_need},
        )
        if deltas:
            self.personality.apply_deltas(deltas)
            balanced = self.balancing.balance(self.personality.get_traits())
            current = self.personality.get_traits()
            for name, value in balanced.items():
                if value != current[name]:
                    self.personality.update_trait(name, value - current[name])

        self.interaction_state.transition_to(InteractionPhase.IDLE)
        self.brain.reset_idle_timer()

    def execute_speech_event(self, event):
        """Speak a queued event; its text is already generated."""
        from interaction_state import InteractionPhase

        self.interaction_state.transition_to(InteractionPhase.GENERATING_RESPONSE)
        self.tts.speak(event.text)
        self.interaction_state.transition_to(InteractionPhase.IDLE)
        self.godot.send_state("idle")
        self.brain.reset_idle_timer()

    # ---- main loop ----

    def _check_environment(self, face_emotion):
        env = self.environment
        if env.user_returned:
            env.user_returned = False
            self.submit_environment_event("The user just came back to you.", face_emotion)
        if env.user_left:
            env.user_left = False
            self.submit_environment_event("The user just walked away from you.", face_emotion)
        if env.new_objects:
            objects, env.new_objects = env.new_objects, []
            self.submit_environment_event(
                f"The following object just appeared: {', '.join(objects)}.", face_emotion)
        if env.removed_objects:
            objects, env.removed_objects = env.removed_objects, []
            self.submit_environment_event(
                f"The following object disappeared: {', '.join(objects)}.", face_emotion)

    def _tick(self):
        from brain_manager import DecisionAction

        if time.time() - self._last_decay_check > DECAY_CHECK_INTERVAL:
            self.run_daily_decay()

        face_emotion = self.face.get_emotion()
        if face_emotion != self._last_sent_emotion:
            self.godot.send_emotion(face_emotion)
            self._last_sent_emotion = face_emotion

        # User speech has priority over everything else.
        text, _audio = self.stt.get_and_clear()
        if text is not None:
            self.process_conversation_turn(text)
            return

        speech_active = self.stt.is_listening() or self.stt.is_transcribing()
        if not speech_active:
            self._check_environment(face_emotion)

        decision = self.brain.decide()
        if decision.action == DecisionAction.SPEAK:
            if speech_active:
                self.event_queue.submit(decision.event)  # don't interrupt the user
            else:
                self.execute_speech_event(decision.event)
            return
        if decision.action == DecisionAction.IDLE_ACTION:
            self.godot.send_idle(decision.idle_action or "blink")
            return
        time.sleep(0.1)

    def run(self):
        self._running = True
        self.stt.start()
        self.face.start()
        self.godot.start()
        log.info("Tom is ready.")
        while self._running:
            try:
                self._tick()
            except Exception:
                # One failed turn must not leave Tom deaf: reset and keep going.
                log.exception("Error in main loop; recovering")
                self.interaction_state.force_idle()
                time.sleep(0.5)

    def stop(self):
        self._running = False

    def shutdown(self):
        import llm_provider

        log.info("Shutting down...")
        for step in (self.stt.stop, self.face.stop, self.godot.stop, llm_provider.close):
            try:
                step()
            except Exception:
                log.exception("Error during shutdown")


def main():
    setup_logging()
    try:
        app = TomApp()
    except (db.DatabaseUnavailable, FileNotFoundError) as e:
        log.error("%s", e)
        return 1

    def _handle_signal(signum, frame):
        app.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _handle_signal)

    app.run_daily_decay()
    try:
        app.run()
    finally:
        app.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
