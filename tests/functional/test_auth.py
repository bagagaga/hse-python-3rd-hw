from unittest.mock import MagicMock, AsyncMock
import uuid
from fastapi import HTTPException, status
from src.auth.users import current_active_user


def test_register_new_user(client, monkeypatch):
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.email = "newuser@example.com"
    mock_user.is_active = True
    mock_user.is_verified = True
    mock_user.is_superuser = False

    async def mock_create(*args, **kwargs):
        return mock_user

    from src.auth.users import UserManager
    monkeypatch.setattr(UserManager, "create", AsyncMock(side_effect=mock_create))

    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "strongpassword123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data


def test_register_duplicate_user(client, monkeypatch):
    async def mock_create_duplicate(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    from src.auth.users import UserManager
    monkeypatch.setattr(UserManager, "create", AsyncMock(side_effect=mock_create_duplicate))

    response = client.post(
        "/auth/register",
        json={
            "email": "existing@example.com",
            "password": "strongpassword123"
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json().get("detail", "").lower()


def test_login_success(client, monkeypatch):
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.email = "test@example.com"

    async def mock_authenticate(*args, **kwargs):
        return mock_user

    from src.auth.users import UserManager
    monkeypatch.setattr(UserManager, "authenticate", AsyncMock(side_effect=mock_authenticate))

    mock_jwt = MagicMock()
    mock_jwt.write_token.return_value = "dummy_token"

    monkeypatch.setattr("src.auth.users.get_jwt_strategy", lambda: mock_jwt)

    response = client.post(
        "/auth/jwt/login",
        data={
            "username": "test@example.com",
            "password": "password"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, monkeypatch):
    async def mock_authenticate_fail(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"
        )

    from src.auth.users import UserManager
    monkeypatch.setattr(UserManager, "authenticate", AsyncMock(side_effect=mock_authenticate_fail))

    response = client.post(
        "/auth/jwt/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 400
    assert "invalid credentials" in response.json().get("detail", "").lower()


def test_protected_route(client, mock_test_user):
    app = client.app
    app.dependency_overrides[current_active_user] = lambda: mock_test_user

    response = client.get("/protected-route")
    assert response.status_code == 200
    assert f"Hello, {mock_test_user.email}" in response.text

    app.dependency_overrides.pop(current_active_user)


def test_unprotected_route(client):
    response = client.get("/unprotected-route")
    assert response.status_code == 200
    assert "Hello, anonym" in response.text
