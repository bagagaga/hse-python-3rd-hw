from datetime import datetime, timezone
import re
from src.links.utils import generate_short_code, default_expires_at, invalidate_cache
from fastapi_cache import FastAPICache
from unittest.mock import MagicMock, AsyncMock, patch


def test_generate_short_code_length():
    short_code = generate_short_code()
    assert len(short_code) == 6

    custom_length = 10
    short_code = generate_short_code(length=custom_length)
    assert len(short_code) == custom_length


def test_generate_short_code_characters():
    short_code = generate_short_code()
    assert re.match(r'^[a-zA-Z0-9]+$', short_code) is not None


def test_generate_short_code_uniqueness():
    codes = [generate_short_code() for _ in range(1000)]
    assert len(set(codes)) >= 990


def test_default_expires_at():
    now = datetime.now(timezone.utc)
    expires = default_expires_at()

    delta = expires - now
    assert delta.days == 10

    assert expires.tzinfo == timezone.utc


def test_invalidate_cache():
    import asyncio
    short_code = "testcode"

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock()

    mock_backend = MagicMock()
    mock_backend.redis = mock_redis

    with patch.object(FastAPICache, 'get_backend', return_value=mock_backend):
        asyncio.run(invalidate_cache(short_code))

        mock_redis.delete.assert_called_once_with(f"fastapi-cache:/links/{short_code}")


def test_invalidate_cache_no_backend():
    import asyncio
    with patch.object(FastAPICache, 'get_backend', return_value=None):
        asyncio.run(invalidate_cache("testcode"))
