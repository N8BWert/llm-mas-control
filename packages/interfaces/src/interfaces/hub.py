"""
Keeps the set of connected browsers and broadcasts JSON messages to them.
"""

import json

from fastapi import WebSocket


class Hub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.clients.discard(websocket)

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        for websocket in list(self.clients):
            try:
                await websocket.send_text(text)
            except Exception:
                self.disconnect(websocket)

    @staticmethod
    async def send(websocket: WebSocket, message: dict):
        await websocket.send_text(json.dumps(message))
