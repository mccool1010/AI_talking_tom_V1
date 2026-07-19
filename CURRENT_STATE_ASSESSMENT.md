# AI Talking Tom Current Engineering Assessment

## 1. Overall Project Status

AI Talking Tom is currently a functional backend prototype for an autonomous AI companion. The project is not a finished product and it is not yet a production-grade system, but it has crossed the threshold from experimental scaffolding into a credible working runtime. The backend already implements the core loop of perception, listening, memory, emotional context, relationship state, and spoken response. That is a major milestone. The architecture is no longer only a concept; it is an operational system that can run locally, listen to the user, perceive the room, update internal state, remember personal information, and respond in a characterful way.

The current implementation is best described as a high-functioning prototype with a strong architectural skeleton. It is mature enough to demonstrate the central vision of an autonomous pet-like companion, but it still contains several prototype-era shortcuts that would make it fragile in production use. The system depends heavily on local models, local audio devices, and local persistence. It is also tightly coupled to a specific Python runtime setup and to a local MongoDB service. That is acceptable for a research-quality prototype, but it is not yet a robust deployment target.

From an engineering perspective, the project is approximately 70 to 80 percent complete at the backend level. The foundational systems are present. The missing work is largely in hardening, orchestration, integration, and scalability rather than in inventing the basic architecture from scratch. Godot integration has not started, dashboard support has not started, personality growth is not implemented, and multi-user support is not present. Those gaps are important, but they do not change the fact that the current backend is already a significant engineering achievement.

The most important distinction in the current state is the difference between architectural maturity and operational maturity. The architecture is fairly mature in the sense that the core responsibilities are now separated into services, state is persistent, and runtime behavior is coordinated through a central loop. Operational maturity is lower because the system still depends on shared mutable state, blocking operations, and a relatively ad hoc control flow. The backend can do the job it was built for, but it would be risky to treat it as a stable platform for large-scale or long-lived deployment without further hardening.

The project is also fundamentally a venv-first local runtime. It is not designed as a cloud-native service and it is not designed as a general-purpose API. It is a local companion runtime that uses a virtual environment, local model files, and local audio and camera devices. That requirement is important because it shapes how future work should be approached. The system should be treated as a local-first AI runtime with an eventual path toward richer external integration rather than as a general distributed platform from the start.

## 2. Completed Systems

### Speech Recognition

Purpose:
The speech recognition subsystem exists to capture microphone input, detect speech segments, transcribe them, and hand the resulting text to the main runtime for processing.

Current implementation:
The implementation is centered in [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py). The service uses the sounddevice library to collect microphone input, detects volume spikes as a proxy for speech, records audio chunks until silence is detected, writes the result to a local WAV file, and then uses Whisper through the faster-whisper integration to transcribe it.

Architecture:
The STT system is now implemented as a background service with its own thread. It exposes shared state through latest_text and latest_audio and uses a threading.Event to coordinate processing. This is a meaningful step up from a blocking design.

Strengths:
The architecture is responsive enough to keep the application alive while listening. It decouples speech capture from the main runtime loop and allows the system to continue processing context while waiting for speech.

Weaknesses:
The system still uses shared variables rather than a proper queue. It is noise-sensitive. It relies on a simple amplitude threshold. It is not resilient to overlapping speech or interruptions. Its state lifecycle is not fully robust and could be improved with a more explicit state machine.

Known issues:
Speech detection can be brittle. The implementation is sensitive to input volume and background noise. The system can also be interrupted by environment changes or user leaving the camera frame. It is suitable for an interactive prototype but not yet a robust speech runtime.

Scalability:
The subsystem would need a better event protocol and potentially a more advanced speech engine if it were to support multiple microphones or more varied audio contexts.

Future improvements:
A queue-based audio processing system, better VAD logic, more graceful interruption handling, and a more structured event-based handoff would improve this subsystem substantially.

### LLM

Purpose:
The LLM subsystem is the main conversational generation engine. It is responsible for turning the current state, user prompt, memory context, relationship context, internal thoughts, and visible objects into a short characterful reply.

Current implementation:
The implementation is in [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py). It uses a local llama.cpp-backed model loaded from the local model file. It stores conversation history in MongoDB and uses that history in subsequent prompts.

Architecture:
The LLM is treated as a content generation service rather than the owner of state. The main loop assembles the context and passes it in. That is a good architectural separation.

Strengths:
The system is coherent, character-driven, and clearly integrated with the rest of the runtime. It responds to current state, relationship values, and memory context.

Weaknesses:
The prompt is long and increasingly brittle. The system is sensitive to prompt size and prompt formatting. It lacks structured output guarantees beyond simple natural-language generation. It also uses a single fixed conversation history length and no memory summarization.

Known issues:
The model can hallucinate. It can repeat itself. It can be verbose relative to the intended short response style. It also depends strongly on prompt quality.

Scalability:
The current prompt design will become harder to maintain as the system grows. Larger context windows and more structured prompt construction will eventually be required.

Future improvements:
Prompt templates should be modularized. The system should likely move toward structured generation, better context selection, and a more robust conversation-memory policy.

### TTS

Purpose:
The text-to-speech subsystem converts the generated response into audible speech.

Current implementation:
The implementation is in [AI-Talking-Tom/backend/tts_service.py](AI-Talking-Tom/backend/tts_service.py). It calls the Piper executable with the local model and writes the result to a local audio file before playing it.

