from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
for t in ['feature', 'package_feature', 'room_allocation', 'stay', 'amenity', 'amenity_type']:
    cols = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=:t ORDER BY ordinal_position"), {'t': t}).fetchall()
    print(f"\n--- {t} ---")
    for c in cols:
        print(f"  {c[0]}: {c[1]}")
