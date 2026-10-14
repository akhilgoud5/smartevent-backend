
from fastapi import WebSocket
from typing import Dict, List
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, event_id: int, websocket: WebSocket):
        await websocket.accept()

        async with self.lock:
            self.active_connections.setdefault(event_id, []).append(websocket)

    async def disconnect(self, event_id: int, websocket: WebSocket):
        async with self.lock:
            connections = self.active_connections.get(event_id, [])

            if websocket in connections:
                connections.remove(websocket)

            if not connections:
                self.active_connections.pop(event_id, None)

    async def broadcast(self, event_id: int, message: dict):
        async with self.lock:
            connections = list(
                self.active_connections.get(event_id, [])
            )

        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            await self.disconnect(event_id, websocket)


manager = ConnectionManager()
