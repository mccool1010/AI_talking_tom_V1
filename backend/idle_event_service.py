import logging
log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


class IdleEventService:

    def __init__(self):
        _debug("Loading Idle Event Service...")
        _debug("Idle Event Service Ready")

    def send(self, action):
        event = {
        "action": action
    }
        _debug(event)
        return event