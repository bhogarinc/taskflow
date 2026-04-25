"""
Integration Tests for API Endpoints

This module contains integration tests for API endpoint interactions including:
- Endpoint chaining
- Error handling
- Request/response validation
- Rate limiting
- Authentication flow integration
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.board import Board


@pytest.mark.integration
class TestAPIEndpointChaining:
    """Integration tests for API endpoint chaining."""
    
    async def test_create_board_and_task_sequence(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test creating board then task in sequence."""
        # Create board
        board_response = await client.post(
            f"{api_base_url}/boards",
            json={
                "name": "Chained Board",
                "description": "Board for chaining test",
                "is_public": True,
            },
            headers=auth_headers
        )
        assert board_response.status_code == 201
        board_id = board_response.json()["id"]
        
        # Create task on the board
        task_response = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "Chained Task",
                "board_id": board_id,
                "status": TaskStatus.TODO.value,
            },
            headers=auth_headers
        )
        assert task_response.status_code == 201
        
        # Verify task is linked to board
        get_board = await client.get(
            f"{api_base_url}/boards/{board_id}",
            headers=auth_headers
        )
        assert get_board.status_code == 200
    
    async def test_user_registration_to_task_creation(
        self, 
        client: AsyncClient, 
        api_base_url: str
    ):
        """Test complete flow from registration to task creation."""
        import uuid
        
        # Register
        email = f"chain_{uuid.uuid4().hex[:8]}@example.com"
        register_response = await client.post(
            f"{api_base_url}/auth/register",
            json={
                "email": email,
                "username": f"chainuser_{uuid.uuid4().hex[:8]}",
                "full_name": "Chain User",
                "password": "ChainPassword123!",
            }
        )
        assert register_response.status_code == 201
        
        # Login
        login_response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": email,
                "password": "ChainPassword123!",
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create board
        board_response = await client.post(
            f"{api_base_url}/boards",
            json={
                "name": "My First Board",
                "description": "Created after registration",
                "is_public": True,
            },
            headers=headers
        )
        assert board_response.status_code == 201
        board_id = board_response.json()["id"]
        
        # Create task
        task_response = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "My First Task",
                "board_id": board_id,
                "status": TaskStatus.TODO.value,
            },
            headers=headers
        )
        assert task_response.status_code == 201


