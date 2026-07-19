# Project Stabilization Plan

## Purpose

This document defines the official stabilization plan for the AI Talking Tom project before future development continues. The objective is not to redesign the system, replace its service-oriented structure, or introduce a fundamentally different architecture. The objective is to harden the current architecture, close critical coordination gaps, and make the existing runtime more reliable, deterministic, and maintainable.

This plan is written for a professional engineering team and is intended to serve as the working reference for the next implementation phase. All recommendations preserve the current service-based design, current data flow, existing runtime responsibilities, and the existing project structure.

## Guiding Principles

The stabilization effort will follow these principles:

- Preserve the current service-oriented architecture.
- Preserve existing services and their responsibilities.
- Preserve current runtime data flow wherever possible.
- Introduce coordination mechanisms rather than replacing the underlying architecture.
- Maintain backward compatibility with the current conversational loop.
- Improve reliability, synchronization, and decision-making without disrupting the core experience.

---

## Problem 1: STT and TTS Synchronization

### Problem

The speech-to-text subsystem was recently moved into a background thread to improve responsiveness. This was a positive architectural change, but the overall conversation pipeline still lacks a complete synchronization model. As a result, the system can begin listening again before the prior interaction has fully completed, creating invalid conversational states.

### Severity

Critical

### Background

The project originally relied on a more direct, blocking speech flow. The STT subsystem has since been redesigned to operate in its own thread, which improves responsiveness but also introduces timing and coordination issues. The architecture now includes multiple stages of processing: speech capture, transcription, conversation processing, LLM response generation, TTS playback, and then a return to listening.

The problem is not that the system is incapable of handling conversations. The problem is that the state transitions between these stages are not yet fully governed by a shared synchronization mechanism. The project now needs an explicit contract that says when the system may listen and when it must remain idle.

### Current Behaviour

The STT thread can begin a new listening cycle while the previous interaction is still in progress. This can happen when the previous conversation is still processing speech, still generating an LLM reply, or still producing spoken output. In practice, the system may become receptive too early and can overlap new speech input with an active or recently completed interaction.

This creates inconsistent user experiences such as:

- Tom listening while still speaking
- Tom hearing overlapping user input during response generation
- Tom entering a new speech turn before the previous turn has fully finished
- The conversation state becoming ambiguous due to partial overlap

### Why It Happens

The issue occurs because the current architecture has improved concurrency but not yet introduced a complete interaction state machine. The STT service runs independently and updates shared state, while the main conversation loop continues to process turns. There is no explicit guard that prevents the system from returning to listening until the entire interaction sequence has completed.

In short, the system has parallelism but not full sequencing discipline.

### Why It Is A Problem

This issue undermines the reliability of the entire conversation loop. A conversational agent must not only process input correctly, but also maintain a clear and stable interaction boundary between turns. Without that boundary, the system can behave incoherently, generate responses at the wrong time, or accept input when it should be silent.

This problem is especially important because it affects the basic trustworthiness of the system. If Tom appears to interrupt itself, respond too early, or listen while busy, the illusion of a coherent companion breaks down.

### Current Architecture

The current architecture consists of the following flow:

1. The STT service captures audio and transcribes speech in a background thread.
2. The main loop reads the latest transcription from shared state.
3. The conversation pipeline processes the speech input.
4. The LLM generates a response.
5. The TTS service produces spoken output.
6. The system returns to a listening state.

The current architecture uses shared state and asynchronous processing, but it does not yet enforce a formal interaction state across the entire pipeline. This is the gap that must be closed.

### Desired Behaviour

Tom must never listen while any of the following is active:

- processing speech
- generating an LLM response
- generating speech
- speaking

Listening should only resume after the complete interaction has finished.

The system should behave as if the conversational turn is a single atomic unit. Once a turn begins, the system should remain in a non-listening state until the turn has fully completed.

### Detailed Solution

The solution is to introduce a shared interaction-state synchronization layer that governs the full conversation lifecycle. The synchronization mechanism should be applied across the STT, main conversation pipeline, LLM, and TTS stages.

