"""
Enhanced API Layer with Advanced Patterns

This module implements advanced FastAPI patterns including:
- Dependency injection
- Request/Response models
- Error handling
- Rate limiting
- API versioning
- Documentation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging
from contextlib import asynccontextmanager

from app.core.database import get_db
from app.core.config import settings
from app.application.handlers import (
    ConversationApplicationService,
    StartConversationCommand,
    SendMessageCommand,
    GetUserConversationsQuery,
    CreateUserCommand,
    CommandBus,
    QueryBus
)
from app.infrastructure.repositories import UnitOfWork
from app.domain.entities import UserId, Email

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Rate limiting
class RateLimiter:
    """Simple rate limiter implementation."""
    
    def __init__(self):
        self._requests: Dict[str, List[datetime]] = {}
        self._max_requests = 60
        self._window_minutes = 1
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self._window_minutes)
        
        # Clean old requests
        if identifier in self._requests:
            self._requests[identifier] = [
                req_time for req_time in self._requests[identifier]
                if req_time > window_start
            ]
        else:
            self._requests[identifier] = []
        
        # Check limit
        if len(self._requests[identifier]) >= self._max_requests:
            return False
        
        # Add current request
        self._requests[identifier].append(now)
        return True

rate_limiter = RateLimiter()

# Dependency injection
async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter dependency."""
    return rate_limiter

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> int:
    """Get current authenticated user ID."""
    # Implement JWT token validation here
    # For now, return a mock user ID
    return 1

async def check_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """Check rate limiting."""
    client_ip = request.client.host
    if not await limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )

async def get_unit_of_work(db: Session = Depends(get_db)) -> UnitOfWork:
    """Get unit of work dependency."""
    return UnitOfWork(db)

# Request/Response Models
from pydantic import BaseModel, Field, validator
from typing import Literal

class StartConversationRequest(BaseModel):
    """Request model for starting a conversation."""
    title: Optional[str] = Field(None, max_length=200, description="Conversation title")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Help with billing question"
            }
        }

class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    message: str = Field(..., min_length=1, max_length=10000, description="Message content")
    generate_ai_response: bool = Field(True, description="Whether to generate AI response")
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty or just whitespace')
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "message": "I'm having trouble with my account login",
                "generate_ai_response": True
            }
        }

class MessageResponse(BaseModel):
    """Response model for a message."""
    id: int
    content: str
    role: Literal["user", "assistant", "system"]
    timestamp: datetime
    tokens_used: int = 0
    response_time_ms: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "content": "Hello, how can I help you?",
                "role": "assistant",
                "timestamp": "2024-01-01T12:00:00Z",
                "tokens_used": 15,
                "response_time_ms": 250
            }
        }

class ConversationResponse(BaseModel):
    """Response model for a conversation."""
    id: int
    title: str
    status: Literal["active", "ended", "archived"]
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "title": "Help with billing",
                "status": "active",
                "message_count": 5,
                "last_message_at": "2024-01-01T12:30:00Z",
                "created_at": "2024-01-01T12:00:00Z"
            }
        }

class ChatResponse(BaseModel):
    """Response model for chat interaction."""
    conversation_id: int
    user_message: MessageResponse
    ai_response: Optional[MessageResponse] = None
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": 1,
                "user_message": {
                    "id": 1,
                    "content": "I need help",
                    "role": "user",
                    "timestamp": "2024-01-01T12:00:00Z"
                },
                "ai_response": {
                    "id": 2,
                    "content": "I'm here to help! What can I assist you with?",
                    "role": "assistant",
                    "timestamp": "2024-01-01T12:00:01Z",
                    "tokens_used": 20,
                    "response_time_ms": 300
                }
            }
        }

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str
    timestamp: datetime
    request_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "detail": "Message content is required",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_12345"
            }
        }

