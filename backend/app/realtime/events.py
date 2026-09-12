import json


class GraphEventRegistry:
    """Tracks connected /events/graph WebSocket clients and broadcasts to all of
    them. One registry is kept in memory per process, so real-time delivery is
    intentionally scoped to this project's single-process deployment."""

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
