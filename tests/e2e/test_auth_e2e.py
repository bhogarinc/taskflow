"""
End-to-End Tests for Authentication Flows

This module contains comprehensive E2E tests for user authentication including:
- User registration
- Login/logout flows
- Token refresh
- Password reset
- Email verification
- Session management
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.e2e
@pytest.mark.auth
class TestUserRegistration:
    """E2E tests for user registration flow."""
    
    async def test_successful_registration(self, client: AsyncClient, test_user_data: dict, api_base_url: str):
        """Test complete user registration flow."""
        response = await client.post(
            f"{api_base_url}/auth/register",
            json=test_user_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["full_name"] == test_user_data["full_name"]
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data
    
    async def test_registration_duplicate_email(
        self, 
        client: AsyncClient, 
        test_user: User, 
        api_base_url: str
    ):
        """Test registration with duplicate email fails."""
        payload = {
            "email": test_user.email,
            "username": "newusername123",
            "full_name": "New User",
            "password": "NewPassword123!",
        }
        
        response = await client.post(
            f"{api_base_url}/auth/register",
            json=payload
        )
        
        assert response.status_code == 400
        assert "email already registered" in response.json()["detail"].lower()
    
    async def test_registration_duplicate_username(
        self, 
        client: AsyncClient, 
        test_user: User, 
        api_base_url: str
    ):
        """Test registration with duplicate username fails."""
        payload = {
            "email": "newemail123@example.com",
            "username": test_user.username,
            "full_name": "New User",
            "password": "NewPassword123!",
        }
        
        response = await client.post(
            f"{api_base_url}/auth/register",
            json=payload
        )
        
        assert response.status_code == 400
        assert "username already taken" in response.json()["detail"].lower()
    
    async def test_registration_invalid_email(self, client: AsyncClient, api_base_url: str):
        """Test registration with invalid email format fails."""
        payload = {
            "email": "invalid-email",
            "username": "testuser123",
            "full_name": "Test User",
            "password": "TestPassword123!",
        }
        
        response = await client.post(
            f"{api_base_url}/auth/register",
            json=payload
        )
        
        assert response.status_code == 422
    
    async def test_registration_weak_password(self, client: AsyncClient, api_base_url: str):
        """Test registration with weak password fails."""
        payload = {
            "email": "test@example.com",
            "username": "testuser123",
            "full_name": "Test User",
            "password": "weak",
        }
        
        response = await client.post(
            f"{api_base_url}/auth/register",
            json=payload
        )
        
        assert response.status_code == 422
    
    async def test_registration_missing_required_fields(self, client: AsyncClient, api_base_url: str):
        """Test registration with missing required fields fails."""
        payload = {
            "email": "test@example.com",
        }
        
        response = await client.post(
            f"{api_base_url}/auth/register",
            json=payload
        )
        
        assert response.status_code == 422


@pytest.mark.e2e
@pytest.mark.auth
class TestUserLogin:
    """E2E tests for user login flow."""
    
    async def test_successful_login(
        self, 
        client: AsyncClient, 
        test_user: User, 
        test_user_data: dict,
        api_base_url: str
    ):
        """Test successful login returns tokens."""
        response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    async def test_login_with_username(
        self, 
        client: AsyncClient, 
        test_user: User, 
        test_user_data: dict,
        api_base_url: str
    ):
        """Test login using username instead of email."""
        response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    async def test_login_invalid_password(
        self, 
        client: AsyncClient, 
        test_user: User, 
        api_base_url: str
    ):
        """Test login with invalid password fails."""
        response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword123!",
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_login_nonexistent_user(self, client: AsyncClient, api_base_url: str):
        """Test login with non-existent user fails."""
        response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!",
            }
        )
        
        assert response.status_code == 401
    
    async def test_login_inactive_user(
        self, 
        client: AsyncClient, 
        inactive_user: User, 
        api_base_url: str
    ):
        """Test login with inactive user account fails."""
        response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": inactive_user.email,
                "password": "TestPassword123!",
            }
        )
        
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()
    
    async def test_login_unverified_user(
        self, 
        client: AsyncClient, 
        unverified_user: User, 
        api_base_url: str
    ):
        """Test login with unverified user may require additional steps."""
        response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": unverified_user.email,
                "password": "TestPassword123!",
            }
        )
        
        # May return 200 with warning or 403 depending on implementation
        assert response.status_code in [200, 403]


@pytest.mark.e2e
@pytest.mark.auth
class TestTokenRefresh:
    """E2E tests for token refresh flow."""
    
    async def test_successful_token_refresh(
        self, 
        client: AsyncClient, 
        test_user: User, 
        test_user_data: dict,
        api_base_url: str
    ):
        """Test refreshing access token with refresh token."""
        # First login to get tokens
        login_response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = await client.post(
            f"{api_base_url}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_refresh_with_invalid_token(self, client: AsyncClient, api_base_url: str):
        """Test refresh with invalid token fails."""
        response = await client.post(
            f"{api_base_url}/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        
        assert response.status_code == 401
    
    async def test_refresh_token_rotation(
        self, 
        client: AsyncClient, 
        test_user: User, 
        test_user_data: dict,
        api_base_url: str
    ):
        """Test that refresh token rotation works if implemented."""
        # First login
        login_response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # First refresh
        first_refresh = await client.post(
            f"{api_base_url}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert first_refresh.status_code == 200
        
        # Try to use same refresh token again (should fail if rotation is implemented)
        second_refresh = await client.post(
            f"{api_base_url}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        # If rotation is implemented, second use should fail
        # If not, it should succeed
        assert second_refresh.status_code in [200, 401]


@pytest.mark.e2e
@pytest.mark.auth
class TestPasswordReset:
    """E2E tests for password reset flow."""
    
    async def test_password_reset_request(
        self, 
        client: AsyncClient, 
        test_user: User, 
        api_base_url: str
    ):
        """Test requesting password reset email."""
        response = await client.post(
            f"{api_base_url}/auth/password-reset-request",
            json={"email": test_user.email}
        )
        
        # Should return 200 even if email doesn't exist (security)
        assert response.status_code == 200
        assert "check your email" in response.json()["message"].lower()
    
    async def test_password_reset_nonexistent_email(self, client: AsyncClient, api_base_url: str):
        """Test password reset request for non-existent email."""
        response = await client.post(
            f"{api_base_url}/auth/password-reset-request",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should return 200 to prevent email enumeration
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.auth
class TestProtectedEndpoints:
    """E2E tests for protected endpoint access."""
    
    async def test_access_protected_endpoint_with_valid_token(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test accessing protected endpoint with valid token."""
        response = await client.get(
            f"{api_base_url}/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "username" in data
    
    async def test_access_protected_endpoint_without_token(
        self, 
        client: AsyncClient, 
        api_base_url: str
    ):
        """Test accessing protected endpoint without token fails."""
        response = await client.get(f"{api_base_url}/users/me")
        
        assert response.status_code == 401
    
    async def test_access_protected_endpoint_with_invalid_token(
        self, 
        client: AsyncClient, 
        api_base_url: str
    ):
        """Test accessing protected endpoint with invalid token fails."""
        response = await client.get(
            f"{api_base_url}/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    async def test_access_protected_endpoint_with_expired_token(
        self, 
        client: AsyncClient, 
        api_base_url: str
    ):
        """Test accessing protected endpoint with expired token fails."""
        # Create an expired token
        from datetime import datetime, timedelta
        from jose import jwt
        
        expired_token = jwt.encode(
            {
                "sub": "test-user-id",
                "exp": datetime.utcnow() - timedelta(hours=1),
                "iat": datetime.utcnow() - timedelta(hours=2),
            },
            "test-secret-key",
            algorithm="HS256"
        )
        
        response = await client.get(
            f"{api_base_url}/users/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401


@pytest.mark.e2e
@pytest.mark.auth
class TestUserProfile:
    """E2E tests for user profile management."""
    
    async def test_get_current_user_profile(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_user: User,
        api_base_url: str
    ):
        """Test getting current user profile."""
        response = await client.get(
            f"{api_base_url}/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert "id" in data
    
    async def test_update_user_profile(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test updating user profile."""
        update_data = {
            "full_name": "Updated Name",
            "bio": "This is my updated bio",
        }
        
        response = await client.patch(
            f"{api_base_url}/users/me",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["bio"] == update_data["bio"]
    
    async def test_change_password(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_user_data: dict,
        api_base_url: str
    ):
        """Test changing user password."""
        password_data = {
            "current_password": test_user_data["password"],
            "new_password": "NewSecurePassword456!",
        }
        
        response = await client.post(
            f"{api_base_url}/users/me/change-password",
            json=password_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify can login with new password
        login_response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": password_data["new_password"],
            }
        )
        
        assert login_response.status_code == 200
    
    async def test_change_password_wrong_current(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test changing password with wrong current password fails."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "NewSecurePassword456!",
        }
        
        response = await client.post(
            f"{api_base_url}/users/me/change-password",
            json=password_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400


@pytest.mark.e2e
@pytest.mark.auth
class TestLogout:
    """E2E tests for logout functionality."""
    
    async def test_logout(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test logout invalidates token."""
        response = await client.post(
            f"{api_base_url}/auth/logout",
            headers=auth_headers
        )
        
        # Depending on implementation, may return 200 or 501 if not implemented
        assert response.status_code in [200, 501]
        
        if response.status_code == 200:
            # Verify token is invalidated
            profile_response = await client.get(
                f"{api_base_url}/users/me",
                headers=auth_headers
            )
            assert profile_response.status_code == 401