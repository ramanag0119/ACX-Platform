from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()

print("=== Currency Rows ===")
for r in db.execute(text("SELECT id, code, name, symbol, minor_units, is_active FROM currency")).fetchall():
    print(" ", r)

print("\n=== energy_stat verification ===")
total = db.execute(text("SELECT count(*) FROM energy_stat")).scalar()
with_device = db.execute(text("SELECT count(*) FROM energy_stat WHERE device_id IS NOT NULL")).scalar()
matched_devices = db.execute(text("""
    SELECT d.id, d.device_uid, d.device_name, es.device_name, count(es.*)
    FROM energy_stat es
    JOIN device d ON d.id = es.device_id
    GROUP BY d.id, d.device_uid, d.device_name, es.device_name
""")).fetchall()
print(f" Total rows: {total}, With device_id: {with_device}")
for m in matched_devices:
    print("  Device Match:", m)

print("\n=== facility currency ===")
for r in db.execute(text("SELECT id, name, currency_id FROM facility")).fetchall():
    print(" ", r)

print("\n=== invoice currency ===")
for r in db.execute(text("SELECT id, invoice_number, total_amount, currency_id FROM invoice")).fetchall():
    print(" ", r)

print("\n=== package pricing ===")
for r in db.execute(text("SELECT id, name, price, currency_id FROM package")).fetchall():
    print(" ", r)

print("\n=== service_category_item currency ===")
for r in db.execute(text("SELECT id, item_name, price_per_unit, currency_id FROM service_category_item LIMIT 5")).fetchall():
    print(" ", r)
