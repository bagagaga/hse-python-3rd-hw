import random
import string
from datetime import datetime, timedelta, timezone
from . import DEFAULT_EXPIRATION_DAYS
from fastapi_cache import FastAPICache


def generate_short_code(length: int = 6) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRATION_DAYS)


async def invalidate_cache(short_code: str):
    backend = FastAPICache.get_backend()
    if backend and hasattr(backend, 'redis'):
        redis = backend.redis
        key = f"fastapi-cache:/links/{short_code}"
        await redis.delete(key)
