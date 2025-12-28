import os
import re
import time
import sqlite3
from datetime import datetime
from urllib.parse import urljoin

import requests
from flask import Flask, request, Response

# ================== 配置 ==================
APP_PORT = int(os.getenv("APP_PORT", "19841"))
DB_FILE = os.getenv("DB_FILE", "/app/data/stream_cache.db")
CACHE_TTL = int(os.getenv("CACHE_TTL", str(6 * 60 * 60)))  # 默认 6 小时
MAX_IFRAME_DEPTH = int(os.getenv("MAX_IFRAME_DEPTH", "2"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "12"))

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

# ================== 解析核心（轻量版） ==================

STREAM_REGEXES = [
    re.compile(r'https?://[^\s\'"<>]+\.m3u8(?:\?[^\s\'"<>]+)?', re.I),
    re.compile(r'https?://[^\s\'"<>]+\.mpd(?:\?[^\s\'"<>]+)?', re.I),
    re.compile(r'https?://[^\s\'"<>]+\.flv(?:\?[^\s\'"<>]+)?', re.I),
    re.compile(r'https?://[^\s\'"<>]+\.mp4(?:\?[^\s\'"<>]+)?', re.I),
]

IFRAME_RE = re.compile(r'<iframe[^>]+src=["\']([^"\']+)["\']', re.I)

def _headers(referer):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": referer,
        "Connection": "close",
    }

def _find_stream(text):
    for rgx in STREAM_REGEXES:
        m = rgx.search(text)
        if m:
            return m.group(0)
    return None

def parse_stream(page_url, depth=0):
    """
    解析策略（无 Playwright）：
    1. 请求页面 HTML，正则找流
    2. 查找 iframe，递归进入（有限深度）
    """
    if depth > MAX_IFRAME_DEPTH:
        return None

    try:
        r = requests.get(
            page_url,
            headers=_headers(page_url),
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
    except Exception:
        return None

    if not r.ok or not r.text:
        return None

    # ① 直接找流
    stream = _find_stream(r.text)
    if stream:
        return stream

    # ② iframe 递归
    iframes = IFRAME_RE.findall(r.text)
    for src in iframes:
        iframe_url = urljoin(page_url, src)
        stream = parse_stream(iframe_url, depth + 1)
        if stream:
            return stream

    return None

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
<script src="/static/hls.min.js"></script>
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

    # ===== 默认：纯文本 =====
    return Response(stream, mimetype="text/plain")

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=APP_PORT)
