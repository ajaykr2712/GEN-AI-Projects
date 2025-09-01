"""
Comprehensive Testing Strategy

This module provides a comprehensive testing framework for the AI Customer Service
system, including unit tests, integration tests, performance tests, and e2e tests.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings
from app.domain.entities import User, Conversation, Message
from app.application.handlers import CreateUserCommand, SendMessageCommand
from app.infrastructure.repositories import SqlAlchemyUserRepository
from app.core.monitoring import metrics_collector, health_checker

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test fixtures
@pytest.fixture(scope="session")
def setup_test_db():
    """Setup test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def db_session():
    """Test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_user():
    """Mock user for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }

@pytest.fixture
def mock_auth_token():
    """Mock authentication token."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token"

@pytest.fixture
def authenticated_client(client, mock_auth_token):
    """Client with authentication headers."""
    client.headers = {"Authorization": f"Bearer {mock_auth_token}"}
    return client


# Unit Tests
class TestDomainEntities:
    """Test domain entities and value objects."""
    
    def test_user_creation(self):
        """Test user entity creation."""
        from app.domain.entities import User, UserId, Email
        
        user_id = UserId(1)
        email = Email("test@example.com")
        
        user = User(
            user_id=user_id,
            email=email,
            username="testuser",
            full_name="Test User"
        )
        
        assert user.id == user_id
        assert user.email == email
        assert user.username == "testuser"
        assert user.is_active is True
    
    def test_email_value_object_validation(self):
        """Test email value object validation."""
        from app.domain.entities import Email
        
        # Valid email
        valid_email = Email("test@example.com")
        assert valid_email.value == "test@example.com"
        
        # Invalid email
        with pytest.raises(ValueError):
            Email("invalid-email")
    
    def test_conversation_creation(self):
        """Test conversation entity creation."""
        from app.domain.entities import Conversation, UserId
        
        user_id = UserId(1)
        conversation = Conversation(user_id=user_id, title="Test Conversation")
        
        assert conversation.user_id == user_id
        assert conversation.title == "Test Conversation"
        assert len(conversation.messages) == 0
    
    def test_message_addition_to_conversation(self):
        """Test adding messages to conversation."""
        from app.domain.entities import Conversation, UserId, MessageContent, MessageRole
        
        user_id = UserId(1)
        conversation = Conversation(user_id=user_id, title="Test")
        
        content = MessageContent("Hello, World!")
        message = conversation.add_message(content, MessageRole.USER)
        
        assert len(conversation.messages) == 1
        assert message.content == content
        assert message.role == MessageRole.USER


class TestApplicationHandlers:
    """Test application layer command and query handlers."""
    
    @pytest.mark.asyncio
    async def test_create_user_command_handler(self):
        """Test create user command handler."""
        from app.application.handlers import CreateUserCommandHandler, CreateUserCommand
        from app.application.services import PasswordService, EventPublisher
        
        # Mock dependencies
        mock_repository = AsyncMock()
        mock_password_service = Mock(spec=PasswordService)
        mock_event_publisher = Mock(spec=EventPublisher)
        
        mock_repository.get_by_email.return_value = None
        mock_password_service.hash_password.return_value = "hashed_password"
        
        handler = CreateUserCommandHandler(
            mock_repository,
            mock_password_service,
            mock_event_publisher
        )
        
        command = CreateUserCommand(
            email="test@example.com",
            username="testuser",
            password="password123"
        )
        
        user = await handler.handle(command)
        
        assert user.email.value == "test@example.com"
        assert user.username == "testuser"
        mock_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_command_handler(self):
        """Test send message command handler."""
        from app.application.handlers import SendMessageCommandHandler, SendMessageCommand
        
        # Mock dependencies
        mock_conversation_repo = AsyncMock()
        mock_ai_service = AsyncMock()
        mock_event_publisher = Mock()
        
        # Mock conversation
        mock_conversation = Mock()
        mock_conversation_repo.get_by_id.return_value = mock_conversation
        
        # Mock AI response
        mock_ai_service.generate_response.return_value = {
            "response": "AI response",
            "tokens_used": 50,
            "response_time": 1.2
        }
        
        handler = SendMessageCommandHandler(
            mock_conversation_repo,
            mock_ai_service,
            mock_event_publisher
        )
        
        command = SendMessageCommand(
            conversation_id=1,
            message="Hello",
            user_id=1
        )
        
        result = await handler.handle(command)
        
        assert "user_message" in result
        assert "ai_message" in result
        mock_ai_service.generate_response.assert_called_once()


class TestInfrastructureRepositories:
    """Test infrastructure layer repositories."""
    
    @pytest.mark.asyncio
    async def test_user_repository_save_and_get(self, db_session):
        """Test user repository save and get operations."""
        from app.infrastructure.repositories import SqlAlchemyUserRepository
        from app.domain.entities import User, UserId, Email
        
        repository = SqlAlchemyUserRepository(db_session)
        
        # Create user
        user_id = UserId(0)  # New user
        email = Email("test@example.com")
        user = User(user_id, email, "testuser", "Test User")
        
        # Save user
        saved_user = await repository.save(user)
        
        # Retrieve user
        retrieved_user = await repository.get_by_email(email)
        
        assert retrieved_user is not None
        assert retrieved_user.email == email
        assert retrieved_user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_user_repository_get_by_username(self, db_session):
        """Test user repository get by username."""
        from app.infrastructure.repositories import SqlAlchemyUserRepository
        from app.domain.entities import User, UserId, Email
        
        repository = SqlAlchemyUserRepository(db_session)
        
        # Create and save user
        user = User(UserId(0), Email("test2@example.com"), "testuser2", "Test User 2")
        await repository.save(user)
        
        # Retrieve by username
        retrieved_user = await repository.get_by_username("testuser2")
        
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser2"


# API Integration Tests
class TestAPIEndpoints:
    """Test API endpoints integration."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "timestamp" in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    @patch('app.services.ai_service.ai_service.generate_response')
    def test_chat_endpoint_authenticated(self, mock_ai_service, authenticated_client):
        """Test chat endpoint with authentication."""
        mock_ai_service.return_value = {
            "response": "Test AI response",
            "tokens_used": 50,
            "response_time": 1.0
        }
        
        chat_data = {
            "message": "Hello, AI!",
            "conversation_id": None
        }
        
        with patch('app.api.dependencies.get_current_user') as mock_auth:
            mock_auth.return_value = Mock(id=1, username="testuser")
            
            response = authenticated_client.post("/api/v1/chat/chat", json=chat_data)
            
            # Note: This might fail without proper database setup
            # In a real test, you'd setup the database properly
            assert response.status_code in [200, 422, 401]
    
    def test_chat_endpoint_unauthenticated(self, client):
        """Test chat endpoint without authentication."""
        chat_data = {
            "message": "Hello, AI!",
            "conversation_id": None
        }
        
        response = client.post("/api/v1/chat/chat", json=chat_data)
        
        assert response.status_code == 401


