"""
Comprehensive Integration Tests for All New Modules

This test suite validates the integration of all newly added modules:
- Analytics system
- Security and rate limiting
- ML pipeline
- API documentation and testing
- Real-time WebSocket features
- E2E testing framework
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

try:
    from fastapi.testclient import TestClient
except ImportError:
    # Fallback for environments without FastAPI
    TestClient = Mock

from main import app
from app.core.analytics import AnalyticsEngine, ConversationAnalytics
from app.core.security import SecurityManager, RateLimiter, SecurityEvent
from app.core.ml_pipeline import MLPipelineManager, ModelMetrics
from app.core.api_docs import APIDocumentationGenerator, EndpointDocumentation
from app.core.realtime import RealtimeManager, SystemStatus
from app.core.e2e_testing import E2ETestRunner, TestScenario


class TestAnalyticsIntegration:
    """Test analytics system integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.analytics = AnalyticsEngine()
        self.mock_db = Mock(spec=Session)
    
    def test_analytics_engine_initialization(self):
        """Test analytics engine can be initialized."""
        assert self.analytics is not None
        assert hasattr(self.analytics, 'db')
    
    def test_conversation_analytics_generation(self):
        """Test conversation analytics data generation."""
        # Mock conversation data
        mock_conversation_data = {
            'conversation_id': 1,
            'user_id': 123,
            'start_time': datetime.now(),
            'message_count': 5,
            'total_tokens': 150
        }
        
        analytics = ConversationAnalytics(
            conversation_id=mock_conversation_data['conversation_id'],
            user_id=mock_conversation_data['user_id'],
            start_time=mock_conversation_data['start_time'],
            end_time=None,
            message_count=mock_conversation_data['message_count'],
            total_tokens=mock_conversation_data['total_tokens'],
            avg_response_time=2.5,
            satisfaction_score=4.2,
            resolution_status="resolved",
            topics=["billing", "technical_support"],
            sentiment_scores=[0.8, 0.6, 0.9]
        )
        
        assert analytics.conversation_id == 1
        assert analytics.user_id == 123
        assert analytics.message_count == 5
        assert len(analytics.topics) == 2
    
    @patch('app.core.analytics.Session')
    def test_analytics_database_integration(self, mock_session):
        """Test analytics database operations."""
        mock_session.return_value = self.mock_db
        
        # Test that analytics can interact with database
        result = self.analytics.get_conversation_insights(
            start_date=datetime.now(),
            end_date=datetime.now()
        )
        
        assert isinstance(result, dict)
        assert 'total_conversations' in result


class TestSecurityIntegration:
    """Test security system integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.security_manager = SecurityManager()
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
    
    def test_security_manager_initialization(self):
        """Test security manager initialization."""
        assert self.security_manager is not None
        assert hasattr(self.security_manager, 'audit_logger')
    
    def test_rate_limiter_functionality(self):
        """Test rate limiting functionality."""
        client_id = "test_client_123"
        
        # Should allow initial requests
        assert self.rate_limiter.is_allowed(client_id)
        
        # Record some requests
        for _ in range(5):
            self.rate_limiter.record_request(client_id)
        
        # Should still be allowed
        assert self.rate_limiter.is_allowed(client_id)
    
    def test_security_event_logging(self):
        """Test security event logging."""
        event = SecurityEvent(
            event_type="authentication_failure",
            user_id="user_123",
            ip_address="192.168.1.1",
            timestamp=datetime.now(),
            details={"reason": "invalid_password"}
        )
        
        # Should be able to log security events
        result = self.security_manager.log_security_event(event)
        assert result


class TestMLPipelineIntegration:
    """Test ML pipeline integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.ml_manager = MLPipelineManager()
    
    def test_ml_pipeline_initialization(self):
        """Test ML pipeline manager initialization."""
        assert self.ml_manager is not None
        assert hasattr(self.ml_manager, 'models')
    
    @patch('app.core.ml_pipeline.joblib')
    def test_model_loading(self, mock_joblib):
        """Test ML model loading functionality."""
        mock_joblib.load.return_value = Mock()
        
        result = self.ml_manager.load_model("sentiment_analyzer", "/path/to/model")
        assert result
        assert "sentiment_analyzer" in self.ml_manager.models
    
    def test_model_metrics_tracking(self):
        """Test model performance metrics tracking."""
        metrics = ModelMetrics(
            model_name="sentiment_analyzer",
            accuracy=0.95,
            precision=0.92,
            recall=0.88,
            f1_score=0.90,
            inference_time=0.05,
            timestamp=datetime.now()
        )
        
        self.ml_manager.record_metrics("sentiment_analyzer", metrics)
        assert "sentiment_analyzer" in self.ml_manager.model_metrics


