from sqlalchemy import text
from app.database.database import engine

with engine.connect() as conn:
    # Check hcps table existence and count rows safely
    try:
        res = conn.execute(text("SELECT count(*) as c FROM hcps"))
        cnt = res.fetchone()[0]
        print(f"hcps_exists: True, row_count={cnt}")
    except Exception as e:
        print("hcps_exists: False, error=", type(e).__name__, str(e))

    # Check users and interactions tables
    for t in ('users','interactions'):
        try:
            r = conn.execute(text(f"SELECT count(*) as c FROM {t}"))
            print(f"{t}_exists: True, row_count={r.fetchone()[0]}")
        except Exception as e:
            print(f"{t}_exists: False, error=", type(e).__name__, str(e))
