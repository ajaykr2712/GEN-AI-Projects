"""
Domain Layer - Core Business Logic

This module contains the core business entities, value objects, and domain services
that represent the heart of the AI Customer Service system.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import uuid


# Domain Events
@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_id: str
    timestamp: datetime
    aggregate_id: str
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()


@dataclass
class ConversationStartedEvent(DomainEvent):
    """Event raised when a new conversation is started."""
    user_id: int
    conversation_title: str


@dataclass
class MessageSentEvent(DomainEvent):
    """Event raised when a message is sent."""
    conversation_id: int
    message_content: str
    sender_role: str
    tokens_used: int


@dataclass
class ConversationEndedEvent(DomainEvent):
    """Event raised when a conversation is ended."""
    conversation_id: int
    total_messages: int
    duration_minutes: int


# Value Objects
@dataclass(frozen=True)
class Email:
    """Email value object with validation."""
    value: str
    
    def __post_init__(self):
        if not self._is_valid_email(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None


@dataclass(frozen=True)
class MessageContent:
    """Message content value object with validation."""
    text: str
    language: str = "en"
    
    def __post_init__(self):
        if not self.text or len(self.text.strip()) == 0:
            raise ValueError("Message content cannot be empty")
        if len(self.text) > 10000:
            raise ValueError("Message content too long (max 10000 characters)")


@dataclass(frozen=True)
class UserId:
    """User ID value object."""
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("User ID must be positive")


# Enums
class MessageRole(Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationStatus(Enum):
    """Conversation status enumeration."""
    ACTIVE = "active"
    ENDED = "ended"
    ARCHIVED = "archived"


class LogPriority(Enum):
    """Log priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class LogStatus(Enum):
    """Log status enumeration."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Domain Entities
class User:
    """User domain entity."""
    
    def __init__(
        self,
        user_id: UserId,
        email: Email,
        username: str,
        full_name: Optional[str] = None,
        is_admin: bool = False
    ):
        self._id = user_id
        self._email = email
        self._username = username
        self._full_name = full_name
        self._is_admin = is_admin
        self._is_active = True
        self._created_at = datetime.utcnow()
        self._conversations: List['Conversation'] = []
        self._domain_events: List[DomainEvent] = []
    
    @property
    def id(self) -> UserId:
        return self._id
    
    @property
    def email(self) -> Email:
        return self._email
    
    @property
    def username(self) -> str:
        return self._username
    
    @property
    def full_name(self) -> Optional[str]:
        return self._full_name
    
    @property
    def is_admin(self) -> bool:
        return self._is_admin
    
    @property
    def is_active(self) -> bool:
        return self._is_active
    
    @property
    def conversations(self) -> List['Conversation']:
        return self._conversations.copy()
    
    def start_conversation(self, title: str = "New Conversation") -> 'Conversation':
        """Start a new conversation."""
        conversation = Conversation(
            user_id=self._id,
            title=title
        )
        self._conversations.append(conversation)
        
        # Raise domain event
        event = ConversationStartedEvent(
            aggregate_id=str(conversation.id),
            user_id=self._id.value,
            conversation_title=title
        )
        self._domain_events.append(event)
        
        return conversation
    
    def deactivate(self):
        """Deactivate the user."""
        self._is_active = False
    
    def get_domain_events(self) -> List[DomainEvent]:
        """Get and clear domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events


