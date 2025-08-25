"""
Application Layer - Use Cases and Command/Query Handlers

This layer implements the CQRS pattern, separating command operations (writes)
from query operations (reads) for better scalability and maintainability.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from app.domain.entities import (
    User, Conversation, Message, CustomerLog,
    UserId, Email, MessageContent, MessageRole,
    ConversationStatus, LogPriority, LogStatus,
    IUserRepository, IConversationRepository, ICustomerLogRepository,
    ConversationDomainService, AIResponseDomainService,
    DomainEvent
)

logger = logging.getLogger(__name__)


# Command/Query Base Classes
@dataclass
class Command:
    """Base class for all commands."""
    pass


@dataclass
class Query:
    """Base class for all queries."""
    pass


class CommandHandler(ABC):
    """Abstract base class for command handlers."""
    
    @abstractmethod
    async def handle(self, command: Command) -> Any:
        pass


class QueryHandler(ABC):
    """Abstract base class for query handlers."""
    
    @abstractmethod
    async def handle(self, query: Query) -> Any:
        pass


# User Commands and Handlers
@dataclass
class CreateUserCommand(Command):
    """Command to create a new user."""
    email: str
    username: str
    password: str
    full_name: Optional[str] = None


@dataclass
class UpdateUserCommand(Command):
    """Command to update user information."""
    user_id: int
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None


@dataclass
class DeactivateUserCommand(Command):
    """Command to deactivate a user."""
    user_id: int


class CreateUserCommandHandler(CommandHandler):
    """Handler for creating new users."""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        password_service: 'IPasswordService',
        event_publisher: 'IEventPublisher'
    ):
        self._user_repository = user_repository
        self._password_service = password_service
        self._event_publisher = event_publisher
    
    async def handle(self, command: CreateUserCommand) -> User:
        """Handle user creation command."""
        # Validate email format
        email = Email(command.email)
        
        # Check if user already exists
        existing_user = await self._user_repository.get_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {command.email} already exists")
        
        existing_username = await self._user_repository.get_by_username(command.username)
        if existing_username:
            raise ValueError(f"User with username {command.username} already exists")
        
        # Hash password
        hashed_password = await self._password_service.hash_password(command.password)
        
        # Create user entity
        user = User(
            user_id=UserId(0),  # Will be set by repository
            email=email,
            username=command.username,
            full_name=command.full_name
        )
        
        # Save user
        saved_user = await self._user_repository.save(user)
        
        # Publish domain events
        events = saved_user.get_domain_events()
        for event in events:
            await self._event_publisher.publish(event)
        
        logger.info(f"User created successfully: {saved_user.username}")
        return saved_user


# Conversation Commands and Handlers
@dataclass
class StartConversationCommand(Command):
    """Command to start a new conversation."""
    user_id: int
    title: Optional[str] = None


@dataclass
class SendMessageCommand(Command):
    """Command to send a message in a conversation."""
    conversation_id: int
    user_id: int
    message_content: str
    generate_ai_response: bool = True


@dataclass
class EndConversationCommand(Command):
    """Command to end a conversation."""
    conversation_id: int
    user_id: int


class StartConversationCommandHandler(CommandHandler):
    """Handler for starting new conversations."""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        conversation_repository: IConversationRepository,
        event_publisher: 'IEventPublisher'
    ):
        self._user_repository = user_repository
        self._conversation_repository = conversation_repository
        self._event_publisher = event_publisher
    
    async def handle(self, command: StartConversationCommand) -> Conversation:
        """Handle start conversation command."""
        # Get user
        user_id = UserId(command.user_id)
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {command.user_id} not found")
        
        # Check business rules
        if not ConversationDomainService.can_user_start_conversation(user):
            raise ValueError("User cannot start a new conversation at this time")
        
        # Create conversation
        title = command.title or "New Conversation"
        conversation = user.start_conversation(title)
        
        # Save conversation
        saved_conversation = await self._conversation_repository.save(conversation)
        
        # Publish domain events
        events = user.get_domain_events()
        for event in events:
            await self._event_publisher.publish(event)
        
        logger.info(f"Conversation started: {saved_conversation.id}")
        return saved_conversation


class SendMessageCommandHandler(CommandHandler):
    """Handler for sending messages."""
    
    def __init__(
        self,
        conversation_repository: IConversationRepository,
        ai_service: 'IAIService',
        event_publisher: 'IEventPublisher'
    ):
        self._conversation_repository = conversation_repository
        self._ai_service = ai_service
        self._event_publisher = event_publisher
    
    async def handle(self, command: SendMessageCommand) -> Dict[str, Any]:
        """Handle send message command."""
        # Get conversation
        conversation = await self._conversation_repository.get_by_id(command.conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {command.conversation_id} not found")
        
        # Validate user ownership
        if conversation.user_id.value != command.user_id:
            raise ValueError("User does not own this conversation")
        
        # Create message content
        content = MessageContent(command.message_content)
        
        # Add user message
        user_message = conversation.add_message(
            content=content,
            role=MessageRole.USER
        )
        
        ai_response = None
        if command.generate_ai_response:
            # Generate AI response
            response_data = await self._ai_service.generate_response(
                message=command.message_content,
                conversation_history=self._build_conversation_history(conversation),
                context_type="customer_service"
            )
            
            # Add AI response message
            ai_content = MessageContent(response_data["response"])
            ai_response = conversation.add_message(
                content=ai_content,
                role=MessageRole.ASSISTANT,
                tokens_used=response_data.get("tokens_used", 0),
                response_time_ms=response_data.get("response_time", 0)
            )
            
            # Check if conversation should be escalated
            if AIResponseDomainService.should_escalate_to_human(conversation):
                # Add escalation logic here
                logger.info(f"Conversation {conversation.id} should be escalated to human")
        
        # Save conversation
        await self._conversation_repository.save(conversation)
        
        # Publish domain events
        events = conversation.get_domain_events()
        for event in events:
            await self._event_publisher.publish(event)
        
        result = {
            "user_message": user_message,
            "ai_response": ai_response,
            "conversation_id": conversation.id
        }
        
        logger.info(f"Message sent in conversation {conversation.id}")
        return result
    
    def _build_conversation_history(self, conversation: Conversation) -> List[Dict[str, str]]:
        """Build conversation history for AI service."""
        history = []
        for message in conversation.messages[-10:]:  # Last 10 messages
            history.append({
                "role": message.role.value,
                "content": message.content.text
            })
        return history


# Query Models (Read Models)
@dataclass
class UserQueryModel:
    """Read model for user data."""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    conversation_count: int


@dataclass
class ConversationQueryModel:
    """Read model for conversation data."""
    id: int
    user_id: int
    title: str
    status: str
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime


@dataclass
class MessageQueryModel:
    """Read model for message data."""
    id: int
    conversation_id: int
    content: str
    role: str
    timestamp: datetime
    tokens_used: int
    response_time_ms: int


# Queries
@dataclass
class GetUserByIdQuery(Query):
    """Query to get user by ID."""
    user_id: int


@dataclass
class GetUserConversationsQuery(Query):
    """Query to get user's conversations."""
    user_id: int
    include_archived: bool = False
    limit: int = 50
    offset: int = 0


