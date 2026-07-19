print("main.py started")
from stt_service import STTService
from llm_service import LLMService
from tts_service import TTSService
from face_emotion_service import FaceEmotionService
from voice_emotion_service import VoiceEmotionService
from emotion_fusion_service import EmotionFusionService
import time
from emotion_memory_service import EmotionMemoryService
from tom_state_service import TomStateService
from needs_service import NeedsService
from profile_memory_service import ProfileMemoryService
from memory_extraction_service import MemoryExtractionService
from relationship_service import RelationshipService
from memory_decay_service import MemoryDecayService
from memory_metadata_service import MemoryMetadataService
from relationship_prompt_service import RelationshipPromptService
from internal_thought_service import InternalThoughtService
from environment_service import EnvironmentService
from idle_behavior_service import IdleBehaviorService
from idle_event_service import IdleEventService
from interaction_state import InteractionState, InteractionPhase
from event_queue import EventQueue, PRIORITY_CONVERSATION, PRIORITY_ENVIRONMENT
from brain_manager import BrainManager, DecisionAction
from personality_profile_service import PersonalityProfileService
from personality_evolution_service import PersonalityEvolutionService
from personality_balancing_service import PersonalityBalancingService
from user_context_service import UserContextService
from dashboard_api import start_api
from godot_bridge import GodotBridge

# ---------------------------------------------------------------
# Service construction (preserving original startup order)
# ---------------------------------------------------------------

# Coordination layer
interaction_state = InteractionState()
event_queue = EventQueue()

# User context (must be created before user-scoped services)
user_context = UserContextService()

# Perception and environment
environment = EnvironmentService()

# Speech services (now receive interaction_state)
stt = STTService(environment, interaction_state)
stt.start()
llm = LLMService(user_context)
tts = TTSService(interaction_state, stt_service=stt)

# Camera and emotion
face = FaceEmotionService(environment)
face.start()
voice = VoiceEmotionService()
fusion = EmotionFusionService()

# State and memory
memory = EmotionMemoryService(user_context)
tom = TomStateService(user_context)
needs = NeedsService(user_context)
profile = ProfileMemoryService(user_context)
decay = MemoryDecayService()
metadata = MemoryMetadataService()
extractor = MemoryExtractionService()
relationship = RelationshipService(user_context)
relationship_prompt = RelationshipPromptService()
thoughts = InternalThoughtService()
idle = IdleBehaviorService()
idle_events = IdleEventService()

# Personality layer
personality = PersonalityProfileService(user_context)
evolution = PersonalityEvolutionService()
balancing = PersonalityBalancingService()

# Brain Manager — central coordinator
brain = BrainManager(
    interaction_state=interaction_state,
    event_queue=event_queue,
    idle_service=idle,
    idle_event_service=idle_events,
    tom_state=tom,
    needs_service=needs,
    personality_service=personality
)

# ---------------------------------------------------------------
# Dashboard API (background thread)
# ---------------------------------------------------------------

start_api({
    "user_context": user_context,
    "tom": tom,
    "needs": needs,
    "relationship": relationship,
    "personality": personality,
    "emotion_memory": memory,
    "profile": profile,
    "llm": llm,
    "face": face
})

# ---------------------------------------------------------------
# Godot Bridge (background thread)
# ---------------------------------------------------------------

godot = GodotBridge()
godot.start()
tts.set_godot_bridge(godot)

# ---------------------------------------------------------------
# Daily memory decay (unchanged)
# ---------------------------------------------------------------

if metadata.should_decay():
    profile_data = profile.get_profile()
    decay.decay(profile_data)
    decay.remove_forgotten_memories(profile_data)
    decay.save_profile(profile_data, profile.collection, user_context.get_user_id())
    metadata.mark_decay_done()
    print("Daily memory decay completed")


# ---------------------------------------------------------------
# Helper: build relationship context (reused in multiple places)
# ---------------------------------------------------------------