class Conversation:
    """Conversation domain entity."""
    
    def __init__(
        self,
        user_id: UserId,
        title: str = "New Conversation",
        conversation_id: Optional[int] = None
    ):
        self._id = conversation_id or id(self)  # Temporary ID, will be set by repository
        self._user_id = user_id
        self._title = title
        self._status = ConversationStatus.ACTIVE
        self._created_at = datetime.utcnow()
        self._messages: List['Message'] = []
        self._domain_events: List[DomainEvent] = []
    
    @property
    def id(self) -> int:
        return self._id
    
    @property
    def user_id(self) -> UserId:
        return self._user_id
    
    @property
    def title(self) -> str:
        return self._title
    
    @property
    def status(self) -> ConversationStatus:
        return self._status
    
    @property
    def messages(self) -> List['Message']:
        return self._messages.copy()
    
    @property
    def message_count(self) -> int:
        return len(self._messages)
    
    def add_message(
        self,
        content: MessageContent,
        role: MessageRole,
        tokens_used: int = 0,
        response_time_ms: int = 0
    ) -> 'Message':
        """Add a message to the conversation."""
        if self._status != ConversationStatus.ACTIVE:
            raise ValueError("Cannot add messages to inactive conversation")
        
        message = Message(
            conversation_id=self._id,
            content=content,
            role=role,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms
        )
        
        self._messages.append(message)
        
        # Raise domain event
        event = MessageSentEvent(
            aggregate_id=str(self._id),
            conversation_id=self._id,
            message_content=content.text,
            sender_role=role.value,
            tokens_used=tokens_used
        )
        self._domain_events.append(event)
        
        return message
    
    def end_conversation(self):
        """End the conversation."""
        if self._status == ConversationStatus.ACTIVE:
            self._status = ConversationStatus.ENDED
            duration = (datetime.utcnow() - self._created_at).total_seconds() / 60
            
            # Raise domain event
            event = ConversationEndedEvent(
                aggregate_id=str(self._id),
                conversation_id=self._id,
                total_messages=len(self._messages),
                duration_minutes=int(duration)
            )
            self._domain_events.append(event)
    
    def archive(self):
        """Archive the conversation."""
        self._status = ConversationStatus.ARCHIVED
    
    def get_domain_events(self) -> List[DomainEvent]:
        """Get and clear domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events


class Message:
    """Message domain entity."""
    
    def __init__(
        self,
        conversation_id: int,
        content: MessageContent,
        role: MessageRole,
        tokens_used: int = 0,
        response_time_ms: int = 0,
        message_id: Optional[int] = None
    ):
        self._id = message_id or id(self)  # Temporary ID
        self._conversation_id = conversation_id
        self._content = content
        self._role = role
        self._tokens_used = tokens_used
        self._response_time_ms = response_time_ms
        self._timestamp = datetime.utcnow()
    
    @property
    def id(self) -> int:
        return self._id
    
    @property
    def conversation_id(self) -> int:
        return self._conversation_id
    
    @property
    def content(self) -> MessageContent:
        return self._content
    
    @property
    def role(self) -> MessageRole:
        return self._role
    
    @property
    def tokens_used(self) -> int:
        return self._tokens_used
    
    @property
    def response_time_ms(self) -> int:
        return self._response_time_ms
    
    @property
    def timestamp(self) -> datetime:
        return self._timestamp


class CustomerLog:
    """Customer log domain entity."""
    
    def __init__(
        self,
        user_id: UserId,
        log_type: str,
        title: str,
        description: Optional[str] = None,
        priority: LogPriority = LogPriority.MEDIUM,
        category: Optional[str] = None,
        log_id: Optional[int] = None
    ):
        self._id = log_id or id(self)
        self._user_id = user_id
        self._log_type = log_type
        self._title = title
        self._description = description
        self._priority = priority
        self._category = category
        self._status = LogStatus.OPEN
        self._created_at = datetime.utcnow()
        self._resolved_at: Optional[datetime] = None
    
    @property
    def id(self) -> int:
        return self._id
    
    @property
    def user_id(self) -> UserId:
        return self._user_id
    
    @property
    def title(self) -> str:
        return self._title
    
    @property
    def status(self) -> LogStatus:
        return self._status
    
    @property
    def priority(self) -> LogPriority:
        return self._priority
    
    def update_status(self, new_status: LogStatus):
        """Update the log status."""
        old_status = self._status
        self._status = new_status
        
        if new_status == LogStatus.RESOLVED and old_status != LogStatus.RESOLVED:
            self._resolved_at = datetime.utcnow()
    
    def escalate_priority(self):
        """Escalate the priority of the log."""
        priority_order = [LogPriority.LOW, LogPriority.MEDIUM, LogPriority.HIGH, LogPriority.URGENT]
        current_index = priority_order.index(self._priority)
        if current_index < len(priority_order) - 1:
            self._priority = priority_order[current_index + 1]


# Repository Interfaces (Abstract)
class IUserRepository(ABC):
    """Abstract user repository interface."""
    
    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_email(self, email: Email) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def save(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def delete(self, user_id: UserId) -> bool:
        pass


class IConversationRepository(ABC):
    """Abstract conversation repository interface."""
    
    @abstractmethod
    async def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UserId) -> List[Conversation]:
        pass
    
    @abstractmethod
    async def save(self, conversation: Conversation) -> Conversation:
        pass
    
    @abstractmethod
    async def delete(self, conversation_id: int) -> bool:
        pass


class ICustomerLogRepository(ABC):
    """Abstract customer log repository interface."""
    
    @abstractmethod
    async def get_by_id(self, log_id: int) -> Optional[CustomerLog]:
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UserId) -> List[CustomerLog]:
        pass
    
    @abstractmethod
    async def save(self, log: CustomerLog) -> CustomerLog:
        pass
    
    @abstractmethod
    async def search(self, filters: Dict[str, Any]) -> List[CustomerLog]:
        pass


# Domain Services
class ConversationDomainService:
    """Domain service for conversation-related business logic."""
    
    @staticmethod
    def can_user_start_conversation(user: User) -> bool:
        """Check if user can start a new conversation."""
        if not user.is_active:
            return False
        
        # Business rule: Users can have max 10 active conversations
        active_conversations = [
            conv for conv in user.conversations 
            if conv.status == ConversationStatus.ACTIVE
        ]
        return len(active_conversations) < 10
    
    @staticmethod
    def should_auto_end_conversation(conversation: Conversation) -> bool:
        """Check if conversation should be automatically ended."""
        # Business rule: Auto-end conversations after 24 hours of inactivity
        if not conversation.messages:
            return False
        
        last_message = max(conversation.messages, key=lambda m: m.timestamp)
        hours_since_last_message = (datetime.utcnow() - last_message.timestamp).total_seconds() / 3600
        
        return hours_since_last_message >= 24


class AIResponseDomainService:
    """Domain service for AI response generation business logic."""
    
    @staticmethod
    def calculate_response_complexity(message_content: MessageContent) -> str:
        """Calculate response complexity based on message content."""
        text_length = len(message_content.text)
        
        if text_length < 50:
            return "simple"
        elif text_length < 200:
            return "medium"
        else:
            return "complex"
    
    @staticmethod
    def should_escalate_to_human(conversation: Conversation) -> bool:
        """Determine if conversation should be escalated to human agent."""
        # Business rule: Escalate if conversation has more than 10 messages
        # or if user expresses frustration
        if len(conversation.messages) > 10:
            return True
        
        # Check for frustration keywords in recent messages
        frustration_keywords = ["frustrated", "angry", "terrible", "worst", "horrible"]
        recent_user_messages = [
            msg for msg in conversation.messages[-5:] 
            if msg.role == MessageRole.USER
        ]
        
        for message in recent_user_messages:
            text_lower = message.content.text.lower()
            if any(keyword in text_lower for keyword in frustration_keywords):
                return True
        
        return False