@dataclass
class GetConversationMessagesQuery(Query):
    """Query to get conversation messages."""
    conversation_id: int
    user_id: int
    limit: int = 100
    offset: int = 0


@dataclass
class SearchCustomerLogsQuery(Query):
    """Query to search customer logs."""
    user_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


@dataclass
class GetAnalyticsQuery(Query):
    """Query to get analytics data."""
    date_from: datetime
    date_to: datetime
    user_id: Optional[int] = None


# Query Handlers
class GetUserByIdQueryHandler(QueryHandler):
    """Handler for getting user by ID."""
    
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository
    
    async def handle(self, query: GetUserByIdQuery) -> Optional[UserQueryModel]:
        """Handle get user by ID query."""
        user_id = UserId(query.user_id)
        user = await self._user_repository.get_by_id(user_id)
        
        if not user:
            return None
        
        return UserQueryModel(
            id=user.id.value,
            email=user.email.value,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user._created_at,
            conversation_count=len(user.conversations)
        )


class GetUserConversationsQueryHandler(QueryHandler):
    """Handler for getting user conversations."""
    
    def __init__(self, conversation_repository: IConversationRepository):
        self._conversation_repository = conversation_repository
    
    async def handle(self, query: GetUserConversationsQuery) -> List[ConversationQueryModel]:
        """Handle get user conversations query."""
        user_id = UserId(query.user_id)
        conversations = await self._conversation_repository.get_by_user_id(user_id)
        
        # Filter based on query parameters
        filtered_conversations = conversations
        if not query.include_archived:
            filtered_conversations = [
                conv for conv in conversations 
                if conv.status != ConversationStatus.ARCHIVED
            ]
        
        # Apply pagination
        start = query.offset
        end = start + query.limit
        paginated_conversations = filtered_conversations[start:end]
        
        # Convert to query models
        result = []
        for conversation in paginated_conversations:
            last_message_at = None
            if conversation.messages:
                last_message_at = max(msg.timestamp for msg in conversation.messages)
            
            result.append(ConversationQueryModel(
                id=conversation.id,
                user_id=conversation.user_id.value,
                title=conversation.title,
                status=conversation.status.value,
                message_count=len(conversation.messages),
                last_message_at=last_message_at,
                created_at=conversation._created_at
            ))
        
        return result


