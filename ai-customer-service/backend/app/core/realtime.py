"""
Enhanced WebSocket Real-time Communication System

This module provides comprehensive real-time features including:
- Live chat with typing indicators
- Real-time notifications
- System status updates
- Multi-room support
- Presence tracking
- Message acknowledgments
"""

import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import logging
from collections import defaultdict

from app.core.config import settings


class MessageType(Enum):
    """WebSocket message types."""
    CHAT_MESSAGE = "chat_message"
    TYPING_INDICATOR = "typing_indicator"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    NOTIFICATION = "notification"
    STATUS_UPDATE = "status_update"
    SYSTEM_ALERT = "system_alert"
    ACKNOWLEDGMENT = "acknowledgment"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class UserStatus(Enum):
    """User presence status."""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    message_id: str
    type: MessageType
    data: Dict[str, Any]
    sender_id: Optional[str] = None
    room_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requires_ack: bool = False


@dataclass
class UserPresence:
    """User presence information."""
    user_id: str
    status: UserStatus
    last_seen: datetime
    current_room: Optional[str] = None
    connection_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatRoom:
    """Chat room information."""
    room_id: str
    name: str
    description: str
    created_at: datetime
    created_by: str
    members: Set[str] = field(default_factory=set)
    moderators: Set[str] = field(default_factory=set)
    settings: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class Notification:
    """Real-time notification."""
    notification_id: str
    user_id: str
    title: str
    message: str
    priority: NotificationPriority
    created_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    read: bool = False
    expires_at: Optional[datetime] = None


