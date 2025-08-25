"""
Infrastructure Layer - Repository Implementations

This layer implements the repository interfaces defined in the domain layer,
providing concrete implementations for data access using SQLAlchemy.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc
from datetime import datetime
import logging

from app.domain.entities import (
    User, Conversation, CustomerLog,
    UserId, Email, MessageContent, MessageRole,
    ConversationStatus, LogPriority, LogStatus,
    IUserRepository, IConversationRepository, ICustomerLogRepository
)
from app.models.models import (
    User as UserModel,
    Conversation as ConversationModel,
    Message as MessageModel,
    CustomerLog as CustomerLogModel
)
from app.core.database import get_db

logger = logging.getLogger(__name__)


class SqlAlchemyUserRepository(IUserRepository):
    """SQLAlchemy implementation of user repository."""
    
    def __init__(self, db_session: Session):
        self._db = db_session
    
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        """Get user by ID."""
        user_model = self._db.query(UserModel).filter(
            UserModel.id == user_id.value
        ).first()
        
        if not user_model:
            return None
        
        return self._map_to_domain_entity(user_model)
    
    async def get_by_email(self, email: Email) -> Optional[User]:
        """Get user by email."""
        user_model = self._db.query(UserModel).filter(
            UserModel.email == email.value
        ).first()
        
        if not user_model:
            return None
        
        return self._map_to_domain_entity(user_model)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        user_model = self._db.query(UserModel).filter(
            UserModel.username == username
        ).first()
        
        if not user_model:
            return None
        
        return self._map_to_domain_entity(user_model)
    
    async def save(self, user: User) -> User:
        """Save user."""
        if user.id.value == 0:  # New user
            user_model = UserModel(
                email=user.email.value,
                username=user.username,
                full_name=user.full_name,
                is_active=user.is_active,
                is_admin=user.is_admin,
                hashed_password=""  # Should be set by caller
            )
            self._db.add(user_model)
            self._db.flush()  # Get the ID
            
            # Update domain entity with new ID
            user._id = UserId(user_model.id)
        else:
            # Update existing user
            user_model = self._db.query(UserModel).filter(
                UserModel.id == user.id.value
            ).first()
            
            if user_model:
                user_model.email = user.email.value
                user_model.username = user.username
                user_model.full_name = user.full_name
                user_model.is_active = user.is_active
                user_model.is_admin = user.is_admin
        
        self._db.commit()
        logger.info(f"User saved: {user.username}")
        return user
    
    async def delete(self, user_id: UserId) -> bool:
        """Delete user."""
        result = self._db.query(UserModel).filter(
            UserModel.id == user_id.value
        ).delete()
        
        self._db.commit()
        return result > 0
    
    def _map_to_domain_entity(self, user_model: UserModel) -> User:
        """Map SQLAlchemy model to domain entity."""
        user = User(
            user_id=UserId(user_model.id),
            email=Email(user_model.email),
            username=user_model.username,
            full_name=user_model.full_name,
            is_admin=user_model.is_admin
        )
        
        # Set private properties
        user._is_active = user_model.is_active
        user._created_at = user_model.created_at
        
        return user


class SqlAlchemyConversationRepository(IConversationRepository):
    """SQLAlchemy implementation of conversation repository."""
    
    def __init__(self, db_session: Session):
        self._db = db_session
    
    async def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID with messages."""
        conversation_model = self._db.query(ConversationModel).options(
            joinedload(ConversationModel.messages)
        ).filter(
            ConversationModel.id == conversation_id
        ).first()
        
        if not conversation_model:
            return None
        
        return self._map_to_domain_entity(conversation_model)
    
    async def get_by_user_id(self, user_id: UserId) -> List[Conversation]:
        """Get conversations by user ID."""
        conversation_models = self._db.query(ConversationModel).options(
            joinedload(ConversationModel.messages)
        ).filter(
            ConversationModel.user_id == user_id.value
        ).order_by(desc(ConversationModel.updated_at)).all()
        
        return [
            self._map_to_domain_entity(model) 
            for model in conversation_models
        ]
    
    async def save(self, conversation: Conversation) -> Conversation:
        """Save conversation with messages."""
        if conversation.id == id(conversation):  # New conversation (temporary ID)
            conversation_model = ConversationModel(
                user_id=conversation.user_id.value,
                title=conversation.title,
                is_active=conversation.status == ConversationStatus.ACTIVE
            )
            self._db.add(conversation_model)
            self._db.flush()  # Get the ID
            
            # Update domain entity with new ID
            conversation._id = conversation_model.id
        else:
            # Update existing conversation
            conversation_model = self._db.query(ConversationModel).filter(
                ConversationModel.id == conversation.id
            ).first()
            
            if conversation_model:
                conversation_model.title = conversation.title
                conversation_model.is_active = conversation.status == ConversationStatus.ACTIVE
        
        # Save messages
        for message in conversation.messages:
            if message.id == id(message):  # New message (temporary ID)
                message_model = MessageModel(
                    conversation_id=conversation.id,
                    content=message.content.text,
                    role=message.role.value,
                    tokens_used=message.tokens_used,
                    response_time=message.response_time_ms
                )
                self._db.add(message_model)
        
        self._db.commit()
        logger.info(f"Conversation saved: {conversation.id}")
        return conversation
    
    async def delete(self, conversation_id: int) -> bool:
        """Delete conversation and its messages."""
        # Delete messages first
        self._db.query(MessageModel).filter(
            MessageModel.conversation_id == conversation_id
        ).delete()
        
        # Delete conversation
        result = self._db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).delete()
        
        self._db.commit()
        return result > 0
    
    def _map_to_domain_entity(self, conversation_model: ConversationModel) -> Conversation:
        """Map SQLAlchemy model to domain entity."""
        conversation = Conversation(
            user_id=UserId(conversation_model.user_id),
            title=conversation_model.title,
            conversation_id=conversation_model.id
        )
        
        # Set status
        conversation._status = (
            ConversationStatus.ACTIVE if conversation_model.is_active
            else ConversationStatus.ENDED
        )
        conversation._created_at = conversation_model.created_at
        
        # Add messages
        for message_model in conversation_model.messages:
            message_content = MessageContent(message_model.content)
            message_role = MessageRole(message_model.role)
            
            message = conversation.add_message(
                content=message_content,
                role=message_role,
                tokens_used=message_model.tokens_used,
                response_time_ms=message_model.response_time
            )
            
            # Set the actual message ID and timestamp
            message._id = message_model.id
            message._timestamp = message_model.timestamp
        
        # Clear events since this is loaded from DB
        conversation._domain_events.clear()
        
        return conversation