This should not be implemented as a loose set of timing checks. It should be structured as a controlled state transition system with explicit states such as:

- Idle
- Listening
- ProcessingInput
- GeneratingResponse
- ProducingSpeech
- Speaking
- TurnComplete

The STT service should not be allowed to start a new listening cycle unless the system is currently in a listening-capable state. The main conversation pipeline should mark the system as busy when it begins processing a turn. The LLM and TTS stages should maintain that busy state until their work is complete. Only after the full chain has completed should the system transition back to listening.

The synchronization mechanism should be thread-safe and should be implemented in a way that prevents race conditions between background processing and the main runtime loop.

### Implementation Strategy

The implementation should be conservative and incremental. The stabilization work should preserve the current service boundaries and add a coordination mechanism at the orchestration boundary.

The recommended strategy is:

1. Define a shared interaction state object that represents the lifecycle of a single conversational turn.
2. Introduce a guard that prevents the STT service from starting or continuing while the system is in a busy state.
3. Update the main conversation loop to transition the interaction state at each major stage.
4. Ensure the TTS service and LLM service participate in the same lifecycle contract.
5. Ensure state transitions are clearly defined and reversible.
6. Add diagnostics that show the current interaction phase for debugging and validation.

The important design point is that the coordination should be centralized around the current main execution flow rather than distributed across independent services.

### Files That Will Change