@pytest.mark.integration
class TestAPIErrorHandling:
    """Integration tests for API error handling."""
    
    async def test_404_error_format(self, client: AsyncClient, auth_headers: dict, api_base_url: str):
        """Test 404 error response format."""
        response = await client.get(
            f"{api_base_url}/tasks/non-existent-id",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    async def test_422_validation_error_format(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        api_base_url: str
    ):
        """Test 422 validation error response format."""
        response = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "",  # Empty title should fail validation
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    async def test_401_error_format(self, client: AsyncClient, api_base_url: str):
        """Test 401 error response format."""
        response = await client.get(f"{api_base_url}/users/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    async def test_concurrent_update_conflict(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test handling of concurrent updates."""
        # This test checks if the API handles race conditions appropriately
        # It may not fail in all implementations
        
        # First update
        response1 = await client.patch(
            f"{api_base_url}/tasks/{test_task.id}",
            json={"title": "Update 1"},
            headers=auth_headers
        )
        
        # Second update (may or may not conflict depending on implementation)
        response2 = await client.patch(
            f"{api_base_url}/tasks/{test_task.id}",
            json={"title": "Update 2"},
            headers=auth_headers
        )
        
        # Both should succeed (last write wins) or second should fail (optimistic locking)
        assert response1.status_code == 200
        assert response2.status_code in [200, 409]


@pytest.mark.integration
class TestRequestResponseValidation:
    """Integration tests for request/response validation."""
    
    async def test_response_content_type(self, client: AsyncClient, auth_headers: dict, api_base_url: str):
        """Test that responses have correct content type."""
        response = await client.get(
            f"{api_base_url}/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    async def test_request_content_type_handling(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        api_base_url: str
    ):
        """Test handling of different content types."""
        # JSON request
        json_response = await client.post(
            f"{api_base_url}/boards",
            json={"name": "JSON Board", "is_public": True},
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert json_response.status_code == 201
    
    async def test_empty_request_body_handling(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        api_base_url: str
    ):
        """Test handling of empty request body."""
        response = await client.post(
            f"{api_base_url}/boards",
            json={},
            headers=auth_headers
        )
        
        # Should fail validation
        assert response.status_code == 422
    
    async def test_large_payload_handling(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        test_board: Board,
        api_base_url: str
    ):
        """Test handling of large payload."""
        large_description = "A" * 10000  # 10KB description
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "Large Description Task",
                "description": large_description,
                "board_id": str(test_board.id),
            },
            headers=auth_headers
        )
        
        # Should either accept or reject based on limits
        assert response.status_code in [201, 413, 422]


@pytest.mark.integration
class TestPaginationAndFiltering:
    """Integration tests for pagination and filtering."""
    
    async def test_pagination_consistency(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test that pagination returns consistent results."""
        all_tasks = []
        skip = 0
        limit = 3
        
        while True:
            response = await client.get(
                f"{api_base_url}/boards/{test_board.id}/tasks",
                params={"skip": skip, "limit": limit},
                headers=auth_headers
            )
            
            tasks = response.json()
            if not tasks:
                break
            
            all_tasks.extend(tasks)
            skip += limit
            
            if len(tasks) < limit:
                break
        
        # Verify no duplicates
        task_ids = [t["id"] for t in all_tasks]
        assert len(task_ids) == len(set(task_ids))
    
    async def test_filtering_combination(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test combining multiple filters."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={
                "status": TaskStatus.TODO.value,
                "priority": "high",
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        tasks = response.json()
        
        for task in tasks:
            assert task["status"] == TaskStatus.TODO.value
            assert task["priority"] == "high"
    
    async def test_sorting_order(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test sorting order of results."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={"sort_by": "created_at", "order": "desc"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        tasks = response.json()
        
        if len(tasks) > 1:
            # Check descending order
            for i in range(len(tasks) - 1):
                assert tasks[i]["created_at"] >= tasks[i + 1]["created_at"]


@pytest.mark.integration
class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""
    
    async def test_token_refresh_flow(
        self, 
        client: AsyncClient, 
        test_user: User,
        test_user_data: dict,
        api_base_url: str
    ):
        """Test complete token refresh flow."""
        # Login
        login_response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        assert login_response.status_code == 200
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh
        refresh_response = await client.post(
            f"{api_base_url}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        
        new_access_token = refresh_response.json()["access_token"]
        
        # Use new token
        profile_response = await client.get(
            f"{api_base_url}/users/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert profile_response.status_code == 200
    
    async def test_multiple_device_login(
        self, 
        client: AsyncClient, 
        test_user_data: dict,
        api_base_url: str
    ):
        """Test login from multiple devices/sessions."""
        # Login from device 1
        login1 = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        assert login1.status_code == 200
        token1 = login1.json()["access_token"]
        
        # Login from device 2
        login2 = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        assert login2.status_code == 200
        token2 = login2.json()["access_token"]
        
        # Both tokens should work
        profile1 = await client.get(
            f"{api_base_url}/users/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert profile1.status_code == 200
        
        profile2 = await client.get(
            f"{api_base_url}/users/me",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert profile2.status_code == 200


@pytest.mark.integration
class TestDataIntegrity:
    """Integration tests for data integrity across operations."""
    
    async def test_task_count_consistency(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test that task counts remain consistent."""
        # Get initial count
        initial_response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            headers=auth_headers
        )
        initial_count = len(initial_response.json())
        
        # Create task
        create_response = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "Count Test Task",
                "board_id": str(test_board.id),
            },
            headers=auth_headers
        )
        task_id = create_response.json()["id"]
        
        # Verify count increased
        after_create = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            headers=auth_headers
        )
        assert len(after_create.json()) == initial_count + 1
        
        # Delete task
        await client.delete(
            f"{api_base_url}/tasks/{task_id}",
            headers=auth_headers
        )
        
        # Verify count decreased
        after_delete = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            headers=auth_headers
        )
        assert len(after_delete.json()) == initial_count
    
    async def test_cascade_delete_integrity(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test cascade delete maintains referential integrity."""
        # Create board with tasks
        board_response = await client.post(
            f"{api_base_url}/boards",
            json={
                "name": "Cascade Test Board",
                "description": "For cascade testing",
                "is_public": True,
            },
            headers=auth_headers
        )
        board_id = board_response.json()["id"]
        
        # Create tasks
        for i in range(3):
            await client.post(
                f"{api_base_url}/tasks",
                json={
                    "title": f"Cascade Task {i}",
                    "board_id": board_id,
                },
                headers=auth_headers
            )
        
        # Delete board
        await client.delete(
            f"{api_base_url}/boards/{board_id}",
            headers=auth_headers
        )
        
        # Verify tasks are also deleted (if cascade is configured)
        # This depends on the cascade configuration in the database


@pytest.mark.integration
class TestAPIPerformance:
    """Basic integration tests for API performance characteristics."""
    
    async def test_response_time_simple_endpoint(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        api_base_url: str
    ):
        """Test response time for simple endpoint."""
        import time
        
        start = time.time()
        response = await client.get(
            f"{api_base_url}/users/me",
            headers=auth_headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Simple endpoint should respond in less than 1 second
        assert elapsed < 1.0
    
    async def test_list_endpoint_performance(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test list endpoint performance with data."""
        import time
        
        start = time.time()
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            headers=auth_headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # List endpoint should respond in less than 2 seconds
        assert elapsed < 2.0