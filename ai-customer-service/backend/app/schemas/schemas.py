from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Message Schemas
class MessageBase(BaseModel):
    content: str
    role: str

class MessageCreate(MessageBase):
    conversation_id: int

class Message(MessageBase):
    id: int
    conversation_id: int
    timestamp: datetime
    tokens_used: int
    response_time: int
    
    class Config:
        from_attributes = True

# Conversation Schemas
class ConversationBase(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    messages: List[Message] = []
    
    class Config:
        from_attributes = True

# Customer Log Schemas
class CustomerLogBase(BaseModel):
    log_type: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    category: Optional[str] = None

class CustomerLogCreate(CustomerLogBase):
    pass

class CustomerLogUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None

class CustomerLog(CustomerLogBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# FAQ Schemas
class FAQBase(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    tags: Optional[str] = None

class FAQCreate(FAQBase):
    pass

class FAQ(FAQBase):
    id: int
    is_active: bool
    view_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Chat Schemas
class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    tokens_used: int
    response_time: int

# Analytics Schemas
class AnalyticsData(BaseModel):
    total_conversations: int
    total_messages: int
    active_users: int
    avg_response_time: float
    popular_categories: List[dict]
