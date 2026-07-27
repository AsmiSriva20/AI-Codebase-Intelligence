import json


class GraphEventRegistry:
    """Tracks connected /events/graph WebSocket clients and broadcasts to all of
    them. One registry, in-memory, per process — fine for this single-instance
    dev tool; would need a pub/sub backend (Redis etc.) behind multiple workers."""

    def __init__(self):
        self._connections = set()

    async def connect(self, websocket):
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket):
        self._connections.discard(websocket)

    async def broadcast(self, message: dict):
        payload = json.dumps(message)
        dead = []
        for websocket in list(self._connections):
            try:
                await websocket.send_text(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self._connections.discard(websocket)


registry = GraphEventRegistry()
