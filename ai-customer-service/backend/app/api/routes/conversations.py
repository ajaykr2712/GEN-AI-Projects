from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import User, Conversation
from app.schemas.schemas import Conversation as ConversationSchema, ConversationCreate
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/conversations", response_model=List[ConversationSchema])
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for the current user."""
    
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_active
    ).order_by(Conversation.updated_at.desc()).all()
    
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationSchema)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with its messages."""
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return conversation

@router.post("/conversations", response_model=ConversationSchema)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    
    conversation = Conversation(
        user_id=current_user.id,
        title=conversation_data.title
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return conversation

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation (soft delete)."""
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    conversation.is_active = False
    db.commit()
    
    return {"message": "Conversation deleted successfully"}