class ConnectionManager:
    """Manage WebSocket connections and routing."""
    
    def __init__(self):
        self.active_connections: Dict[str, Any] = {}  # connection_id -> websocket
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)  # user_id -> connection_ids
        self.room_connections: Dict[str, Set[str]] = defaultdict(set)  # room_id -> connection_ids
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: Any, user_id: str, connection_id: str, room_id: Optional[str] = None):
        """Register a new WebSocket connection."""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        self.user_connections[user_id].add(connection_id)
        
        if room_id:
            self.room_connections[room_id].add(connection_id)
        
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "room_id": room_id,
            "connected_at": datetime.utcnow(),
            "last_heartbeat": datetime.utcnow()
        }
        
        self.logger.info(f"User {user_id} connected with connection {connection_id}")
        
        # Notify others in the room
        if room_id:
            await self.broadcast_to_room(
                room_id,
                WebSocketMessage(
                    message_id=str(uuid.uuid4()),
                    type=MessageType.USER_JOINED,
                    data={"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
                    room_id=room_id
                ),
                exclude_connections={connection_id}
            )
    
    async def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id not in self.active_connections:
            return
        
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")
        room_id = metadata.get("room_id")
        
        # Remove from tracking
        del self.active_connections[connection_id]
        
        if user_id and connection_id in self.user_connections[user_id]:
            self.user_connections[user_id].remove(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        if room_id and connection_id in self.room_connections[room_id]:
            self.room_connections[room_id].remove(connection_id)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        self.logger.info(f"Connection {connection_id} disconnected")
        
        # Notify others in the room
        if room_id and user_id:
            await self.broadcast_to_room(
                room_id,
                WebSocketMessage(
                    message_id=str(uuid.uuid4()),
                    type=MessageType.USER_LEFT,
                    data={"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
                    room_id=room_id
                )
            )
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to a specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps({
                    "message_id": message.message_id,
                    "type": message.type.value,
                    "data": message.data,
                    "sender_id": message.sender_id,
                    "room_id": message.room_id,
                    "timestamp": message.timestamp.isoformat(),
                    "requires_ack": message.requires_ack
                }))
            except Exception as e:
                self.logger.error(f"Error sending message to connection {connection_id}: {e}")
                await self.disconnect(connection_id)
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send message to all connections of a user."""
        if user_id in self.user_connections:
            tasks = []
            for connection_id in self.user_connections[user_id].copy():
                tasks.append(self.send_to_connection(connection_id, message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude_connections: Optional[Set[str]] = None
    ):
        """Broadcast message to all users in a room."""
        if room_id in self.room_connections:
            exclude_connections = exclude_connections or set()
            tasks = []
            
            for connection_id in self.room_connections[room_id].copy():
                if connection_id not in exclude_connections:
                    tasks.append(self.send_to_connection(connection_id, message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all connected users."""
        tasks = []
        for connection_id in self.active_connections.copy():
            tasks.append(self.send_to_connection(connection_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_room_users(self, room_id: str) -> Set[str]:
        """Get all users currently in a room."""
        users = set()
        if room_id in self.room_connections:
            for connection_id in self.room_connections[room_id]:
                metadata = self.connection_metadata.get(connection_id, {})
                user_id = metadata.get("user_id")
                if user_id:
                    users.add(user_id)
        return users
    
    def get_user_count(self, room_id: Optional[str] = None) -> int:
        """Get count of users in a room or total."""
        if room_id:
            return len(self.get_room_users(room_id))
        else:
            return len(self.user_connections)
    
    async def cleanup_stale_connections(self):
        """Remove stale connections that haven't sent heartbeats."""
        current_time = datetime.utcnow()
        stale_connections = []
        
        for connection_id, metadata in self.connection_metadata.items():
            last_heartbeat = metadata.get("last_heartbeat", current_time)
            if current_time - last_heartbeat > timedelta(minutes=5):  # 5 minute timeout
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            await self.disconnect(connection_id)


class PresenceManager:
    """Manage user presence and status."""
    
    def __init__(self):
        self.user_presence: Dict[str, UserPresence] = {}
        self.status_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)
    
    def update_presence(
        self,
        user_id: str,
        status: UserStatus,
        room_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update user presence information."""
        
        current_time = datetime.utcnow()
        
        if user_id in self.user_presence:
            old_status = self.user_presence[user_id].status
            self.user_presence[user_id].status = status
            self.user_presence[user_id].last_seen = current_time
            
            if room_id:
                self.user_presence[user_id].current_room = room_id
            if connection_id:
                self.user_presence[user_id].connection_id = connection_id
            if metadata:
                self.user_presence[user_id].metadata.update(metadata)
        else:
            self.user_presence[user_id] = UserPresence(
                user_id=user_id,
                status=status,
                last_seen=current_time,
                current_room=room_id,
                connection_id=connection_id,
                metadata=metadata or {}
            )
            old_status = UserStatus.OFFLINE
        
        # Record status change
        if old_status != status:
            self.status_history[user_id].append({
                "from_status": old_status.value,
                "to_status": status.value,
                "timestamp": current_time.isoformat(),
                "room_id": room_id
            })
            
            # Keep only last 50 status changes
            if len(self.status_history[user_id]) > 50:
                self.status_history[user_id] = self.status_history[user_id][-50:]
    
    def get_presence(self, user_id: str) -> Optional[UserPresence]:
        """Get user presence information."""
        return self.user_presence.get(user_id)
    
    def get_room_presence(self, room_id: str) -> List[UserPresence]:
        """Get presence of all users in a room."""
        return [
            presence for presence in self.user_presence.values()
            if presence.current_room == room_id and presence.status != UserStatus.OFFLINE
        ]
    
    def get_online_users(self) -> List[UserPresence]:
        """Get all online users."""
        return [
            presence for presence in self.user_presence.values()
            if presence.status != UserStatus.OFFLINE
        ]
    
    def cleanup_offline_users(self, timeout_minutes: int = 30):
        """Mark users as offline if they haven't been seen recently."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        offline_users = []
        
        for user_id, presence in self.user_presence.items():
            if presence.last_seen < cutoff_time and presence.status != UserStatus.OFFLINE:
                presence.status = UserStatus.OFFLINE
                offline_users.append(user_id)
        
        return offline_users


class NotificationManager:
    """Manage real-time notifications."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.notifications: Dict[str, List[Notification]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
        expires_in_minutes: Optional[int] = None
    ) -> str:
        """Send a real-time notification to a user."""
        
        notification_id = str(uuid.uuid4())
        expires_at = None
        
        if expires_in_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        
        notification = Notification(
            notification_id=notification_id,
            user_id=user_id,
            title=title,
            message=message,
            priority=priority,
            created_at=datetime.utcnow(),
            data=data or {},
            expires_at=expires_at
        )
        
        # Store notification
        self.notifications[user_id].append(notification)
        
        # Keep only last 100 notifications per user
        if len(self.notifications[user_id]) > 100:
            self.notifications[user_id] = self.notifications[user_id][-100:]
        
        # Send via WebSocket
        await self.connection_manager.send_to_user(
            user_id,
            WebSocketMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.NOTIFICATION,
                data={
                    "notification_id": notification_id,
                    "title": title,
                    "message": message,
                    "priority": priority.value,
                    "data": data or {},
                    "created_at": notification.created_at.isoformat(),
                    "expires_at": expires_at.isoformat() if expires_at else None
                },
                sender_id="system",
                requires_ack=priority in [NotificationPriority.HIGH, NotificationPriority.CRITICAL]
            )
        )
        
        self.logger.info(f"Sent notification {notification_id} to user {user_id}")
        return notification_id
    
    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read."""
        for notification in self.notifications[user_id]:
            if notification.notification_id == notification_id:
                notification.read = True
                return True
        return False
    
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user."""
        notifications = self.notifications[user_id]
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        # Filter out expired notifications
        current_time = datetime.utcnow()
        notifications = [
            n for n in notifications
            if n.expires_at is None or n.expires_at > current_time
        ]
        
        return sorted(notifications, key=lambda x: x.created_at, reverse=True)[:limit]
    
    async def broadcast_system_alert(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.HIGH,
        room_id: Optional[str] = None
    ):
        """Broadcast a system alert to all users or users in a room."""
        
        alert_data = {
            "alert_id": str(uuid.uuid4()),
            "title": title,
            "message": message,
            "priority": priority.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        alert_message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            type=MessageType.SYSTEM_ALERT,
            data=alert_data,
            sender_id="system",
            room_id=room_id,
            requires_ack=priority == NotificationPriority.CRITICAL
        )
        
        if room_id:
            await self.connection_manager.broadcast_to_room(room_id, alert_message)
        else:
            await self.connection_manager.broadcast_to_all(alert_message)
        
        self.logger.warning(f"Broadcast system alert: {title}")


class TypingIndicatorManager:
    """Manage typing indicators for real-time chat."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.typing_users: Dict[str, Dict[str, datetime]] = defaultdict(dict)  # room_id -> {user_id: timestamp}
        self.logger = logging.getLogger(__name__)
    
    async def start_typing(self, user_id: str, room_id: str):
        """Indicate that a user started typing."""
        self.typing_users[room_id][user_id] = datetime.utcnow()
        
        await self.connection_manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.TYPING_INDICATOR,
                data={
                    "user_id": user_id,
                    "action": "start_typing",
                    "timestamp": datetime.utcnow().isoformat()
                },
                sender_id=user_id,
                room_id=room_id
            )
        )
    
    async def stop_typing(self, user_id: str, room_id: str):
        """Indicate that a user stopped typing."""
        if room_id in self.typing_users and user_id in self.typing_users[room_id]:
            del self.typing_users[room_id][user_id]
            
            if not self.typing_users[room_id]:
                del self.typing_users[room_id]
        
        await self.connection_manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.TYPING_INDICATOR,
                data={
                    "user_id": user_id,
                    "action": "stop_typing",
                    "timestamp": datetime.utcnow().isoformat()
                },
                sender_id=user_id,
                room_id=room_id
            )
        )
    
    def get_typing_users(self, room_id: str) -> List[str]:
        """Get list of users currently typing in a room."""
        if room_id not in self.typing_users:
            return []
        
        # Remove stale typing indicators (older than 10 seconds)
        current_time = datetime.utcnow()
        stale_users = []
        
        for user_id, timestamp in self.typing_users[room_id].items():
            if current_time - timestamp > timedelta(seconds=10):
                stale_users.append(user_id)
        
        for user_id in stale_users:
            del self.typing_users[room_id][user_id]
        
        return list(self.typing_users[room_id].keys())
    
    async def cleanup_stale_indicators(self):
        """Remove stale typing indicators."""
        current_time = datetime.utcnow()
        
        for room_id in list(self.typing_users.keys()):
            stale_users = []
            
            for user_id, timestamp in self.typing_users[room_id].items():
                if current_time - timestamp > timedelta(seconds=10):
                    stale_users.append(user_id)
            
            for user_id in stale_users:
                await self.stop_typing(user_id, room_id)


