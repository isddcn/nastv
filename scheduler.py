import sqlite3
import time
import json
import logging
import requests
from datetime import datetime, timedelta

DB_FILE = "/app/data/stream_cache.db"
LOG_FILE = "/app/logs/scheduler.log"

SCAN_INTERVAL = 60  # 秒，每分钟扫描一次

# ================= 日志 =================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("scheduler")

# ================= 工具 =================

def now():
    return datetime.now()

def parse_time(t):
    return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")

def should_run_today(last_run, today_time):
    if not last_run:
        return True
    return last_run.date() < today_time.date()

# ================= 刷新判断 =================

def need_refresh(row):
    """
    根据规则判断该频道是否需要刷新
    """
    if not row["enabled"] or not row["refresh_enabled"]:
        return False, None

    now_dt = now()

    # 1. 手动刷新（最高优先级）
    if row["manual_refresh_at"]:
        return True, "manual"

    # 2. 定时刷新
    if row["refresh_times"]:
        try:
            times = json.loads(row["refresh_times"])
            for t in times:
                h, m = map(int, t.split(":"))
                today_time = now_dt.replace(hour=h, minute=m, second=0, microsecond=0)
                if now_dt >= today_time:
                    if should_run_today(row["last_refresh_at"], today_time):
                        return True, "scheduled"
        except Exception:
            pass

    # 3. 间隔刷新
    if row["refresh_interval_hours"] and row["last_open_at"]:
        last_open = parse_time(row["last_open_at"])
        delta = timedelta(hours=row["refresh_interval_hours"])
        if now_dt - last_open >= delta:
            if not row["last_refresh_at"] or parse_time(row["last_refresh_at"]) < last_open:
                return True, "interval"

    return False, None

# ================= 执行刷新 =================

def do_refresh(row):
    """
    真正执行刷新：
    - 调用 parse 接口
    - 成功才更新缓存
    """
    url = row["url"]
    parse_url = f"http://127.0.0.1:19842/parse?url={requests.utils.quote(url)}&s=1"

    try:
        r = requests.get(parse_url, timeout=15)
        if r.status_code != 200:
            raise Exception("HTTP 非 200")

        stream = r.text.strip()
        if not stream.startswith("http"):
            raise Exception("解析结果异常")

        return True, stream

    except Exception as e:
        log.error(f"[FAIL] {row['id']} {url} - {e}")
        return False, None

# ================= 主循环 =================

def main():
    log.info("NASTV Scheduler 启动")

    while True:
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT * FROM channels")
            rows = cur.fetchall()

            for row in rows:
                need, reason = need_refresh(row)
                if not need:
                    continue

                log.info(f"[REFRESH] id={row['id']} reason={reason}")

                ok, stream = do_refresh(row)
                if ok:
                    cur.execute("""
                        UPDATE channels
                        SET last_refresh_at = ?, manual_refresh_at = NULL
                        WHERE id = ?
                    """, (now().strftime("%Y-%m-%d %H:%M:%S"), row["id"]))
                    conn.commit()
                    log.info(f"[OK] id={row['id']}")
                else:
                    log.warning(f"[SKIP] id={row['id']} 保留旧缓存")

            conn.close()

        except Exception as e:
            log.error(f"[ERROR] 调度异常：{e}")

        time.sleep(SCAN_INTERVAL)

# ================= 启动 =================

if __name__ == "__main__":
    main()
