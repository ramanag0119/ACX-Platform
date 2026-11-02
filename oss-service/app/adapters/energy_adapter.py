"""OSS -> contract adapters for energy statistics.

VERIFIED OSS REALITY (see docs/DESIGN_AND_READINESS.md):
  * OSS has NO energy table and NO pre-aggregated hourly energy.
  * The only energy signal is `active_energy` inside
    `insp_device_performance.param_data`, and it is a MONOTONICALLY INCREASING
    CUMULATIVE COUNTER (e.g. 0.667 -> 0.722 -> 0.777 ... per reading).

  HMS `EnergyStatRead.energy_consumed` is HOURLY CONSUMPTION. Deriving it from a
  cumulative counter requires a delta + time-bucketing AGGREGATION RULE that the
  OSS schema does not define. Per the integration rules we do NOT invent that
  rule (nor any unit/conversion). Energy is therefore returned as an explicit
  UNSUPPORTED resource pending a business-confirmed calculation, rather than
  fabricated consumption values.

  Options to confirm with the business (then this adapter is implemented):
    (a) expose RAW cumulative `active_energy` readings as-is (no consumption), or
    (b) compute consumption = delta of consecutive cumulative readings, bucketed
        to the hour, with a confirmed reset/rollover policy.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.adapters.base import AdapterNotMapped

_REASON = (
    "energy (OSS has only a cumulative active_energy counter in param_data; "
    "HMS energy_consumed is hourly consumption and needs a business-confirmed "
    "delta/bucketing rule -- not invented here)"
)


def list_energy_stats(db: Session, *, page: int, page_size: int, **filters):
    raise AdapterNotMapped(_REASON)


def energy_summary(db: Session, *, group_by: str, **filters):
    raise AdapterNotMapped(_REASON)
