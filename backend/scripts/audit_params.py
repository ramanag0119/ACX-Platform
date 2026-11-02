from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
rows = db.execute(text("""
    SELECT id, param_name, device_type, data_type, unit
    FROM device_param
    WHERE param_name ILIKE '%energy%' OR param_name ILIKE '%power%'
""")).fetchall()

for r in rows:
    print(r)
