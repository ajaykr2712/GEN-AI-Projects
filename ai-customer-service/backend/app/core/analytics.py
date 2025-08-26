"""
Advanced Analytics and Performance Monitoring System

This module provides comprehensive analytics for AI customer service operations,
including conversation insights, performance metrics, and business intelligence.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.models import User, Conversation, Message


class MetricType(Enum):
    RESPONSE_TIME = "response_time"
    TOKEN_USAGE = "token_usage"
    CONVERSATION_LENGTH = "conversation_length"
    USER_SATISFACTION = "user_satisfaction"
    ERROR_RATE = "error_rate"
    PEAK_USAGE = "peak_usage"


@dataclass
class ConversationAnalytics:
    """Analytics data for conversation performance."""
    conversation_id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime]
    message_count: int
    total_tokens: int
    avg_response_time: float
    satisfaction_score: Optional[float]
    resolution_status: str
    topics: List[str]
    sentiment_scores: List[float]


@dataclass
class UserEngagementMetrics:
    """User engagement and behavior metrics."""
    user_id: int
    total_conversations: int
    avg_session_duration: float
    last_activity: datetime
    preferred_topics: List[str]
    satisfaction_trend: List[float]
    retention_score: float


@dataclass
class SystemPerformanceMetrics:
    """System-wide performance metrics."""
    timestamp: datetime
    active_users: int
    conversations_per_hour: int
    avg_response_time: float
    error_rate: float
    token_usage_rate: float
    system_load: float
    memory_usage: float
    cpu_usage: float


class AnalyticsEngine:
    """Advanced analytics engine for AI customer service insights."""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_conversation_analytics(
        self, 
        start_date: datetime, 
        end_date: datetime,
        user_id: Optional[int] = None
    ) -> List[ConversationAnalytics]:
        """Get detailed conversation analytics for a time period."""
        
        query = self.db.query(Conversation).filter(
            and_(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            )
        )
        
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        
        conversations = query.all()
        analytics = []
        
        for conv in conversations:
            messages = self.db.query(Message).filter(
                Message.conversation_id == conv.id
            ).all()
            
            # Calculate metrics
            message_count = len(messages)
            total_tokens = sum(msg.tokens_used or 0 for msg in messages)
            
            # Calculate average response time
            response_times = []
            for i in range(1, len(messages)):
                if messages[i-1].role == "user" and messages[i].role == "assistant":
                    time_diff = (messages[i].created_at - messages[i-1].created_at).total_seconds()
                    response_times.append(time_diff)
            
            avg_response_time = np.mean(response_times) if response_times else 0
            
            # Extract topics and sentiment (simplified)
            topics = self._extract_topics(messages)
            sentiment_scores = self._analyze_sentiment(messages)
            
            analytics.append(ConversationAnalytics(
                conversation_id=conv.id,
                user_id=conv.user_id,
                start_time=conv.created_at,
                end_time=conv.updated_at,
                message_count=message_count,
                total_tokens=total_tokens,
                avg_response_time=avg_response_time,
                satisfaction_score=self._calculate_satisfaction(messages),
                resolution_status=self._determine_resolution_status(messages),
                topics=topics,
                sentiment_scores=sentiment_scores
            ))
        
        return analytics
    
    async def get_user_engagement_metrics(
        self, 
        user_id: Optional[int] = None
    ) -> List[UserEngagementMetrics]:
        """Get user engagement and behavior metrics."""
        
        if user_id:
            users = [self.db.query(User).filter(User.id == user_id).first()]
        else:
            users = self.db.query(User).all()
        
        metrics = []
        
        for user in users:
            if not user:
                continue
                
            conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user.id
            ).all()
            
            if not conversations:
                continue
            
            # Calculate session durations
            session_durations = []
            for conv in conversations:
                if conv.updated_at and conv.created_at:
                    duration = (conv.updated_at - conv.created_at).total_seconds()
                    session_durations.append(duration)
            
            avg_session_duration = np.mean(session_durations) if session_durations else 0
            
            # Extract preferred topics
            all_messages = []
            for conv in conversations:
                messages = self.db.query(Message).filter(
                    Message.conversation_id == conv.id
                ).all()
                all_messages.extend(messages)
            
            preferred_topics = self._extract_topics(all_messages)
            
            # Calculate satisfaction trend
            satisfaction_scores = []
            for conv in conversations:
                messages = self.db.query(Message).filter(
                    Message.conversation_id == conv.id
                ).all()
                score = self._calculate_satisfaction(messages)
                if score:
                    satisfaction_scores.append(score)
            
            # Calculate retention score
            if len(conversations) > 1:
                time_gaps = []
                sorted_convs = sorted(conversations, key=lambda x: x.created_at)
                for i in range(1, len(sorted_convs)):
                    gap = (sorted_convs[i].created_at - sorted_convs[i-1].created_at).days
                    time_gaps.append(gap)
                
                avg_gap = np.mean(time_gaps)
                retention_score = max(0, 1 - (avg_gap / 30))  # 30-day baseline
            else:
                retention_score = 0.5
            
            metrics.append(UserEngagementMetrics(
                user_id=user.id,
                total_conversations=len(conversations),
                avg_session_duration=avg_session_duration,
                last_activity=max(conv.updated_at for conv in conversations),
                preferred_topics=preferred_topics[:5],  # Top 5
                satisfaction_trend=satisfaction_scores[-10:],  # Last 10
                retention_score=retention_score
            ))
        
        return metrics
    
    async def get_system_performance_metrics(
        self, 
        hours_back: int = 24
    ) -> List[SystemPerformanceMetrics]:
        """Get system-wide performance metrics."""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        metrics = []
        
        # Generate hourly metrics
        current_time = start_time
        while current_time < end_time:
            hour_end = current_time + timedelta(hours=1)
            
            # Active users in this hour
            active_users = self.db.query(func.count(func.distinct(Conversation.user_id))).filter(
                and_(
                    Conversation.created_at >= current_time,
                    Conversation.created_at < hour_end
                )
            ).scalar()
            
            # Conversations per hour
            conversations_count = self.db.query(func.count(Conversation.id)).filter(
                and_(
                    Conversation.created_at >= current_time,
                    Conversation.created_at < hour_end
                )
            ).scalar()
            
            # Calculate response times for this hour
            messages_in_hour = self.db.query(Message).filter(
                and_(
                    Message.created_at >= current_time,
                    Message.created_at < hour_end,
                    Message.role == "assistant"
                )
            ).all()
            
            response_times = []
            for msg in messages_in_hour:
                # Find the previous user message
                prev_msg = self.db.query(Message).filter(
                    and_(
                        Message.conversation_id == msg.conversation_id,
                        Message.created_at < msg.created_at,
                        Message.role == "user"
                    )
                ).order_by(Message.created_at.desc()).first()
                
                if prev_msg:
                    response_time = (msg.created_at - prev_msg.created_at).total_seconds()
                    response_times.append(response_time)
            
            avg_response_time = np.mean(response_times) if response_times else 0
            
            # Error rate (simplified - would need error logging)
            error_rate = 0.02  # Placeholder
            
            # Token usage rate
            total_tokens = self.db.query(func.sum(Message.tokens_used)).filter(
                and_(
                    Message.created_at >= current_time,
                    Message.created_at < hour_end
                )
            ).scalar() or 0
            
            token_usage_rate = total_tokens / 3600 if total_tokens else 0  # per second
            
            metrics.append(SystemPerformanceMetrics(
                timestamp=current_time,
                active_users=active_users or 0,
                conversations_per_hour=conversations_count or 0,
                avg_response_time=avg_response_time,
                error_rate=error_rate,
                token_usage_rate=token_usage_rate,
                system_load=0.75,  # Placeholder - would integrate with system monitoring
                memory_usage=0.68,  # Placeholder
                cpu_usage=0.45     # Placeholder
            ))
            
            current_time = hour_end
        
        return metrics
    
    async def generate_insights_report(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive insights report."""
        
        conversation_analytics = await self.get_conversation_analytics(start_date, end_date)
        user_metrics = await self.get_user_engagement_metrics()
        system_metrics = await self.get_system_performance_metrics()
        
        # Calculate key insights
        total_conversations = len(conversation_analytics)
        avg_satisfaction = np.mean([
            ca.satisfaction_score for ca in conversation_analytics 
            if ca.satisfaction_score is not None
        ]) if conversation_analytics else 0
        
        avg_resolution_time = np.mean([
            ca.avg_response_time for ca in conversation_analytics
        ]) if conversation_analytics else 0
        
        total_tokens_used = sum(ca.total_tokens for ca in conversation_analytics)
        
        # Top topics
        all_topics = []
        for ca in conversation_analytics:
            all_topics.extend(ca.topics)
        
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # User retention insights
        high_retention_users = [
            um for um in user_metrics 
            if um.retention_score > 0.7
        ]
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_days": (end_date - start_date).days
            },
            "summary": {
                "total_conversations": total_conversations,
                "unique_users": len(user_metrics),
                "avg_satisfaction_score": round(avg_satisfaction, 2),
                "avg_resolution_time_seconds": round(avg_resolution_time, 2),
                "total_tokens_used": total_tokens_used,
                "high_retention_users": len(high_retention_users)
            },
            "top_topics": top_topics,
            "performance_trends": {
                "avg_response_time_trend": [sm.avg_response_time for sm in system_metrics[-24:]],
                "conversations_per_hour_trend": [sm.conversations_per_hour for sm in system_metrics[-24:]],
                "error_rate_trend": [sm.error_rate for sm in system_metrics[-24:]]
            },
            "recommendations": self._generate_recommendations(
                conversation_analytics, user_metrics, system_metrics
            )
        }
    
    def _extract_topics(self, messages: List[Message]) -> List[str]:
        """Extract topics from conversation messages (simplified implementation)."""
        # This would typically use NLP libraries like spaCy or NLTK
        common_topics = [
            "billing", "technical_support", "account_management", 
            "product_information", "refund", "shipping", "login_issues",
            "password_reset", "feature_request", "bug_report"
        ]
        
        found_topics = []
        for message in messages:
            content = message.content.lower()
            for topic in common_topics:
                if topic.replace("_", " ") in content or topic in content:
                    if topic not in found_topics:
                        found_topics.append(topic)
        
        return found_topics[:3]  # Top 3 topics
    
    def _analyze_sentiment(self, messages: List[Message]) -> List[float]:
        """Analyze sentiment of messages (simplified implementation)."""
        # This would typically use sentiment analysis libraries
        sentiments = []
        
        positive_words = ["good", "great", "excellent", "thank", "helpful", "solved", "perfect"]
        negative_words = ["bad", "terrible", "awful", "frustrated", "angry", "useless", "broken"]
        
        for message in messages:
            if message.role == "user":
                content = message.content.lower()
                positive_count = sum(1 for word in positive_words if word in content)
                negative_count = sum(1 for word in negative_words if word in content)
                
                if positive_count > negative_count:
                    sentiment = 0.7 + (positive_count - negative_count) * 0.1
                elif negative_count > positive_count:
                    sentiment = 0.3 - (negative_count - positive_count) * 0.1
                else:
                    sentiment = 0.5
                
                sentiments.append(max(0, min(1, sentiment)))
        
        return sentiments
    
    def _calculate_satisfaction(self, messages: List[Message]) -> Optional[float]:
        """Calculate conversation satisfaction score."""
        if not messages:
            return None
        
        sentiment_scores = self._analyze_sentiment(messages)
        if not sentiment_scores:
            return None
        
        # Weight recent messages more heavily
        weights = [1.0 + (i * 0.1) for i in range(len(sentiment_scores))]
        weighted_avg = np.average(sentiment_scores, weights=weights)
        
        return round(weighted_avg, 2)
    
    def _determine_resolution_status(self, messages: List[Message]) -> str:
        """Determine if conversation was resolved."""
        if not messages:
            return "unknown"
        
        last_messages = messages[-3:]  # Check last 3 messages
        
        resolution_indicators = [
            "resolved", "solved", "fixed", "thank you", "thanks", 
            "that works", "perfect", "issue resolved"
        ]
        
        for message in last_messages:
            content = message.content.lower()
            if any(indicator in content for indicator in resolution_indicators):
                return "resolved"
        
        if len(messages) > 10:
            return "escalated"
        elif len(messages) < 3:
            return "abandoned"
        else:
            return "in_progress"
    
    def _generate_recommendations(
        self,
        conversation_analytics: List[ConversationAnalytics],
        user_metrics: List[UserEngagementMetrics],
        system_metrics: List[SystemPerformanceMetrics]
    ) -> List[str]:
        """Generate actionable recommendations based on analytics."""
        recommendations = []
        
        if conversation_analytics:
            avg_response_time = np.mean([ca.avg_response_time for ca in conversation_analytics])
            if avg_response_time > 30:  # 30 seconds
                recommendations.append(
                    "Consider optimizing AI response generation to reduce average response time"
                )
            
            avg_satisfaction = np.mean([
                ca.satisfaction_score for ca in conversation_analytics 
                if ca.satisfaction_score is not None
            ])
            if avg_satisfaction < 0.6:
                recommendations.append(
                    "Customer satisfaction is below 60%. Review AI training data and responses"
                )
        
        if user_metrics:
            low_retention_users = [um for um in user_metrics if um.retention_score < 0.3]
            if len(low_retention_users) > len(user_metrics) * 0.3:
                recommendations.append(
                    "High user churn detected. Implement proactive engagement strategies"
                )
        
        if system_metrics:
            recent_metrics = system_metrics[-6:]  # Last 6 hours
            if recent_metrics:
                avg_error_rate = np.mean([sm.error_rate for sm in recent_metrics])
                if avg_error_rate > 0.05:  # 5%
                    recommendations.append(
                        "Error rate is elevated. Investigate system stability issues"
                    )
        
        if not recommendations:
            recommendations.append("System performance is within normal parameters")
        
        return recommendations


# Usage example and service initialization
async def create_analytics_service(db: Session) -> AnalyticsEngine:
    """Factory function to create analytics service."""
    return AnalyticsEngine(db)