class SqlAlchemyCustomerLogRepository(ICustomerLogRepository):
    """SQLAlchemy implementation of customer log repository."""
    
    def __init__(self, db_session: Session):
        self._db = db_session
    
    async def get_by_id(self, log_id: int) -> Optional[CustomerLog]:
        """Get customer log by ID."""
        log_model = self._db.query(CustomerLogModel).filter(
            CustomerLogModel.id == log_id
        ).first()
        
        if not log_model:
            return None
        
        return self._map_to_domain_entity(log_model)
    
    async def get_by_user_id(self, user_id: UserId) -> List[CustomerLog]:
        """Get customer logs by user ID."""
        log_models = self._db.query(CustomerLogModel).filter(
            CustomerLogModel.user_id == user_id.value
        ).order_by(desc(CustomerLogModel.created_at)).all()
        
        return [
            self._map_to_domain_entity(model) 
            for model in log_models
        ]
    
    async def save(self, log: CustomerLog) -> CustomerLog:
        """Save customer log."""
        if log.id == id(log):  # New log (temporary ID)
            log_model = CustomerLogModel(
                user_id=log.user_id.value,
                log_type=log._log_type,
                title=log.title,
                description=log._description,
                status=log.status.value,
                priority=log.priority.value,
                category=log._category
            )
            self._db.add(log_model)
            self._db.flush()  # Get the ID
            
            # Update domain entity with new ID
            log._id = log_model.id
        else:
            # Update existing log
            log_model = self._db.query(CustomerLogModel).filter(
                CustomerLogModel.id == log.id
            ).first()
            
            if log_model:
                log_model.title = log.title
                log_model.description = log._description
                log_model.status = log.status.value
                log_model.priority = log.priority.value
                log_model.category = log._category
                log_model.resolved_at = log._resolved_at
        
        self._db.commit()
        logger.info(f"Customer log saved: {log.id}")
        return log
    
    async def search(self, filters: Dict[str, Any]) -> List[CustomerLog]:
        """Search customer logs with filters."""
        query = self._db.query(CustomerLogModel)
        
        # Apply filters
        if filters.get("user_id"):
            query = query.filter(CustomerLogModel.user_id == filters["user_id"])
        
        if filters.get("status"):
            query = query.filter(CustomerLogModel.status == filters["status"])
        
        if filters.get("priority"):
            query = query.filter(CustomerLogModel.priority == filters["priority"])
        
        if filters.get("category"):
            query = query.filter(CustomerLogModel.category == filters["category"])
        
        if filters.get("date_from"):
            query = query.filter(CustomerLogModel.created_at >= filters["date_from"])
        
        if filters.get("date_to"):
            query = query.filter(CustomerLogModel.created_at <= filters["date_to"])
        
        # Apply search term
        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    CustomerLogModel.title.ilike(search_term),
                    CustomerLogModel.description.ilike(search_term)
                )
            )
        
        # Apply pagination
        limit = filters.get("limit", 50)
        offset = filters.get("offset", 0)
        
        log_models = query.order_by(
            desc(CustomerLogModel.created_at)
        ).limit(limit).offset(offset).all()
        
        return [
            self._map_to_domain_entity(model) 
            for model in log_models
        ]
    
    def _map_to_domain_entity(self, log_model: CustomerLogModel) -> CustomerLog:
        """Map SQLAlchemy model to domain entity."""
        customer_log = CustomerLog(
            user_id=UserId(log_model.user_id),
            log_type=log_model.log_type,
            title=log_model.title,
            description=log_model.description,
            priority=LogPriority(log_model.priority),
            category=log_model.category,
            log_id=log_model.id
        )
        
        # Set status and timestamps
        customer_log._status = LogStatus(log_model.status)
        customer_log._created_at = log_model.created_at
        customer_log._resolved_at = log_model.resolved_at
        
        return customer_log


