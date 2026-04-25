"""
End-to-End Tests for Board Management

This module contains comprehensive E2E tests for board operations including:
- Board CRUD operations
- Board membership and permissions
- Board visibility (public/private)
- Board templates
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import Board, BoardMember, BoardRole
from app.models.user import User


@pytest.mark.e2e
@pytest.mark.boards
class TestBoardCreation:
    """E2E tests for board creation."""
    
    async def test_create_board_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board_data: dict,
        api_base_url: str
    ):
        """Test successful board creation."""
        response = await client.post(
            f"{api_base_url}/boards",
            json=test_board_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == test_board_data["name"]
        assert data["description"] == test_board_data["description"]
        assert data["is_public"] == test_board_data["is_public"]
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data
    
    async def test_create_private_board(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test creating a private board."""
        payload = {
            "name": "Private Test Board",
            "description": "A private board",
            "is_public": False,
        }
        
        response = await client.post(
            f"{api_base_url}/boards",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        assert response.json()["is_public"] is False
    
    async def test_create_board_without_auth(
        self, 
        client: AsyncClient, 
        test_board_data: dict,
        api_base_url: str
    ):
        """Test board creation without authentication fails."""
        response = await client.post(
            f"{api_base_url}/boards",
            json=test_board_data
        )
        
        assert response.status_code == 401
    
    async def test_create_board_missing_name(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test board creation without name fails."""
        payload = {
            "description": "Board without name",
        }
        
        response = await client.post(
            f"{api_base_url}/boards",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_create_board_duplicate_name_same_user(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test creating board with duplicate name for same user."""
        payload = {
            "name": test_board.name,
            "description": "Another board with same name",
        }
        
        response = await client.post(
            f"{api_base_url}/boards",
            json=payload,
            headers=auth_headers
        )
        
        # May allow or disallow based on implementation
        assert response.status_code in [201, 400]


@pytest.mark.e2e
@pytest.mark.boards
class TestBoardRetrieval:
    """E2E tests for board retrieval."""
    
    async def test_get_board_by_id(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test retrieving a specific board."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_board.id)
        assert data["name"] == test_board.name
    
    async def test_get_public_board_without_auth(
        self, 
        client: AsyncClient, 
        test_board: Board,
        api_base_url: str
    ):
        """Test retrieving public board without authentication."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_board.id)
    
    async def test_get_private_board_without_auth(
        self, 
        client: AsyncClient, 
        private_board: Board,
        api_base_url: str
    ):
        """Test retrieving private board without authentication fails."""
        response = await client.get(
            f"{api_base_url}/boards/{private_board.id}"
        )
        
        assert response.status_code in [401, 403, 404]
    
    async def test_get_private_board_by_non_member(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        private_board: Board,
        api_base_url: str
    ):
        """Test retrieving private board by non-member fails."""
        response = await client.get(
            f"{api_base_url}/boards/{private_board.id}",
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_get_nonexistent_board(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test retrieving non-existent board returns 404."""
        response = await client.get(
            f"{api_base_url}/boards/123e4567-e89b-12d3-a456-426614174000",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_list_user_boards(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test listing boards for current user."""
        response = await client.get(
            f"{api_base_url}/boards",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(board["id"] == str(test_board.id) for board in data)
    
    async def test_list_public_boards(
        self, 
        client: AsyncClient, 
        test_board: Board,
        api_base_url: str
    ):
        """Test listing all public boards."""
        response = await client.get(
            f"{api_base_url}/boards/public"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include public boards
        assert any(board["id"] == str(test_board.id) for board in data)


@pytest.mark.e2e
@pytest.mark.boards
class TestBoardUpdate:
    """E2E tests for board updates."""
    
    async def test_update_board_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test successful board update."""
        update_data = {
            "name": "Updated Board Name",
            "description": "Updated description",
        }
        
        response = await client.patch(
            f"{api_base_url}/boards/{test_board.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    async def test_update_board_visibility(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test updating board visibility."""
        update_data = {"is_public": False}
        
        response = await client.patch(
            f"{api_base_url}/boards/{test_board.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["is_public"] is False
    
    async def test_update_board_by_non_owner(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test board update by non-owner fails."""
        update_data = {"name": "Hacked Board Name"}
        
        response = await client.patch(
            f"{api_base_url}/boards/{test_board.id}",
            json=update_data,
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.boards
class TestBoardDeletion:
    """E2E tests for board deletion."""
    
    async def test_delete_board_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test successful board deletion."""
        response = await client.delete(
            f"{api_base_url}/boards/{test_board.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify board is deleted
        get_response = await client.get(
            f"{api_base_url}/boards/{test_board.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    async def test_delete_board_by_non_owner(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test board deletion by non-owner fails."""
        response = await client.delete(
            f"{api_base_url}/boards/{test_board.id}",
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_delete_board_with_tasks(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        multiple_tasks: list,
        api_base_url: str
    ):
        """Test deleting board with existing tasks."""
        response = await client.delete(
            f"{api_base_url}/boards/{test_board.id}",
            headers=auth_headers
        )
        
        # May allow or prevent based on implementation
        assert response.status_code in [204, 400]


@pytest.mark.e2e
@pytest.mark.boards
class TestBoardMembership:
    """E2E tests for board membership management."""
    
    async def test_add_member_to_board(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        test_user_2: User,
        api_base_url: str
    ):
        """Test adding a member to a board."""
        response = await client.post(
            f"{api_base_url}/boards/{test_board.id}/members",
            json={
                "user_id": str(test_user_2.id),
                "role": BoardRole.MEMBER.value,
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(test_user_2.id)
        assert data["role"] == BoardRole.MEMBER.value
    
    async def test_add_member_by_non_owner(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test adding member by non-owner fails."""
        response = await client.post(
            f"{api_base_url}/boards/{test_board.id}/members",
            json={
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "role": BoardRole.MEMBER.value,
            },
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_list_board_members(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test listing board members."""
        response = await client.get(
            f"{api_base_url}/boards/{test_board.id}/members",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include the owner
        assert len(data) >= 1
    
    async def test_update_member_role(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        test_user_2: User,
        api_base_url: str
    ):
        """Test updating a member's role."""
        # First add member
        await client.post(
            f"{api_base_url}/boards/{test_board.id}/members",
            json={
                "user_id": str(test_user_2.id),
                "role": BoardRole.MEMBER.value,
            },
            headers=auth_headers
        )
        
        # Update role
        response = await client.patch(
            f"{api_base_url}/boards/{test_board.id}/members/{test_user_2.id}",
            json={"role": BoardRole.ADMIN.value},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["role"] == BoardRole.ADMIN.value
    
    async def test_remove_member_from_board(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        test_user_2: User,
        api_base_url: str
    ):
        """Test removing a member from a board."""
        # First add member
        await client.post(
            f"{api_base_url}/boards/{test_board.id}/members",
            json={
                "user_id": str(test_user_2.id),
                "role": BoardRole.MEMBER.value,
            },
            headers=auth_headers
        )
        
        # Remove member
        response = await client.delete(
            f"{api_base_url}/boards/{test_board.id}/members/{test_user_2.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    async def test_leave_board(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        board_with_member: Board,
        test_user_2: User,
        api_base_url: str
    ):
        """Test member leaving a board."""
        response = await client.post(
            f"{api_base_url}/boards/{board_with_member.id}/leave",
            headers=auth_headers_user_2
        )
        
        assert response.status_code == 200
        
        # Verify no longer a member
        members_response = await client.get(
            f"{api_base_url}/boards/{board_with_member.id}/members",
            headers=auth_headers_user_2
        )
        
        # Should no longer have access
        assert members_response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.boards
class TestBoardPermissions:
    """E2E tests for board permission enforcement."""
    
    async def test_member_can_create_task(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        board_with_member: Board,
        api_base_url: str
    ):
        """Test board member can create tasks."""
        payload = {
            "title": "Member Created Task",
            "description": "Created by a member",
            "board_id": str(board_with_member.id),
        }
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json=payload,
            headers=auth_headers_user_2
        )
        
        assert response.status_code == 201
    
    async def test_viewer_cannot_create_task(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test non-member cannot create tasks."""
        payload = {
            "title": "Unauthorized Task",
            "description": "Should not be created",
            "board_id": str(test_board.id),
        }
        
        response = await client.post(
            f"{api_base_url}/tasks",
            json=payload,
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_member_cannot_delete_board(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        board_with_member: Board,
        api_base_url: str
    ):
        """Test board member cannot delete board."""
        response = await client.delete(
            f"{api_base_url}/boards/{board_with_member.id}",
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.boards
class TestBoardSearch:
    """E2E tests for board search functionality."""
    
    async def test_search_boards_by_name(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_board: Board,
        api_base_url: str
    ):
        """Test searching boards by name."""
        response = await client.get(
            f"{api_base_url}/boards/search",
            params={"q": test_board.name[:5]},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(board["id"] == str(test_board.id) for board in data)
    
    async def test_search_public_boards_without_auth(
        self, 
        client: AsyncClient, 
        test_board: Board,
        api_base_url: str
    ):
        """Test searching public boards without authentication."""
        response = await client.get(
            f"{api_base_url}/boards/search",
            params={"q": test_board.name[:5]}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should only include public boards
        for board in data:
            assert board["is_public"] is True