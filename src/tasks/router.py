from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from uuid import UUID

from src.auth.users import current_active_user
from src.database import get_async_session
from src.models import User, Link
from src.tasks.tasks import trigger_cleanup_task, trigger_grant_admin_task

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


@router.post("/cleanup")
async def manual_cleanup(user: User = Depends(current_active_user)):
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can trigger cleanup."
        )

    trigger_cleanup_task()
    return {"status": "Cleanup task triggered via Celery"}


@router.delete("/links/all")
async def delete_all_links(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete all links."
        )

    await session.execute(delete(Link))
    await session.commit()
    return {"status": "All links deleted from database."}


@router.post("/users/{user_id}/make-admin")
async def make_user_superuser(
    user_id: UUID,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can promote other users."
        )

    result = await session.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    trigger_grant_admin_task(str(user_id))
    return {"status": f"User {user_id} promotion to superuser scheduled via Celery."}
