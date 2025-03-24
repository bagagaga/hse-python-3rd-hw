from fastapi import APIRouter
from src.tasks.tasks import cleanup_old_links

router = APIRouter(prefix="/tasks")


@router.post("/cleanup")
async def manual_cleanup():
    cleanup_old_links.delay()
    return {"status": "Cleanup task triggered via Celery"}
