"""Append explicit ENUM type drops to the Phase 1 migration's downgrade().

Alembic's autogenerate creates PostgreSQL ENUM types implicitly as part of
create_table(), but drop_table() does not remove them. Without this patch the
migration is not reversible: downgrade leaves the types behind and the next
upgrade fails with 'type ... already exists'.

Run once after generating the Phase 1 revision:
    python scripts/patch_downgrade_enums.py
"""

import glob
import io
import os

ENUM_TYPES = [
    "role_type",
    "device_type",
    "device_config_status",
    "device_status",
    "job_order_type",
    "job_order_status",
    "incident_status",
    "alert_severity",
    "limit_type",
    "notification_type",
    "scheduled_task_type",
    "scheduled_task_status",
    "aggregate_interval",
]

MARKER = "    # ### end Alembic commands ###"
SENTINEL = "DROP TYPE IF EXISTS"


def main() -> None:
    versions = sorted(glob.glob(os.path.join("migrations", "versions", "*.py")))
    if not versions:
        raise SystemExit("No migration files found under migrations/versions/")

    for path in versions:
        src = io.open(path, encoding="utf-8").read()
        if SENTINEL in src:
            print(f"skip (already patched): {os.path.basename(path)}")
            continue

        block = (
            "\n    # Drop the PostgreSQL ENUM types created implicitly by "
            "create_table().\n"
            "    # drop_table() does not remove them, which would make this "
            "migration\n"
            "    # irreversible ('type ... already exists' on re-upgrade).\n"
        )
        for name in ENUM_TYPES:
            block += f"    op.execute('DROP TYPE IF EXISTS {name}')\n"

        idx = src.rfind(MARKER)  # last marker == downgrade()
        if idx == -1:
            print(f"skip (no marker): {os.path.basename(path)}")
            continue

        io.open(path, "w", encoding="utf-8").write(src[:idx] + block + src[idx:])
        print(f"patched: {os.path.basename(path)} (+{len(ENUM_TYPES)} DROP TYPE)")


if __name__ == "__main__":
    main()