class TestAPIDocumentationIntegration:
    """Test API documentation integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.doc_generator = APIDocumentationGenerator()
        self.client = TestClient(app)
    
    def test_doc_generator_initialization(self):
        """Test documentation generator initialization."""
        assert self.doc_generator is not None
        assert hasattr(self.doc_generator, 'endpoints')
    
    def test_endpoint_documentation_generation(self):
        """Test endpoint documentation generation."""
        endpoint_doc = EndpointDocumentation(
            path="/api/v1/chat",
            method="POST",
            summary="Send chat message",
            description="Send a message to the AI assistant",
            parameters=[],
            responses={}
        )
        
        self.doc_generator.add_endpoint(endpoint_doc)
        assert len(self.doc_generator.endpoints) > 0
    
    def test_api_health_check(self):
        """Test API health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestRealtimeIntegration:
    """Test real-time system integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.realtime_manager = RealtimeManager()
    
    def test_realtime_manager_initialization(self):
        """Test realtime manager initialization."""
        assert self.realtime_manager is not None
        assert hasattr(self.realtime_manager, 'active_connections')
    
    def test_system_status_monitoring(self):
        """Test system status monitoring."""
        status = SystemStatus(
            timestamp=datetime.now(),
            cpu_usage=45.2,
            memory_usage=67.8,
            active_connections=12,
            response_time=120.5,
            error_rate=0.05
        )
        
        self.realtime_manager.update_system_status(status)
        assert self.realtime_manager.current_status is not None
    
    async def test_websocket_connection_handling(self):
        """Test WebSocket connection handling."""
        mock_websocket = Mock()
        
        # Test connection addition
        connection_id = self.realtime_manager.add_connection(mock_websocket)
        assert connection_id in self.realtime_manager.active_connections
        
        # Test connection removal
        self.realtime_manager.remove_connection(connection_id)
        assert connection_id not in self.realtime_manager.active_connections


class TestE2EIntegration:
    """Test E2E testing framework integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.e2e_runner = E2ETestRunner()
        self.client = TestClient(app)
    
    def test_e2e_runner_initialization(self):
        """Test E2E test runner initialization."""
        assert self.e2e_runner is not None
        assert hasattr(self.e2e_runner, 'scenarios')
    
    def test_test_scenario_creation(self):
        """Test test scenario creation."""
        scenario = TestScenario(
            name="user_authentication_flow",
            description="Test complete user authentication process",
            steps=[
                {"action": "POST", "endpoint": "/auth/register", "data": {}},
                {"action": "POST", "endpoint": "/auth/login", "data": {}},
                {"action": "GET", "endpoint": "/auth/profile", "headers": {}}
            ],
            expected_outcomes=["user_created", "login_successful", "profile_retrieved"]
        )
        
        self.e2e_runner.add_scenario(scenario)
        assert len(self.e2e_runner.scenarios) > 0
    
    def test_full_application_flow(self):
        """Test a complete application flow."""
        # This would test the entire application flow from start to finish
        # Including authentication, chat functionality, and logging
        
        # Test application startup
        response = self.client.get("/health")
        assert response.status_code == 200
        
        # Test that all main endpoints are accessible
        docs_response = self.client.get("/docs")
        assert docs_response.status_code == 200


class TestCrossModuleIntegration:
    """Test integration between different modules."""
    
    def setup_method(self):
        """Setup test environment."""
        self.analytics = AnalyticsEngine()
        self.security_manager = SecurityManager()
        self.ml_manager = MLPipelineManager()
        self.realtime_manager = RealtimeManager()
    
    def test_analytics_security_integration(self):
        """Test integration between analytics and security."""
        # Security events should be logged and analyzed
        security_event = SecurityEvent(
            event_type="suspicious_activity",
            user_id="user_456",
            ip_address="10.0.0.1",
            timestamp=datetime.now(),
            details={"requests_per_minute": 200}
        )
        
        # Log security event
        self.security_manager.log_security_event(security_event)
        
        # Analytics should be able to process security data
        security_insights = self.analytics.get_security_insights()
        assert isinstance(security_insights, dict)
    
    def test_ml_realtime_integration(self):
        """Test integration between ML pipeline and real-time system."""
        # ML predictions should be available in real-time
        prediction_result = {
            "model": "sentiment_analyzer",
            "prediction": "positive",
            "confidence": 0.89,
            "timestamp": datetime.now()
        }
        
        # Real-time system should be able to broadcast ML results
        self.realtime_manager.broadcast_ml_result(prediction_result)
        assert self.realtime_manager.last_ml_result is not None
    
    def test_full_system_integration(self):
        """Test full system integration across all modules."""
        # Simulate a complete user interaction
        user_interaction = {
            "user_id": "user_789",
            "message": "Hello, I need help with my account",
            "timestamp": datetime.now(),
            "ip_address": "203.0.113.1"
        }
        
        # 1. Security check        
        is_allowed = self.security_manager.check_request_security(
            user_interaction["user_id"],
            user_interaction["ip_address"]
        )
        assert is_allowed
        
        # 2. ML processing (sentiment analysis)
        ml_result = self.ml_manager.predict(
            "sentiment_analyzer",
            user_interaction["message"]
        )
        assert ml_result is not None
        
        # 3. Real-time update
        self.realtime_manager.broadcast_user_activity(user_interaction)
        
        # 4. Analytics tracking
        self.analytics.track_user_interaction(user_interaction)
        
        # All modules should work together seamlessly
        assert True  # If we reach here, integration is working


if __name__ == "__main__":
    # Run the integration tests
    pytest.main([__file__, "-v", "--tb=short"])
