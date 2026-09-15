from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.core.database import get_session
from app.core.security.auth import AuthUser, get_current_user
from app.main import app
from app.shared.infrastructure.db import models  # noqa: F401


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@pytest.fixture(name="usuario_autenticado")
def usuario_autenticado_fixture() -> AuthUser:
    return AuthUser(user_id="usuario-propietario-1", email="propietario@drawi.com")


@pytest.fixture(name="usuario_secundario")
def usuario_secundario_fixture() -> AuthUser:
    return AuthUser(user_id="usuario-ajeno-2", email="ajeno@drawi.com")


@pytest.fixture(name="client")
def client_fixture(
    session: Session, usuario_autenticado: AuthUser
) -> Generator[TestClient, None, None]:
    def _override_get_session():
        yield session

    def _override_get_current_user():
        return usuario_autenticado

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(name="unauthenticated_client")
def unauthenticated_client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
