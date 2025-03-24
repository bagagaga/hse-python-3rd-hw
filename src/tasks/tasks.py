from src.database import DATABASE_URL_SYNC
from . import N_DAYS_UNUSED
from celery import Celery
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, update, delete, or_
from sqlalchemy.orm import sessionmaker
from src.models import Link
from celery.schedules import crontab

celery = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)


engine = create_engine(DATABASE_URL_SYNC)
SessionLocal = sessionmaker(bind=engine)


@celery.task
def increment_visit_count(link_id: str):
    with SessionLocal() as session:
        stmt = (
            update(Link)
            .where(Link.id == link_id)
            .values(
                visit_count=Link.visit_count + 1,
                last_used_at=datetime.now(timezone.utc)
            )
        )
        session.execute(stmt)
        session.commit()


@celery.task
def cleanup_old_links():
    with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=N_DAYS_UNUSED)
        stmt = (
            delete(Link)
            .where(
                or_(
                    Link.expires_at < now,
                    Link.last_used_at < threshold
                )
            )
        )
        session.execute(stmt)
        session.commit()


celery.conf.beat_schedule = {
    "cleanup-every-10-minutes": {
        "task": "src.tasks.tasks.cleanup_old_links",
        "schedule": crontab(minute="*/10"),
    },
}
