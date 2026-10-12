"""Persistent AlertService (Phase 21). Replaces V1's in-memory dedup dict.
Dedup is now a persisted `dedup_key` (so it survives a restart and is
visible across workers, unlike V1's process-local dict) and gates the
Redis pub/sub broadcast only — the `Alert` row itself is always written,
with `status=SUPPRESSED` recording that a duplicate was intentionally not
re-broadcast (never silently dropped with no trace)."""

import json
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.infrastructure.redis import RedisLike, get_redis_client
from app.models.alert import Alert, AlertLevelEnum, AlertStatusEnum
from app.models.security import RoleEnum, User

THRESHOLD = 0.5  # matches V1 / the frontend Alerts panel's severity cutoff


def level_for_severity(severity: float) -> AlertLevelEnum:
    if severity >= 0.85:
        return AlertLevelEnum.CRITICAL
    if severity >= 0.5:
        return AlertLevelEnum.HIGH
    if severity >= 0.3:
        return AlertLevelEnum.WARNING
    return AlertLevelEnum.INFO


def publish_if_worthy(
    db: Session,
    *,
    incident_id: uuid.UUID,
    agent_id: str,
    action: str | None,
    severity: float,
    target_agency_id: uuid.UUID | None,
    is_global: bool = False,
    redis_client: RedisLike | None = None,
) -> Alert | None:
    """Below-threshold recommendations are not alert-worthy at all — no row
    is written, matching V1's unconditional non-push below THRESHOLD."""
    if severity < THRESHOLD:
        return None

    dedup_key = f"{incident_id}:{agent_id}:{action}:{severity}"
    already_published = db.scalars(
        select(Alert).where(Alert.dedup_key == dedup_key, Alert.status == AlertStatusEnum.PUBLISHED)
    ).first()

    alert = Alert(
        incident_id=incident_id,
        level=level_for_severity(severity),
        message=f"{agent_id}: {action}",
        target_agency_id=target_agency_id,
        is_global=is_global,
        dedup_key=dedup_key,
        status=AlertStatusEnum.SUPPRESSED if already_published else AlertStatusEnum.PUBLISHED,
    )
    db.add(alert)
    db.commit()

    if already_published:
        return alert

    client = redis_client or get_redis_client()
    channel = "alerts:global" if is_global else f"alerts:{target_agency_id or 'unassigned'}"
    client.publish(channel, json.dumps({
        "alert_id": str(alert.id), "incident_id": str(incident_id), "level": alert.level.value, "message": alert.message,
    }))
    return alert


def list_for_user(db: Session, user: User) -> list[Alert]:
    stmt = select(Alert)
    if user.role != RoleEnum.ADMIN:
        stmt = stmt.where(or_(Alert.target_agency_id == user.agency_id, Alert.is_global.is_(True)))
    return list(db.scalars(stmt.order_by(Alert.created_at.desc())))