Architecture:
The TTS service is intentionally simple and synchronous. It is a direct, concrete interface to the local speech engine.

Strengths:
The implementation is easy to understand and works as a straightforward local speech layer.

Weaknesses:
The subprocess call and subsequent playback block the main loop. This is acceptable for a prototype but not for a more responsive runtime.

Known issues:
The system can create audible clipping or unnatural pacing if the generated text is not well shaped. It also blocks the control loop while speaking.

Scalability:
The current approach is not suitable for a future event-driven or multi-agent system that wants speech to be buffered and parallelized.

Future improvements:
The service should eventually be made asynchronous, support queueing, and perhaps support voice profiles or emotional intonation.

### Emotion Detection

Purpose:
The project uses emotion detection to make responses feel attached to the user’s emotional state.

Current implementation:
The current emotion pipeline is split between [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py), [AI-Talking-Tom/backend/voice_emotion_service.py](AI-Talking-Tom/backend/voice_emotion_service.py), and [AI-Talking-Tom/backend/emotion_fusion_service.py](AI-Talking-Tom/backend/emotion_fusion_service.py). Face emotion uses DeepFace and the webcam. Voice emotion uses a transformers-based audio classifier. The fusion layer combines them into a single emotional signal.

Architecture:
The subsystem is modular but still lightweight. It is not a psychologically rigorous model; it is a pragmatic multi-modal affect signal.

Strengths:
The subsystem is clear and useful. It improves the immediacy of the companion experience.

Weaknesses:
The fusion logic is simple and heuristic. The face and voice emotion signals are not robustly weighted or contextualized. The system can be misled by poor lighting, noisy audio, or poor model confidence.

Known issues:
The emotion pipeline can be unstable under difficult conditions. The voice classifier may produce labels that do not map cleanly to the intended emotional categories.

Scalability:
The subsystem would benefit from confidence-based fusion and more sophisticated emotional modeling.

Future improvements:
A more robust affect model, calibration, and per-signal confidence handling would improve this subsystem significantly.

### Environment Awareness

Purpose:
Environment awareness allows Tom to notice whether the user is present, how many people are present, which objects are visible, and whether the environment has changed.

Current implementation:
The environment subsystem is implemented in [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py), with perception support from [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py) and [AI-Talking-Tom/backend/object_detection_service.py](AI-Talking-Tom/backend/object_detection_service.py).

Architecture:
The system uses a simple environment state object and a set of event flags that the main loop consumes. This is a good early implementation of situational awareness.

Strengths:
It is simple, understandable, and immediately increases the feeling of immersion.

Weaknesses:
The event model is very basic. There is no throttling, no event history, and no confidence-based scene update logic.

Known issues:
Object detection can produce flickering labels. Person detection can be unstable. Environment state can change rapidly and create noisy events.

Scalability:
The current approach is fine for a local prototype but would need refinement for a richer embodied system.

Future improvements:
A proper event queue, scene smoothing, persistence of scene context, and richer object semantics are needed.

### Relationship System

Purpose:
The relationship system makes Tom feel socially connected to the user by tracking trust, friendship, and attachment over time.

Current implementation:
The system is implemented in [AI-Talking-Tom/backend/relationship_service.py](AI-Talking-Tom/backend/relationship_service.py) and [AI-Talking-Tom/backend/relationship_prompt_service.py](AI-Talking-Tom/backend/relationship_prompt_service.py).

Architecture:
The system uses simple numeric values stored in MongoDB and injects those values into the prompt context for the LLM.

Strengths:
It improves the sense of continuity and social connection.

Weaknesses:
The model is very coarse and is not yet tied to a richer social or memory model.

Known issues:
Relationship values can change in a simplistic way and are not yet grounded in a richer behavioral model.

Scalability:
The current approach will likely need to become more nuanced as the system becomes more dependent on long-term companionship behavior.

Future improvements:
More expressive social state, episodic interaction history, and relationship memory would be natural extensions.

### Memory System

Purpose:
The memory system allows Tom to remember user facts, likes, dislikes, and profile information.

Current implementation:
The core implementation is in [AI-Talking-Tom/backend/profile_memory_service.py](AI-Talking-Tom/backend/profile_memory_service.py), with extraction handled by [AI-Talking-Tom/backend/memory_extraction_service.py](AI-Talking-Tom/backend/memory_extraction_service.py).

Architecture:
Memory is stored in MongoDB as structured profile entries with importance, learned_at, and last_accessed fields. This is a strong first version of a memory architecture.

Strengths:
The system is structured and persistent. It can reinforce repeated memories and influence future prompts.

Weaknesses:
The memory system still uses simple keyword-based retrieval and a fairly shallow schema. It has no semantic memory, no episodic memory, and no multi-user support.

Known issues:
Memory retrieval can be too literal and can retrieve irrelevant or overly broad items.

Scalability:
The current system will need semantic retrieval or vector-based recall if memory becomes much larger.

Future improvements:
A more expressive memory graph, similarity-based retrieval, and memory summarization are likely next steps.

### Memory Decay

Purpose:
The memory decay system prevents memory from growing forever and makes older or unused facts less prominent over time.

Current implementation:
The system is implemented in [AI-Talking-Tom/backend/memory_decay_service.py](AI-Talking-Tom/backend/memory_decay_service.py) and [AI-Talking-Tom/backend/memory_metadata_service.py](AI-Talking-Tom/backend/memory_metadata_service.py).

