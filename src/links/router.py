from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session
from typing import Optional
from . import schemas
from ..models import User, Link
from src.auth.users import current_optional_user, current_active_user
from .utils import generate_short_code, invalidate_cache
from fastapi_cache.decorator import cache
from datetime import datetime, timezone
from fastapi.responses import RedirectResponse
from ..tasks.tasks import increment_visit_count

router = APIRouter(
    prefix="/links",
    tags=["links"]
)


@router.get("/{short_code}", response_class=RedirectResponse)
async def redirect_to_original(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(Link).where(
            Link.short_code == short_code,
            Link.expires_at > datetime.now(timezone.utc)
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    increment_visit_count.apply_async(args=[link.id])
    await session.commit()
    return link.original_url


@router.post("/shorten", response_model=schemas.LinkRead)
async def create_short_link(
    link_data: schemas.LinkCreate,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(current_optional_user)
):
    now = datetime.now(timezone.utc)
    if link_data.custom_alias:
        result = await session.execute(
            select(Link).where(
                Link.short_code == link_data.custom_alias,
                Link.expires_at > now
            )
        )
        if result.scalars().all():
            raise HTTPException(status_code=400, detail="Alias already in use")

        short_code = link_data.custom_alias

    else:
        while True:
            short_code = generate_short_code()
            result = await session.execute(
                select(Link).where(
                    Link.short_code == short_code,
                    Link.expires_at > now
                )
            )
            if not result.scalars().all():
                break

    link = Link(
        original_url=str(link_data.original_url),
        short_code=short_code,
        expires_at=link_data.expires_at,
        user_id=user.id if user else None
    )

    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


@router.get("/{short_code}/stats", response_model=schemas.LinkRead)
@cache(expire=60)
async def get_stats(
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Link).where(Link.short_code == short_code, Link.user_id == user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link


@router.put("/{short_code}", response_model=schemas.LinkRead)
async def update_link(
    short_code: str,
    link_update: schemas.LinkUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Link).where(Link.short_code == short_code, Link.user_id == user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found or access denied")

    if link_update.original_url:
        link.original_url = str(link_update.original_url)
    if link_update.expires_at:
        link.expires_at = link_update.expires_at

    await invalidate_cache(short_code)
    await session.commit()
    await session.refresh(link)
    return link


@router.get("/search/", response_model=list[schemas.LinkRead])
@cache(expire=60)
async def search_by_original_url(
    original_url: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):

    result = await session.execute(
        select(Link).where(Link.original_url == original_url, Link.user_id == user.id)
    )
    links = result.scalars().all()

    if not links:
        raise HTTPException(status_code=404, detail="No links found for the given URL.")

    return links


@router.delete("/{short_code}")
async def delete_link(
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Link).where(Link.short_code == short_code, Link.user_id == user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found or access denied")

    await invalidate_cache(short_code)
    await session.delete(link)
    await session.commit()
    return {"detail": "Link deleted"}