def _build_relationship_context():
    return relationship_prompt.build(
        relationship.trust,
        relationship.friendship,
        relationship.attachment,
        user_context.get_user_name()
    )


# ---------------------------------------------------------------
# Helper: generate event response and submit to speech queue
# ---------------------------------------------------------------

_last_env_event_time = 0
_ENV_EVENT_COOLDOWN = 30  # seconds between environment events

def _submit_environment_event(event_text, face_emotion):
    """Generate an LLM event response and submit it to the speech queue.
    
    Skips if:
    - An environment event was processed recently (cooldown)
    - User started speaking while we were about to generate
    """
    global _last_env_event_time
    
    # Cooldown check
    now = time.time()
    if now - _last_env_event_time < _ENV_EVENT_COOLDOWN:
        return
    
    # Check if user started speaking before we block on LLM
    if stt.is_listening() or stt.is_transcribing():
        return
    
    _last_env_event_time = now
    
    event_response = llm.generate_event(
        event=event_text,
        emotion=face_emotion,
        energy=tom.energy,
        friendliness=tom.friendliness,
        curiosity=tom.curiosity,
        relationship_context=_build_relationship_context()
    )
    print("Tom:", event_response)
    brain.submit_environment_event(event_response)



# ---------------------------------------------------------------
# Helper: process a full conversation turn
# ---------------------------------------------------------------

def _process_conversation_turn(text, audio):
    """
    Process a complete speech-to-response turn.

    Transitions interaction state through:
        PROCESSING_INPUT -> GENERATING_RESPONSE -> (TTS handles the rest)

    Memory extraction is deferred until AFTER the response is spoken
    so the user gets a faster reply.
    """
    interaction_state.transition_to(InteractionPhase.PROCESSING_INPUT)

    # Memory retrieval (fast — just DB lookups, no LLM)
    retrieved_memories = []
    words = text.lower().split()
    for word in words:
        memories = profile.get_top_memories(word)
        for retrieved_memory in memories:
            if retrieved_memory not in retrieved_memories:
                retrieved_memories.append(retrieved_memory)
    retrieved_memories.sort(
        key=lambda x: x["importance"],
        reverse=True
    )
    retrieved_memories = retrieved_memories[:3]
    print("Retrieved Memories:", retrieved_memories)

    # Emotion fusion
    voice_emotion = voice.get_emotion("recording.wav")
    face_emotion = face.get_emotion()
    print("Face Emotion:", face_emotion)
    print("Voice Emotion:", voice_emotion)
    final_emotion = fusion.get_emotion(face_emotion, voice_emotion)

    # State updates
    mood = memory.get_mood(final_emotion)
    personality_traits = personality.get_traits()
    relationship.update_from_conversation(mood)
    tom.update_from_conversation(mood, personality_traits)
    needs.update_from_conversation(personality_traits)

    likes = profile.get_likes()
    dislikes = profile.get_dislikes()
    facts = profile.get_facts()

    print(f"User:{text}")
    print("Current mood:", mood)

    memory_text = [m["value"] for m in retrieved_memories]

    relationship_context = _build_relationship_context()

    internal_thoughts = thoughts.generate(
        tom.energy,
        needs.hunger,
        needs.sleepiness,
        needs.social_need,
        {
            "trust": relationship.trust,
            "attachment": relationship.attachment
        },
        memory_text,
        user_context.get_user_name()
    )

    # LLM response generation
    interaction_state.transition_to(InteractionPhase.GENERATING_RESPONSE)

    response = llm.generate(
        text,
        mood,
        tom.energy,
        tom.friendliness,
        tom.curiosity,
        needs.hunger,
        needs.sleepiness,
        needs.social_need,
        likes,
        dislikes,
        facts,
        relationship.trust,
        relationship.friendship,
        relationship.attachment,
        relationship_context,
        memory_text,
        internal_thoughts,
        environment.objects,
        personality_traits
    )

    print(f"Tom:{response}")

    # TTS speaks (transitions PRODUCING_SPEECH -> SPEAKING -> TURN_COMPLETE)
    tts.speak(response)

    # ---- Post-speech tasks (user already got their response) ----

    # Memory extraction (deferred — runs AFTER response so it doesn't block)
    memory_data = extractor.extract(text)
    for item in memory_data["likes"]:
        profile.add_like(item)
    for item in memory_data["dislikes"]:
        profile.add_dislike(item)
    for item in memory_data["facts"]:
        profile.add_fact(item)

    # Personality evolution
    deltas = evolution.evolve(
        mood,
        {
            "trust": relationship.trust,
            "friendship": relationship.friendship,
            "attachment": relationship.attachment
        },
        memory.history,
        {
            "hunger": needs.hunger,
            "sleepiness": needs.sleepiness,
            "social_need": needs.social_need
        }
    )
    if deltas:
        personality.apply_deltas(deltas)
        balanced = balancing.balance(personality.get_traits())
        current = personality.get_traits()
        for trait_name, balanced_value in balanced.items():
            diff = balanced_value - current[trait_name]
            if diff != 0:
                personality.update_trait(trait_name, diff)
        print("[Personality]", personality.get_traits())

    interaction_state.transition_to(InteractionPhase.IDLE)
    brain.reset_idle_timer()