Architecture:
The system uses a daily decay pass based on metadata and importance scores.

Strengths:
It makes memory feel less static and more like an evolving internal state.

Weaknesses:
The decay logic is heuristic and not very adaptive.

Known issues:
The system can still over-retain or under-retain information depending on the chosen thresholds.

Scalability:
The present implementation is fine for a prototype but would become more complex if memory volume grows significantly.

Future improvements:
Adaptive forgetting policies and memory type-specific decay would improve realism.

### Internal Thoughts

Purpose:
The internal thought system introduces a hidden motivational layer that subtly influences Tom’s tone and behavior.

Current implementation:
The system is implemented in [AI-Talking-Tom/backend/internal_thought_service.py](AI-Talking-Tom/backend/internal_thought_service.py).

Architecture:
Thoughts are generated from state values and passed into the LLM prompt as hidden context.

Strengths:
It is a lightweight and practical way to create the impression of internal state.

Weaknesses:
It is still a heuristic layer and should not be mistaken for real planning.

Known issues:
The results can be too simplistic and may not meaningfully change response behavior in all cases.

Scalability:
This will likely need a more expressive reasoning layer if the system becomes more deeply autonomous.

Future improvements:
A richer planner, more structured intentions, or a symbolic abstraction layer would improve this subsystem.

### Needs

Purpose:
The needs system gives Tom simple internal drives such as hunger, sleepiness, and social need.

Current implementation:
The subsystem is implemented in [AI-Talking-Tom/backend/needs_service.py](AI-Talking-Tom/backend/needs_service.py).

Architecture:
These values are stored in MongoDB and updated after conversation.

Strengths:
The system is simple and understandable.

Weaknesses:
The needs model is too simple to be highly believable or expressive.

Known issues:
The system can feel arbitrary because the values do not yet map to a deeper biological or emotional model.

Scalability:
It will likely need to expand into a broader set of needs or affective states if the companion becomes more complex.

Future improvements:
A richer internal drives model with curiosity, comfort, boredom, and attention would be a natural step.

### Idle Behaviour

Purpose:
The idle behavior system gives Tom simple autonomous actions when the user is not actively interacting.

Current implementation:
The subsystem is implemented in [AI-Talking-Tom/backend/idle_behavior_service.py](AI-Talking-Tom/backend/idle_behavior_service.py) and [AI-Talking-Tom/backend/idle_event_service.py](AI-Talking-Tom/backend/idle_event_service.py).

Architecture:
The service chooses an action from a small pool based on current state and wraps it in an event object.

Strengths:
This is one of the most important features for making the runtime feel alive.

Weaknesses:
The behavior is currently just an event abstraction. It is not yet mapped to animation or embodied behavior.

Known issues:
The current system can produce repetitive idle actions.

Scalability:
It is a good foundation for a future scheduler and action pipeline.

Future improvements:
A real behavior scheduler and a more sophisticated action selection model would greatly improve this subsystem.

### Profile Memory

Purpose:
Profile memory stores the user’s likes, dislikes, and facts over time.

Current implementation:
The implementation is in [AI-Talking-Tom/backend/profile_memory_service.py](AI-Talking-Tom/backend/profile_memory_service.py).

Architecture:
The service persists memory in MongoDB and updates importance values over time.

Strengths:
This is one of the strongest parts of the backend from a memory-design perspective.

Weaknesses:
It is not yet multi-user and is still heavily tied to a single owner identity.

Known issues:
The code uses hard-coded ownership values such as Hari and default identities.

Scalability:
The current model would need identity-aware storage and better schemas for broader use.

Future improvements:
Multi-user memory, ownership abstraction, and richer memory types would be the next step.

### Conversation Memory

Purpose:
The conversation memory layer preserves recent conversational context so Tom can behave more coherently across turns.

Current implementation:
The implementation is in [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py).

Architecture:
The conversation history is stored in MongoDB and trimmed to the most recent 20 messages.

Strengths:
It is simple and practical.

Weaknesses:
The model is not yet backed by a more sophisticated summarization or retrieval strategy.

Known issues:
History truncation can remove context prematurely.

Scalability:
A smarter memory summarization layer would eventually be necessary.

Future improvements:
Conversation memory should eventually be separated into short-term and long-term memory layers.

### Object Detection

Purpose:
Object detection is used to make Tom aware of visible items in the environment.

Current implementation:
The implementation is in [AI-Talking-Tom/backend/object_detection_service.py](AI-Talking-Tom/backend/object_detection_service.py).

Architecture:
The service uses YOLO and the local model weights.

Strengths:
The subsystem is a practical way to get environment awareness into the runtime quickly.

Weaknesses:
It can produce unstable labels and is not yet connected to a stronger scene understanding model.

Known issues:
Detection confidence thresholds and label stability need attention.

Scalability:
A more structured perception stack would be necessary for richer world understanding.

Future improvements:
Temporal object tracking and object persistence would improve this subsystem greatly.

## 3. Current Architecture Health

The current architecture is healthy in broad strokes. The most important strength is that the system now has clear domain boundaries. Speech, emotion, memory, relationship state, environment state, idle behavior, and speech output each have a dedicated implementation surface. That separation is a major improvement over a monolithic approach and is one of the strongest reasons the project can continue evolving.

The architecture is especially good at handling the following:

- multi-modal interaction through separate perception services
- memory persistence through a dedicated data layer
- stateful personality elements through service-owned state values
- basic autonomy through the idle subsystem
- a clear separation between the main loop and domain services

