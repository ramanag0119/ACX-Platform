from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
rows = db.execute(text("""
    SELECT d.id, d.device_uid, d.device_name, d.device_type, dt.name as type_name, dt.device_short_code,
           d.amenity_id, a.name as room_name, d.facility_id
    FROM device d
    JOIN device_type dt ON dt.id = d.device_type
    LEFT JOIN amenity a ON a.id = d.amenity_id
    WHERE a.name IN ('101', '106', '205')
    ORDER BY a.name, dt.name
""")).fetchall()

for r in rows:
    print(r)
