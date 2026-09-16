"""Group L - scheduler (2 tables).

Blueprint §5, tables 84-85.

Replaces the Phase 1 `scheduled_task` table, which had no IKANOS counterpart.
The executor is the `caleido_scheduler` pair; its `jobs` table is renamed
`scheduler_job` to resolve the collision with `caleido.jobs` (-> `job_order`).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPk, HMSBase, TimestampMixin, UUIDPk
from app.models import enums


class SchedulerJob(HMSBase, UUIDPk):
    """Cron job definition -- housekeeping, sanitation, checkout, expiry.
    IKANOS `caleido_scheduler.jobs`. ADAPT.

    The Phase 1 `scheduled_task` columns (type, target_entity, scheduled_at,
    last_executed, recur_pattern) have no IKANOS counterpart: the schedule
    lives inside `job_data`, and execution history lives in
    `scheduler_job_execution`. Closes NEEDS_REVIEW D10.
    """

    __tablename__ = "scheduler_job"

    # IKANOS `job_id` -- the cron key. Renamed to avoid reading as an FK.
    job_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    job_name: Mapped[str] = mapped_column(String(50), nullable=False)
    job_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(enums.scheduler_job_status, nullable=False)
    is_dynamic_job: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )


class SchedulerJobExecution(HMSBase, BigIntPk):
    """One run of a scheduled job. IKANOS `job_executions`. ADAPT.

    IKANOS has no created_on/updated_on here; they are added per §5.0.
    """

    __tablename__ = "scheduler_job_execution"

    scheduler_job_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scheduler_job.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_execution_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    job_response: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(
        enums.scheduler_execution_status, nullable=False
    )
    # Milliseconds.
    job_run_duration: Mapped[int] = mapped_column(Integer, nullable=False)