The architecture is weaker in the following areas:

- state is distributed across many services instead of being unified
- the main loop is still responsible for a large amount of orchestration complexity
- there is no real shared event bus or queue
- the system relies on shared mutable variables in a few key places
- the behavior model is still largely prompt-driven rather than being governed by a dedicated runtime controller

The architecture is therefore strong in modularity but weaker in control flow discipline. It is not yet a formal agent architecture. It is a service-oriented runtime with intelligent prompt composition and stateful services. That is appropriate for the current stage, but it will eventually need a more deliberate coordination layer.

## 4. Threading Assessment

The threading model is functional but still incomplete. The project currently uses a main thread for orchestration and a separate background thread for the face service and for the speech service. This is enough to keep the system responsive, but it creates several architectural concerns.

The current thread responsibilities are:

- Main thread: orchestration, event handling, state updates, LLM calls, TTS calls
- Face thread: camera capture, emotion analysis, object detection, environment updates
- STT thread: microphone capture, speech detection, transcription, shared output handoff

The main issue is that the system depends heavily on shared mutable variables between threads. The face service writes to the environment service, the STT service writes latest_text and latest_audio, and the main loop reads them. That is a workable design for a prototype, but it is fragile. There is no true queue, no ordering guarantee, no message envelope, and no synchronization discipline beyond simple variable access.

The current threading model is sufficient for a prototype and even for a local demo, but it is not sufficient for a more stable or extensible runtime. If the system begins to support more sensors, more agents, more event streams, or a real animation layer, the current approach will become harder to reason about.

The most important improvement would be a queue-based or event-driven communication layer. The current shared-state approach should be treated as a temporary bridge, not a long-term design.

## 5. Service Health Report

| Service | Purpose | Quality | Limitations | Risk | Stability | Maintainability |
|---|---|---|---|---|---|---|
| STTService | Speech capture and transcription | Moderate | Needs better state machine and queue | High | Moderate | Moderate |
| LLMService | Response generation | Moderate | Prompt brittleness and context growth | High | Moderate | Moderate |
| TTSService | Speech playback | Moderate | Blocking and hard-coded paths | Medium | Moderate | High |
| FaceEmotionService | Camera and emotion analysis | Moderate | Heavy runtime cost and noisy detection | High | Moderate | Moderate |
| VoiceEmotionService | Voice affect classification | Moderate | External model and unstable output | Medium | Moderate | Moderate |
| EmotionFusionService | Combine mood signals | Low-Moderate | Overly simple logic | Medium | High | High |
| EnvironmentService | Scene state | Moderate | Very simple event representation | Medium | High | High |
| RelationshipService | Social state | Moderate | Coarse social model | Medium | High | High |
| ProfileMemoryService | User memory | Moderate | Single-owner and shallow retrieval | Medium | Moderate | Moderate |
| MemoryExtractionService | Structured memory extraction | Moderate | Prompt-based and fragile | High | Moderate | Moderate |
| MemoryDecayService | Forgetting logic | Moderate | Heuristic only | Medium | High | High |
| NeedsService | Internal needs | Low-Moderate | Too simple | Medium | High | High |
| IdleBehaviorService | Autonomous actions | Moderate | Action selection is basic | Medium | High | High |
| IdleEventService | Idle event wrapper | Low-Moderate | Not yet connected to real action pipeline | Medium | High | High |
| TomStateService | Core pet state | Moderate | Simple and somewhat hard-coded | Medium | High | High |
| EmotionMemoryService | Mood history | Low-Moderate | Simple moving-history logic | Medium | High | High |

## 6. Current Technical Debt

The project currently carries a broad set of technical debt items. Some are minor quality issues and some are fundamental architectural constraints. The most important ones are listed below.

### Shared variables between threads
Problem:
The speech and face services communicate through shared variables rather than through explicit messages or events.
Impact:
This makes the runtime less predictable and more difficult to debug.
Severity: High
Current workaround:
The main loop reads the shared variables directly.
Ideal solution:
A queue-based event bus or message passing layer.
Difficulty: Medium to High
Priority: High

### Lack of event queue
Problem:
There is no central event queue that represents all runtime events such as speech, user return, object change, idle action, and state update.
Impact:
The system cannot reliably sequence or prioritize events.
Severity: High
Current workaround:
Ad hoc flags and direct checks in the main loop.
Ideal solution:
A formal event pipeline with typed messages and priority ordering.
Difficulty: High
Priority: High

### Temporary synchronization scheme
Problem:
The STT and main loop use a simple event and shared variables to coordinate processing.
Impact:
This is easy to break and difficult to expand.
Severity: High
Current workaround:
The processing_done event and latest_text/latest_audio fields.
Ideal solution:
A queue or a more explicit state machine.
Difficulty: Medium
Priority: High

### Large main loop
Problem:
The main runtime loop is doing too much orchestration and decision-making directly.
Impact:
The control flow is harder to evolve and easier to break.
Severity: Medium
Current workaround:
The loop is kept as the central conductor.
Ideal solution:
A dedicated controller or brain manager layer.
Difficulty: Medium to High
Priority: High

### Prompt size and prompt brittleness
Problem:
The LLM prompt is large and increasingly complex.
Impact:
The quality of responses becomes sensitive to prompt formatting and context length.
Severity: High
Current workaround:
The code passes a long prompt assembled in a single method.
Ideal solution:
Prompt modules, structured context composition, and prompt summarization.
Difficulty: Medium
Priority: High

