import threading
import time
from dataclasses import dataclass, field
from queue import PriorityQueue, Empty


# Priority levels — higher number = higher priority
PRIORITY_CONVERSATION = 100
PRIORITY_ENVIRONMENT = 80
PRIORITY_IDLE = 20


@dataclass(order=True)
class SpeechEvent:
    """
    Represents a request for Tom to speak.

    Events are ordered by priority (descending) then by timestamp (ascending).
    The PriorityQueue returns the smallest item first, so we negate priority
    for correct ordering.
    """
    sort_key: tuple = field(init=False, repr=False)
    priority: int = field(compare=False)
    source: str = field(compare=False)
    text: str = field(compare=False)
    context: dict = field(default_factory=dict, compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)

    def __post_init__(self):
        # Negate priority so higher priority sorts first in PriorityQueue
        self.sort_key = (-self.priority, self.timestamp)


class EventQueue:
    """
    Thread-safe priority queue for speech events.

    All services submit speech requests through this queue.
    The Brain Manager (or main loop) drains and dispatches events.
    """

    def __init__(self):
        self._queue = PriorityQueue()
        self._lock = threading.Lock()
        print("[EventQueue] Initialized")

    def submit(self, event):
        """
        Submit a speech event to the queue.

        Args:
            event: A SpeechEvent instance.
        """
        self._queue.put(event)
        print(
            f"[EventQueue] Submitted: source={event.source}, "
            f"priority={event.priority}, text='{event.text[:40]}...'"
            if len(event.text) > 40
            else f"[EventQueue] Submitted: source={event.source}, "
                 f"priority={event.priority}, text='{event.text}'"
        )

    def next(self):
        """
        Return the highest-priority event, or None if the queue is empty.

        This is non-blocking.
        """
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    def is_empty(self):
        """Return True if no events are pending."""
        return self._queue.empty()

    def clear(self):
        """Discard all pending events."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except Empty:
                    break
        print("[EventQueue] Cleared")

    def size(self):
        """Return the number of pending events."""
        return self._queue.qsize()
