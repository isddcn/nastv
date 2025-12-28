import time
import sqlite3
import requests
import os

DB_FILE = os.getenv("DB_FILE", "/app/data/stream_cache.db")
SLEEP_SECONDS = int(os.getenv("SCHEDULER_SLEEP", "60"))

def db():
    return sqlite3.connect(DB_FILE)

def init_db():
    with db() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS refresh_rules (
            page_url TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            interval_hours INTEGER DEFAULT 6,
            last_refresh INTEGER DEFAULT 0
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            k TEXT PRIMARY KEY,
            v TEXT
        )
        """)
        conn.commit()

def get_global_enabled():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT v FROM system_settings WHERE k='refresh_enabled'")
        row = c.fetchone()
        return row is None or row[0] != "0"

def get_rules():
    with db() as conn:
        c = conn.cursor()
        c.execute("""
        SELECT page_url, interval_hours, last_refresh
        FROM refresh_rules
        WHERE enabled=1
        """)
        return c.fetchall()

def update_last_refresh(url):
    with db() as conn:
        c = conn.cursor()
        c.execute("""
        UPDATE refresh_rules
        SET last_refresh=?
        WHERE page_url=?
        """, (int(time.time()), url))
        conn.commit()

def trigger_refresh(url):
    try:
        requests.get(
            "http://127.0.0.1:19841/parse",
            params={"url": url, "s": 1},
            timeout=20
        )
    except Exception:
        pass

def main():
    init_db()
    print("[scheduler] started")

    while True:
        if get_global_enabled():
            now = int(time.time())
            for url, interval, last in get_rules():
                if now - last >= interval * 3600:
                    trigger_refresh(url)
                    update_last_refresh(url)
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