### Godot placeholder events
Problem:
The idle system currently emits simple events but does not yet have a real bridge to a game or animation engine.
Impact:
The architecture is not yet capable of embodied action.
Severity: Medium
Current workaround:
The current event format is a simple action packet.
Ideal solution:
A typed event protocol and transport layer.
Difficulty: Medium
Priority: Medium

### Idle scheduling
Problem:
Idle behavior is time-based and simple, but not yet scheduled in a richer or more adaptive way.
Impact:
The system can be repetitive or poorly timed.
Severity: Medium
Current workaround:
A single idle timer in the main loop.
Ideal solution:
A scheduler with priorities and action durations.
Difficulty: Medium
Priority: Medium

### Database coupling and hard-coded identity
Problem:
The project uses hard-coded owner and tom identifiers and assumes a local MongoDB deployment.
Impact:
This limits multi-user potential and makes the system less portable.
Severity: Medium
Current workaround:
Single default documents and hard-coded identity values.
Ideal solution:
Identity-aware storage and configuration.
Difficulty: Medium
Priority: Medium

### Hard-coded runtime paths
Problem:
Several services assume specific absolute file paths such as local model locations and executables.
Impact:
The project is less portable and harder to run in another environment.
Severity: Medium
Current workaround:
The paths are fixed in code.
Ideal solution:
Configuration files and environment-based path resolution.
Difficulty: Low to Medium
Priority: Medium

### TTS blocking behavior
Problem:
TTS playback blocks the runtime loop until speech finishes.
Impact:
The system feels less responsive and cannot easily overlap speech with other actions.
Severity: Medium
Current workaround:
The runtime waits for playback to finish.
Ideal solution:
Asynchronous playback and speech queueing.
Difficulty: Medium
Priority: Medium

### STT/TTS overlap
Problem:
The speech system and TTS system are not yet coordinated in a robust way for overlapping events.
Impact:
The system can become awkward during fast interactions.
Severity: Medium
Current workaround:
The loop processes one turn at a time.
Ideal solution:
A turn manager or interaction scheduler.
Difficulty: Medium
Priority: Medium

### Object detection stability
Problem:
Object labels can flicker or be unstable due to frame-based detection noise.
Impact:
The environment system can produce spurious events.
Severity: Medium
Current workaround:
The system uses simple set comparisons to detect changes.
Ideal solution:
Temporal smoothing and object tracking.
Difficulty: Medium
Priority: Medium

### Environment event throttling
Problem:
Environment events are not throttled or aggregated.
Impact:
The system can overreact to rapid scene changes.
Severity: Medium
Current workaround:
The state is updated directly and consumed immediately.
Ideal solution:
Event filtering and debounce logic.
Difficulty: Medium
Priority: Medium

### Logging quality
Problem:
The project uses print-based logging and does not yet have a structured logging layer.
Impact:
Debugging and monitoring are harder than they should be.
Severity: Medium
Current workaround:
Console logging.
Ideal solution:
Structured logger with levels and sinks.
Difficulty: Low
Priority: Medium

### Configuration management
Problem:
The project relies heavily on embedded defaults and hard-coded paths.
Impact:
The runtime is harder to configure and more fragile across machines.
Severity: Medium
Current workaround:
The services set defaults at initialization.
Ideal solution:
A configuration module or YAML/JSON configuration layer.
Difficulty: Low to Medium
Priority: Medium

### Model loading cost
Problem:
Large models are loaded on startup and can add substantial initialization cost.
Impact:
The system feels heavier than necessary and is less convenient to start.
Severity: Medium
Current workaround:
Models are loaded during service construction.
Ideal solution:
Lazy loading, caching, or optional startup profiles.
Difficulty: Medium
Priority: Medium

## 7. Known Bugs

The following issues are either visible from the current implementation or are highly likely to appear during regular use of this backend.

### Repeated idle actions
Cause:
The idle behavior service avoids repeating the immediately previous action, but the selection logic remains simple and can still produce repetitive behavior.
Symptoms:
The system may repeat similar actions in a short window.
How to reproduce:
Leave the system idle for a long period with stable state values.
Temporary workaround:
Increase the cooldown or reduce the action pool.
Permanent fix:
Introduce a more structured action scheduler with recency and state-based constraints.

### Speech detection edge cases
Cause:
The STT service uses a threshold on average amplitude and a fixed silence duration.
Symptoms:
The system can miss quiet speech or falsely trigger on noise.
How to reproduce:
Test in a noisy environment or with soft speech.
Temporary workaround:
Increase the microphone gain or lower background noise.
Permanent fix:
Use a proper voice activity detection system or more advanced audio segmentation.

### STT interruption and cancellation
Cause:
The STT service can be interrupted by the environment state and will return early when the user leaves.
Symptoms:
The system may drop a partially transcribed utterance.
How to reproduce:
Walk out of view during speech capture.
Temporary workaround:
Avoid relying on long utterances when user presence is unstable.
Permanent fix:
Introduce a more robust turn management and cancellation policy.

### TTS blocking
Cause:
The TTS service plays audio synchronously.
Symptoms:
The main loop pauses while speech is playing.
How to reproduce:
Trigger speech repeatedly or start another event while speech is in progress.
Temporary workaround:
Keep responses short.
Permanent fix:
Use an asynchronous speech queue.

