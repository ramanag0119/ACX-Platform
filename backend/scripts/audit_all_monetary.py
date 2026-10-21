from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
rows = db.execute(text("""
    SELECT table_name, column_name, data_type, numeric_precision, numeric_scale, is_nullable
    FROM information_schema.columns
    WHERE table_schema='public'
      AND (
          data_type IN ('numeric', 'double precision', 'real', 'money')
          OR column_name ~* '(price|amount|tax|discount|cost|fee|currency|tariff)'
      )
    ORDER BY table_name, ordinal_position
""")).fetchall()

for r in rows:
    print(r)