# API Router
router = APIRouter(prefix="/api/v1", tags=["Chat API v1"])

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
    description="Create a new conversation for the authenticated user",
    responses={
        201: {"description": "Conversation created successfully"},
        400: {"description": "Invalid request data", "model": ErrorResponse},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
    }
)
async def start_conversation(
    request: StartConversationRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_unit_of_work),
    _: None = Depends(check_rate_limit)
) -> ConversationResponse:
    """Start a new conversation."""
    try:
        # Create conversation through application service
        command = StartConversationCommand(user_id=user_id, title=request.title)
        
        # Here you would use the command bus
        # conversation = await command_bus.execute(command)
        
        # For now, simulate the response
        response = ConversationResponse(
            id=1,
            title=request.title or "New Conversation",
            status="active",
            message_count=0,
            last_message_at=None,
            created_at=datetime.utcnow()
        )
        
        # Add background task for analytics
        background_tasks.add_task(track_conversation_started, user_id, response.id)
        
        logger.info(f"Conversation started for user {user_id}")
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatResponse,
    summary="Send a message in a conversation",
    description="Send a message to an AI assistant and optionally get a response",
    responses={
        200: {"description": "Message sent successfully"},
        400: {"description": "Invalid request data", "model": ErrorResponse},
        401: {"description": "Authentication required"},
        404: {"description": "Conversation not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
async def send_message(
    conversation_id: int,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_unit_of_work),
    _: None = Depends(check_rate_limit)
) -> ChatResponse:
    """Send a message in a conversation."""
    try:
        # Validate conversation exists and user has access
        conversation = await uow.conversations.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        if conversation.user_id.value != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        # Create command
        command = SendMessageCommand(
            conversation_id=conversation_id,
            user_id=user_id,
            message_content=request.message,
            generate_ai_response=request.generate_ai_response
        )
        
        # Execute command (would use command bus in real implementation)
        # result = await command_bus.execute(command)
        
        # For now, simulate the response
        user_message = MessageResponse(
            id=1,
            content=request.message,
            role="user",
            timestamp=datetime.utcnow()
        )
        
        ai_response = None
        if request.generate_ai_response:
            ai_response = MessageResponse(
                id=2,
                content="Thank you for your message. How can I assist you today?",
                role="assistant",
                timestamp=datetime.utcnow(),
                tokens_used=25,
                response_time_ms=300
            )
        
        response = ChatResponse(
            conversation_id=conversation_id,
            user_message=user_message,
            ai_response=ai_response
        )
        
        # Add background tasks
        background_tasks.add_task(track_message_sent, user_id, conversation_id)
        if ai_response:
            background_tasks.add_task(update_ai_metrics, ai_response.tokens_used, ai_response.response_time_ms)
        
        logger.info(f"Message sent in conversation {conversation_id}")
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    summary="Get user conversations",
    description="Retrieve all conversations for the authenticated user",
    responses={
        200: {"description": "Conversations retrieved successfully"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
    }
)
async def get_conversations(
    include_archived: bool = False,
    limit: int = Field(50, ge=1, le=100),
    offset: int = Field(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_unit_of_work),
    _: None = Depends(check_rate_limit)
) -> List[ConversationResponse]:
    """Get user conversations."""
    try:
        # Create query
        query = GetUserConversationsQuery(
            user_id=user_id,
            include_archived=include_archived,
            limit=limit,
            offset=offset
        )
        
        # Execute query (would use query bus in real implementation)
        # conversations = await query_bus.execute(query)
        
        # For now, return mock data
        conversations = [
            ConversationResponse(
                id=1,
                title="Help with billing",
                status="active",
                message_count=3,
                last_message_at=datetime.utcnow() - timedelta(hours=1),
                created_at=datetime.utcnow() - timedelta(hours=2)
            ),
            ConversationResponse(
                id=2,
                title="Technical support",
                status="ended",
                message_count=8,
                last_message_at=datetime.utcnow() - timedelta(days=1),
                created_at=datetime.utcnow() - timedelta(days=1, hours=2)
            )
        ]
        
        logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
        return conversations
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="Get conversation messages",
    description="Retrieve all messages from a conversation",
    responses={
        200: {"description": "Messages retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "Conversation not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Field(100, ge=1, le=500),
    offset: int = Field(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_unit_of_work),
    _: None = Depends(check_rate_limit)
) -> List[MessageResponse]:
    """Get conversation messages."""
    try:
        # Validate conversation access
        conversation = await uow.conversations.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        if conversation.user_id.value != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        # For now, return mock messages
        messages = [
            MessageResponse(
                id=1,
                content="Hello, I need help with my account",
                role="user",
                timestamp=datetime.utcnow() - timedelta(minutes=10)
            ),
            MessageResponse(
                id=2,
                content="I'd be happy to help you with your account. What specific issue are you experiencing?",
                role="assistant",
                timestamp=datetime.utcnow() - timedelta(minutes=9),
                tokens_used=30,
                response_time_ms=250
            )
        ]
        
        logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Delete a conversation and all its messages",
    responses={
        204: {"description": "Conversation deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "Conversation not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
async def delete_conversation(
    conversation_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_unit_of_work),
    _: None = Depends(check_rate_limit)
):
    """Delete a conversation."""
    try:
        # Validate conversation exists and user has access
        conversation = await uow.conversations.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        if conversation.user_id.value != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        # Delete conversation
        await uow.conversations.delete(conversation_id)
        
        # Add background task for cleanup
        background_tasks.add_task(cleanup_conversation_data, conversation_id)
        
        logger.info(f"Conversation {conversation_id} deleted by user {user_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Background tasks
async def track_conversation_started(user_id: int, conversation_id: int):
    """Background task to track conversation started."""
    logger.info(f"Analytics: Conversation {conversation_id} started by user {user_id}")
    # Implement analytics tracking here

async def track_message_sent(user_id: int, conversation_id: int):
    """Background task to track message sent."""
    logger.info(f"Analytics: Message sent in conversation {conversation_id} by user {user_id}")
    # Implement analytics tracking here

async def update_ai_metrics(tokens_used: int, response_time_ms: int):
    """Background task to update AI metrics."""
    logger.info(f"AI Metrics: {tokens_used} tokens used, {response_time_ms}ms response time")
    # Implement metrics tracking here

async def cleanup_conversation_data(conversation_id: int):
    """Background task to cleanup conversation data."""
    logger.info(f"Cleanup: Removing analytics data for conversation {conversation_id}")
    # Implement cleanup logic here

# Error handlers
@router.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="ValidationError",
            detail=str(exc),
            timestamp=datetime.utcnow(),
            request_id=getattr(request.state, "request_id", None)
        ).dict()
    )

@router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            detail="An internal server error occurred",
            timestamp=datetime.utcnow(),
            request_id=getattr(request.state, "request_id", None)
        ).dict()
    )

# Health check
@router.get(
    "/health",
    summary="Health check",
    description="Check the health status of the API",
    responses={
        200: {"description": "API is healthy"},
        503: {"description": "API is unhealthy"},
    }
)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connectivity
        # Check external services
        # Check cache connectivity
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "version": settings.VERSION,
            "environment": getattr(settings, "ENVIRONMENT", "development")
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

# Metrics endpoint
@router.get(
    "/metrics",
    summary="API metrics",
    description="Get API performance and usage metrics",
    responses={
        200: {"description": "Metrics retrieved successfully"},
        401: {"description": "Authentication required"},
    }
)
async def get_metrics(
    user_id: int = Depends(get_current_user_id)
):
    """Get API metrics."""
    try:
        # Calculate metrics
        metrics = {
            "total_conversations": 150,
            "total_messages": 1250,
            "avg_response_time_ms": 285,
            "active_users_24h": 45,
            "ai_tokens_used_24h": 12500,
            "error_rate_24h": 0.02,
            "uptime_percentage": 99.9
        }
        
        return {
            "metrics": metrics,
            "timestamp": datetime.utcnow(),
            "period": "24h"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving metrics"
        )