### Synchronization issues between threads
Cause:
The speech and camera threads update shared state while the main loop reads it.
Symptoms:
State may appear inconsistent or arrive out of order.
How to reproduce:
Run the system while moving quickly between speech and environment changes.
Temporary workaround:
Keep state updates simple and avoid relying on rapid event ordering.
Permanent fix:
Use a message queue or event bus.

### Object flicker
Cause:
Object detection is frame-based and the labels can fluctuate from frame to frame.
Symptoms:
Objects appear and disappear rapidly.
How to reproduce:
Point a camera at a cluttered scene with moving objects.
Temporary workaround:
Use a simple debounce or ignore unstable labels.
Permanent fix:
Temporal tracking and confidence smoothing.

### Memory duplication
Cause:
Profile memory inserts new entries when it does not find an exact normalized match.
Symptoms:
The system may store similar facts as separate memories.
How to reproduce:
Repeat similar user statements with minor wording differences.
Temporary workaround:
Normalize or canonicalize user input before storage.
Permanent fix:
Use better matching and normalization strategies.

### Prompt repetition
Cause:
The prompt context is assembled from many sources including memory, relationship state, and internal thoughts, and the conversation can become repetitive.
Symptoms:
Tom may repeat the same phrasing or topic structure.
How to reproduce:
Use the system for several turns with the same state.
Temporary workaround:
Trim context or vary prompt structure.
Permanent fix:
Add stronger prompt diversity and memory summarization.

### LLM hallucinations
Cause:
The model is being asked to do many things in a compact prompt and may hallucinate or overgeneralize.
Symptoms:
Responses may contain invented details or overconfident statements.
How to reproduce:
Ask ambiguous or highly contextual questions.
Temporary workaround:
Keep prompts constrained and short.
Permanent fix:
Structured generation and stricter context control.

## 8. Current Performance Analysis

### CPU usage
The backend is CPU-intensive because it runs local speech transcription, local LLM inference, camera processing, object detection, and emotion analysis. The system is feasible on a developer machine but will not be lightweight. The heaviest CPU cost comes from the camera and object detection pipeline and from local LLM inference.

### RAM usage
The runtime uses a noticeable amount of memory because it loads several models and keeps the runtime state alive in memory. The biggest memory cost is from the local LLM and the transformers-based voice model. The camera pipeline also has some overhead.

### Model loading
Model loading occurs on service initialization. That makes startup slower and more sensitive to hardware. The runtime would benefit from lazy loading or more explicit startup configuration.

### MongoDB impact
MongoDB is used lightly but effectively. The current usage pattern involves repeated writes for state, memory, and conversation updates. The system does not yet use a complex query pattern, so the database is not a major bottleneck. However, it will become more significant as memory grows.

### Whisper
The Whisper transcription stage is one of the more expensive inference steps and can create noticeable latency. It is acceptable for a local demo but should be considered a performance bottleneck.

### LLM
The LLM is the biggest source of conversational latency. The prompt is large and the model is a local model rather than a cloud endpoint. This latency is acceptable for a prototype but should be treated as a primary performance bottleneck for further scaling.

### Camera processing
Camera processing is expensive because each frame is analyzed for emotion and object detection. This is acceptable for a single camera but becomes less practical with more sensors or more complex vision pipelines.

### Object detection
Object detection is comparatively expensive and can create lag if used continuously on every frame. It is likely the most expensive vision operation in the current runtime.

### Idle system
The idle system is lightweight and contributes very little to overall performance cost.

### Speech latency
Speech latency depends heavily on microphone quality, transcription quality, and model load cost. It is acceptable for a local prototype but not ideal.

### Response latency
The overall response loop is not extremely fast. The dominant cost is the combination of speech recognition, memory extraction, LLM generation, and TTS playback. The system is suitable for interactive personal use but not for low-latency, high-throughput deployment.

## 9. Code Quality Assessment

The code quality is decent for a research prototype but not yet polished for long-term engineering work. The project is readable and understandable, and the service boundaries are mostly clear. The biggest weakness is that the implementation has many places where practicality was prioritized over elegance. That is understandable, but it does mean the codebase is not yet fully consistent in style, structure, and error handling.

### Strengths
The codebase is readable. It uses straightforward classes. The services are conceptually separated. The main orchestrator is easy to follow. The state and persistence layers are easy to locate.

### Weaknesses
The code uses many print statements. There is inconsistent formatting. There is limited error handling around external dependencies. There is little environment configuration. There are hard-coded paths and values. The code is sometimes too procedural and could benefit from clearer abstractions around state transitions.

### Naming
Naming is generally understandable, but some class and method names reflect the early exploratory stage of the project rather than a mature engineering style.

### Comments
Comments are present but sparse and sometimes inconsistent. The code would benefit from more explanatory comments around critical design decisions.

### Service separation
This is one of the strongest parts of the codebase. The services have reasonably clear ownership boundaries.

### Function size
Some methods are large and do many things. The main loop is the clearest example. That is a maintainability concern.

### Error handling
The current error handling is minimal. Many service methods will fail loudly or fall back in a simplistic way rather than providing structured recovery.

### Logging
Logging is currently mostly print-based and not structured. This makes debugging harder and makes the runtime less suitable for long-term monitoring.

### Configuration
Configuration is insufficient. The project relies on defaults embedded in code rather than a configuration layer.

## 10. Security Assessment

The project is not yet a security-critical system, but there are still several areas where security concerns should be acknowledged.

