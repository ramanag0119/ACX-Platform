from app.main import app
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.db.session import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta, UTC

db = SessionLocal()
uid = db.execute(text("SELECT id FROM app_user WHERE user_name='arjun.menon'")).scalar()
token, _ = create_access_token(uid)
client = TestClient(app)
h = {'Authorization': f'Bearer {token}'}

# 1. KPI query
res_all = client.get('/api/v1/alerts?page_size=1', headers=h).json()
res_crit = client.get('/api/v1/alerts?page_size=1&alert_severity=critical', headers=h).json()
res_warn = client.get('/api/v1/alerts?page_size=1&alert_severity=warning', headers=h).json()
print("KPI Tile (All Time):", res_all['total'], f"({res_crit['total']} critical, {res_warn['total']} warning)")

# 2. Alerts Panel with Week filter
week_ago = (datetime.now(UTC) - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
res_week = client.get(f'/api/v1/alerts?page_size=10&created_from={week_ago}', headers=h).json()
print(f"Alerts Panel (Week filter from {week_ago}):", res_week['total'], "items count:", len(res_week['items']))

# 3. Alerts Panel with Month filter
month_ago = (datetime.now(UTC) - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
res_month = client.get(f'/api/v1/alerts?page_size=10&created_from={month_ago}', headers=h).json()
print(f"Alerts Panel (Month filter from {month_ago}):", res_month['total'], "items count:", len(res_month['items']))

# 4. Check actual timestamps of alerts in DB
rows = db.execute(text("SELECT id, alert_severity, created_on FROM device_alert ORDER BY created_on DESC")).fetchall()
print("\nActual rows in device_alert table:")
for r in rows:
    print("  ", r)
