import time
import sqlite3
import json
from datetime import datetime

# ================== 基础配置 ==================

DB_FILE = "./data/stream_cache.db"
DEFAULT_SCAN_INTERVAL = 60  # 秒（兜底值）

# ================== 工具函数 ==================

def now_ts():
    return int(time.time())

def ts_to_str(ts):
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

# ================== 数据库操作 ==================

def get_db():
    return sqlite3.connect(DB_FILE)

def get_setting(conn, key, default=None):
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else default

def get_channels(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id, page_url, name,
            enabled, refresh_enabled,
            refresh_mode,
            refresh_times,
            refresh_interval_hours,
            manual_refresh_at
        FROM channels
        WHERE enabled = 1
    """)
    return cur.fetchall()

def get_channel_state(conn, channel_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            last_refresh_at,
            last_open_at
        FROM channel_state
        WHERE channel_id = ?
    """, (channel_id,))
    row = cur.fetchone()
    if not row:
        return {
            "last_refresh_at": None,
            "last_open_at": None,
        }
    return {
        "last_refresh_at": row[0],
        "last_open_at": row[1],
    }

# ================== 规则判断 ==================

def should_refresh_by_time(now, refresh_times, last_refresh_at):
    """
    定时刷新判断：
    - refresh_times: ["02:00", "14:30"]
    - 当天该时间点是否已执行过
    """
    if not refresh_times:
        return False

    try:
        times = json.loads(refresh_times)
    except Exception:
        return False

    today = datetime.fromtimestamp(now).strftime("%Y-%m-%d")

    for t in times:
        target = datetime.strptime(f"{today} {t}", "%Y-%m-%d %H:%M")
        target_ts = int(target.timestamp())

        if now >= target_ts:
            if not last_refresh_at or last_refresh_at < target_ts:
                return True

    return False

def should_refresh_by_interval(now, last_open_at, interval_hours):
    """
    间隔刷新判断：
    - 当前时间 >= last_open_at + interval
    """
    if not last_open_at or not interval_hours:
        return False

    return now >= last_open_at + interval_hours * 3600

# ================== 主扫描逻辑 ==================

def scan_once():
    conn = get_db()

    refresh_enabled = get_setting(conn, "refresh_enabled", "0")
    scan_interval = int(get_setting(conn, "scheduler_interval", DEFAULT_SCAN_INTERVAL))

    print("\n==============================")
    print(f"[SCAN] {ts_to_str(now_ts())}")
    print(f"全局刷新开关: {'开启' if refresh_enabled == '1' else '关闭'}")
    print(f"扫描间隔: {scan_interval} 秒")

    if refresh_enabled != "1":
        print(">> 自动刷新已暂停")
        conn.close()
        return scan_interval

    channels = get_channels(conn)

    for ch in channels:
        (
            ch_id, page_url, name,
            enabled, refresh_enabled,
            refresh_mode,
            refresh_times,
            refresh_interval_hours,
            manual_refresh_at
        ) = ch

        if refresh_enabled != 1:
            continue

        state = get_channel_state(conn, ch_id)
        last_refresh_at = state["last_refresh_at"]
        last_open_at = state["last_open_at"]

        need_refresh = False
        reason = []

        # 手动刷新
        if manual_refresh_at:
            if now_ts() >= manual_refresh_at:
                need_refresh = True
                reason.append("手动刷新请求")

        # 定时刷新
        if refresh_mode in ("time", "both"):
            if should_refresh_by_time(now_ts(), refresh_times, last_refresh_at):
                need_refresh = True
                reason.append("定时刷新")

        # 间隔刷新
        if refresh_mode in ("interval", "both"):
            if should_refresh_by_interval(now_ts(), last_open_at, refresh_interval_hours):
                need_refresh = True
                reason.append("间隔刷新")

        print(f"\n频道: {name or page_url}")
        print(f"  上次刷新: {ts_to_str(last_refresh_at)}")
        print(f"  上次访问: {ts_to_str(last_open_at)}")

        if need_refresh:
            print(f"  >>> 应刷新 ({', '.join(reason)})")
        else:
            print("  不需要刷新")

    conn.close()
    return scan_interval

# ================== 主循环 ==================

def main():
    print("NASTV Scheduler 启动（阶段 1：规则判断）")

    while True:
        try:
            interval = scan_once()
        except Exception as e:
            print(f"[ERROR] {e}")
            interval = DEFAULT_SCAN_INTERVAL

        time.sleep(interval)

if __name__ == "__main__":
    main()