- [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)
- [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
- [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
- [AI-Talking-Tom/backend/tts_service.py](AI-Talking-Tom/backend/tts_service.py)
- [AI-Talking-Tom/backend/tom_state_service.py](AI-Talking-Tom/backend/tom_state_service.py)

### Files That Must NOT Change

- [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py)
- [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py)
- [AI-Talking-Tom/backend/relationship_service.py](AI-Talking-Tom/backend/relationship_service.py)
- [AI-Talking-Tom/backend/profile_memory_service.py](AI-Talking-Tom/backend/profile_memory_service.py)
- [AI-Talking-Tom/backend/needs_service.py](AI-Talking-Tom/backend/needs_service.py)
- [AI-Talking-Tom/backend/idle_behavior_service.py](AI-Talking-Tom/backend/idle_behavior_service.py)
- [AI-Talking-Tom/backend/idle_event_service.py](AI-Talking-Tom/backend/idle_event_service.py)

### Implementation Steps

1. Review the current STT and main loop interaction points.
2. Define the interaction lifecycle states.
3. Add a shared coordination state to the main runtime path.
4. Update STT to respect the busy state.
5. Update the conversation pipeline so that it marks the runtime as busy during turn processing.
6. Update LLM and TTS stages to participate in the same state transition model.
7. Add observability around the current state so it can be inspected during runtime.
8. Validate that the system cannot re-enter listening until the full turn is complete.

### Potential Risks

- Introducing a lock or state guard that accidentally blocks legitimate behavior
- Creating deadlocks if the busy state is not released correctly
- Breaking the current turn flow due to state transition ordering mistakes
- Creating race conditions if STT updates are not handled carefully

### Testing Procedure

Testing should validate the complete interaction lifecycle end to end.

The test procedure should include:

1. Trigger speech input while the system is idle.
2. Verify that the system enters a busy state immediately after speech is detected.
3. Verify that the system does not start a new listening cycle while the LLM is generating a response.
4. Verify that the system does not re-enter listening while TTS is speaking.
5. Verify that listening resumes only after the full interaction completes.
6. Repeat the process under rapid consecutive inputs to confirm stability.
7. Confirm that no deadlocks or blocking behaviors occur during repeated turns.

### Expected Result

The system will have a stable turn boundary. Each conversational interaction will be treated as a single atomic sequence from speech capture through TTS completion. The system will no longer interrupt itself by re-entering listening too early.

### Completion Checklist

- [ ] A shared interaction-state model exists.
- [ ] STT respects the busy state.
- [ ] The main conversation pipeline transitions the state correctly.
- [ ] LLM and TTS participate in the same lifecycle contract.
- [ ] Listening resumes only after the full turn is complete.
- [ ] The implementation is thread-safe.
- [ ] The behavior is verified through runtime testing.

### Notes

This is one of the most important stabilization items because it directly affects conversational integrity. The solution should be implemented as a coordination improvement, not as a redesign of the speech or response services.

---

## Problem 2: Multiple Services Can Speak Simultaneously

### Problem

The project now contains several event-producing systems that can independently request speech. Without central coordination, services may compete for speech generation and produce overlapping or conflicting spoken output.

### Severity

Critical

### Background

The system has begun to grow beyond a single, isolated conversation path. It now includes environmental events, user presence events, user departure events, idle behavior events, and other future event sources. These events are all capable of producing speech or conversational output. As the system grows, the risk of multiple services initiating speech at the same time increases significantly.

### Current Behaviour

The following systems can currently request speech independently:

- Environment events
- User returned events
- User left events
- Idle behavior events

The current architecture does not yet enforce a single speech owner. As a result, more than one subsystem can effectively contend for output at the same time.

### Why It Happens

The current architecture allows services to generate or request speech through the existing runtime path without an explicit central scheduler. The system is modular, but speech output is not yet governed by a single admission control mechanism. The result is a coordination gap in the output layer.

### Why It Is A Problem

Speech is a high-impact output channel. If multiple systems attempt to speak concurrently, the experience becomes disorganized and unnatural. Tom may interrupt itself, speak out of turn, or generate responses that are conceptually inconsistent with the most relevant event. This also creates future maintenance issues because each new subsystem would need to know how to coordinate manually with the others.

### Current Architecture

Speech generation currently occurs through the existing TTS path and is triggered from the main conversation flow. Services such as the environment and idle subsystems can produce events, but not all of those events are yet funneled through a single speech arbitration mechanism. The project therefore has distributed speech intent rather than centralized speech control.

### Desired Behaviour

Speech generation should be controlled by only one central system.

Every speech request should first enter an event queue. Speech should never be triggered directly by multiple services. Instead, the system should route speech intent through one scheduling layer that decides when to speak and which message has priority.

### Detailed Solution

Introduce an event queue and a centralized speech scheduling mechanism. This should be implemented as a coordination layer that preserves the current services but ensures that all speech-related requests are normalized before they reach the TTS layer.

The flow should be:

1. A service produces an event or speech request.
2. The request enters the event queue.
3. The central scheduler evaluates the request against the current system state.
4. The scheduler determines whether speech should be emitted immediately, deferred, or suppressed.
5. The selected event is sent to the TTS layer for output.

This approach creates a single authoritative path for speech generation and prevents direct contention between independent services.

### Implementation Strategy

The implementation should build on the existing architecture rather than replacing it.

The recommended strategy is:

1. Introduce a shared event queue that can hold speech and non-speech events.
2. Add a centralized speech scheduler that owns the decision to emit speech.
3. Ensure that services publish event requests rather than calling speech output directly.
4. Keep the TTS service as the final execution stage, not as an independent trigger point.
5. Preserve the existing services by changing only the way they request or publish events.

The design should be intentionally simple and deterministic. It should support future extensibility without requiring a redesign of the current service model.

### Files That Will Change

- [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)
- [AI-Talking-Tom/backend/tts_service.py](AI-Talking-Tom/backend/tts_service.py)
- [AI-Talking-Tom/backend/idle_behavior_service.py](AI-Talking-Tom/backend/idle_behavior_service.py)
- [AI-Talking-Tom/backend/idle_event_service.py](AI-Talking-Tom/backend/idle_event_service.py)
- [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py)
- [AI-Talking-Tom/backend/tom_state_service.py](AI-Talking-Tom/backend/tom_state_service.py)
- event queue coordination module (new)

### Files That Must NOT Change

- [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
- [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
- [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py)
- [AI-Talking-Tom/backend/relationship_service.py](AI-Talking-Tom/backend/relationship_service.py)
- [AI-Talking-Tom/backend/profile_memory_service.py](AI-Talking-Tom/backend/profile_memory_service.py)
- [AI-Talking-Tom/backend/needs_service.py](AI-Talking-Tom/backend/needs_service.py)

### Implementation Steps

1. Define a minimal event structure that can represent speech requests.
2. Introduce a central event queue for the runtime.
3. Update services to publish speech-related requests into the queue instead of triggering speech directly.
4. Introduce a centralized scheduler that evaluates incoming requests.
5. Route the selected request to the existing TTS service.
6. Add priority rules so important conversational events outrank low-priority background events.
7. Ensure that the scheduler protects against duplicate or overlapping output.

### Potential Risks

- Introducing queue latency that delays speech too much
- Creating priority conflicts between conversation and idle events
- Accidental suppression of meaningful but low-priority events
- Rigid scheduling rules that make the system feel less natural

### Testing Procedure

The testing plan should validate that only one speech-producing path is active at a time.

The procedure should include:

1. Trigger a normal conversation turn while an idle event is pending.
2. Verify that the scheduler chooses the higher-priority event.
3. Trigger multiple speech requests in quick succession.
4. Verify that the system serializes them rather than emitting them concurrently.
5. Confirm that environment and idle events are deferred correctly when conversation is active.
6. Confirm that high-priority user-facing speech still occurs promptly.

### Expected Result

The system will have a single, centralized speech authority. Services will no longer compete for speech output. The runtime will feel more coherent and more deterministic, especially as more event-producing systems are added.

### Completion Checklist

- [ ] All speech-emitting requests flow through a central queue.
- [ ] The scheduler owns speech dispatch.
- [ ] Speech requests are prioritized.
- [ ] No service directly triggers speech output without routing through the scheduler.
- [ ] The system serializes speech output correctly.
- [ ] Regression testing confirms that conversation flow remains intact.

### Notes

This stabilization item is foundational. Without centralized speech control, the project will become increasingly difficult to extend safely as additional event sources are introduced.

---

## Problem 3: Missing Brain Manager

### Problem

The project now includes multiple independent autonomous systems, but it does not yet have a central decision-making authority responsible for coordinating them. The current runtime has services and state, but it does not yet have a clear coordinator that decides what Tom should do next.

### Severity

High

### Background

As more systems were added, the project grew from a simple interactive loop into a more autonomous runtime. The system now contains speech, perception, memory, relationships, environment awareness, idle behavior, and several forms of state. Each of these subsystems contributes to the overall experience, but the project still lacks a central integrator that decides how they should interact.

### Current Behaviour

Services operate relatively independently. The main runtime loop is responsible for orchestrating many actions, but it does not yet function as a true central decision layer. In practice, the system is capable of many behaviors, but there is no single coordinator that is responsible for prioritization, conflict suppression, or high-level planning.

### Why It Happens

The current architecture is modular and service-oriented, but the coordination layer has not yet matured to match the growth of the subsystems. The main loop is still doing a significant amount of real-time decision-making. That works for a prototype, but it creates a bottleneck as more autonomous behaviors are introduced.

### Why It Is A Problem

Without a Brain Manager, the project lacks a clear decision center. This makes it harder to reason about behavior, harder to manage conflicts, and harder to guarantee consistent priorities. It also makes future expansion more difficult because new subsystems would need to be manually integrated into the main flow rather than being coordinated by a dedicated decision layer.

### Current Architecture

The architecture currently consists of several specialized services plus a main orchestration loop. Services produce state updates and events, and the main loop reacts to them. This is workable, but the decision-making responsibilities are still distributed throughout the runtime rather than being owned by a dedicated coordinating component.

### Desired Behaviour

Create a Brain Manager that becomes the central coordinator of the project.

The Brain Manager should responsibly:

- receive events
- prioritize events
- schedule events
- decide when Tom should speak
- decide when Tom should remain idle
- prevent conflicts between services

The Brain Manager should operate as the central authority for runtime decisions while preserving the current services underneath it.

### Detailed Solution

Introduce a Brain Manager as a supervisory coordination layer above the existing services. Its role is not to replace the services, but to orchestrate their outputs in a consistent and prioritized way.

The Brain Manager should be responsible for maintaining the runtime’s high-level state and making decisions about the next action. It should receive events from the services, evaluate them against the current system state, and decide whether to:

- allow the event to proceed
- defer the event
- suppress the event
- escalate it to a higher-priority behavior
- route it to the speech system
- route it to the idle system
- decide that Tom should remain idle

This makes the system more deterministic and makes future growth easier to manage.

### Implementation Strategy

The implementation should be additive and should preserve the existing service boundaries.

The recommended strategy is:

1. Introduce a Brain Manager module as a new coordination layer.
2. Keep the existing services intact and let them continue producing state and events.
3. Route the main runtime loop through the Brain Manager for event handling and decision-making.
4. Define a simple event prioritization model.
5. Allow the Brain Manager to make high-level decisions while the services continue to own their domain-specific work.
6. Use the Brain Manager to mediate between speech, idle behavior, environment updates, and other runtime actions.

This is not a replacement for the architecture; it is a stabilization layer that adds central control without collapsing the service model.

### Files That Will Change

- [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)
- [AI-Talking-Tom/backend/tom_state_service.py](AI-Talking-Tom/backend/tom_state_service.py)
- [AI-Talking-Tom/backend/idle_behavior_service.py](AI-Talking-Tom/backend/idle_behavior_service.py)
- [AI-Talking-Tom/backend/idle_event_service.py](AI-Talking-Tom/backend/idle_event_service.py)
- [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py)
- Brain Manager coordination module (new)

### Files That Must NOT Change

- [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
- [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
- [AI-Talking-Tom/backend/tts_service.py](AI-Talking-Tom/backend/tts_service.py)
- [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py)
- [AI-Talking-Tom/backend/relationship_service.py](AI-Talking-Tom/backend/relationship_service.py)
- [AI-Talking-Tom/backend/profile_memory_service.py](AI-Talking-Tom/backend/profile_memory_service.py)
- [AI-Talking-Tom/backend/needs_service.py](AI-Talking-Tom/backend/needs_service.py)

### Implementation Steps

1. Define the Brain Manager’s responsibilities and boundaries.
2. Introduce a runtime coordination interface between services and the Brain Manager.
3. Move high-level event decision-making into the Brain Manager instead of leaving it in the main loop.
4. Define a priority model for conversation, environment events, idle behavior, and other actions.
5. Ensure the Brain Manager can decide between speaking, remaining idle, or deferring an action.
6. Validate that the service boundaries remain intact.

### Potential Risks

- Over-centralizing decision-making and making the system too rigid
- Creating a coordination layer that becomes another source of complexity
- Introducing unclear ownership between services and the Brain Manager
- Increasing latency if decisions are over-processed

### Testing Procedure

Testing should validate that the Brain Manager makes consistent decisions under changing conditions.

The procedure should include:

1. Trigger a user speech event while an idle event is pending.
2. Verify that the Brain Manager prioritizes the conversation turn over idle behavior.
3. Trigger environment events while the system is speaking.
4. Verify that those events do not interrupt the active turn.
5. Simulate multiple simultaneous events.
6. Verify that the Brain Manager resolves them in a deterministic order.

### Expected Result

The runtime will gain a clear decision layer that coordinates the project’s autonomous behaviors. The system will become easier to extend and less dependent on the main loop for all decisions.

### Completion Checklist

- [ ] A Brain Manager module exists.
- [ ] Events are routed through the Brain Manager.
- [ ] Priority handling is defined.
- [ ] The system can decide when to speak and when to remain idle.
- [ ] The current service architecture remains intact.
- [ ] Runtime behavior is consistent under concurrent events.

### Notes

This item should be treated as a coordination enhancement, not as a rewrite. The Brain Manager is a supervisory layer intended to organize the existing architecture, not replace its foundations.

---

## Problem 4: STT Thread Lifecycle

### Problem

The STT system was redesigned from a blocking function into a continuously running background thread. Although this improved responsiveness, the lifecycle of the thread is still not fully finalized. The current implementation must be reviewed and stabilized before additional systems are added.

### Severity

High

### Background

The STT service has moved from a blocking, single-shot operation to a background loop that is expected to continuously run while the system is active. This is a meaningful architectural improvement, but it also introduces lifecycle responsibilities that must be managed correctly.

The current implementation includes several lifecycle concepts such as latest text, latest audio, listening state, running state, start, stop, and the internal listen loop. These are necessary, but they need to be treated as a deliberate lifecycle contract rather than a loose collection of state flags.

### Current Behaviour

The current STT structure is functional, but the lifecycle behavior is still somewhat implicit. The system must start, pause, resume, stop, and release resources correctly, and it must do so without introducing race conditions or inconsistent state.

### Why It Happens

The thread-based architecture is newer than the older, simpler approach. The system is capable of operating, but it was introduced as a practical concurrency improvement rather than as a fully final lifecycle design. This means the code needs a more explicit and disciplined contract around start, stop, pause, resume, and state cleanup.

### Why It Is A Problem

A thread-based subsystem must have a well-defined lifecycle. If the STT thread is started or stopped incorrectly, the entire project can experience inconsistent audio capture, leaked resources, or state corruption. Given that the STT service is one of the most sensitive components in the runtime, lifecycle correctness is critical.

### Current Architecture

The STT service runs as a background thread and communicates with the main runtime through shared state. The current structure uses several control variables and worker loop state. This is a valid temporary approach, but it should now be formalized to ensure predictable behavior.

### Desired Behaviour

The STT thread should:

- start correctly
- pause correctly
- resume correctly
- stop correctly
- release resources correctly
- remain thread-safe

The implementation should be finalized before new systems are integrated on top of it.

### Detailed Solution

The solution is to formalize the STT lifecycle as a stable, documented contract. This should include clear state transitions and explicit resource management. The thread should be able to switch between active and inactive modes without leaving stale state behind. The service should also be able to stop safely and release resources when shutdown is required.

The implementation should ensure that:

- start does not create duplicate or conflicting loops
- stop transitions the service into a clean shutdown path
- pause and resume are consistent with the conversation lifecycle
- shared state is not left in a partially updated state after shutdown
- the internal listen loop exits predictably

### Implementation Strategy

The implementation should preserve the current STT role and thread-based model while tightening its lifecycle behavior.

The recommended strategy is:

1. Define explicit lifecycle states for the STT service.
2. Ensure that all transitions between those states are controlled and predictable.
3. Add proper cleanup logic for thread shutdown and resource release.
4. Make the service pause and resume behavior consistent with the conversation lifecycle.
5. Ensure that shared state updates are safe under concurrency.

### Files That Will Change

- [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
- [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)

### Files That Must NOT Change

- [AI-Talking-Tom/backend/tts_service.py](AI-Talking-Tom/backend/tts_service.py)
- [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
- [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py)
- [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py)
- [AI-Talking-Tom/backend/idle_behavior_service.py](AI-Talking-Tom/backend/idle_behavior_service.py)

### Implementation Steps

1. Document the intended STT lifecycle states.
2. Ensure the service transitions through those states cleanly.
3. Add shutdown and resource cleanup paths.
4. Ensure the thread loop exits predictably when stopped.
5. Verify that pause/resume does not leave stale state behind.
6. Validate the service under repeated start/stop cycles.

### Potential Risks

- Stopping the thread while it is mid-processing can leave inconsistent state
- Pause/resume logic may be implemented inconsistently
- Resource cleanup may be incomplete if shutdown occurs unexpectedly
- Shared state may still require careful protection

### Testing Procedure

The testing plan should validate start, stop, pause, resume, and shutdown behavior.

The procedure should include:

1. Start the STT service and verify that it enters the listening state correctly.
2. Pause the service and confirm that it stops consuming input.
3. Resume the service and confirm that it resumes normally.
4. Stop the service and confirm that the thread exits cleanly.
5. Repeat the cycle multiple times to check consistency.
6. Confirm that no stale transcription remains after stop and restart.

### Expected Result

The STT thread will behave like a stable subsystem with predictable lifecycle behavior. It will start cleanly, pause and resume predictably, stop safely, and release its resources without leaving the runtime in an inconsistent state.

### Completion Checklist

- [ ] STT lifecycle states are clearly defined.
- [ ] Start, stop, pause, and resume behavior are consistent.
- [ ] Resource cleanup is implemented.
- [ ] The thread exits cleanly on shutdown.
- [ ] The service remains safe under repeated lifecycle transitions.

### Notes

This item should be treated as a stabilization and hardening task. It is not a redesign of the STT subsystem, but it is essential for future reliability.

---

## Problem 5: Idle Behaviour Coordination

### Problem

An autonomous idle behavior system has recently been introduced, but its coordination with the rest of the runtime is still immature. As the system grows, idle behavior could interfere with higher-priority activity or become a source of conflict.

### Severity

Medium

### Background

Idle behavior was added to make Tom feel more autonomous and alive during periods of low interaction. This is a valuable capability, but it currently depends on simple timing checks and listening state. As more autonomous systems become active, idle behavior will need to be coordinated by the broader runtime rather than operating as an independent decision-making path.

### Current Behaviour

Idle behavior currently depends on simple timing and listening state. It operates as a separate behavior stream that is evaluated based on the current system condition. The behavior is useful, but it is still not integrated with the broader coordination model.

### Why It Happens

The idle system was introduced as an additive feature. It was designed to be lightweight and practical, but the coordination model has not yet been expanded to account for future decision-making complexity. As a result, idle behavior is still acting more like a local heuristic than a fully integrated runtime capability.

### Why It Is A Problem

Idle behavior should not interfere with speech, conversation, or important runtime events. If it continues to make independent decisions, it can compete with the system’s more important behaviors or create timing conflicts. This is especially problematic as the project adds more autonomous systems and more event-driven behavior.

### Current Architecture

The current architecture contains an idle behavior service and an idle event service. These services are active components of the runtime, but they still operate more independently than the rest of the system. They are not yet fully integrated into a central decision architecture.

### Desired Behaviour

Idle behaviour should never interrupt:

- speech
- conversation
- high-priority events
- future Brain Manager decisions

Idle behavior should eventually become another event source managed by the centralized Brain Manager rather than making independent decisions.

### Detailed Solution

The solution is to treat idle behavior as one event source within the broader runtime coordination layer. It should be allowed to produce behavior, but only within the constraints of the current system state. The idle subsystem should not decide independently whether it can interrupt an active conversation or a high-priority event.

The idle system should publish requests to the coordination layer, and the coordinator should decide whether to accept, defer, or suppress those requests. This preserves the idle subsystem’s role while making it subordinate to the runtime’s broader decision logic.

### Implementation Strategy

The implementation should be incremental and should preserve the idle behavior service itself.

The recommended strategy is:

1. Keep the idle behavior service as the source of idle behavior proposals.
2. Route its output through the central coordination layer.
3. Introduce a policy that prevents idle behavior from overlapping with active speech or active high-priority turns.
4. Ensure that the central coordinator can defer idle behavior while the system is busy.
5. Prepare the system for future Brain Manager-driven prioritization.

### Files That Will Change

- [AI-Talking-Tom/backend/idle_behavior_service.py](AI-Talking-Tom/backend/idle_behavior_service.py)
- [AI-Talking-Tom/backend/idle_event_service.py](AI-Talking-Tom/backend/idle_event_service.py)
- [AI-Talking-Tom/backend/main.py](AI-Talking-Tom/backend/main.py)
- [AI-Talking-Tom/backend/tom_state_service.py](AI-Talking-Tom/backend/tom_state_service.py)

### Files That Must NOT Change

- [AI-Talking-Tom/backend/stt_service.py](AI-Talking-Tom/backend/stt_service.py)
- [AI-Talking-Tom/backend/llm_service.py](AI-Talking-Tom/backend/llm_service.py)
- [AI-Talking-Tom/backend/tts_service.py](AI-Talking-Tom/backend/tts_service.py)
- [AI-Talking-Tom/backend/environment_service.py](AI-Talking-Tom/backend/environment_service.py)
- [AI-Talking-Tom/backend/face_emotion_service.py](AI-Talking-Tom/backend/face_emotion_service.py)
- [AI-Talking-Tom/backend/relationship_service.py](AI-Talking-Tom/backend/relationship_service.py)

### Implementation Steps

1. Define idle behavior as a request-producing subsystem rather than a directly acting subsystem.
2. Route idle behavior requests through the coordination layer.
3. Add guard conditions so idle behavior cannot interrupt active conversation or speech.
4. Ensure idle requests are deferred when the system is busy.
5. Prepare the subsystem to be fully managed by the Brain Manager in the next stage.

### Potential Risks

- Idle behavior becoming too suppressed and losing its personality
- Overly strict blocking rules that make Tom feel inert
- Compatibility issues with the existing timing model
- Confusion between local idle heuristics and centralized scheduling

### Testing Procedure

Testing should validate that idle activity does not interfere with active interactions.

The procedure should include:

1. Start the system in an idle state.
2. Verify that idle behavior can trigger under the correct conditions.
3. Begin a conversation turn and confirm that idle behavior is suppressed.
4. Start speech or TTS playback and verify that no idle event interrupts it.
5. Verify that idle behavior resumes after the active turn has completed.

### Expected Result

Idle behavior will remain part of the experience, but it will no longer act as an uncoordinated source of disruption. It will become a safe, subordinate event source that respects the current runtime state.

### Completion Checklist

- [ ] Idle behavior is routed through the coordination layer.
- [ ] Idle behavior cannot interrupt active speech or conversation.
- [ ] Idle actions are deferred while the system is busy.
- [ ] The subsystem is ready to be absorbed by a future Brain Manager model.
- [ ] Runtime behavior remains natural and non-disruptive.

### Notes

This stabilization item is important for maintaining the personality of the project while ensuring that autonomous behavior remains controlled and non-conflicting.

---

## Cross-Cutting Implementation Approach

The five problems above are related and should be stabilized as a coordinated effort rather than as five isolated changes. The recommended implementation approach is to introduce coordination mechanisms that improve the runtime without changing the overall service-based structure.

The stabilization effort should proceed in this order:

1. Stabilize the conversational turn lifecycle.
2. Introduce a centralized event and speech scheduling path.
3. Add a Brain Manager coordination layer.
4. Finalize STT lifecycle behavior.
5. Reconcile idle behavior with the central coordination model.

This order is deliberate. It ensures that the project first establishes control over interaction boundaries, then centralizes speech dispatch, then adds a broader decision layer, and finally aligns the idle behavior system with that new coordination model.

## Architectural Constraints

The following constraints must be preserved throughout the stabilization effort:

- The project remains service-oriented.
- Existing services continue to own their specialized responsibilities.
- The main runtime remains the execution environment.
- The current data flow remains intact wherever possible.
- New coordination layers are introduced as supervisory mechanisms, not as replacements for the services.

## Risk Management Strategy

The stabilization effort should be implemented in small, verifiable steps. Each change should be tested before the next one is introduced. The engineering team should avoid broad rewrites and should prefer controlled modifications to the existing runtime path.

The team should especially avoid:

- replacing existing services
- merging responsibilities across services
- introducing a new architecture without migration planning
- creating overly complex coordination logic before the simpler coordination model is proven

## Final Expected Outcome

Upon completion of this stabilization plan, the project will have:

- a deterministic conversational turn model
- centralized speech dispatch
- a supervisory Brain Manager layer
- a finalized STT lifecycle
- coordinated idle behavior

The project will be significantly more reliable, easier to extend, and more prepared for the next phase of development without sacrificing its current architecture.
