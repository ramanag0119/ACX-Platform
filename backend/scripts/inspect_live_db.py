import os
import sys
from app.db.session import engine
from sqlalchemy import text, inspect

def main():
    print("=== LIVE POSTGRESQL INSPECTION ===")
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT version();")).scalar()
        db_name = conn.execute(text("SELECT current_database();")).scalar()
        cur_schema = conn.execute(text("SELECT current_schema();")).scalar()
        print(f"Database: {db_name}, Schema: {cur_schema}")
        print(f"Version: {ver}")
        
        # Alembic version
        try:
            alem = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
            print(f"Alembic current revision: {alem}")
        except Exception as e:
            print(f"Alembic version table error: {e}")
            
        inspector = inspect(conn)
        tables = sorted(inspector.get_table_names(schema='public'))
        print(f"\nTotal tables found in public schema: {len(tables)}")
        
        table_info = []
        for t in tables:
            columns = inspector.get_columns(t, schema='public')
            pks = inspector.get_pk_constraint(t, schema='public')
            fks = inspector.get_foreign_keys(t, schema='public')
            uqs = inspector.get_unique_constraints(t, schema='public')
            idxs = inspector.get_indexes(t, schema='public')
            
            try:
                cnt = conn.execute(text(f'SELECT count(*) FROM "{t}";')).scalar()
            except Exception as e:
                cnt = -1
                
            table_info.append({
                "name": t,
                "col_count": len(columns),
                "columns": [c["name"] for c in columns],
                "pk": pks.get("constrained_columns", []),
                "fks": len(fks),
                "fk_details": [(fk.get("constrained_columns"), fk.get("referred_table"), fk.get("referred_columns")) for fk in fks],
                "uqs": len(uqs),
                "indexes": len(idxs),
                "rows": cnt
            })
            
        print("\n--- Summary of Tables with Rows > 0 ---")
        non_empty = [t for t in table_info if t["rows"] > 0]
        for t in non_empty:
            print(f"  {t['name']}: {t['rows']} rows (cols: {t['col_count']}, PK: {t['pk']})")
            
        print(f"\nTotal non-empty tables: {len(non_empty)} / {len(tables)}")
        
        # Let's save the full metadata to a file for audit
        import json
        with open("docs/live_postgres_inventory.json", "w", encoding="utf-8") as f:
            json.dump(table_info, f, indent=2, default=str)
        print("Full inventory saved to docs/live_postgres_inventory.json")

if __name__ == "__main__":
    main()
