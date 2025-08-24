from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import User, Conversation, Message, FAQ, KnowledgeBase
from app.schemas.schemas import (
    ChatMessage, ChatResponse, Conversation as ConversationSchema,
    ConversationCreate, Message as MessageSchema
)
from app.services.ai_service import ai_service
from app.api.dependencies import get_current_user

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_data: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the AI assistant and get a response."""
    
    # Get or create conversation
    conversation = None
    if chat_data.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == chat_data.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation
        conversation = Conversation(
            user_id=current_user.id,
            title=chat_data.message[:50] + "..." if len(chat_data.message) > 50 else chat_data.message
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Get conversation history
    conversation_history = []
    if conversation:
        recent_messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.timestamp.desc()).limit(10).all()
        
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(recent_messages)
        ]
    
    # Get relevant knowledge base content
    knowledge_items = db.query(KnowledgeBase).filter(
        KnowledgeBase.is_public == True
    ).all()
    
    relevant_context = ai_service.search_knowledge_base(
        chat_data.message, 
        [{"title": kb.title, "content": kb.content} for kb in knowledge_items]
    )
    
    additional_context = ""
    if relevant_context:
        additional_context = "Relevant information: " + " ".join([
            f"{item['title']}: {item['content'][:200]}" 
            for item in relevant_context[:2]
        ])
    
    # Generate AI response
    ai_response = await ai_service.generate_response(
        message=chat_data.message,
        conversation_history=conversation_history,
        context_type="customer_service",
        additional_context=additional_context
    )
    
    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        content=chat_data.message,
        role="user"
    )
    db.add(user_message)
    
    # Save AI response
    ai_message = Message(
        conversation_id=conversation.id,
        content=ai_response["response"],
        role="assistant",
        tokens_used=ai_response["tokens_used"],
        response_time=ai_response["response_time"]
    )
    db.add(ai_message)
    
    db.commit()
    
    return ChatResponse(
        response=ai_response["response"],
        conversation_id=conversation.id,
        tokens_used=ai_response["tokens_used"],
        response_time=ai_response["response_time"]
    )

@router.get("/conversations", response_model=List[ConversationSchema])
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for the current user."""
    
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
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

@router.get("/faqs", response_model=List[dict])
async def get_faqs(
    category: str = None,
    db: Session = Depends(get_db)
):
    """Get frequently asked questions."""
    
    query = db.query(FAQ).filter(FAQ.is_active == True)
    
    if category:
        query = query.filter(FAQ.category == category)
    
    faqs = query.order_by(FAQ.view_count.desc()).all()
    
    # Increment view count for returned FAQs
    for faq in faqs:
        faq.view_count += 1
    
    db.commit()
    
    return [
        {
            "id": faq.id,
            "question": faq.question,
            "answer": faq.answer,
            "category": faq.category,
            "view_count": faq.view_count
        }
        for faq in faqs
    ]
