class IdleEventService:

    def __init__(self):
        print("Loading Idle Event Service...")
        print("Idle Event Service Ready")

    def send(self, action):
        event = {
        "action": action
    }
        print(event)
        return event