### MongoDB
MongoDB is currently used locally and without a hardened configuration. The project assumes a local deployment and does not yet implement authentication or access control concerns beyond local access.

### File handling
The system writes and reads local audio files and model outputs. That is acceptable for a local prototype, but file operations should be better managed and isolated.

### Prompt injection
The project accepts user text directly into the LLM prompt. That means prompt injection is possible in principle. The current character instructions help reduce the risk, but the system should not assume that user text is safe or fully trustworthy.

### Unsafe inputs
The system does not yet sanitize or constrain all user inputs before they enter the prompt and memory extraction logic.

### Thread safety
The current threading model is not heavily hardened against unsafe shared access. That is a concurrency concern more than a security concern, but it matters for robustness.

### Future authentication and multi-user security
These areas are not implemented. They should be planned before the system supports multiple users or remote access.

## 11. Scalability Assessment

The current architecture can support a single local user and a single local companion instance fairly well. It cannot yet support the more ambitious future targets without substantial architectural changes.

### Multiple users
Not supported. The system assumes a single hard-coded owner and a single default Tom identity.

### Larger models
The architecture can likely support larger models, but the runtime cost will increase significantly. The system is currently designed around local inference and may need load management if the model grows.

### More cameras
The camera subsystem is not yet built for multi-camera or multi-sensor support.

### Godot integration
The architecture is not yet ready for a real Godot bridge. It needs an event protocol and a transport abstraction.

### Cloud deployment
The current design is not cloud-native. It would need configuration management, service abstraction, networking, and possibly containerization.

### Remote APIs
The system is not designed around remote APIs or microservices. It would need a more formal service boundary if it were to be distributed.

### Plugins or additional sensors
The architecture could support them, but only if the runtime is refactored to support richer event streams and external integration.

## 12. Production Readiness

The current project is not suitable for production release in its present form. It is a strong prototype and a good foundation for a future product, but it still fails several tests that a production-grade system would need to pass.

Blocking issues include:
- lack of robust configuration management
- hard-coded paths and identity values
- weak threading discipline
- absence of an event queue
- lack of formal error recovery and logging
- no real authentication or multi-user security scheme
- no Godot integration layer
- no full testing infrastructure
- no graceful shutdown or lifecycle management

The project is, however, suitable for continued development and local demonstrations. It is already good enough to show the vision of the system to others and to validate that the overall architecture is viable.

Estimated engineering effort to reach a more robust release candidate:
- Moderate for a polished local prototype
- High for a production-quality, multi-user, multi-sensor companion runtime

## 13. Future Improvements

### Minor Improvements
- Add configuration files for model paths, MongoDB connection strings, and camera settings
- Replace print-based logging with structured logging
- Improve error handling around missing dependencies
- Normalize memory entries before insertion
- Add simple input validation for prompts and memory text
- Improve the idle action selection model with cooldowns and state-aware variety

### Medium Improvements
- Introduce a central event queue or message bus
- Refactor the main loop into a more explicit controller layer
- Make TTS asynchronous
- Improve the environment event model with debounce and confidence-based filtering
- Create a clearer turn manager for speech and response coordination
- Add more structured prompt composition and prompt templates

### Major Architectural Improvements
- Introduce a Brain Manager or Agent Controller layer
- Move from shared-state communication to message-driven communication
- Add a formal action system and event schema
- Create a Godot connector and action protocol
- Support multi-user identity and ownership separation
- Develop a more expressive memory architecture and richer personality model

## 14. High Priority Tasks

| Priority | Task | Difficulty | Risk | Why it matters |
|---|---|---|---|---|
| 1 | Introduce a queue-based event system | High | High | This is the biggest architectural improvement for reliability |
| 2 | Refactor the main loop into a controller layer | Medium | Medium | Reduces complexity and improves maintainability |
| 3 | Make TTS asynchronous | Medium | Medium | Removes a key responsiveness bottleneck |
| 4 | Improve STT state handling and audio buffering | Medium | Medium | Makes speech interaction more robust |
| 5 | Add configuration management | Low | Low | Improves portability and future deployment |
| 6 | Add structured logging and diagnostics | Low | Low | Makes debugging far easier |
| 7 | Harden memory normalization and duplication handling | Medium | Medium | Improves memory quality |
| 8 | Add event throttling and scene smoothing | Medium | Medium | Reduces noisy environment state |
| 9 | Create a real Godot communication bridge | High | High | Enables embodiment and future visual integration |
| 10 | Refactor identity handling for multi-user support | High | High | Necessary for broader product ambitions |

## 15. Files That Should Never Be Modified Carelessly

### [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)
Why critical:
This file is the current orchestration center. It coordinates the runtime loop and state flow. Changing it carelessly can affect the entire behavior model.
Risks:
It is tightly coupled to the current service architecture and the order of runtime operations.
Safe practices:
Change it only when the orchestration model itself is being refactored and preserve the existing service contract.

### [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
Why critical:
This service owns the speech capture loop and state transitions.
Risks:
It is one of the most concurrency-sensitive parts of the project.
Safe practices:
Treat it as a high-risk service and change it with an event model in mind.

### [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
Why critical:
This is the main response generator and influences almost every conversation.
Risks:
Prompt changes can dramatically alter behavior.
Safe practices:
Refactor carefully and preserve the service interface.

