import sys
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
import app.models  # Ensure all models are registered in Base.metadata
from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import Role, RoleEnum, User

# In-memory async SQLite engine for isolated test execution
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_async_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh database schema for each test function and seed standard roles and test accounts."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        # Seed standard roles
        roles = {}
        for r in RoleEnum:
            role = Role(name=r.value, description=f"{r.value} Role")
            session.add(role)
            roles[r.value] = role
        await session.flush()

        # Seed standard test users
        users = [
            ("admin@metacheck.gov.in", "Administrator", RoleEnum.ADMIN.value, "Admin@123"),
            ("officer@metacheck.gov.in", "Enforcement Officer Verma", RoleEnum.ENFORCEMENT_OFFICER.value, "Officer@123"),
            ("viewer@metacheck.gov.in", "Compliance Auditor", RoleEnum.VIEWER.value, "Viewer@123"),
        ]
        for email, name, role_name, raw_pwd in users:
            u = User(
                email=email,
                name=name,
                password_hash=hash_password(raw_pwd),
                role_id=roles[role_name].id,
                is_active=True,
            )
            session.add(u)
        await session.commit()

        yield session

    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def unauthenticated_client(db_session: AsyncSession):
    """Raw unauthenticated Async HTTP client fixture."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession):
    """
    Standard test Async HTTP client with valid Admin JWT header.
    Tests can override headers per-request to test unauthenticated / custom roles.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Find admin user for test token
    res = await db_session.execute(select(User).where(User.email == "admin@metacheck.gov.in"))
    admin_user = res.scalar_one()

    token = create_access_token(
        subject=admin_user.id,
        claims={"email": admin_user.email, "role": RoleEnum.ADMIN.value, "name": admin_user.name},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def officer_token(db_session: AsyncSession) -> str:
    res = await db_session.execute(select(User).where(User.email == "officer@metacheck.gov.in"))
    officer_user = res.scalar_one()
    return create_access_token(
        subject=officer_user.id,
        claims={"email": officer_user.email, "role": RoleEnum.ENFORCEMENT_OFFICER.value, "name": officer_user.name},
    )


@pytest_asyncio.fixture(scope="function")
async def admin_token(db_session: AsyncSession) -> str:
    res = await db_session.execute(select(User).where(User.email == "admin@metacheck.gov.in"))
    admin_user = res.scalar_one()
    return create_access_token(
        subject=admin_user.id,
        claims={"email": admin_user.email, "role": RoleEnum.ADMIN.value, "name": admin_user.name},
    )


@pytest_asyncio.fixture(scope="function")
async def viewer_token(db_session: AsyncSession) -> str:
    res = await db_session.execute(select(User).where(User.email == "viewer@metacheck.gov.in"))
    viewer_user = res.scalar_one()
    return create_access_token(
        subject=viewer_user.id,
        claims={"email": viewer_user.email, "role": RoleEnum.VIEWER.value, "name": viewer_user.name},
    )
