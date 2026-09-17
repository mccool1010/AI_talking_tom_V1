import socket
import threading
import json
import logging

import config

log = logging.getLogger(__name__)


class GodotBridge:
    """
    Sends runtime events to Godot over a TCP socket.

    Protocol: JSON Lines (one JSON object per line, newline-delimited).
    Godot connects as a TCP client and receives events in real time.

    Event types:
        {"type": "speak",   "text": "Hello!", "emotion": "happy"}
        {"type": "emotion", "value": "happy"}
        {"type": "idle",    "action": "blink"}
        {"type": "state",   "phase": "listening"}
    """

    SEND_TIMEOUT = 1.0

    def __init__(self, host=None, port=None):
        self._host = host or config.GODOT_HOST
        self._port = port or config.GODOT_PORT
        self._client = None
        self._lock = threading.Lock()
        self._running = False

    def start(self):
        """Start the TCP server in a background thread."""
        self._running = True
        thread = threading.Thread(target=self._serve, daemon=True, name="godot-bridge")
        thread.start()
        log.info("Godot bridge listening on %s:%d", self._host, self._port)

    def _serve(self):
        """Accept one Godot client at a time."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self._host, self._port))
        server.listen(1)
        server.settimeout(1.0)

        while self._running:
            try:
                client, addr = server.accept()
                # A stalled Godot must never block the main loop.
                client.settimeout(self.SEND_TIMEOUT)
                with self._lock:
                    if self._client:
                        try:
                            self._client.close()
                        except OSError:
                            pass
                    self._client = client
                log.info("Godot connected from %s", addr)
            except socket.timeout:
                continue
            except OSError:
                break

        server.close()

    # ------------------------------------------------------------------
    # Public send methods
    # ------------------------------------------------------------------

    def send(self, event_type, **data):
        """Send a JSON event to Godot. Silently drops if not connected."""
        msg = {"type": event_type, **data}
        with self._lock:
            if self._client is None:
                return
            try:
                line = json.dumps(msg) + "\n"
                self._client.sendall(line.encode("utf-8"))
            except OSError:
                log.info("Godot disconnected")
                try:
                    self._client.close()
                except OSError:
                    pass
                self._client = None

    def send_speak(self, text, emotion="neutral"):
        """Notify Godot that Tom is about to speak."""
        self.send("speak", text=text, emotion=emotion)

    def send_speak_end(self):
        """Notify Godot that Tom finished speaking."""
        self.send("speak_end")

    def send_emotion(self, emotion):
        """Send the current detected emotion."""
        self.send("emotion", value=emotion)

    def send_idle(self, action):
        """Send an idle action (blink, yawn, look_left, etc.)."""
        self.send("idle", action=action)

    def send_state(self, phase):
        """Send interaction state change (idle, listening, speaking, etc.)."""
        self.send("state", phase=phase)

    def stop(self):
        """Shut down the bridge."""
        self._running = False
        with self._lock:
            if self._client:
                try:
                    self._client.close()
                except OSError:
                    pass
                self._client = None
