"""
End-to-End Tests for Task Management

This module contains comprehensive E2E tests for task operations including:
- Task CRUD operations
- Task status transitions
- Task assignments
- Task filtering and search
- Task comments and attachments
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskPriority
from app.models.user import User
from app.models.board import Board


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskCreation:
    """E2E tests for task creation."""
    
    async def test_create_task_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        test_task_data: dict,
        api_base_url: str
    ):
        """Test successful task creation."""
        payload = {
            **test_task_data,
            "board_id": str(test_board.id),
        }
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["status"] == payload["status"]
        assert data["priority"] == payload["priority"]
        assert "id" in data
        assert "created_at" in data
    
    async def test_create_task_without_auth(
        self, 
        client: AsyncClient, 
        test_board: Board,
        test_task_data: dict,
        api_base_url: str
    ):
        """Test task creation without authentication fails."""
        payload = {
            **test_task_data,
            "board_id": str(test_board.id),
        }
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json=payload
        )
        
        assert response.status_code == 401
    
    async def test_create_task_on_unauthorized_board(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        private_board: Board,
        test_task_data: dict,
        api_base_url: str
    ):
        """Test task creation on board without access fails."""
        payload = {
            **test_task_data,
            "board_id": str(private_board.id),
        }
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json=payload,
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_create_task_missing_required_fields(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test task creation with missing required fields fails."""
        payload = {
            "description": "Task without title",
        }
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_create_task_invalid_priority(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test task creation with invalid priority fails."""
        payload = {
            "title": "Test Task",
            "board_id": str(test_board.id),
            "priority": "invalid_priority",
        }
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskRetrieval:
    """E2E tests for task retrieval."""
    
    async def test_get_task_by_id(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test retrieving a specific task by ID."""
        response = await client.get(
            f"{api_base_url}/tasks/{test_task.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_task.id)
        assert data["title"] == test_task.title
        assert data["description"] == test_task.description
    
    async def test_get_nonexistent_task(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test retrieving non-existent task returns 404."""
        response = await client.get(
            f"{api_base_url}/tasks/123e4567-e89b-12d3-a456-426614174000",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_get_tasks_by_board(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test retrieving all tasks for a board."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(multiple_tasks)
    
    async def test_get_tasks_pagination(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test task list pagination."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={"skip": 0, "limit": 5},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5
        
        # Get next page
        response2 = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={"skip": 5, "limit": 5},
            headers=auth_headers
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Ensure no overlap between pages
        page1_ids = {task["id"] for task in data}
        page2_ids = {task["id"] for task in data2}
        assert not page1_ids.intersection(page2_ids)


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskUpdate:
    """E2E tests for task updates."""
    
    async def test_update_task_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test successful task update."""
        update_data = {
            "title": "Updated Task Title",
            "description": "Updated description",
            "priority": TaskPriority.HIGH.value,
        }
        
        response = await client.patch(
            f"{api_base_url}/tasks/{test_task.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["priority"] == update_data["priority"]
    
    async def test_update_task_status_transition(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test task status transition."""
        update_data = {
            "status": TaskStatus.IN_PROGRESS.value,
        }
        
        response = await client.patch(
            f"{api_base_url}/tasks/{test_task.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TaskStatus.IN_PROGRESS.value
        
        # Transition to done
        update_data = {"status": TaskStatus.DONE.value}
        response2 = await client.patch(
            f"{api_base_url}/tasks/{test_task.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response2.status_code == 200
        assert response2.json()["status"] == TaskStatus.DONE.value
    
    async def test_update_task_by_non_member(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test task update by non-board member fails."""
        update_data = {"title": "Hacked Title"}
        
        response = await client.patch(
            f"{api_base_url}/tasks/{test_task.id}",
            json=update_data,
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_update_task_invalid_status(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test task update with invalid status fails."""
        update_data = {"status": "invalid_status"}
        
        response = await client.patch(
            f"{api_base_url}/tasks/{test_task.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskDeletion:
    """E2E tests for task deletion."""
    
    async def test_delete_task_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test successful task deletion."""
        response = await client.delete(
            f"{api_base_url}/tasks/{test_task.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify task is deleted
        get_response = await client.get(
            f"{api_base_url}/tasks/{test_task.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    async def test_delete_task_by_non_owner(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test task deletion by non-owner fails."""
        response = await client.delete(
            f"{api_base_url}/tasks/{test_task.id}",
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_delete_nonexistent_task(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test deleting non-existent task returns 404."""
        response = await client.delete(
            f"{api_base_url}/tasks/123e4567-e89b-12d3-a456-426614174000",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskAssignment:
    """E2E tests for task assignment."""
    
    async def test_assign_task_to_user(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        test_user_2: User,
        api_base_url: str
    ):
        """Test assigning task to a user."""
        response = await client.post(
            f"{api_base_url}/tasks/{test_task.id}/assign",
            json={"assignee_id": str(test_user_2.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["assignee_id"] == str(test_user_2.id)
    
    async def test_unassign_task(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        test_user_2: User,
        api_base_url: str
    ):
        """Test unassigning a task."""
        # First assign the task
        await client.post(
            f"{api_base_url}/tasks/{test_task.id}/assign",
            json={"assignee_id": str(test_user_2.id)},
            headers=auth_headers
        )
        
        # Then unassign
        response = await client.post(
            f"{api_base_url}/tasks/{test_task.id}/unassign",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["assignee_id"] is None
    
    async def test_get_assigned_tasks(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        test_user: User,
        api_base_url: str
    ):
        """Test retrieving tasks assigned to current user."""
        response = await client.get(
            f"{api_base_url}/tasks/assigned-to-me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include tasks where user is assignee
        for task in data:
            assert task["assignee_id"] == str(test_user.id)


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskFiltering:
    """E2E tests for task filtering and search."""
    
    async def test_filter_tasks_by_status(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test filtering tasks by status."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={"status": TaskStatus.TODO.value},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        for task in data:
            assert task["status"] == TaskStatus.TODO.value
    
    async def test_filter_tasks_by_priority(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test filtering tasks by priority."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={"priority": TaskPriority.HIGH.value},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        for task in data:
            assert task["priority"] == TaskPriority.HIGH.value
    
    async def test_filter_tasks_by_assignee(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        test_user: User,
        api_base_url: str
    ):
        """Test filtering tasks by assignee."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={"assignee_id": str(test_user.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        for task in data:
            assert task["assignee_id"] == str(test_user.id)
    
    async def test_search_tasks(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        test_task: Task,
        api_base_url: str
    ):
        """Test searching tasks by query string."""
        response = await client.get(
            f"{api_base_url}/tasks/search",
            params={"q": test_task.title[:10], "board_id": str(test_board.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should find the task
        assert any(task["id"] == str(test_task.id) for task in data)
    
    async def test_filter_tasks_by_date_range(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test filtering tasks by due date range."""
        from_date = datetime.utcnow().isoformat()
        to_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/tasks",
            params={
                "due_date_from": from_date,
                "due_date_to": to_date,
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskBulkOperations:
    """E2E tests for bulk task operations."""
    
    async def test_bulk_update_task_status(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test bulk updating task status."""
        task_ids = [str(task.id) for task in multiple_tasks[:3]]
        
        response = await client.post(
            f"{api_base_url}/tasks/bulk-update",
            json={
                "task_ids": task_ids,
                "updates": {"status": TaskStatus.IN_PROGRESS.value}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 3
        
        # Verify updates
        for task_id in task_ids:
            get_response = await client.get(
                f"{api_base_url}/tasks/{task_id}",
                headers=auth_headers
            )
            assert get_response.json()["status"] == TaskStatus.IN_PROGRESS.value
    
    async def test_bulk_delete_tasks(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test bulk deleting tasks."""
        task_ids = [str(task.id) for task in multiple_tasks[-3:]]
        
        response = await client.post(
            f"{api_base_url}/tasks/bulk-delete",
            json={"task_ids": task_ids},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 3
        
        # Verify deletions
        for task_id in task_ids:
            get_response = await client.get(
                f"{api_base_url}/tasks/{task_id}",
                headers=auth_headers
            )
            assert get_response.status_code == 404


@pytest.mark.e2e
@pytest.mark.tasks
class TestTaskComments:
    """E2E tests for task comments."""
    
    async def test_add_comment_to_task(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test adding a comment to a task."""
        response = await client.post(
            f"{api_base_url}/tasks/{test_task.id}/comments",
            json={"content": "This is a test comment"},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a test comment"
        assert "id" in data
        assert "created_at" in data
    
    async def test_get_task_comments(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test retrieving comments for a task."""
        # Add a comment first
        await client.post(
            f"{api_base_url}/tasks/{test_task.id}/comments",
            json={"content": "Test comment 1"},
            headers=auth_headers
        )
        
        await client.post(
            f"{api_base_url}/tasks/{test_task.id}/comments",
            json={"content": "Test comment 2"},
            headers=auth_headers
        )
        
        response = await client.get(
            f"{api_base_url}/tasks/{test_task.id}/comments",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
    
    async def test_delete_comment(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_task: Task,
        api_base_url: str
    ):
        """Test deleting a comment."""
        # Add a comment
        comment_response = await client.post(
            f"{api_base_url}/tasks/{test_task.id}/comments",
            json={"content": "Comment to delete"},
            headers=auth_headers
        )
        
        comment_id = comment_response.json()["id"]
        
        # Delete the comment
        response = await client.delete(
            f"{api_base_url}/tasks/{test_task.id}/comments/{comment_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204