class RealTimeMessageHandler:
    """Handle real-time message processing and routing."""
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        presence_manager: PresenceManager,
        notification_manager: NotificationManager,
        typing_manager: TypingIndicatorManager
    ):
        self.connection_manager = connection_manager
        self.presence_manager = presence_manager
        self.notification_manager = notification_manager
        self.typing_manager = typing_manager
        self.message_history: Dict[str, List[WebSocketMessage]] = defaultdict(list)
        self.acknowledgments: Dict[str, Set[str]] = defaultdict(set)  # message_id -> connection_ids
        self.logger = logging.getLogger(__name__)
    
    async def handle_message(self, connection_id: str, raw_message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(raw_message)
            
            message_type = MessageType(data.get("type"))
            message_data = data.get("data", {})
            
            metadata = self.connection_manager.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")
            room_id = metadata.get("room_id")
            
            if message_type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(connection_id, user_id)
            
            elif message_type == MessageType.CHAT_MESSAGE:
                await self._handle_chat_message(connection_id, user_id, room_id, message_data)
            
            elif message_type == MessageType.TYPING_INDICATOR:
                await self._handle_typing_indicator(user_id, room_id, message_data)
            
            elif message_type == MessageType.ACKNOWLEDGMENT:
                await self._handle_acknowledgment(connection_id, message_data)
            
            elif message_type == MessageType.STATUS_UPDATE:
                await self._handle_status_update(user_id, room_id, message_data)
            
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling message from {connection_id}: {e}")
            await self._send_error(connection_id, str(e))
    
    async def _handle_heartbeat(self, connection_id: str, user_id: str):
        """Handle heartbeat message."""
        if connection_id in self.connection_manager.connection_metadata:
            self.connection_manager.connection_metadata[connection_id]["last_heartbeat"] = datetime.utcnow()
        
        # Update presence
        if user_id:
            self.presence_manager.update_presence(user_id, UserStatus.ONLINE)
    
    async def _handle_chat_message(
        self,
        connection_id: str,
        user_id: str,
        room_id: str,
        message_data: Dict[str, Any]
    ):
        """Handle chat message."""
        if not user_id or not room_id:
            await self._send_error(connection_id, "User ID and Room ID required for chat messages")
            return
        
        message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            type=MessageType.CHAT_MESSAGE,
            data=message_data,
            sender_id=user_id,
            room_id=room_id,
            requires_ack=True
        )
        
        # Store message history
        self.message_history[room_id].append(message)
        if len(self.message_history[room_id]) > 1000:  # Keep last 1000 messages
            self.message_history[room_id] = self.message_history[room_id][-1000:]
        
        # Broadcast to room
        await self.connection_manager.broadcast_to_room(room_id, message)
        
        # Stop typing indicator for sender
        await self.typing_manager.stop_typing(user_id, room_id)
    
    async def _handle_typing_indicator(
        self,
        user_id: str,
        room_id: str,
        message_data: Dict[str, Any]
    ):
        """Handle typing indicator."""
        if not user_id or not room_id:
            return
        
        action = message_data.get("action")
        
        if action == "start_typing":
            await self.typing_manager.start_typing(user_id, room_id)
        elif action == "stop_typing":
            await self.typing_manager.stop_typing(user_id, room_id)
    
    async def _handle_acknowledgment(self, connection_id: str, message_data: Dict[str, Any]):
        """Handle message acknowledgment."""
        message_id = message_data.get("message_id")
        if message_id:
            self.acknowledgments[message_id].add(connection_id)
    
    async def _handle_status_update(
        self,
        user_id: str,
        room_id: str,
        message_data: Dict[str, Any]
    ):
        """Handle user status update."""
        if not user_id:
            return
        
        status_str = message_data.get("status")
        if status_str:
            try:
                status = UserStatus(status_str)
                self.presence_manager.update_presence(
                    user_id,
                    status,
                    room_id,
                    metadata=message_data.get("metadata", {})
                )
            except ValueError:
                self.logger.warning(f"Invalid status: {status_str}")
    
    async def _send_error(self, connection_id: str, error_message: str):
        """Send error message to connection."""
        await self.connection_manager.send_to_connection(
            connection_id,
            WebSocketMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.ERROR,
                data={"error": error_message, "timestamp": datetime.utcnow().isoformat()},
                sender_id="system"
            )
        )
    
    def get_room_history(self, room_id: str, limit: int = 50) -> List[WebSocketMessage]:
        """Get recent message history for a room."""
        messages = self.message_history.get(room_id, [])
        return messages[-limit:] if limit else messages


# Factory functions for dependency injection
def create_connection_manager() -> ConnectionManager:
    """Create connection manager instance."""
    return ConnectionManager()


def create_presence_manager() -> PresenceManager:
    """Create presence manager instance."""
    return PresenceManager()


def create_notification_manager(connection_manager: ConnectionManager) -> NotificationManager:
    """Create notification manager instance."""
    return NotificationManager(connection_manager)


def create_typing_manager(connection_manager: ConnectionManager) -> TypingIndicatorManager:
    """Create typing indicator manager instance."""
    return TypingIndicatorManager(connection_manager)


def create_message_handler(
    connection_manager: ConnectionManager,
    presence_manager: PresenceManager,
    notification_manager: NotificationManager,
    typing_manager: TypingIndicatorManager
) -> RealTimeMessageHandler:
    """Create real-time message handler instance."""
    return RealTimeMessageHandler(
        connection_manager,
        presence_manager,
        notification_manager,
        typing_manager
    )
