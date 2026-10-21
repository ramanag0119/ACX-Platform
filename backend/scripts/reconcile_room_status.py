"""Data reconciliation script for Room Status and Room Condition synchronization.

Usage:
    python -m scripts.reconcile_room_status --dry-run   (default: read-only diagnostic)
    python -m scripts.reconcile_room_status --apply     (applies safe corrections)
"""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AmenityType,
    RoomAllocation,
    RoomStatusConditionApplicability,
    Stay,
)
from app.services.occupancy import determine_room_status_for_applicability


def audit_and_reconcile(db: Session, apply_changes: bool = False) -> dict[str, Any]:
    statuses = {s.id: s.amenity_status_name for s in db.execute(select(AmenityStatus)).scalars().all()}
    status_by_name = {v.lower(): k for k, v in statuses.items()}

    # Rooms to evaluate
    rooms = (
        db.execute(
            select(Amenity)
            .join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
            .where(AmenityType.amenity_category == "room")
            .order_by(Amenity.name)
        )
        .scalars()
        .all()
    )

    report: list[dict[str, Any]] = []
    reconciled_count = 0
    manual_review_count = 0
    consistent_count = 0

    for room in rooms:
        stored_status_id = room.status
        stored_status_name = statuses.get(stored_status_id, f"Unknown({stored_status_id})")

        # Active conditions
        cond_rows = db.execute(
            select(AmenityConditionStatus, AmenityCondition)
            .join(AmenityCondition, AmenityCondition.id == AmenityConditionStatus.amenity_condition_id)
            .where(AmenityConditionStatus.amenity_id == room.id, AmenityConditionStatus.status == 1)
        ).all()
        active_conds = [c for _, c in cond_rows]
        cond_names = [c.name for c in active_conds]

        # Active stay / allocation
        in_house_stay = db.execute(
            select(Stay)
            .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
            .where(
                RoomAllocation.room_id == room.id,
                Stay.actual_checkin_time.is_not(None),
                Stay.actual_checkout_time.is_(None),
            )
        ).scalar_one_or_none()

        pending_stay = db.execute(
            select(Stay)
            .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
            .where(
                RoomAllocation.room_id == room.id,
                Stay.status == "pending",
                Stay.actual_checkin_time.is_(None),
                Stay.actual_checkout_time.is_(None),
            )
        ).scalar_one_or_none()

        # Check blocking condition via data-driven applicability
        has_blocking = False
        for c in active_conds:
            app = db.execute(
                select(RoomStatusConditionApplicability).where(
                    RoomStatusConditionApplicability.condition_id == c.id,
                    RoomStatusConditionApplicability.is_active == True,
                    (RoomStatusConditionApplicability.blocks_readiness == True)
                    | (RoomStatusConditionApplicability.blocks_checkin == True),
                )
            ).first()
            if app:
                has_blocking = True
                break

        # Derive target status
        target_status_name = None
        action_type = "CONSISTENT"
        reason = ""

        if in_house_stay:
            target_status_name = "Occupied"
            if stored_status_name != "Occupied":
                action_type = "RECONCILE"
                reason = f"Room has in-house stay ({in_house_stay.internal_stay_ref_number}) but status is {stored_status_name}"
        elif pending_stay:
            target_status_name = "Allotted"
            if stored_status_name not in ("Allotted", "Allocated"):
                action_type = "RECONCILE"
                reason = f"Room has pending allocation ({pending_stay.internal_stay_ref_number}) but status is {stored_status_name}"
        elif has_blocking:
            target_status_name = "Unavailable"
            if stored_status_name != "Unavailable":
                action_type = "RECONCILE"
                reason = f"Room has active blocking condition ({', '.join(cond_names)}) but status is {stored_status_name}"
        else:
            # Vacant, unallocated, unblocked
            target_status_name = "Available"
            if stored_status_name == "Occupied":
                # Stored as Occupied without active stay (e.g. Room 201)
                action_type = "MANUAL_CONFIRMATION"
                reason = "Stored status is Occupied but no active stay exists; requires business confirmation before clearing"
            elif stored_status_name == "Unavailable" and not active_conds:
                action_type = "MANUAL_CONFIRMATION"
                reason = "Stored status is Unavailable with no active condition; verify whether room is blocked by administrative hold"
            elif stored_status_name != "Available":
                action_type = "RECONCILE"
                reason = f"Vacant unblocked room stored with status {stored_status_name}"

        target_status_id = status_by_name.get(target_status_name.lower()) if target_status_name else stored_status_id

        entry = {
            "room_id": str(room.id),
            "room_name": room.name,
            "stored_status": stored_status_name,
            "target_status": target_status_name,
            "conditions": cond_names,
            "action": action_type,
            "reason": reason,
        }
        report.append(entry)

        if action_type == "CONSISTENT":
            consistent_count += 1
        elif action_type == "RECONCILE":
            reconciled_count += 1
            if apply_changes and target_status_id is not None:
                room.status = target_status_id
        elif action_type == "MANUAL_CONFIRMATION":
            manual_review_count += 1

    if apply_changes:
        db.commit()

    return {
        "total_rooms": len(rooms),
        "consistent_count": consistent_count,
        "reconciled_count": reconciled_count,
        "manual_review_count": manual_review_count,
        "applied": apply_changes,
        "items": report,
    }


def main():
    parser = argparse.ArgumentParser(description="Reconcile Room Statuses with Conditions and Lifecycle")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Diagnostic dry run (default)")
    parser.add_argument("--apply", action="store_true", help="Apply safe reconciliations to the database")
    args = parser.parse_args()

    apply = args.apply
    db = SessionLocal()
    try:
        results = audit_and_reconcile(db, apply_changes=apply)
        print("=" * 80)
        mode = "APPLY" if results["applied"] else "DRY-RUN (READ-ONLY)"
        print(f"ROOM STATUS RECONCILIATION REPORT — Mode: {mode}")
        print("=" * 80)
        print(f"Total rooms evaluated    : {results['total_rooms']}")
        print(f"Consistent rooms         : {results['consistent_count']}")
        print(f"Safe to reconcile        : {results['reconciled_count']}")
        print(f"Requires manual review   : {results['manual_review_count']}")
        print("-" * 80)

        for item in results["items"]:
            if item["action"] != "CONSISTENT":
                print(f"Room {item['room_name']:<6} | Stored: {item['stored_status']:<12} | Target: {item['target_status']:<12} | Action: {item['action']}")
                print(f"       Reason: {item['reason']}")
                if item["conditions"]:
                    print(f"       Conditions: {', '.join(item['conditions'])}")
                print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
