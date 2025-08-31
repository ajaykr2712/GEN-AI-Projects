"""
Dependency Injection Container

This module provides a centralized dependency injection container for managing
service lifetimes and dependencies throughout the application.
"""

from typing import Dict, Any, TypeVar, Callable
from functools import lru_cache
import logging

from app.core.database import SessionLocal
from app.infrastructure.repositories import (
    SqlAlchemyUserRepository, 
    SqlAlchemyConversationRepository, 
    SqlAlchemyCustomerLogRepository
)
from app.application.handlers import (
    CreateUserCommandHandler, 
    UpdateUserCommandHandler, 
    SendMessageCommandHandler,
    GetUserQueryHandler,
    GetConversationQueryHandler,
    CreateConversationCommandHandler
)
from app.application.services import (
    PasswordService, 
    EventPublisher, 
    CommandBus, 
    QueryBus,
    CacheService,
    EmailService
)
from app.services.ai_service import AIService, ai_service
from app.core.socket_manager import SocketManager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Container:
    """
    Centralized dependency injection container.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}

        # Register core services
        self.register_singleton(SocketManager, SocketManager())
        self.register_singleton(PasswordService, PasswordService())
        self.register_singleton(EventPublisher, EventPublisher())
        self.register_singleton(CacheService, CacheService())
        self.register_singleton(EmailService, EmailService())
        self.register_singleton("AIService", ai_service)
    
    def register_singleton(self, interface: str, implementation: Any):
        """Register a singleton service."""
        self._singletons[interface] = implementation
        logger.debug(f"Registered singleton: {interface}")
    
    def register_factory(self, interface: str, factory: Callable):
        """Register a factory function for creating services."""
        self._factories[interface] = factory
        logger.debug(f"Registered factory: {interface}")
    
    def register_transient(self, interface: str, implementation: Any):
        """Register a transient service (new instance each time)."""
        self._services[interface] = implementation
        logger.debug(f"Registered transient: {interface}")
    
    def get(self, interface: str) -> Any:
        """Get a service instance."""
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check factories
        if interface in self._factories:
            instance = self._factories[interface]()
            return instance
        
        # Check transient services
        if interface in self._services:
            service_class = self._services[interface]
            if callable(service_class):
                return service_class()
            return service_class
        
        raise KeyError(f"Service not registered: {interface}")


# Global container instance
container = Container()


def configure_container():
    """Configure the dependency injection container with all services."""
    
    # Register database repositories
    container.register_factory(
        "IUserRepository",
        lambda: SqlAlchemyUserRepository(SessionLocal())
    )
    
    container.register_factory(
        "IConversationRepository", 
        lambda: SqlAlchemyConversationRepository(SessionLocal())
    )
    
    container.register_factory(
        "ICustomerLogRepository",
        lambda: SqlAlchemyCustomerLogRepository(SessionLocal())
    )
    
    # Register application services
    container.register_singleton("PasswordService", PasswordService())
    container.register_singleton("EventPublisher", EventPublisher())
    container.register_singleton("AIService", ai_service)
    container.register_singleton("CacheService", CacheService())
    container.register_singleton("EmailService", EmailService())
    
    # Register command handlers
    container.register_factory(
        "CreateUserCommandHandler",
        lambda: CreateUserCommandHandler(
            container.get("IUserRepository"),
            container.get("PasswordService"),
            container.get("EventPublisher")
        )
    )
    
    container.register_factory(
        "UpdateUserCommandHandler",
        lambda: UpdateUserCommandHandler(
            container.get("IUserRepository"),
            container.get("EventPublisher")
        )
    )
    
    container.register_factory(
        "SendMessageCommandHandler",
        lambda: SendMessageCommandHandler(
            container.get("IConversationRepository"),
            container.get("AIService"),
            container.get("EventPublisher")
        )
    )
    
    container.register_factory(
        "CreateConversationCommandHandler",
        lambda: CreateConversationCommandHandler(
            container.get("IConversationRepository"),
            container.get("IUserRepository"),
            container.get("EventPublisher")
        )
    )
    
    # Register query handlers
    container.register_factory(
        "GetUserQueryHandler",
        lambda: GetUserQueryHandler(container.get("IUserRepository"))
    )
    
    container.register_factory(
        "GetConversationQueryHandler",
        lambda: GetConversationQueryHandler(container.get("IConversationRepository"))
    )
    
    # Register buses
    command_bus = CommandBus()
    query_bus = QueryBus()
    
    # Register command handlers with bus
    command_bus.register("CreateUserCommand", container.get("CreateUserCommandHandler"))
    command_bus.register("UpdateUserCommand", container.get("UpdateUserCommandHandler"))
    command_bus.register("SendMessageCommand", container.get("SendMessageCommandHandler"))
    command_bus.register("CreateConversationCommand", container.get("CreateConversationCommandHandler"))
    
    # Register query handlers with bus
    query_bus.register("GetUserQuery", container.get("GetUserQueryHandler"))
    query_bus.register("GetConversationQuery", container.get("GetConversationQueryHandler"))
    
    container.register_singleton("CommandBus", command_bus)
    container.register_singleton("QueryBus", query_bus)
    
    logger.info("Dependency injection container configured successfully")


# Initialize the container
container = Container()

# Dependency-injection providers
@lru_cache(maxsize=None)
def get_socket_manager() -> SocketManager:
    return container.resolve(SocketManager)

@lru_cache(maxsize=None)
def get_password_service() -> PasswordService:
    return container.resolve(PasswordService)


@lru_cache(maxsize=None)
def get_event_publisher() -> EventPublisher:
    return container.resolve(EventPublisher)


@lru_cache(maxsize=None)
def get_ai_service() -> AIService:
    return container.resolve(AIService)


@lru_cache(maxsize=None)
def get_query_bus() -> QueryBus:
    """Get the query bus instance."""
    return container.get("QueryBus")
