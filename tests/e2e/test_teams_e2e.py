"""
End-to-End Tests for Team Management

This module contains comprehensive E2E tests for team operations including:
- Team CRUD operations
- Team membership and roles
- Team-board associations
- Team permissions
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team, TeamMember, TeamRole
from app.models.board import Board
from app.models.user import User


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamCreation:
    """E2E tests for team creation."""
    
    async def test_create_team_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team_data: dict,
        api_base_url: str
    ):
        """Test successful team creation."""
        response = await client.post(
            f"{api_base_url}/teams",
            json=test_team_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == test_team_data["name"]
        assert data["description"] == test_team_data["description"]
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data
    
    async def test_create_team_without_auth(
        self, 
        client: AsyncClient, 
        test_team_data: dict,
        api_base_url: str
    ):
        """Test team creation without authentication fails."""
        response = await client.post(
            f"{api_base_url}/teams",
            json=test_team_data
        )
        
        assert response.status_code == 401
    
    async def test_create_team_missing_name(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        api_base_url: str
    ):
        """Test team creation without name fails."""
        payload = {
            "description": "Team without name",
        }
        
        response = await client.post(
            f"{api_base_url}/teams",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamRetrieval:
    """E2E tests for team retrieval."""
    
    async def test_get_team_by_id(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test retrieving a specific team."""
        response = await client.get(
            f"{api_base_url}/teams/{test_team.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_team.id)
        assert data["name"] == test_team.name
    
    async def test_get_team_by_non_member(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test team retrieval by non-member."""
        response = await client.get(
            f"{api_base_url}/teams/{test_team.id}",
            headers=auth_headers_user_2
        )
        
        # May allow or restrict based on implementation
        assert response.status_code in [200, 403, 404]
    
    async def test_list_user_teams(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test listing teams for current user."""
        response = await client.get(
            f"{api_base_url}/teams",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(team["id"] == str(test_team.id) for team in data)


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamUpdate:
    """E2E tests for team updates."""
    
    async def test_update_team_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test successful team update."""
        update_data = {
            "name": "Updated Team Name",
            "description": "Updated description",
        }
        
        response = await client.patch(
            f"{api_base_url}/teams/{test_team.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    async def test_update_team_by_non_owner(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test team update by non-owner fails."""
        update_data = {"name": "Hacked Team Name"}
        
        response = await client.patch(
            f"{api_base_url}/teams/{test_team.id}",
            json=update_data,
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamDeletion:
    """E2E tests for team deletion."""
    
    async def test_delete_team_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test successful team deletion."""
        response = await client.delete(
            f"{api_base_url}/teams/{test_team.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify team is deleted
        get_response = await client.get(
            f"{api_base_url}/teams/{test_team.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    async def test_delete_team_by_non_owner(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test team deletion by non-owner fails."""
        response = await client.delete(
            f"{api_base_url}/teams/{test_team.id}",
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamMembership:
    """E2E tests for team membership management."""
    
    async def test_invite_member_to_team(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        test_user_2: User,
        api_base_url: str
    ):
        """Test inviting a member to a team."""
        response = await client.post(
            f"{api_base_url}/teams/{test_team.id}/invite",
            json={
                "user_id": str(test_user_2.id),
                "role": TeamRole.MEMBER.value,
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(test_user_2.id)
        assert data["role"] == TeamRole.MEMBER.value
    
    async def test_invite_member_by_non_admin(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test inviting member by non-admin fails."""
        response = await client.post(
            f"{api_base_url}/teams/{test_team.id}/invite",
            json={
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "role": TeamRole.MEMBER.value,
            },
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_list_team_members(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test listing team members."""
        response = await client.get(
            f"{api_base_url}/teams/{test_team.id}/members",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    async def test_update_member_role(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        test_user_2: User,
        api_base_url: str
    ):
        """Test updating a member's role."""
        # First invite member
        await client.post(
            f"{api_base_url}/teams/{test_team.id}/invite",
            json={
                "user_id": str(test_user_2.id),
                "role": TeamRole.MEMBER.value,
            },
            headers=auth_headers
        )
        
        # Update role
        response = await client.patch(
            f"{api_base_url}/teams/{test_team.id}/members/{test_user_2.id}",
            json={"role": TeamRole.ADMIN.value},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["role"] == TeamRole.ADMIN.value
    
    async def test_remove_member_from_team(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        test_user_2: User,
        api_base_url: str
    ):
        """Test removing a member from a team."""
        # First invite member
        await client.post(
            f"{api_base_url}/teams/{test_team.id}/invite",
            json={
                "user_id": str(test_user_2.id),
                "role": TeamRole.MEMBER.value,
            },
            headers=auth_headers
        )
        
        # Remove member
        response = await client.delete(
            f"{api_base_url}/teams/{test_team.id}/members/{test_user_2.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    async def test_leave_team(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        team_with_members: Team,
        test_user_2: User,
        api_base_url: str
    ):
        """Test member leaving a team."""
        response = await client.post(
            f"{api_base_url}/teams/{team_with_members.id}/leave",
            headers=auth_headers_user_2
        )
        
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamBoards:
    """E2E tests for team-board associations."""
    
    async def test_add_board_to_team(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        test_board: Board,
        api_base_url: str
    ):
        """Test adding a board to a team."""
        response = await client.post(
            f"{api_base_url}/teams/{test_team.id}/boards",
            json={"board_id": str(test_board.id)},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
    
    async def test_list_team_boards(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test listing boards associated with a team."""
        response = await client.get(
            f"{api_base_url}/teams/{test_team.id}/boards",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_remove_board_from_team(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        test_board: Board,
        api_base_url: str
    ):
        """Test removing a board from a team."""
        # First add board
        await client.post(
            f"{api_base_url}/teams/{test_team.id}/boards",
            json={"board_id": str(test_board.id)},
            headers=auth_headers
        )
        
        # Remove board
        response = await client.delete(
            f"{api_base_url}/teams/{test_team.id}/boards/{test_board.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamPermissions:
    """E2E tests for team permission enforcement."""
    
    async def test_admin_can_invite_members(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        test_user_2: User,
        api_base_url: str
    ):
        """Test team admin can invite members."""
        response = await client.post(
            f"{api_base_url}/teams/{test_team.id}/invite",
            json={
                "user_id": str(test_user_2.id),
                "role": TeamRole.MEMBER.value,
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
    
    async def test_member_cannot_invite_members(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        team_with_members: Team,
        api_base_url: str
    ):
        """Test regular member cannot invite members."""
        response = await client.post(
            f"{api_base_url}/teams/{team_with_members.id}/invite",
            json={
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "role": TeamRole.MEMBER.value,
            },
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]
    
    async def test_member_cannot_delete_team(
        self, 
        client: AsyncClient, 
        auth_headers_user_2: dict,
        team_with_members: Team,
        api_base_url: str
    ):
        """Test team member cannot delete team."""
        response = await client.delete(
            f"{api_base_url}/teams/{team_with_members.id}",
            headers=auth_headers_user_2
        )
        
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.teams
class TestTeamSearch:
    """E2E tests for team search functionality."""
    
    async def test_search_teams(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_team: Team,
        api_base_url: str
    ):
        """Test searching teams."""
        response = await client.get(
            f"{api_base_url}/teams/search",
            params={"q": test_team.name[:5]},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(team["id"] == str(test_team.id) for team in data)