from typing import Dict, List

from fastapi import WebSocket


class SocketManager:
    """
    Manages WebSocket connections for real-time communication.
    """

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """
        Accepts and stores a new WebSocket connection.
        """
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    def disconnect(self, client_id: str, websocket: WebSocket):
        """
        Removes a WebSocket connection.
        """
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def broadcast(self, message: str):
        """
        Sends a message to all connected clients.
        """
        for client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_text(message)

    async def send_to_client(self, client_id: str, message: str):
        """
        Sends a message to a specific client.
        """
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_text(message)


socket_manager = SocketManager()
