import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import time

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_register_user_success(self, client):
        """Test successful user registration"""
        user_data = {
            "username": f"testuser_{int(time.time())}",
            "password": "testpass123",
            "device_id": "test-device"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        assert "message" in response.json()
        assert response.json()["message"] == "User registered successfully"
    
    def test_register_duplicate_user(self, client):
        """Test duplicate user registration fails"""
        user_data = {
            "username": "duplicateuser",
            "password": "testpass123",
            "device_id": "test-device"
        }
        
        # First registration should succeed
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Second registration should fail
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "error" in response.json()
    
    def test_login_success(self, client):
        """Test successful login"""
        # First register a user
        user_data = {
            "username": "loginuser",
            "password": "testpass123",
            "device_id": "test-device"
        }
        client.post("/api/auth/register", json=user_data)
        
        # Then login
        login_data = {
            "username": "loginuser",
            "password": "testpass123",
            "remember_me": True,
            "device_id": "test-device"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()
        # Check if refresh token cookie was set
        assert "refresh_token" in response.cookies
    
    def test_login_wrong_password(self, client):
        """Test login with wrong password fails"""
        # First register a user
        user_data = {
            "username": "wrongpassuser",
            "password": "correctpass",
            "device_id": "test-device"
        }
        client.post("/api/auth/register", json=user_data)
        
        # Try login with wrong password
        login_data = {
            "username": "wrongpassuser",
            "password": "wrongpass",
            "remember_me": True,
            "device_id": "test-device"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        assert "error" in response.json()
    
    def test_protected_endpoint_with_token(self, client):
        """Test accessing protected endpoint with valid token"""
        # Register and login to get token
        user_data = {
            "username": "protecteduser",
            "password": "testpass123",
            "device_id": "test-device"
        }
        client.post("/api/auth/register", json=user_data)
        
        login_data = {
            "username": "protecteduser",
            "password": "testpass123",
            "remember_me": True,
            "device_id": "test-device"
        }
        login_response = client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        assert "username" in response.json()
        assert response.json()["username"] == "protecteduser"
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token fails"""
        response = client.get("/api/auth/me")
        assert response.status_code == 403  # FastAPI returns 403 for missing auth header
    
    def test_token_refresh(self, client):
        """Test token refresh functionality"""
        # Register and login
        user_data = {
            "username": "refreshuser",
            "password": "testpass123",
            "device_id": "test-device"
        }
        client.post("/api/auth/register", json=user_data)
        
        login_data = {
            "username": "refreshuser",
            "password": "testpass123",
            "remember_me": True,
            "device_id": "test-device"
        }
        login_response = client.post("/api/auth/login", json=login_data)
        
        # Refresh token
        response = client.post("/api/auth/refresh")
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_logout(self, client):
        """Test logout functionality"""
        # Register and login
        user_data = {
            "username": "logoutuser",
            "password": "testpass123",
            "device_id": "test-device"
        }
        client.post("/api/auth/register", json=user_data)
        
        login_data = {
            "username": "logoutuser",
            "password": "testpass123",
            "remember_me": True,
            "device_id": "test-device"
        }
        client.post("/api/auth/login", json=login_data)
        
        # Logout
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        
        # Try to refresh after logout (should fail)
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401
    
    @pytest.mark.parametrize("invalid_data,expected_status", [
        ({"username": "", "password": "pass"}, 422),  # Empty username
        ({"username": "user", "password": ""}, 422),  # Empty password
        ({"username": "user", "password": "short"}, 422),  # Short password
        ({"username": "a" * 51, "password": "validpass"}, 422),  # Too long username
    ])
    def test_register_validation(self, client, invalid_data, expected_status):
        """Test registration validation"""
        response = client.post("/api/auth/register", json=invalid_data)
        assert response.status_code == expected_status
    
    @pytest.mark.parametrize("invalid_data,expected_status", [
        ({"username": "", "password": "pass"}, 422),  # Empty username
        ({"username": "user", "password": ""}, 422),  # Empty password
    ])
    def test_login_validation(self, client, invalid_data, expected_status):
        """Test login validation"""
        response = client.post("/api/auth/login", json=invalid_data)
        assert response.status_code == expected_status
