import logging
import time
from enum import Enum
from interaction_state import InteractionState, InteractionPhase
from event_queue import (
    EventQueue, SpeechEvent,
    PRIORITY_CONVERSATION, PRIORITY_ENVIRONMENT, PRIORITY_IDLE
)


log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


class DecisionAction(Enum):
    """What the Brain Manager decided to do this cycle."""
    SPEAK = "speak"
    IDLE_ACTION = "idle_action"
    WAIT = "wait"


class Decision:
    """
    The result of a Brain Manager decision cycle.

    Attributes:
        action: What to do (speak, idle_action, or wait).
        event: The SpeechEvent to speak (if action is SPEAK).
        idle_action: The idle action string (if action is IDLE_ACTION).
    """

    def __init__(self, action, event=None, idle_action=None):
        self.action = action
        self.event = event
        self.idle_action = idle_action

    def __repr__(self):
        if self.action == DecisionAction.SPEAK:
            return (
                f"Decision(SPEAK, source={self.event.source}, "
                f"priority={self.event.priority})"
            )
        elif self.action == DecisionAction.IDLE_ACTION:
            return f"Decision(IDLE_ACTION, action={self.idle_action})"
        return "Decision(WAIT)"


class BrainManager:
    """
    Central decision coordinator for the AI Talking Tom runtime.

    The Brain Manager is a supervisory layer above the existing services.
    It does NOT own the services or replace them. It coordinates their
    outputs by:
      - evaluating the event queue
      - checking the interaction state
      - deciding whether to speak, trigger idle, or wait
      - preventing conflicts between services

    The main loop calls brain.decide() each iteration and executes
    the returned Decision.
    """

    def __init__(
        self,
        interaction_state,
        event_queue,
        idle_service,
        idle_event_service,
        tom_state,
        needs_service,
        personality_service=None,
        idle_cooldown=10
    ):
        self._interaction_state = interaction_state
        self._event_queue = event_queue
        self._idle_service = idle_service
        self._idle_event_service = idle_event_service
        self._tom_state = tom_state
        self._needs = needs_service
        self._personality = personality_service
        self._idle_cooldown = idle_cooldown
        self._last_idle_time = time.time()
        _debug("[BrainManager] Initialized")

    @property
    def interaction_state(self):
        return self._interaction_state

    @property
    def event_queue(self):
        return self._event_queue

    def submit_environment_event(self, text, context=None):
        """Submit an environment event (user left/returned, objects) to the queue."""
        self._event_queue.submit(SpeechEvent(
            priority=PRIORITY_ENVIRONMENT,
            source="environment",
            text=text,
            context=context or {}
        ))

    def submit_conversation_event(self, text, context=None):
        """Submit a conversation response to the queue."""
        self._event_queue.submit(SpeechEvent(
            priority=PRIORITY_CONVERSATION,
            source="conversation",
            text=text,
            context=context or {}
        ))

    def decide(self):
        """
        Evaluate current state and return a Decision.

        Priority order:
          1. If system is busy -> WAIT
          2. If speech events are pending -> SPEAK (highest priority first)
          3. If idle cooldown has expired -> IDLE_ACTION
          4. Otherwise -> WAIT

        Returns:
            A Decision object.
        """
        # If the system is busy (mid-turn), do nothing
        if self._interaction_state.is_busy():
            return Decision(DecisionAction.WAIT)

        # Check the event queue for pending speech
        event = self._event_queue.next()
        if event is not None:
            return Decision(DecisionAction.SPEAK, event=event)

        # Check if idle behavior should fire
        elapsed = time.time() - self._last_idle_time
        if elapsed > self._idle_cooldown:
            personality_traits = self._personality.get_traits() if self._personality else None
            action = self._idle_service.get_action(
                self._tom_state.energy,
                self._needs.sleepiness,
                self._needs.hunger,
                self._needs.social_need,
                self._tom_state.curiosity,
                personality_traits
            )
            self._idle_event_service.send(action)
            self._last_idle_time = time.time()
            return Decision(DecisionAction.IDLE_ACTION, idle_action=action)

        return Decision(DecisionAction.WAIT)

    def reset_idle_timer(self):
        """Reset the idle timer after an interaction completes."""
        self._last_idle_time = time.time()