### [AI-Talking-Tom/backend/profile_memory_service.py](AI-Talking-Tom/backend/profile_memory_service.py)
Why critical:
This service owns the memory schema and retrieval behavior.
Risks:
Changes here can invalidate the current memory semantics.
Safe practices:
Preserve the current document shape unless the schema is being intentionally upgraded.

### [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py)
Why critical:
This service defines the runtime’s situational state.
Risks:
Changes here affect the environment event flow.
Safe practices:
Keep changes consistent with the existing event model.

## 16. Refactoring Candidates

The following files are good candidates for future refactoring.

### [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)
Why:
It is still too large and too responsible for orchestration details.
Suggested future architecture:
A controller or brain manager with event-driven subroutines.

### [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
Why:
It mixes audio capture, buffering, transcription, and state handoff.
Suggested future architecture:
Separate listening, buffering, transcription, and event emission layers.

### [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
Why:
The prompt assembly is large and highly coupled to the current runtime context.
Suggested future architecture:
Prompt templates, context builder objects, and structured generation helpers.

### [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py)
Why:
It contains image capture, object detection, emotion inference, and state updates in one place.
Suggested future architecture:
Separate perception modules and a perception manager.

## 17. Current Readiness for Future Phases

### Phase 21
Readiness: Partial
The backend is ready for some of the groundwork of a future phase, but it still needs better event handling and configuration management.

### Phase 22
Readiness: Partial
The architecture is ready for more advanced behavior logic, but it needs a stronger control layer.

### Phase 23
Readiness: Partial
The project is not yet ready for broad integration work until the event and runtime architecture are hardened.

### Phase 24
Readiness: Low
The current project is not ready for full embodied or multi-user integration without a stronger runtime abstraction.

## 18. Engineering Recommendations

If a new engineering team took over this project tomorrow, the first actions should be:

1. Make the runtime configurable.
2. Add structured logging.
3. Introduce an event pipeline or queue.
4. Refactor the main loop into a controller layer.
5. Preserve the existing service boundaries while improving coordination.
6. Keep the current service architecture unless a deeper redesign is absolutely necessary.

The team should avoid:
- rewriting the whole architecture at once
- replacing the current services without a migration plan
- making the LLM the owner of core state
- introducing a distributed microservice architecture prematurely

## 19. Risk Analysis

| Risk | Likelihood | Impact | Mitigation | Monitoring |
|---|---|---|---|---|
| Threading bugs | High | High | Event queue and stronger synchronization | Runtime logs and stress testing |
| Prompt instability | High | Medium | Prompt modularization | Response quality review |
| Memory quality degradation | Medium | Medium | Normalization and retrieval improvements | Memory inspection tools |
| Environment noise | High | Medium | Scene smoothing and event filtering | Visual behavior logs |
| Deployment friction | High | Medium | Configuration and path management | Setup checklist |
| Godot integration drift | Medium | High | Define a clear action protocol early | Interface mockups and contract tests |

## 20. Current Project Scorecard

| Area | Score | Assessment |
|---|---:|---|
| Architecture | 8/10 | Good modular structure, but coordination is still too ad hoc |
| Maintainability | 6/10 | Understandable but still too tightly coupled in the main loop |
| Readability | 7/10 | Clear service structure, but many shortcuts and print-based flows |
| Scalability | 4/10 | Good for a prototype, not for a larger multi-user or multi-sensor system |
| Performance | 5/10 | Functional but constrained by local models and perception cost |
| AI Quality | 6/10 | Characterful and coherent, but prompt-driven and somewhat brittle |
| Memory | 7/10 | Strong first version, but still shallow and single-user |
| Relationships | 6/10 | Good initial social model, but coarse |
| Environment | 6/10 | Useful and immersive, but unstable and simplistic |
| Threading | 5/10 | Functional but not yet robust enough for long-term growth |
| Testing | 3/10 | Minimal structured testing is present |
| Documentation | 7/10 | The project is now better documented than before, but still not fully self-explanatory |
| Godot Readiness | 2/10 | Not yet started |

## If another AI coding agent continues this project...

The first thing to understand is that this project is currently a local-first AI companion runtime, not a general web service or a polished application. The architecture is mostly service-oriented and stateful, but it still uses a fairly direct style of coordination. The safest way to continue development is to preserve the current service boundaries and improve the runtime coordination layer in a controlled way.

Dangerous modifications include:
- replacing the main orchestration flow without preserving the current behavioral contract
- changing the memory schema without a migration path
- introducing a new threading model without replacing the underlying shared-state assumptions
- changing the LLM prompt contract without validating how the rest of the runtime depends on it

Safe extension points include:
- adding a configuration module
- introducing a queue-based event system
- creating a dedicated controller layer
- improving the environment and idle event protocols
- adding tests around the service interfaces

Files to study first:
1. [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)
2. [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
3. [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
4. [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py)
5. [AI-Talking-Tom/backend/profile_memory_service.py](AI-Talking-Tom/backend/profile_memory_service.py)

Recommended reading order:
1. main orchestration
2. perception services
3. state and memory services
4. LLM and TTS services
5. idle and environment behavior

Testing checklist before making changes:
- verify the venv environment is active
- verify model files exist
- verify MongoDB is available
- verify microphone and camera access if relevant
- verify the current main loop still starts and runs in the expected local environment

Required architectural understanding:
The project is not just a chat bot. It is a stateful companion runtime that depends on a layered architecture of perception, memory, social state, and autonomy. Any major change should preserve that alignment.
