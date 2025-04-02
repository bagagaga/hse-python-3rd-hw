from datetime import datetime, timezone
from src.models import User, Link


def test_user_model_init():
    import uuid as uuid_module
    user_id = uuid_module.uuid4()
    now = datetime.now(timezone.utc)
    user = User(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        registered_at=now
    )

    assert user.id == user_id
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.is_verified is True
    assert user.registered_at == now


def test_link_model_init():
    link_id = "123e4567-e89b-12d3-a456-426614174000"
    user_id = "223e4567-e89b-12d3-a456-426614174000"
    now = datetime.now(timezone.utc)

    link = Link(
        id=link_id,
        short_code="testcode",
        original_url="https://example.com",
        user_id=user_id,
        created_at=now,
        last_used_at=now,
        expires_at=now,
        visit_count=0
    )

    assert str(link.id) == link_id
    assert link.short_code == "testcode"
    assert link.original_url == "https://example.com"
    assert str(link.user_id) == user_id
    assert link.created_at == now
    assert link.last_used_at == now
    assert link.expires_at == now
    assert link.visit_count == 0


def test_user_link_relationship(sync_session):
    import uuid as uuid_module
    from datetime import datetime, timedelta, timezone

    user_id = uuid_module.uuid4()
    user = User(
        id=user_id,
        email="relationship_test@example.com",
        hashed_password="password",
        is_active=True,
        is_superuser=False,
        is_verified=True
    )
    sync_session.add(user)
    sync_session.commit()

    now = datetime.now(timezone.utc)
    link = Link(
        id=uuid_module.uuid4(),
        short_code="relationtest",
        original_url="https://example.com/relation",
        user_id=user.id,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=7),
        visit_count=0
    )
    sync_session.add(link)
    sync_session.commit()

    sync_session.refresh(user)

    user_links = user.links
    assert len(user_links) > 0
    assert any(l.id == link.id for l in user_links)

    sync_session.refresh(link)
    assert link.users.id == user.id
