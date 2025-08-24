from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.models import User, CustomerLog
from app.schemas.schemas import (
    CustomerLog as CustomerLogSchema,
    CustomerLogCreate,
    CustomerLogUpdate
)
from app.services.log_processor import log_processor
from app.api.dependencies import get_current_user, get_admin_user

router = APIRouter()

@router.post("/logs", response_model=CustomerLogSchema)
async def create_customer_log(
    log_data: CustomerLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new customer log entry."""
    
    # Prepare log data for processing
    log_dict = {
        "user_id": current_user.id,
        "title": log_data.title,
        "description": log_data.description,
        "log_type": log_data.log_type,
    }
    
    # Process the log entry (categorization and prioritization)
    log_entry = await log_processor.process_log_entry(log_dict, db)
    
    return log_entry

@router.get("/logs", response_model=List[CustomerLogSchema])
async def get_customer_logs(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get customer logs for the current user."""
    
    # Get logs by timeframe
    logs = await log_processor.get_logs_by_timeframe(db, hours, current_user.id)
    
    # Apply filters
    if status:
        logs = [log for log in logs if log.status == status]
    
    if category:
        logs = [log for log in logs if log.category == category]
    
    if priority:
        logs = [log for log in logs if log.priority == priority]
    
    return logs

@router.get("/logs/{log_id}", response_model=CustomerLogSchema)
async def get_customer_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific customer log."""
    
    log = db.query(CustomerLog).filter(
        CustomerLog.id == log_id,
        CustomerLog.user_id == current_user.id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found"
        )
    
    return log

@router.put("/logs/{log_id}", response_model=CustomerLogSchema)
async def update_customer_log(
    log_id: int,
    log_update: CustomerLogUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a customer log entry."""
    
    log = db.query(CustomerLog).filter(
        CustomerLog.id == log_id,
        CustomerLog.user_id == current_user.id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found"
        )
    
    # Update fields
    update_data = log_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(log, field, value)
    
    db.commit()
    db.refresh(log)
    
    return log

@router.get("/logs/summary", response_model=dict)
async def get_logs_summary(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a summary of customer logs."""
    
    summary = await log_processor.generate_log_summary(db, hours)
    
    # Filter to current user's logs only
    user_logs = await log_processor.get_logs_by_timeframe(db, hours, current_user.id)
    
    user_summary = {
        "timeframe_hours": hours,
        "total_logs": len(user_logs),
        "status_breakdown": {},
        "category_breakdown": {},
        "priority_breakdown": {}
    }
    
    for log in user_logs:
        user_summary["status_breakdown"][log.status] = user_summary["status_breakdown"].get(log.status, 0) + 1
        user_summary["category_breakdown"][log.category] = user_summary["category_breakdown"].get(log.category, 0) + 1
        user_summary["priority_breakdown"][log.priority] = user_summary["priority_breakdown"].get(log.priority, 0) + 1
    
    return user_summary

@router.get("/logs/trending", response_model=List[dict])
async def get_trending_issues(
    hours: int = 24,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get trending issues across all users (admin only)."""
    
    trending = await log_processor.get_trending_issues(db, hours)
    return trending

@router.get("/admin/logs", response_model=List[CustomerLogSchema])
async def get_all_customer_logs(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    hours: int = 24,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all customer logs across all users (admin only)."""
    
    # Get all logs by timeframe
    logs = await log_processor.get_logs_by_timeframe(db, hours)
    
    # Apply filters
    if status:
        logs = [log for log in logs if log.status == status]
    
    if category:
        logs = [log for log in logs if log.category == category]
    
    if priority:
        logs = [log for log in logs if log.priority == priority]
    
    return logs

@router.get("/admin/logs/summary", response_model=dict)
async def get_admin_logs_summary(
    hours: int = 24,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive logs summary for admin."""
    
    summary = await log_processor.generate_log_summary(db, hours)
    return summary
