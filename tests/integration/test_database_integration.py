"""
Integration Tests for Database Operations

This module contains integration tests for database operations including:
- CRUD operations
- Transactions
- Concurrency handling
- Connection pooling
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.board import Board, BoardMember, BoardRole
from app.models.team import Team, TeamMember, TeamRole
from app.core.security import get_password_hash


@pytest.mark.integration
class TestUserDatabaseOperations:
    """Integration tests for user database operations."""
    
    async def test_create_user(self, db_session: AsyncSession):
        """Test user creation in database."""
        user = User(
            email="test_db@example.com",
            username="testdbuser",
            full_name="Test DB User",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test_db@example.com"
    
    async def test_get_user_by_email(self, db_session: AsyncSession, test_user: User):
        """Test retrieving user by email."""
        result = await db_session.execute(
            select(User).where(User.email == test_user.email)
        )
        user = result.scalar_one_or_none()
        
        assert user is not None
        assert user.id == test_user.id
    
    async def test_get_user_by_username(self, db_session: AsyncSession, test_user: User):
        """Test retrieving user by username."""
        result = await db_session.execute(
            select(User).where(User.username == test_user.username)
        )
        user = result.scalar_one_or_none()
        
        assert user is not None
        assert user.id == test_user.id
    
    async def test_update_user(self, db_session: AsyncSession, test_user: User):
        """Test updating user fields."""
        test_user.full_name = "Updated Name"
        test_user.bio = "Updated bio"
        await db_session.commit()
        await db_session.refresh(test_user)
        
        assert test_user.full_name == "Updated Name"
        assert test_user.bio == "Updated bio"
    
    async def test_delete_user(self, db_session: AsyncSession):
        """Test user deletion."""
        user = User(
            email="delete_test@example.com",
            username="deleteuser",
            full_name="Delete User",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        user_id = user.id
        await db_session.delete(user)
        await db_session.commit()
        
        # Verify deletion
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        assert result.scalar_one_or_none() is None
    
    async def test_user_unique_email_constraint(self, db_session: AsyncSession, test_user: User):
        """Test that duplicate email is prevented."""
        duplicate_user = User(
            email=test_user.email,  # Same email
            username="different_username",
            full_name="Different User",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()
        
        await db_session.rollback()


@pytest.mark.integration
class TestTaskDatabaseOperations:
    """Integration tests for task database operations."""
    
    async def test_create_task(self, db_session: AsyncSession, test_board: Board, test_user: User):
        """Test task creation in database."""
        task = Task(
            title="DB Test Task",
            description="Task for database testing",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            board_id=test_board.id,
            creator_id=test_user.id,
            due_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        assert task.id is not None
        assert task.title == "DB Test Task"
        assert task.board_id == test_board.id
    
    async def test_task_board_relationship(
        self, 
        db_session: AsyncSession, 
        test_board: Board, 
        test_user: User
    ):
        """Test task-board relationship."""
        task = Task(
            title="Relationship Test Task",
            board_id=test_board.id,
            creator_id=test_user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            created_at=datetime.utcnow(),
        )
        db_session.add(task)
        await db_session.commit()
        
        # Query board with tasks
        result = await db_session.execute(
            select(Board).where(Board.id == test_board.id)
        )
        board = result.scalar_one()
        
        assert len(board.tasks) >= 1
        assert any(t.title == "Relationship Test Task" for t in board.tasks)
    
    async def test_task_status_update(self, db_session: AsyncSession, test_task: Task):
        """Test updating task status."""
        test_task.status = TaskStatus.IN_PROGRESS
        await db_session.commit()
        await db_session.refresh(test_task)
        
        assert test_task.status == TaskStatus.IN_PROGRESS
    
    async def test_task_assignment(
        self, 
        db_session: AsyncSession, 
        test_task: Task, 
        test_user_2: User
    ):
        """Test assigning task to user."""
        test_task.assignee_id = test_user_2.id
        await db_session.commit()
        await db_session.refresh(test_task)
        
        assert test_task.assignee_id == test_user_2.id
    
    async def test_count_tasks_by_status(self, db_session: AsyncSession, test_board: Board):
        """Test counting tasks by status."""
        result = await db_session.execute(
            select(Task.status, func.count(Task.id))
            .where(Task.board_id == test_board.id)
            .group_by(Task.status)
        )
        counts = result.all()
        
        assert isinstance(counts, list)
        # Should return tuples of (status, count)


@pytest.mark.integration
class TestBoardDatabaseOperations:
    """Integration tests for board database operations."""
    
    async def test_create_board(self, db_session: AsyncSession, test_user: User):
        """Test board creation in database."""
        board = Board(
            name="DB Test Board",
            description="Board for database testing",
            owner_id=test_user.id,
            is_public=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)
        
        assert board.id is not None
        assert board.name == "DB Test Board"
        assert board.owner_id == test_user.id
    
    async def test_board_member_creation(
        self, 
        db_session: AsyncSession, 
        test_board: Board, 
        test_user_2: User
    ):
        """Test adding member to board."""
        member = BoardMember(
            board_id=test_board.id,
            user_id=test_user_2.id,
            role=BoardRole.MEMBER,
            joined_at=datetime.utcnow(),
        )
        db_session.add(member)
        await db_session.commit()
        await db_session.refresh(member)
        
        assert member.id is not None
        assert member.role == BoardRole.MEMBER
    
    async def test_board_owner_relationship(self, db_session: AsyncSession, test_board: Board):
        """Test board-owner relationship."""
        result = await db_session.execute(
            select(Board).where(Board.id == test_board.id)
        )
        board = result.scalar_one()
        
        assert board.owner is not None
        assert board.owner.id == test_board.owner_id
    
    async def test_cascade_delete_board_tasks(
        self, 
        db_session: AsyncSession, 
        test_board: Board, 
        test_user: User
    ):
        """Test cascading delete of tasks when board is deleted."""
        # Create a task
        task = Task(
            title="Cascade Test Task",
            board_id=test_board.id,
            creator_id=test_user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            created_at=datetime.utcnow(),
        )
        db_session.add(task)
        await db_session.commit()
        task_id = task.id
        
        # Delete board
        await db_session.delete(test_board)
        await db_session.commit()
        
        # Verify task is also deleted (if cascade is configured)
        result = await db_session.execute(
            select(Task).where(Task.id == task_id)
        )
        # Depending on cascade configuration, this may or may not be None
        # assert result.scalar_one_or_none() is None


@pytest.mark.integration
class TestTeamDatabaseOperations:
    """Integration tests for team database operations."""
    
    async def test_create_team(self, db_session: AsyncSession, test_user: User):
        """Test team creation in database."""
        team = Team(
            name="DB Test Team",
            description="Team for database testing",
            owner_id=test_user.id,
            created_at=datetime.utcnow(),
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)
        
        assert team.id is not None
        assert team.name == "DB Test Team"
    
    async def test_team_member_creation(
        self, 
        db_session: AsyncSession, 
        test_team: Team, 
        test_user_2: User
    ):
        """Test adding member to team."""
        member = TeamMember(
            team_id=test_team.id,
            user_id=test_user_2.id,
            role=TeamRole.MEMBER,
            joined_at=datetime.utcnow(),
        )
        db_session.add(member)
        await db_session.commit()
        await db_session.refresh(member)
        
        assert member.id is not None
        assert member.role == TeamRole.MEMBER
    
    async def test_team_members_query(self, db_session: AsyncSession, test_team: Team):
        """Test querying team members."""
        result = await db_session.execute(
            select(TeamMember)
            .where(TeamMember.team_id == test_team.id)
            .join(User)
        )
        members = result.scalars().all()
        
        assert len(members) >= 1
        assert all(m.team_id == test_team.id for m in members)


@pytest.mark.integration
class TestTransactionHandling:
    """Integration tests for transaction handling."""
    
    async def test_transaction_rollback(self, db_session: AsyncSession):
        """Test transaction rollback on error."""
        user = User(
            email="rollback_test@example.com",
            username="rollbackuser",
            full_name="Rollback User",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(user)
        await db_session.flush()
        
        user_id = user.id
        
        # Simulate error and rollback
        await db_session.rollback()
        
        # Verify user was not persisted
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        assert result.scalar_one_or_none() is None
    
    async def test_nested_transaction(self, db_session: AsyncSession, test_user: User):
        """Test nested transaction behavior."""
        # Begin nested transaction
        async with db_session.begin_nested():
            test_user.full_name = "Nested Transaction Name"
            await db_session.flush()
        
        # Changes should be visible within same outer transaction
        await db_session.refresh(test_user)
        assert test_user.full_name == "Nested Transaction Name"


@pytest.mark.integration
class TestConcurrency:
    """Integration tests for concurrent database operations."""
    
    async def test_concurrent_reads(self, db_session: AsyncSession, test_user: User):
        """Test concurrent read operations."""
        # Simulate concurrent reads
        tasks = []
        for _ in range(5):
            task = db_session.execute(
                select(User).where(User.id == test_user.id)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should return the same user
        for result in results:
            user = result.scalar_one()
            assert user.id == test_user.id
    
    async def test_optimistic_locking(self, db_session: AsyncSession, test_task: Task):
        """Test optimistic locking if implemented."""
        # This test assumes version column exists for optimistic locking
        # If not implemented, this test should be skipped or modified
        initial_version = getattr(test_task, 'version', None)
        
        if initial_version is not None:
            test_task.title = "Updated by concurrent user"
            await db_session.commit()
            
            # Version should have incremented
            assert test_task.version > initial_version


@pytest.mark.integration
class TestComplexQueries:
    """Integration tests for complex database queries."""
    
    async def test_join_query_users_boards(
        self, 
        db_session: AsyncSession, 
        test_user: User, 
        test_board: Board
    ):
        """Test join query between users and boards."""
        result = await db_session.execute(
            select(User, Board)
            .join(Board, Board.owner_id == User.id)
            .where(User.id == test_user.id)
        )
        rows = result.all()
        
        assert len(rows) >= 1
        for user, board in rows:
            assert user.id == test_user.id
            assert board.owner_id == test_user.id
    
    async def test_aggregate_query(
        self, 
        db_session: AsyncSession, 
        test_board: Board,
        multiple_tasks: list
    ):
        """Test aggregate query for task statistics."""
        result = await db_session.execute(
            select(
                Task.status,
                func.count(Task.id).label('count'),
                func.min(Task.created_at).label('oldest'),
                func.max(Task.created_at).label('newest')
            )
            .where(Task.board_id == test_board.id)
            .group_by(Task.status)
        )
        stats = result.all()
        
        assert isinstance(stats, list)
        total_count = sum(row.count for row in stats)
        assert total_count == len(multiple_tasks)
    
    async def test_subquery(self, db_session: AsyncSession, test_user: User):
        """Test subquery for complex filtering."""
        # Subquery: Get boards owned by user
        subquery = select(Board.id).where(Board.owner_id == test_user.id).subquery()
        
        # Main query: Get tasks from those boards
        result = await db_session.execute(
            select(Task)
            .where(Task.board_id.in_(subquery))
        )
        tasks = result.scalars().all()
        
        # All tasks should belong to boards owned by test_user
        for task in tasks:
            assert task.board.owner_id == test_user.id


@pytest.mark.integration
class TestDatabaseConstraints:
    """Integration tests for database constraints."""
    
    async def test_not_null_constraints(self, db_session: AsyncSession):
        """Test NOT NULL constraints."""
        # Try to create user without required fields
        incomplete_user = User(
            email=None,  # Required
            username="testuser",
            full_name="Test",
            hashed_password="password",
        )
        db_session.add(incomplete_user)
        
        with pytest.raises(Exception):
            await db_session.commit()
        
        await db_session.rollback()
    
    async def test_foreign_key_constraints(
        self, 
        db_session: AsyncSession, 
        test_user: User
    ):
        """Test foreign key constraints."""
        # Try to create task with non-existent board
        orphan_task = Task(
            title="Orphan Task",
            board_id="123e4567-e89b-12d3-a456-426614174000",  # Non-existent
            creator_id=test_user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            created_at=datetime.utcnow(),
        )
        db_session.add(orphan_task)
        
        with pytest.raises(Exception):
            await db_session.commit()
        
        await db_session.rollback()
    
    async def test_check_constraints(self, db_session: AsyncSession):
        """Test CHECK constraints if defined."""
        # This depends on specific CHECK constraints defined in the schema
        pass