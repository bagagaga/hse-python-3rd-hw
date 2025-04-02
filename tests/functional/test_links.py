from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
import uuid
from src.auth.users import current_active_user, current_optional_user


def test_create_short_link_anonymous(client, mock_async_session):
    app = client.app
    app.dependency_overrides[current_optional_user] = lambda: None

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_async_session.execute.return_value = mock_result

    link_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    mock_link = MagicMock()
    mock_link.id = link_id
    mock_link.short_code = "abcdef"
    mock_link.original_url = "https://example.com/long-url"
    mock_link.created_at = now
    mock_link.last_used_at = now
    mock_link.expires_at = now + timedelta(days=10)
    mock_link.visit_count = 0

    async def mock_refresh(link, *args, **kwargs):
        for attr in ['id', 'short_code', 'original_url', 'created_at',
                     'last_used_at', 'expires_at', 'visit_count']:
            setattr(link, attr, getattr(mock_link, attr))

    mock_async_session.refresh.side_effect = mock_refresh

    with patch('src.links.router.generate_short_code', return_value="abcdef"):
        response = client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/long-url"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == "https://example.com/long-url"
        assert data["short_code"] == "abcdef"

    app.dependency_overrides.pop(current_optional_user)


def test_create_short_link_with_custom_alias(client, mock_async_session, mock_test_user):
    app = client.app
    app.dependency_overrides[current_optional_user] = lambda: mock_test_user

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_async_session.execute.return_value = mock_result

    link_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    mock_link = MagicMock()
    mock_link.id = link_id
    mock_link.short_code = "mycustom"
    mock_link.original_url = "https://example.com/custom-path"
    mock_link.created_at = now
    mock_link.last_used_at = now
    mock_link.expires_at = now + timedelta(days=10)
    mock_link.visit_count = 0
    mock_link.user_id = mock_test_user.id

    async def mock_refresh(link, *args, **kwargs):
        for attr in ['id', 'short_code', 'original_url', 'created_at',
                     'last_used_at', 'expires_at', 'visit_count', 'user_id']:
            setattr(link, attr, getattr(mock_link, attr))

    mock_async_session.refresh.side_effect = mock_refresh

    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/custom-path",
            "custom_alias": "mycustom"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://example.com/custom-path"
    assert data["short_code"] == "mycustom"

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_link]
    mock_async_session.execute.return_value = mock_result

    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/another-path",
            "custom_alias": "mycustom"
        }
    )
    assert response.status_code == 400
    assert "already in use" in response.json().get("detail", "").lower()

    app.dependency_overrides.pop(current_optional_user)


def test_redirect_to_original(client, mock_async_session, mock_test_link):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_test_link
    mock_async_session.execute.return_value = mock_result

    with patch("src.links.router.increment_visit_count") as mock_increment:
        mock_increment.apply_async = MagicMock()

        response = client.get(f"/links/{mock_test_link.short_code}", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == mock_test_link.original_url

        mock_increment.apply_async.assert_called_once_with(args=[mock_test_link.id])


def test_redirect_with_expired_link(client, mock_async_session, mock_test_link):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_async_session.execute.return_value = mock_result

    response = client.get(f"/links/{mock_test_link.short_code}")
    assert response.status_code == 404
    assert "not found" in response.json().get("detail", "").lower()


def test_get_link_stats(client, mock_async_session, mock_test_user, mock_test_link):
    app = client.app
    app.dependency_overrides[current_active_user] = lambda: mock_test_user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_test_link
    mock_async_session.execute.return_value = mock_result

    with patch("fastapi_cache.decorator.cache", lambda *args, **kwargs: lambda f: f):
        response = client.get(f"/links/{mock_test_link.short_code}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(mock_test_link.id)
        assert data["short_code"] == mock_test_link.short_code
        assert data["original_url"] == mock_test_link.original_url
        assert data["visit_count"] == mock_test_link.visit_count

    app.dependency_overrides.pop(current_active_user)


def test_update_link(client, mock_async_session, mock_test_user, mock_test_link):
    app = client.app
    app.dependency_overrides[current_active_user] = lambda: mock_test_user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_test_link
    mock_async_session.execute.return_value = mock_result

    updated_link = MagicMock()
    updated_link.id = mock_test_link.id
    updated_link.short_code = mock_test_link.short_code
    updated_link.original_url = "https://example.com/updated-url"
    updated_link.created_at = mock_test_link.created_at
    updated_link.last_used_at = mock_test_link.last_used_at
    updated_link.expires_at = mock_test_link.expires_at
    updated_link.visit_count = mock_test_link.visit_count

    async def mock_refresh(link, *args, **kwargs):
        link.original_url = "https://example.com/updated-url"

    mock_async_session.refresh.side_effect = mock_refresh

    with patch("src.links.router.invalidate_cache") as mock_invalidate:
        mock_invalidate.return_value = AsyncMock()

        response = client.put(
            f"/links/{mock_test_link.short_code}",
            json={
                "original_url": "https://example.com/updated-url"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == "https://example.com/updated-url"

        mock_invalidate.assert_called_once_with(mock_test_link.short_code)

    app.dependency_overrides.pop(current_active_user)


def test_search_by_original_url(client, mock_async_session, mock_test_user, mock_test_link):
    app = client.app
    app.dependency_overrides[current_active_user] = lambda: mock_test_user

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_test_link]
    mock_async_session.execute.return_value = mock_result

    with patch("fastapi_cache.decorator.cache", lambda *args, **kwargs: lambda f: f):
        response = client.get(f"/links/search/?original_url={mock_test_link.original_url}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(link["id"] == str(mock_test_link.id) for link in data)

    app.dependency_overrides.pop(current_active_user)


def test_delete_link(client, mock_async_session, mock_test_user, mock_test_link):
    app = client.app
    app.dependency_overrides[current_active_user] = lambda: mock_test_user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_test_link
    mock_async_session.execute.return_value = mock_result

    with patch("src.links.router.invalidate_cache") as mock_invalidate:
        mock_invalidate.return_value = AsyncMock()

        response = client.delete(f"/links/{mock_test_link.short_code}")

        assert response.status_code == 200
        assert response.json() == {"detail": "Link deleted"}

        mock_invalidate.assert_called_once_with(mock_test_link.short_code)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        response = client.get(f"/links/{mock_test_link.short_code}")
        assert response.status_code == 404

    app.dependency_overrides.pop(current_active_user)
