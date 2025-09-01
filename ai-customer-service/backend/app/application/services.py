"""
Application Services

This module contains application-level services that orchestrate domain logic
and coordinate between different layers of the application.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import logging
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
import json
from datetime import datetime, timedelta

from app.core.config import settings
from app.domain.entities import DomainEvent

logger = logging.getLogger(__name__)


class IPasswordService(ABC):
    """Interface for password hashing and verification."""
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        pass
    
    @abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        pass


class PasswordService(IPasswordService):
    """Password service implementation using bcrypt."""
    
    def __init__(self):
        import bcrypt
        self._bcrypt = bcrypt
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = self._bcrypt.gensalt()
        hashed = self._bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self._bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )


class IEventPublisher(ABC):
    """Interface for publishing domain events."""
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event."""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """Publish multiple domain events."""
        pass


class EventPublisher(IEventPublisher):
    """Event publisher implementation."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[callable]] = {}
        self._event_queue: List[DomainEvent] = []
    
    def subscribe(self, event_type: str, handler: callable):
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler to event: {event_type}")
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event."""
        event_type = type(event).__name__
        
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error handling event {event_type}: {e}")
        
        # Store event for audit purposes
        self._event_queue.append(event)
        logger.debug(f"Published event: {event_type}")
    
    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """Publish multiple domain events."""
        for event in events:
            await self.publish(event)


class ICacheService(ABC):
    """Interface for caching operations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, expire_seconds: int = 3600) -> None:
        """Set a value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        pass


class CacheService(ICacheService):
    """Redis-based cache service."""
    
    def __init__(self):
        try:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis.ping()  # Test connection
            logger.info("Redis cache service initialized")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self._memory_cache: Dict[str, Dict[str, Any]] = {}
            self._redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            if self._redis:
                value = self._redis.get(key)
                if value:
                    return json.loads(value)
            else:
                # Use in-memory cache
                if key in self._memory_cache:
                    cache_item = self._memory_cache[key]
                    if cache_item['expires_at'] > datetime.utcnow():
                        return cache_item['value']
                    else:
                        del self._memory_cache[key]
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, expire_seconds: int = 3600) -> None:
        """Set a value in cache."""
        try:
            if self._redis:
                self._redis.setex(key, expire_seconds, json.dumps(value))
            else:
                # Use in-memory cache
                expires_at = datetime.utcnow() + timedelta(seconds=expire_seconds)
                self._memory_cache[key] = {
                    'value': value,
                    'expires_at': expires_at
                }
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete a value from cache."""
        try:
            if self._redis:
                self._redis.delete(key)
            else:
                self._memory_cache.pop(key, None)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            if self._redis:
                return bool(self._redis.exists(key))
            else:
                if key in self._memory_cache:
                    cache_item = self._memory_cache[key]
                    if cache_item['expires_at'] > datetime.utcnow():
                        return True
                    else:
                        del self._memory_cache[key]
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
        return False


class IEmailService(ABC):
    """Interface for email operations."""
    
    @abstractmethod
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> bool:
        """Send an email."""
        pass


class EmailService(IEmailService):
    """Email service implementation."""
    
    def __init__(self):
        self._smtp_server = getattr(settings, 'SMTP_SERVER', 'localhost')
        self._smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self._smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self._smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self._from_email = getattr(settings, 'FROM_EMAIL', 'noreply@example.com')
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> bool:
        """Send an email."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self._from_email
            msg['To'] = to_email
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Note: In production, this should use async SMTP
            # For now, this is a synchronous implementation
            with smtplib.SMTP(self._smtp_server, self._smtp_port) as server:
                if self._smtp_username:
                    server.starttls()
                    server.login(self._smtp_username, self._smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False


class IAIServiceInterface(ABC):
    """Interface for AI service operations."""
    
    @abstractmethod
    async def generate_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        context_type: str = "customer_service",
        additional_context: str = ""
    ) -> Dict[str, Any]:
        """Generate an AI response."""
        pass
    
    @abstractmethod
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        pass
    
    @abstractmethod
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text."""
        pass


class CommandBus:
    """Command bus for handling commands."""
    
    def __init__(self):
        self._handlers: Dict[str, Any] = {}
    
    def register(self, command_type: str, handler: Any):
        """Register a command handler."""
        self._handlers[command_type] = handler
        logger.debug(f"Registered command handler: {command_type}")
    
    async def send(self, command: Any) -> Any:
        """Send a command to its handler."""
        command_type = type(command).__name__
        
        if command_type not in self._handlers:
            raise ValueError(f"No handler registered for command: {command_type}")
        
        handler = self._handlers[command_type]
        
        if asyncio.iscoroutinefunction(handler.handle):
            return await handler.handle(command)
        else:
            return handler.handle(command)


class QueryBus:
    """Query bus for handling queries."""
    
    def __init__(self):
        self._handlers: Dict[str, Any] = {}
    
    def register(self, query_type: str, handler: Any):
        """Register a query handler."""
        self._handlers[query_type] = handler
        logger.debug(f"Registered query handler: {query_type}")
    
    async def send(self, query: Any) -> Any:
        """Send a query to its handler."""
        query_type = type(query).__name__
        
        if query_type not in self._handlers:
            raise ValueError(f"No handler registered for query: {query_type}")
        
        handler = self._handlers[query_type]
        
        if asyncio.iscoroutinefunction(handler.handle):
            return await handler.handle(query)
        else:
            return handler.handle(query)
