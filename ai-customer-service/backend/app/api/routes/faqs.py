from fastapi import APIRouter, Depends, Session
from typing import List

from app.core.database import get_db
from app.models.models import FAQ

router = APIRouter()

@router.get("/faqs", response_model=List[dict])
async def get_faqs(
    category: str = None,
    db: Session = Depends(get_db)
):
    """Get frequently asked questions."""
    
    query = db.query(FAQ).filter(FAQ.is_active)
    
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