# ---------------------------------------------------------------
# Helper: execute a speech event from the queue
# ---------------------------------------------------------------

def _execute_speech_event(event):
    """
    Speak a queued event (environment or conversation).
    Manages interaction state transitions for non-conversation speech.
    Event speech skips LISTENING/PROCESSING_INPUT — text is already generated.
    """
    # Mark system as busy — go directly to GENERATING_RESPONSE
    interaction_state.transition_to(InteractionPhase.GENERATING_RESPONSE)

    # TTS handles PRODUCING_SPEECH -> SPEAKING -> TURN_COMPLETE
    tts.speak(event.text)

    # Back to IDLE
    interaction_state.transition_to(InteractionPhase.IDLE)
    godot.send_state("idle")
    brain.reset_idle_timer()


# ---------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------

while True:
    face_emotion = face.get_emotion()
    godot.send_emotion(face_emotion)

    # ----- Check for user speech FIRST (highest priority) -----

    text, audio = stt.get_and_clear()

    if text is not None:
        # User spoke — process immediately, skip everything else
        _process_conversation_turn(text, audio)
        continue

    # ----- Environment events: skip when user is actively speaking -----
    # is_listening() = True only when speech is detected (volume > threshold)
    # is_transcribing() = True during Whisper transcription

    speech_active = stt.is_listening() or stt.is_transcribing()

    if not speech_active:

        if environment.user_returned:
            print("User returned.")
            _submit_environment_event(
                "The user just came back to you.",
                face_emotion
            )
            environment.user_returned = False

        if environment.user_left:
            print("User left.")
            _submit_environment_event(
                "The user just walked away from you.",
                face_emotion
            )
            environment.user_left = False

        if environment.new_objects:
            print("New object detected.")
            _submit_environment_event(
                f"The following object just appeared: "
                f"{', '.join(environment.new_objects)}.",
                face_emotion
            )
            environment.new_objects = []

        if environment.removed_objects:
            print("Object removed.")
            _submit_environment_event(
                f"The following object disappeared: "
                f"{', '.join(environment.removed_objects)}.",
                face_emotion
            )
            environment.removed_objects = []

    # ----- Brain Manager decision cycle (always runs) -----

    decision = brain.decide()

    if decision.action == DecisionAction.SPEAK:
        if not speech_active:
            _execute_speech_event(decision.event)
        else:
            # User is speaking — re-queue, don't interrupt
            event_queue.submit(decision.event)
        continue

    if decision.action == DecisionAction.IDLE_ACTION:
        godot.send_idle(decision.idle_action or "blink")
        continue

    time.sleep(0.1)

