import threading
from enum import Enum


class InteractionPhase(Enum):
    """
    Represents the current phase of a single conversational turn.

    Lifecycle:
        IDLE -> LISTENING -> PROCESSING_INPUT -> GENERATING_RESPONSE
             -> PRODUCING_SPEECH -> SPEAKING -> TURN_COMPLETE -> IDLE
    """
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING_INPUT = "processing_input"
    GENERATING_RESPONSE = "generating_response"
    PRODUCING_SPEECH = "producing_speech"
    SPEAKING = "speaking"
    TURN_COMPLETE = "turn_complete"


# Valid state transitions. Each key maps to the set of states it can transition to.
_VALID_TRANSITIONS = {
    InteractionPhase.IDLE: {
        InteractionPhase.LISTENING,
        InteractionPhase.PROCESSING_INPUT,
        InteractionPhase.GENERATING_RESPONSE,
    },
    InteractionPhase.LISTENING: {
        InteractionPhase.PROCESSING_INPUT,
        InteractionPhase.IDLE,  # cancelled listen (e.g. user left)
    },
    InteractionPhase.PROCESSING_INPUT: {
        InteractionPhase.GENERATING_RESPONSE,
    },
    InteractionPhase.GENERATING_RESPONSE: {
        InteractionPhase.PRODUCING_SPEECH,
    },
    InteractionPhase.PRODUCING_SPEECH: {
        InteractionPhase.SPEAKING,
    },
    InteractionPhase.SPEAKING: {
        InteractionPhase.TURN_COMPLETE,
    },
    InteractionPhase.TURN_COMPLETE: {
        InteractionPhase.IDLE,
    },
}


class InteractionState:
    """
    Thread-safe interaction state that governs the full conversation lifecycle.

    The STT service checks can_listen() before starting a new listening cycle.
    The main loop and TTS service transition the state at each pipeline stage.

    All transitions are guarded by a lock and validated against the allowed
    transition graph.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._phase = InteractionPhase.IDLE
        print("[InteractionState] Initialized -> IDLE")

    @property
    def phase(self):
        """Return the current interaction phase (read is atomic for enum)."""
        return self._phase

    def can_listen(self):
        """
        Return True if the system is in a state where STT may begin listening.

        Listening is only allowed when the system is IDLE. During any other
        phase, the system is considered busy and STT must wait.
        """
        return self._phase == InteractionPhase.IDLE

    def transition_to(self, target):
        """
        Attempt to transition to the target phase.

        Args:
            target: An InteractionPhase value.

        Returns:
            True if the transition succeeded, False if it was invalid.
        """
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._phase, set())
            if target not in allowed:
                print(
                    f"[InteractionState] INVALID transition: "
                    f"{self._phase.value} -> {target.value}"
                )
                return False

            previous = self._phase
            self._phase = target
            print(
                f"[InteractionState] {previous.value} -> {target.value}"
            )
            return True

    def force_idle(self):
        """
        Force the state back to IDLE. Used only for error recovery
        to prevent the system from getting stuck in a busy state.
        """
        with self._lock:
            previous = self._phase
            self._phase = InteractionPhase.IDLE
            print(
                f"[InteractionState] FORCE RESET: "
                f"{previous.value} -> idle"
            )

    def is_busy(self):
        """
        Return True if the system is in any phase other than IDLE.
        """
        return self._phase != InteractionPhase.IDLE

    def __repr__(self):
        return f"InteractionState(phase={self._phase.value})"
