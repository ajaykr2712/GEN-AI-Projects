import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.models import CustomerLog, User
from app.core.database import get_db

class LogProcessor:
    """Service for processing and analyzing customer inquiry logs."""
    
    def __init__(self):
        self.log_categories = {
            "technical": ["error", "bug", "crash", "broken", "not working", "issue", "problem"],
            "billing": ["payment", "charge", "bill", "invoice", "refund", "subscription"],
            "account": ["login", "password", "account", "profile", "settings"],
            "product": ["feature", "how to", "tutorial", "guide", "help"],
            "general": ["question", "inquiry", "information", "support"]
        }
        
        self.urgency_keywords = {
            "urgent": ["urgent", "emergency", "critical", "immediately", "asap"],
            "high": ["important", "priority", "soon", "quickly"],
            "medium": ["help", "question", "issue", "problem"],
            "low": ["info", "information", "general", "when convenient"]
        }
    
    async def process_log_entry(self, log_data: Dict, db: Session) -> CustomerLog:
        """Process a single log entry and categorize it."""
        
        # Extract relevant information
        title = log_data.get("title", "")
        description = log_data.get("description", "")
        combined_text = f"{title} {description}".lower()
        
        # Determine category
        category = self._determine_category(combined_text)
        
        # Determine urgency
        priority = self._determine_urgency(combined_text)
        
        # Create log entry
        log_entry = CustomerLog(
            user_id=log_data.get("user_id"),
            log_type=log_data.get("log_type", "inquiry"),
            title=title,
            description=description,
            category=category,
            priority=priority,
            status="open"
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        return log_entry
    
    def _determine_category(self, text: str) -> str:
        """Determine the category based on text content."""
        
        category_scores = {}
        
        for category, keywords in self.log_categories.items():
            score = sum(1 for keyword in keywords if keyword in text)
            category_scores[category] = score
        
        # Return category with highest score, default to 'general'
        if max(category_scores.values()) > 0:
            return max(category_scores, key=category_scores.get)
        return "general"
    
    def _determine_urgency(self, text: str) -> str:
        """Determine urgency level based on text content."""
        
        for urgency, keywords in self.urgency_keywords.items():
            if any(keyword in text for keyword in keywords):
                return urgency
        return "medium"
    
    async def get_logs_by_timeframe(
        self, 
        db: Session, 
        hours: int = 24,
        user_id: Optional[int] = None
    ) -> List[CustomerLog]:
        """Retrieve logs from the specified timeframe."""
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = db.query(CustomerLog).filter(CustomerLog.created_at >= start_time)
        
        if user_id:
            query = query.filter(CustomerLog.user_id == user_id)
        
        return query.order_by(CustomerLog.created_at.desc()).all()
    
    async def get_trending_issues(self, db: Session, hours: int = 24) -> List[Dict]:
        """Identify trending issues based on log frequency."""
        
        logs = await self.get_logs_by_timeframe(db, hours)
        
        # Count issues by category and keywords
        issue_counts = {}
        
        for log in logs:
            key_words = self._extract_keywords(log.title + " " + (log.description or ""))
            for word in key_words:
                issue_counts[word] = issue_counts.get(word, 0) + 1
        
        # Sort by frequency
        trending = [
            {"issue": issue, "count": count}
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            if count >= 3  # Only show issues with 3+ occurrences
        ]
        
        return trending[:10]  # Top 10 trending issues
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        
        # Simple keyword extraction - can be improved with NLP
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "can", "may", "might", "must"}
        
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        
        return keywords[:5]  # Return top 5 keywords
    
    async def generate_log_summary(self, db: Session, hours: int = 24) -> Dict:
        """Generate a summary of logs in the specified timeframe."""
        
        logs = await self.get_logs_by_timeframe(db, hours)
        
        # Calculate statistics
        total_logs = len(logs)
        status_counts = {}
        category_counts = {}
        priority_counts = {}
        
        for log in logs:
            status_counts[log.status] = status_counts.get(log.status, 0) + 1
            category_counts[log.category] = category_counts.get(log.category, 0) + 1
            priority_counts[log.priority] = priority_counts.get(log.priority, 0) + 1
        
        return {
            "timeframe_hours": hours,
            "total_logs": total_logs,
            "status_breakdown": status_counts,
            "category_breakdown": category_counts,
            "priority_breakdown": priority_counts,
            "trending_issues": await self.get_trending_issues(db, hours)
        }

# Global log processor instance
log_processor = LogProcessor()