# Repository Factory
class RepositoryFactory:
    """Factory for creating repository instances."""
    
    @staticmethod
    def create_user_repository(db_session: Session) -> IUserRepository:
        """Create user repository."""
        return SqlAlchemyUserRepository(db_session)
    
    @staticmethod
    def create_conversation_repository(db_session: Session) -> IConversationRepository:
        """Create conversation repository."""
        return SqlAlchemyConversationRepository(db_session)
    
    @staticmethod
    def create_customer_log_repository(db_session: Session) -> ICustomerLogRepository:
        """Create customer log repository."""
        return SqlAlchemyCustomerLogRepository(db_session)


# Unit of Work Pattern
class UnitOfWork:
    """Unit of Work pattern implementation."""
    
    def __init__(self, db_session: Session):
        self._db = db_session
        self._users = None
        self._conversations = None
        self._customer_logs = None
    
    @property
    def users(self) -> IUserRepository:
        """Get user repository."""
        if self._users is None:
            self._users = RepositoryFactory.create_user_repository(self._db)
        return self._users
    
    @property
    def conversations(self) -> IConversationRepository:
        """Get conversation repository."""
        if self._conversations is None:
            self._conversations = RepositoryFactory.create_conversation_repository(self._db)
        return self._conversations
    
    @property
    def customer_logs(self) -> ICustomerLogRepository:
        """Get customer log repository."""
        if self._customer_logs is None:
            self._customer_logs = RepositoryFactory.create_customer_log_repository(self._db)
        return self._customer_logs
    
    def commit(self):
        """Commit transaction."""
        self._db.commit()
    
    def rollback(self):
        """Rollback transaction."""
        self._db.rollback()
    
    def close(self):
        """Close session."""
        self._db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        self.close()


# Caching Layer
from abc import ABC, abstractmethod
import json
import pickle
from typing import Union


class ICacheService(ABC):
    """Abstract cache service interface."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass


class RedisCacheService(ICacheService):
    """Redis cache service implementation."""
    
    def __init__(self, redis_client):
        self._redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self._redis.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache."""
        try:
            serialized_value = pickle.dumps(value)
            await self._redis.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self._redis.exists(key)
        except Exception as e:
            logger.error(f"Error checking cache existence: {e}")
            return False


class InMemoryCacheService(ICacheService):
    """In-memory cache service for development/testing."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            cache_entry = self._cache[key]
            
            # Check if expired
            if datetime.utcnow().timestamp() > cache_entry["expires_at"]:
                del self._cache[key]
                return None
            
            return cache_entry["value"]
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache."""
        expires_at = datetime.utcnow().timestamp() + ttl
        self._cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
    
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        if key in self._cache:
            del self._cache[key]
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if key in self._cache:
            cache_entry = self._cache[key]
            
            # Check if expired
            if datetime.utcnow().timestamp() > cache_entry["expires_at"]:
                del self._cache[key]
                return False
            
            return True
        return False


# Cached Repository Decorator
class CachedRepository:
    """Decorator for adding caching to repositories."""
    
    def __init__(self, repository: IUserRepository, cache_service: ICacheService):
        self._repository = repository
        self._cache = cache_service
        self._cache_ttl = 3600  # 1 hour
    
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        """Get user by ID with caching."""
        cache_key = f"user:{user_id.value}"
        
        # Try cache first
        cached_user = await self._cache.get(cache_key)
        if cached_user:
            logger.debug(f"Cache hit for user {user_id.value}")
            return cached_user
        
        # Fallback to repository
        user = await self._repository.get_by_id(user_id)
        if user:
            await self._cache.set(cache_key, user, self._cache_ttl)
            logger.debug(f"Cached user {user_id.value}")
        
        return user
    
    async def save(self, user: User) -> User:
        """Save user and invalidate cache."""
        saved_user = await self._repository.save(user)
        
        # Invalidate cache
        cache_key = f"user:{saved_user.id.value}"
        await self._cache.delete(cache_key)
        
        return saved_user
    
    def __getattr__(self, name):
        """Delegate other methods to the original repository."""
        return getattr(self._repository, name)