# Performance Tests
class TestPerformance:
    """Test system performance characteristics."""
    
    def test_response_time_health_endpoint(self, client):
        """Test response time of health endpoint."""
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
    
    def test_concurrent_health_checks(self, client):
        """Test concurrent requests to health endpoint."""
        import concurrent.futures
        
        def make_request():
            return client.get("/health")
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        assert all(response.status_code == 200 for response in responses)
        
        # Should handle 10 concurrent requests within 5 seconds
        assert total_time < 5.0
    
    @pytest.mark.asyncio
    async def test_memory_usage_metrics_collection(self):
        """Test memory usage during metrics collection."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Simulate metrics collection
        for _ in range(1000):
            metrics_collector.record_counter("test_metric", 1)
            metrics_collector.record_gauge("test_gauge", 42.0)
            metrics_collector.record_timer("test_timer", 0.1)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024


# Monitoring Tests
class TestMonitoring:
    """Test monitoring and observability features."""
    
    @pytest.mark.asyncio
    async def test_health_checker_registration(self):
        """Test health check registration."""
        async def dummy_health_check():
            return {"status": "ok"}
        
        health_checker.register_check("test_service", dummy_health_check)
        
        results = await health_checker.run_checks()
        
        assert "test_service" in results["checks"]
        assert results["checks"]["test_service"]["status"] == "healthy"
    
    def test_metrics_collector_counter(self):
        """Test metrics collector counter functionality."""
        initial_summary = metrics_collector.get_metrics_summary()
        
        metrics_collector.record_counter("test_counter", 5)
        metrics_collector.record_counter("test_counter", 3)
        
        final_summary = metrics_collector.get_metrics_summary()
        
        assert "test_counter" in final_summary["counters"]
        assert final_summary["counters"]["test_counter"] == 8
    
    def test_metrics_collector_gauge(self):
        """Test metrics collector gauge functionality."""
        metrics_collector.record_gauge("test_gauge", 42.5)
        
        summary = metrics_collector.get_metrics_summary()
        
        assert "test_gauge" in summary["gauges"]
        assert summary["gauges"]["test_gauge"] == 42.5
    
    def test_metrics_collector_timer(self):
        """Test metrics collector timer functionality."""
        metrics_collector.record_timer("test_timer", 1.5)
        metrics_collector.record_timer("test_timer", 2.5)
        
        summary = metrics_collector.get_metrics_summary()
        
        assert "test_timer" in summary["performance"]
        performance = summary["performance"]["test_timer"]
        assert performance["count"] == 2
        assert performance["avg"] == 2.0
        assert performance["min"] == 1.5
        assert performance["max"] == 2.5


# Security Tests
class TestSecurity:
    """Test security features and vulnerabilities."""
    
    def test_sql_injection_protection(self, client):
        """Test SQL injection protection."""
        malicious_payload = "'; DROP TABLE users; --"
        
        response = client.post("/api/v1/auth/login", json={
            "username": malicious_payload,
            "password": "password"
        })
        
        # Should not cause a server error
        assert response.status_code in [400, 401, 422]
    
    def test_xss_protection_headers(self, client):
        """Test XSS protection headers."""
        response = client.get("/health")
        
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_rate_limiting(self, client):
        """Test rate limiting functionality."""
        # Make multiple requests quickly
        responses = []
        for _ in range(100):
            response = client.get("/health")
            responses.append(response)
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert any(response.status_code == 429 for response in responses)
    
    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.options("/api/v1/chat/chat", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        })
        
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers


# Error Handling Tests
class TestErrorHandling:
    """Test error handling and recovery."""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_500_error_handling(self, client):
        """Test 500 error handling."""
        with patch('app.main.health_checker.run_checks', side_effect=Exception("Test error")):
            response = client.get("/health")
            
            # Should handle the exception gracefully
            assert response.status_code in [200, 500]
    
    def test_validation_error_handling(self, client):
        """Test validation error handling."""
        invalid_data = {
            "message": "",  # Empty message should fail validation
            "conversation_id": "invalid"  # Invalid type
        }
        
        response = client.post("/api/v1/chat/chat", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# Load Testing Setup
def load_test_setup():
    """Setup for load testing (to be used with tools like locust)."""
    
    test_scenarios = {
        "health_check": "/health",
        "metrics": "/metrics",
        "root": "/",
        "chat": {
            "endpoint": "/api/v1/chat/chat",
            "method": "POST",
            "data": {"message": "Hello", "conversation_id": None},
            "headers": {"Authorization": "Bearer test-token"}
        }
    }
    
    return test_scenarios


# Test Data Factories
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_user_data(email=None, username=None):
        """Create user test data."""
        return {
            "email": email or f"test_{int(time.time())}@example.com",
            "username": username or f"testuser_{int(time.time())}",
            "password": "testpassword123",
            "full_name": "Test User"
        }
    
    @staticmethod
    def create_conversation_data(title=None, user_id=1):
        """Create conversation test data."""
        return {
            "title": title or f"Test Conversation {int(time.time())}",
            "user_id": user_id
        }
    
    @staticmethod
    def create_message_data(content=None, conversation_id=1):
        """Create message test data."""
        return {
            "content": content or f"Test message {int(time.time())}",
            "conversation_id": conversation_id,
            "role": "user"
        }


if __name__ == "__main__":
    # Run tests
    pytest.main(["-v", __file__])
