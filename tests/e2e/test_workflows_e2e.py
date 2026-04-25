"""
End-to-End Tests for Complete User Workflows

This module contains scenario-based E2E tests that simulate real user workflows:
- User onboarding flow
- Project creation and task management
- Team collaboration workflow
- Cross-feature integration scenarios
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.models.task import TaskStatus, TaskPriority
from app.models.board import BoardRole
from app.models.team import TeamRole


@pytest.mark.e2e
class TestUserOnboardingWorkflow:
    """E2E tests for complete user onboarding workflow."""
    
    async def test_complete_user_onboarding(
        self, 
        client: AsyncClient, 
        test_user_data: dict,
        api_base_url: str
    ):
        """
        Test complete user onboarding flow:
        1. Register new user
        2. Login
        3. Get user profile
        4. Update profile
        5. Change password
        6. Login with new password
        """
        # Step 1: Register
        register_response = await client.post(
            f"{api_base_url}/auth/register",
            json=test_user_data
        )
        assert register_response.status_code == 201
        user_id = register_response.json()["id"]
        
        # Step 2: Login
        login_response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 3: Get profile
        profile_response = await client.get(
            f"{api_base_url}/users/me",
            headers=headers
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["email"] == test_user_data["email"]
        
        # Step 4: Update profile
        update_response = await client.patch(
            f"{api_base_url}/users/me",
            json={
                "full_name": "Updated User Name",
                "bio": "Software developer passionate about productivity",
            },
            headers=headers
        )
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "Updated User Name"
        
        # Step 5: Change password
        new_password = "NewSecurePassword789!"
        password_response = await client.post(
            f"{api_base_url}/users/me/change-password",
            json={
                "current_password": test_user_data["password"],
                "new_password": new_password,
            },
            headers=headers
        )
        assert password_response.status_code == 200
        
        # Step 6: Login with new password
        new_login_response = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": new_password,
            }
        )
        assert new_login_response.status_code == 200


@pytest.mark.e2e
class TestProjectManagementWorkflow:
    """E2E tests for project management workflow."""
    
    async def test_complete_project_workflow(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """
        Test complete project management flow:
        1. Create a board
        2. Create multiple tasks
        3. Update task statuses
        4. Assign tasks
        5. Add comments
        6. Filter and search tasks
        7. Complete tasks
        """
        # Step 1: Create board
        board_response = await client.post(
            f"{api_base_url}/boards",
            json={
                "name": "Q1 Product Launch",
                "description": "Board for managing Q1 product launch tasks",
                "is_public": True,
            },
            headers=auth_headers
        )
        assert board_response.status_code == 201
        board_id = board_response.json()["id"]
        
        # Step 2: Create tasks
        tasks = []
        task_data = [
            {"title": "Design landing page", "priority": TaskPriority.HIGH.value},
            {"title": "Set up analytics", "priority": TaskPriority.MEDIUM.value},
            {"title": "Write blog post", "priority": TaskPriority.LOW.value},
            {"title": "Configure CI/CD", "priority": TaskPriority.HIGH.value},
        ]
        
        for task in task_data:
            task_response = await client.post(
                f"{api_base_url}/tasks",
                json={
                    **task,
                    "description": f"Description for {task['title']}",
                    "board_id": board_id,
                    "status": TaskStatus.TODO.value,
                },
                headers=auth_headers
            )
            assert task_response.status_code == 201
            tasks.append(task_response.json())
        
        assert len(tasks) == 4
        
        # Step 3: Update task statuses
        for i, task in enumerate(tasks[:2]):
            update_response = await client.patch(
                f"{api_base_url}/tasks/{task['id']}",
                json={"status": TaskStatus.IN_PROGRESS.value},
                headers=auth_headers
            )
            assert update_response.status_code == 200
            assert update_response.json()["status"] == TaskStatus.IN_PROGRESS.value
        
        # Step 4: Add comments to first task
        comment_response = await client.post(
            f"{api_base_url}/tasks/{tasks[0]['id']}/comments",
            json={"content": "Started working on the designs"},
            headers=auth_headers
        )
        assert comment_response.status_code == 201
        
        comment2_response = await client.post(
            f"{api_base_url}/tasks/{tasks[0]['id']}/comments",
            json={"content": "First draft completed, need review"},
            headers=auth_headers
        )
        assert comment2_response.status_code == 201
        
        # Step 5: Filter high priority tasks
        filter_response = await client.get(
            f"{api_base_url}/boards/{board_id}/tasks",
            params={"priority": TaskPriority.HIGH.value},
            headers=auth_headers
        )
        assert filter_response.status_code == 200
        high_priority_tasks = filter_response.json()
        assert len(high_priority_tasks) == 2
        
        # Step 6: Search for specific task
        search_response = await client.get(
            f"{api_base_url}/tasks/search",
            params={"q": "landing", "board_id": board_id},
            headers=auth_headers
        )
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results) >= 1
        assert any("landing" in task["title"].lower() for task in search_results)
        
        # Step 7: Complete tasks
        for task in tasks[:2]:
            complete_response = await client.patch(
                f"{api_base_url}/tasks/{task['id']}",
                json={"status": TaskStatus.DONE.value},
                headers=auth_headers
            )
            assert complete_response.status_code == 200
            assert complete_response.json()["status"] == TaskStatus.DONE.value
        
        # Verify board statistics
        board_response = await client.get(
            f"{api_base_url}/boards/{board_id}",
            headers=auth_headers
        )
        assert board_response.status_code == 200


@pytest.mark.e2e
class TestTeamCollaborationWorkflow:
    """E2E tests for team collaboration workflow."""
    
    async def test_team_collaboration_workflow(
        self, 
        client: AsyncClient, 
        test_user_data: dict,
        test_user_data_2: dict,
        api_base_url: str
    ):
        """
        Test team collaboration flow:
        1. User 1 creates team
        2. User 1 invites User 2
        3. User 2 accepts invitation
        4. User 1 creates board for team
        5. Both users create and manage tasks
        6. User 2 leaves team
        """
        # Register and login both users
        # User 1
        await client.post(f"{api_base_url}/auth/register", json=test_user_data)
        login1 = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            }
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}
        
        # User 2
        await client.post(f"{api_base_url}/auth/register", json=test_user_data_2)
        login2 = await client.post(
            f"{api_base_url}/auth/login",
            data={
                "username": test_user_data_2["email"],
                "password": test_user_data_2["password"],
            }
        )
        user2_id = login2.json().get("user_id") or "user2-id"
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}
        
        # Step 1: User 1 creates team
        team_response = await client.post(
            f"{api_base_url}/teams",
            json={
                "name": "Engineering Team",
                "description": "Core engineering team",
            },
            headers=headers1
        )
        assert team_response.status_code == 201
        team_id = team_response.json()["id"]
        
        # Get User 2 ID from profile
        user2_profile = await client.get(
            f"{api_base_url}/users/me",
            headers=headers2
        )
        user2_id = user2_profile.json()["id"]
        
        # Step 2: User 1 invites User 2
        invite_response = await client.post(
            f"{api_base_url}/teams/{team_id}/invite",
            json={
                "user_id": user2_id,
                "role": TeamRole.MEMBER.value,
            },
            headers=headers1
        )
        assert invite_response.status_code == 201
        
        # Step 3: Verify User 2 can see team
        teams_response = await client.get(
            f"{api_base_url}/teams",
            headers=headers2
        )
        assert teams_response.status_code == 200
        assert any(team["id"] == team_id for team in teams_response.json())
        
        # Step 4: User 1 creates board
        board_response = await client.post(
            f"{api_base_url}/boards",
            json={
                "name": "Sprint 1",
                "description": "Sprint 1 board",
                "is_public": False,
            },
            headers=headers1
        )
        assert board_response.status_code == 201
        board_id = board_response.json()["id"]
        
        # Add board to team
        await client.post(
            f"{api_base_url}/teams/{team_id}/boards",
            json={"board_id": board_id},
            headers=headers1
        )
        
        # Add User 2 to board
        await client.post(
            f"{api_base_url}/boards/{board_id}/members",
            json={
                "user_id": user2_id,
                "role": BoardRole.MEMBER.value,
            },
            headers=headers1
        )
        
        # Step 5: Both users create tasks
        task1 = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "User 1 Task",
                "board_id": board_id,
                "status": TaskStatus.TODO.value,
            },
            headers=headers1
        )
        assert task1.status_code == 201
        
        task2 = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "User 2 Task",
                "board_id": board_id,
                "status": TaskStatus.TODO.value,
            },
            headers=headers2
        )
        assert task2.status_code == 201
        
        # Step 6: User 2 leaves team
        leave_response = await client.post(
            f"{api_base_url}/teams/{team_id}/leave",
            headers=headers2
        )
        assert leave_response.status_code == 200


@pytest.mark.e2e
class TestBoardPrivacyWorkflow:
    """E2E tests for board privacy workflow."""
    
    async def test_private_board_workflow(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        auth_headers_user_2: dict,
        api_base_url: str
    ):
        """
        Test private board workflow:
        1. Create private board
        2. Verify only owner can access
        3. Add member
        4. Verify member can access
        5. Remove member
        6. Verify member cannot access
        """
        # Step 1: Create private board
        board_response = await client.post(
            f"{api_base_url}/boards",
            json={
                "name": "Secret Project",
                "description": "Confidential board",
                "is_public": False,
            },
            headers=auth_headers
        )
        assert board_response.status_code == 201
        board_id = board_response.json()["id"]
        
        # Step 2: Verify owner can access
        owner_access = await client.get(
            f"{api_base_url}/boards/{board_id}",
            headers=auth_headers
        )
        assert owner_access.status_code == 200
        
        # Step 3: Verify non-member cannot access
        non_member_access = await client.get(
            f"{api_base_url}/boards/{board_id}",
            headers=auth_headers_user_2
        )
        assert non_member_access.status_code in [403, 404]
        
        # Get User 2 ID
        user2_profile = await client.get(
            f"{api_base_url}/users/me",
            headers=auth_headers_user_2
        )
        user2_id = user2_profile.json()["id"]
        
        # Step 4: Add member
        add_member = await client.post(
            f"{api_base_url}/boards/{board_id}/members",
            json={
                "user_id": user2_id,
                "role": BoardRole.MEMBER.value,
            },
            headers=auth_headers
        )
        assert add_member.status_code == 201
        
        # Step 5: Verify member can now access
        member_access = await client.get(
            f"{api_base_url}/boards/{board_id}",
            headers=auth_headers_user_2
        )
        assert member_access.status_code == 200
        
        # Step 6: Remove member
        remove_member = await client.delete(
            f"{api_base_url}/boards/{board_id}/members/{user2_id}",
            headers=auth_headers
        )
        assert remove_member.status_code == 204
        
        # Step 7: Verify member cannot access again
        removed_access = await client.get(
            f"{api_base_url}/boards/{board_id}",
            headers=auth_headers_user_2
        )
        assert removed_access.status_code in [403, 404]


@pytest.mark.e2e
class TestTaskLifecycleWorkflow:
    """E2E tests for complete task lifecycle."""
    
    async def test_task_lifecycle(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: dict,
        api_base_url: str
    ):
        """
        Test complete task lifecycle:
        1. Create task
        2. Add comments
        3. Assign to user
        4. Update status through workflow
        5. Add more comments
        6. Mark as complete
        7. Optionally archive
        """
        # Step 1: Create task
        task_response = await client.post(
            f"{api_base_url}/tasks",
            json={
                "title": "Feature Implementation",
                "description": "Implement new feature",
                "board_id": test_board["id"],
                "status": TaskStatus.TODO.value,
                "priority": TaskPriority.HIGH.value,
            },
            headers=auth_headers
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]
        
        # Step 2: Add initial comments
        await client.post(
            f"{api_base_url}/tasks/{task_id}/comments",
            json={"content": "Initial requirements gathered"},
            headers=auth_headers
        )
        
        # Step 3: Start working on task
        await client.patch(
            f"{api_base_url}/tasks/{task_id}",
            json={"status": TaskStatus.IN_PROGRESS.value},
            headers=auth_headers
        )
        
        # Step 4: Add progress comment
        await client.post(
            f"{api_base_url}/tasks/{task_id}/comments",
            json={"content": "Implementation 50% complete"},
            headers=auth_headers
        )
        
        # Step 5: Move to review
        await client.patch(
            f"{api_base_url}/tasks/{task_id}",
            json={"status": TaskStatus.IN_REVIEW.value},
            headers=auth_headers
        )
        
        # Step 6: Complete task
        await client.patch(
            f"{api_base_url}/tasks/{task_id}",
            json={{"status": TaskStatus.DONE.value}},
            headers=auth_headers
        )
        
        # Step 7: Verify final state
        final_task = await client.get(
            f"{api_base_url}/tasks/{task_id}",
            headers=auth_headers
        )
        assert final_task.status_code == 200
        assert final_task.json()["status"] == TaskStatus.DONE.value
        
        # Verify comments
        comments = await client.get(
            f"{api_base_url}/tasks/{task_id}/comments",
            headers=auth_headers
        )
        assert comments.status_code == 200
        assert len(comments.json()) >= 2


@pytest.mark.e2e
class TestBulkOperationsWorkflow:
    """E2E tests for bulk operations workflow."""
    
    async def test_bulk_operations(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: dict,
        api_base_url: str
    ):
        """
        Test bulk operations:
        1. Create multiple tasks
        2. Bulk update status
        3. Bulk assign
        4. Bulk delete
        """
        # Step 1: Create multiple tasks
        task_ids = []
        for i in range(5):
            task_response = await client.post(
                f"{api_base_url}/tasks",
                json={
                    "title": f"Bulk Task {i+1}",
                    "board_id": test_board["id"],
                    "status": TaskStatus.TODO.value,
                },
                headers=auth_headers
            )
            assert task_response.status_code == 201
            task_ids.append(task_response.json()["id"])
        
        # Step 2: Bulk update status
        bulk_update = await client.post(
            f"{api_base_url}/tasks/bulk-update",
            json={
                "task_ids": task_ids,
                "updates": {"status": TaskStatus.IN_PROGRESS.value}
            },
            headers=auth_headers
        )
        assert bulk_update.status_code == 200
        assert bulk_update.json()["updated_count"] == 5
        
        # Verify updates
        for task_id in task_ids:
            task = await client.get(
                f"{api_base_url}/tasks/{task_id}",
                headers=auth_headers
            )
            assert task.json()["status"] == TaskStatus.IN_PROGRESS.value
        
        # Step 3: Bulk delete
        bulk_delete = await client.post(
            f"{api_base_url}/tasks/bulk-delete",
            json={"task_ids": task_ids[:3]},
            headers=auth_headers
        )
        assert bulk_delete.status_code == 200
        assert bulk_delete.json()["deleted_count"] == 3
        
        # Verify deletions
        for task_id in task_ids[:3]:
            deleted_task = await client.get(
                f"{api_base_url}/tasks/{task_id}",
                headers=auth_headers
            )
            assert deleted_task.status_code == 404
        
        # Verify remaining tasks
        for task_id in task_ids[3:]:
            remaining_task = await client.get(
                f"{api_base_url}/tasks/{task_id}",
                headers=auth_headers
            )
            assert remaining_task.status_code == 200