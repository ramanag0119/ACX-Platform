import sys
from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()

def cols(t):
    rows = db.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=:t
        ORDER BY ordinal_position
    """), {'t': t}).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]

def fks(t):
    rows = db.execute(text("""
        SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name=:t
    """), {'t': t}).fetchall()
    return [(r[0], r[1], r[2], r[3]) for r in rows]

print("=== energy_stat columns ===")
for c in cols("energy_stat"):
    print(c)
print("=== energy_stat FKs ===")
for f in fks("energy_stat"):
    print(f)
print("=== energy_stat count ===")
print(db.execute(text("SELECT count(*) FROM energy_stat")).scalar())

print("=== energy_stat sample ===")
rows = db.execute(text("SELECT * FROM energy_stat LIMIT 5")).fetchall()
for r in rows:
    print(r)

print("\n=== device sample (id, device_uid, device_name, facility_id, amenity_id) ===")
rows = db.execute(text("SELECT id, device_uid, device_name, facility_id, amenity_id FROM device LIMIT 10")).fetchall()
for r in rows:
    print(r)

print("\n=== distinct device_name in energy_stat ===")
names = db.execute(text("SELECT DISTINCT device_name FROM energy_stat")).fetchall()
for n in names:
    print(n)

print("\n=== matching energy_stat.device_name to device ===")
matches = db.execute(text("""
    SELECT es.device_name, count(es.*), 
           count(d_by_name.id) as matched_by_name,
           count(d_by_uid.id) as matched_by_uid
    FROM energy_stat es
    LEFT JOIN device d_by_name ON d_by_name.device_name = es.device_name
    LEFT JOIN device d_by_uid ON d_by_uid.device_uid = es.device_name
    GROUP BY es.device_name
""")).fetchall()
for m in matches:
    print(m)
