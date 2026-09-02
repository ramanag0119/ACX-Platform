"""Group N - energy and reporting (2 tables).

Blueprint §5, tables 91-92.
"""

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models import enums


class EnergyStat(Base, TimestampMixin):
    """Hourly energy rollup per device per room. Backs Energy View and the
    Dashboard energy chart. IKANOS `energy_stats`. ADAPT -- replaces the
    Phase 1 `energy_aggregate`.

    `avg_power`, `max_power`, `total_energy`, `interval` and `room_id` do not
    exist [FACT]. IKANOS stores ONE metric, hourly only. The invented
    `aggregate_interval` enum is gone -- daily and weekly rollups are
    aggregated at query time.
    """

    __tablename__ = "energy_stat"

    # A room can hold several standalone devices.
    device_name: Mapped[str] = mapped_column(String(11), primary_key=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        primary_key=True,
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Hours elapsed since 2000 -- NOT a timestamp.
    hour: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    energy_consumed: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)

    __table_args__ = (
        Index("ix_energy_stat_amenity_id_hour", "amenity_id", "hour"),
        Index("ix_energy_stat_facility_id_hour", "facility_id", "hour"),
    )


class DailyDualDataPoint(Base, TimestampMixin):
    """Pre-aggregated daily KPI pairs. IKANOS `daily_dual_data_points`. USE.

    `metric_type` is exactly the Caleido At Work KPI set, and the dp_1/dp_2
    pair is why the Dashboard rings show "n of m".

    REVIEW (blueprint §10 #9 / OPEN DECISION #6): `facility_id` is NOT part of
    the IKANOS primary key, so the table is single-facility as built. That is
    preserved verbatim rather than silently widened.
    """

    __tablename__ = "daily_dual_data_point"

    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    metric_type: Mapped[str] = mapped_column(enums.daily_metric_type, primary_key=True)
    # Numerator, e.g. rooms online.
    dp_1: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Denominator, e.g. rooms total.
    dp_2: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_daily_dual_data_point_facility_id_metric_date",
            "facility_id",
            "metric_date",
        ),
    )
