import os
import time
import sqlite3
from datetime import datetime
from flask import Flask, request, Response
from playwright.sync_api import sync_playwright

# ================== 配置 ==================
APP_PORT = int(os.getenv("APP_PORT", "19841"))
DB_FILE = os.getenv("DB_FILE", "/app/data/stream_cache.db")
CACHE_TTL = int(os.getenv("CACHE_TTL", str(6 * 60 * 60)))  # 6 小时
PARSE_TIMEOUT = int(os.getenv("PARSE_TIMEOUT", "25"))     # 抓流最长等待秒

STREAM_HINTS = (".m3u8", ".flv", ".mp4", ".mpd", ".webm")

app = Flask(__name__)

# ================== 数据库 ==================
def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stream_cache (
            page_url TEXT PRIMARY KEY,
            stream_url TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def db_get(page_url):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT stream_url, updated_at FROM stream_cache WHERE page_url = ?",
        (page_url,)
    )
    row = cur.fetchone()
    conn.close()
    return row

def db_set(page_url, stream_url):
    now = int(time.time())
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO stream_cache (page_url, stream_url, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(page_url) DO UPDATE SET
            stream_url = excluded.stream_url,
            updated_at = excluded.updated_at
    """, (page_url, stream_url, now))
    conn.commit()
    conn.close()
    return now

# ================== Playwright 抓流 ==================
def parse_stream(page_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )

        page = context.new_page()
        stream_url = None

        def hit(url: str):
            nonlocal stream_url
            if stream_url:
                return
            u = url.lower()
            if any(x in u for x in STREAM_HINTS):
                stream_url = url

        # 同时监听 request + response（非常关键）
        page.on("request", lambda req: hit(req.url))
        page.on("response", lambda resp: hit(resp.url))

        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            # 等待网络空闲（播放器通常在这之后开始拉流）
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        start = time.time()
        while time.time() - start < PARSE_TIMEOUT:
            if stream_url:
                break
            time.sleep(0.4)

        context.close()
        browser.close()
        return stream_url

# ================== 路由 ==================
@app.route("/parse")
def parse():
    page_url = request.args.get("url", "").strip()
    use_cache = "s" in request.args
    tv_mode = "tv" in request.args

    if not page_url:
        return "missing url", 400

    now = int(time.time())
    stream = None
    cache_time = None

    if use_cache:
        row = db_get(page_url)
        if row:
            stream, cache_time = row
            if now - cache_time >= CACHE_TTL:
                stream = None

    if not stream:
        stream = parse_stream(page_url)
        if not stream:
            return "stream not found", 404
        if use_cache:
            cache_time = db_set(page_url, stream)

    # ===== tv 模式 =====
    if tv_mode:
        next_ts = (cache_time + CACHE_TTL) if (use_cache and cache_time) else 0
        next_str = datetime.fromtimestamp(next_ts).strftime("%Y-%m-%d %H:%M:%S") if next_ts else ""

        return Response(f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NASTV</title>
<style>
html,body{{margin:0;background:#000;height:100%;}}
video{{width:100%;height:100%;object-fit:contain}}
#info{{position:fixed;right:10px;bottom:10px;
background:rgba(0,0,0,.6);color:#fff;padding:10px;
font-size:13px;border-radius:8px;max-width:92%;
word-break:break-all;line-height:1.4}}
</style>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body>
<video id="v" autoplay muted playsinline controls></video>
<div id="info">
<div>网页：{page_url}</div>
<div>流：{stream}</div>
{"<div>下次刷新：" + next_str + "</div>" if next_str else ""}
</div>
<script>
const v=document.getElementById("v");
document.addEventListener("click",()=>{{v.muted=false}});
if(v.canPlayType("application/vnd.apple.mpegurl")){{v.src="{stream}";}}
else if(window.Hls && Hls.isSupported()){{const h=new Hls();h.loadSource("{stream}");h.attachMedia(v);}}
</script>
</body></html>""", mimetype="text/html")

    # ===== 默认：只输出流地址（你要求的行为）=====
    return Response(stream, mimetype="text/plain")

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=APP_PORT)
