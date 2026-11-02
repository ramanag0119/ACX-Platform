from sqlalchemy import text
from app.db.session import SessionLocal

def main():
    with SessionLocal() as db:
        db.execute(text("UPDATE stay SET status = 'active', actual_checkout_time = NULL WHERE internal_stay_ref_number = 'STY-2026-0001'"))
        db.execute(text("UPDATE stay SET status = 'pending', actual_checkin_time = NULL WHERE internal_stay_ref_number = 'STY-2026-0003'"))
        db.execute(text("UPDATE stay SET status = 'checked out' WHERE internal_stay_ref_number = 'STY-2026-0004'"))
        db.execute(text("UPDATE stay SET status = 'cancelled' WHERE internal_stay_ref_number = 'STY-2026-0005'"))
        db.commit()
        print("Reset seeded stays successfully.")

if __name__ == "__main__":
    main()