# Application Services
class ConversationApplicationService:
    """Application service for conversation use cases."""
    
    def __init__(
        self,
        start_conversation_handler: StartConversationCommandHandler,
        send_message_handler: SendMessageCommandHandler,
        get_conversations_handler: GetUserConversationsQueryHandler,
        get_messages_handler: 'GetConversationMessagesQueryHandler'
    ):
        self._start_conversation_handler = start_conversation_handler
        self._send_message_handler = send_message_handler
        self._get_conversations_handler = get_conversations_handler
        self._get_messages_handler = get_messages_handler
    
    async def start_conversation(self, user_id: int, title: Optional[str] = None) -> Conversation:
        """Start a new conversation."""
        command = StartConversationCommand(user_id=user_id, title=title)
        return await self._start_conversation_handler.handle(command)
    
    async def send_message(
        self, 
        conversation_id: int, 
        user_id: int, 
        message: str
    ) -> Dict[str, Any]:
        """Send a message and get AI response."""
        command = SendMessageCommand(
            conversation_id=conversation_id,
            user_id=user_id,
            message_content=message
        )
        return await self._send_message_handler.handle(command)
    
    async def get_user_conversations(
        self, 
        user_id: int, 
        include_archived: bool = False
    ) -> List[ConversationQueryModel]:
        """Get user's conversations."""
        query = GetUserConversationsQuery(
            user_id=user_id,
            include_archived=include_archived
        )
        return await self._get_conversations_handler.handle(query)


# Event Publishing
class IEventPublisher(ABC):
    """Abstract event publisher interface."""
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        pass


class InMemoryEventPublisher(IEventPublisher):
    """In-memory event publisher for development/testing."""
    
    def __init__(self):
        self._handlers: Dict[type, List[callable]] = {}
    
    def subscribe(self, event_type: type, handler: callable):
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers."""
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error handling event {event_type}: {e}")


# Service Interfaces
class IPasswordService(ABC):
    """Abstract password service interface."""
    
    @abstractmethod
    async def hash_password(self, password: str) -> str:
        pass
    
    @abstractmethod
    async def verify_password(self, password: str, hashed: str) -> bool:
        pass


class IAIService(ABC):
    """Abstract AI service interface."""
    
    @abstractmethod
    async def generate_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        context_type: str
    ) -> Dict[str, Any]:
        pass


# Command/Query Bus
class CommandBus:
    """Command bus for routing commands to handlers."""
    
    def __init__(self):
        self._handlers: Dict[type, CommandHandler] = {}
    
    def register_handler(self, command_type: type, handler: CommandHandler):
        """Register a command handler."""
        self._handlers[command_type] = handler
    
    async def execute(self, command: Command) -> Any:
        """Execute a command."""
        command_type = type(command)
        if command_type not in self._handlers:
            raise ValueError(f"No handler registered for command {command_type}")
        
        handler = self._handlers[command_type]
        return await handler.handle(command)


class QueryBus:
    """Query bus for routing queries to handlers."""
    
    def __init__(self):
        self._handlers: Dict[type, QueryHandler] = {}
    
    def register_handler(self, query_type: type, handler: QueryHandler):
        """Register a query handler."""
        self._handlers[query_type] = handler
    
    async def execute(self, query: Query) -> Any:
        """Execute a query."""
        query_type = type(query)
        if query_type not in self._handlers:
            raise ValueError(f"No handler registered for query {query_type}")
        
        handler = self._handlers[query_type]
        return await handler.handle(query)
