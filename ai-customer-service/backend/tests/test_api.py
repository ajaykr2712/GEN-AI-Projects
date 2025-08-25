import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200

def test_auth_register():
    """Test user registration"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }
    response = client.post("/auth/register", json=user_data)
    # Should return 201 for successful registration or 400 if user exists
    assert response.status_code in [201, 400]

def test_invalid_endpoint():
    """Test invalid endpoint returns 404"""
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404
