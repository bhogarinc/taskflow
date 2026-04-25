"""
Pytest configuration and fixtures for TaskFlow E2E and integration tests.

This module provides comprehensive fixtures for testing the TaskFlow API,
including database setup, authentication, and test data generation.
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Generator, List, Optional

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5433/taskflow_test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-do-not-use-in-production"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

from app.main import app
from app.core.config import settings
from app.db.base import Base, get_db
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.board import Board, BoardMember, BoardRole
from app.models.team import Team, TeamMember, TeamRole
from app.core.security import create_access_token, get_password_hash

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5433/taskflow_test"
SYNC_TEST_DATABASE_URL = "postgresql://test:test@localhost:5433/taskflow_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    async with async_session() as session:
        # Begin nested transaction
        await session.begin_nested()
        
        yield session
        
        # Rollback after test
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ==================== Test Data Fixtures ====================

@pytest.fixture
def test_user_data() -> Dict:
    """Return test user data."""
    return {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "full_name": "Test User",
        "password": "TestPassword123!",
    }


@pytest.fixture
def test_user_data_2() -> Dict:
    """Return second test user data."""
    return {
        "email": f"test2_{uuid.uuid4().hex[:8]}@example.com",
        "username": f"testuser2_{uuid.uuid4().hex[:8]}",
        "full_name": "Test User 2",
        "password": "TestPassword456!",
    }


@pytest.fixture
def test_board_data() -> Dict:
    """Return test board data."""
    return {
        "name": f"Test Board {uuid.uuid4().hex[:8]}",
        "description": "A test board for integration testing",
        "is_public": True,
    }


@pytest.fixture
def test_task_data() -> Dict:
    """Return test task data."""
    return {
        "title": f"Test Task {uuid.uuid4().hex[:8]}",
        "description": "A test task for integration testing",
        "status": TaskStatus.TODO.value,
        "priority": TaskPriority.MEDIUM.value,
        "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
    }


@pytest.fixture
def test_team_data() -> Dict:
    """Return test team data."""
    return {
        "name": f"Test Team {uuid.uuid4().hex[:8]}",
        "description": "A test team for integration testing",
    }


# ==================== User Fixtures ====================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_user_data: Dict) -> User:
    """Create a test user in the database."""
    user = User(
        email=test_user_data["email"],
        username=test_user_data["username"],
        full_name=test_user_data["full_name"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession, test_user_data_2: Dict) -> User:
    """Create a second test user in the database."""
    user = User(
        email=test_user_data_2["email"],
        username=test_user_data_2["username"],
        full_name=test_user_data_2["full_name"],
        hashed_password=get_password_hash(test_user_data_2["password"]),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    """Create an inactive test user."""
    user = User(
        email=f"inactive_{uuid.uuid4().hex[:8]}@example.com",
        username=f"inactive_{uuid.uuid4().hex[:8]}",
        full_name="Inactive User",
        hashed_password=get_password_hash("TestPassword123!"),
        is_active=False,
        is_verified=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user(db_session: AsyncSession) -> User:
    """Create an unverified test user."""
    user = User(
        email=f"unverified_{uuid.uuid4().hex[:8]}@example.com",
        username=f"unverified_{uuid.uuid4().hex[:8]}",
        full_name="Unverified User",
        hashed_password=get_password_hash("TestPassword123!"),
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ==================== Authentication Fixtures ====================

@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Generate authentication headers for test user."""
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def auth_headers_user_2(test_user_2: User) -> Dict[str, str]:
    """Generate authentication headers for second test user."""
    access_token = create_access_token(data={"sub": str(test_user_2.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, auth_headers: Dict[str, str]) -> AsyncClient:
    """Return authenticated client with headers set."""
    client.headers.update(auth_headers)
    return client


# ==================== Board Fixtures ====================

@pytest_asyncio.fixture
async def test_board(db_session: AsyncSession, test_user: User, test_board_data: Dict) -> Board:
    """Create a test board owned by test user."""
    board = Board(
        name=test_board_data["name"],
        description=test_board_data["description"],
        owner_id=test_user.id,
        is_public=test_board_data["is_public"],
        created_at=datetime.utcnow(),
    )
    db_session.add(board)
    await db_session.commit()
    await db_session.refresh(board)
    
    # Add owner as admin member
    member = BoardMember(
        board_id=board.id,
        user_id=test_user.id,
        role=BoardRole.ADMIN,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    await db_session.commit()
    
    return board


@pytest_asyncio.fixture
async def private_board(db_session: AsyncSession, test_user: User) -> Board:
    """Create a private test board."""
    board = Board(
        name=f"Private Board {uuid.uuid4().hex[:8]}",
        description="A private test board",
        owner_id=test_user.id,
        is_public=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(board)
    await db_session.commit()
    await db_session.refresh(board)
    
    member = BoardMember(
        board_id=board.id,
        user_id=test_user.id,
        role=BoardRole.ADMIN,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    await db_session.commit()
    
    return board


@pytest_asyncio.fixture
async def board_with_member(db_session: AsyncSession, test_board: Board, test_user_2: User) -> Board:
    """Create a board with test_user_2 as a member."""
    member = BoardMember(
        board_id=test_board.id,
        user_id=test_user_2.id,
        role=BoardRole.MEMBER,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    await db_session.commit()
    return test_board


# ==================== Task Fixtures ====================

@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_board: Board, test_user: User, test_task_data: Dict) -> Task:
    """Create a test task on a board."""
    task = Task(
        title=test_task_data["title"],
        description=test_task_data["description"],
        status=TaskStatus(test_task_data["status"]),
        priority=TaskPriority(test_task_data["priority"]),
        board_id=test_board.id,
        creator_id=test_user.id,
        due_date=datetime.fromisoformat(test_task_data["due_date"]),
        created_at=datetime.utcnow(),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def multiple_tasks(db_session: AsyncSession, test_board: Board, test_user: User) -> List[Task]:
    """Create multiple test tasks with different statuses and priorities."""
    tasks = []
    statuses = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE]
    priorities = [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, TaskPriority.URGENT]
    
    for i in range(10):
        task = Task(
            title=f"Task {i+1} {uuid.uuid4().hex[:6]}",
            description=f"Description for task {i+1}",
            status=statuses[i % 3],
            priority=priorities[i % 4],
            board_id=test_board.id,
            creator_id=test_user.id,
            assignee_id=test_user.id if i % 2 == 0 else None,
            due_date=datetime.utcnow() + timedelta(days=i+1),
            created_at=datetime.utcnow(),
        )
        db_session.add(task)
        tasks.append(task)
    
    await db_session.commit()
    for task in tasks:
        await db_session.refresh(task)
    
    return tasks


# ==================== Team Fixtures ====================

@pytest_asyncio.fixture
async def test_team(db_session: AsyncSession, test_user: User, test_team_data: Dict) -> Team:
    """Create a test team with test_user as owner."""
    team = Team(
        name=test_team_data["name"],
        description=test_team_data["description"],
        owner_id=test_user.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    
    # Add owner as admin member
    member = TeamMember(
        team_id=team.id,
        user_id=test_user.id,
        role=TeamRole.ADMIN,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    await db_session.commit()
    
    return team


@pytest_asyncio.fixture
async def team_with_members(db_session: AsyncSession, test_team: Team, test_user_2: User) -> Team:
    """Create a team with multiple members."""
    member = TeamMember(
        team_id=test_team.id,
        user_id=test_user_2.id,
        role=TeamRole.MEMBER,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    await db_session.commit()
    return test_team


# ==================== Utility Fixtures ====================

@pytest.fixture
def api_base_url() -> str:
    """Return base API URL."""
    return "/api/v1"


@pytest.fixture
def datetime_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


@pytest.fixture
def future_date() -> datetime:
    """Return a future date for testing."""
    return datetime.utcnow() + timedelta(days=30)


@pytest.fixture
def past_date() -> datetime:
    """Return a past date for testing."""
    return datetime.utcnow() - timedelta(days=30)


# ==================== Performance Test Fixtures ====================

@pytest.fixture
def load_test_config() -> Dict:
    """Configuration for load testing."""
    return {
        "num_users": 100,
        "spawn_rate": 10,
        "run_time": "5m",
        "host": "http://localhost:8000",
    }


@pytest_asyncio.fixture
async def bulk_users(db_session: AsyncSession, request) -> List[User]:
    """Create multiple users for load testing."""
    count = getattr(request, "param", 50)
    users = []
    
    for i in range(count):
        user = User(
            email=f"bulk_{uuid.uuid4().hex[:8]}_{i}@example.com",
            username=f"bulkuser_{uuid.uuid4().hex[:8]}_{i}",
            full_name=f"Bulk User {i}",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(user)
        users.append(user)
    
    await db_session.commit()
    for user in users:
        await db_session.refresh(user)
    
    return users


# ==================== Cleanup Fixtures ====================

@pytest.fixture(autouse=True)
async def cleanup_db(db_session: AsyncSession):
    """Automatically cleanup database after each test."""
    yield
    # Cleanup is handled by transaction rollback in db_session fixture
    pass