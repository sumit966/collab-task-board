"""In-memory pub/sub for real-time WebSocket events."""
import asyncio
from typing import Dict, Set, Any
from fastapi import WebSocket


class ConnectionManager:
    """Tracks active WebSocket connections per board."""

    def __init__(self):
        self.rooms: Dict[int, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, board_id: int, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.rooms.setdefault(board_id, set()).add(ws)

    async def disconnect(self, board_id: int, ws: WebSocket):
        async with self.lock:
            if board_id in self.rooms:
                self.rooms[board_id].discard(ws)
                if not self.rooms[board_id]:
                    del self.rooms[board_id]

    async def broadcast(self, board_id: int, message: dict):
        """Send message to all connected clients in a board room."""
        async with self.lock:
            sockets = list(self.rooms.get(board_id, set()))
        dead = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(board_id, ws)


manager = ConnectionManager()
