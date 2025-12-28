#!/usr/bin/env bash
set -e

APP_NAME="nastv"
APP_PORT_DEFAULT=19841

echo "== NASTV 安装程序 =="

# ---------- Docker ----------
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ 未检测到 Docker，请先安装 Docker"
  exit 1
fi

# ---------- Compose ----------
if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  echo "❌ 未检测到 docker-compose"
  exit 1
fi

# ---------- .env ----------
if [ ! -f .env ]; then
  echo "首次安装，创建 .env"
  cp .env.example .env

  read -p "设置 UP_PASSWORD: " UP_PWD
  read -p "设置对外端口 [${APP_PORT_DEFAULT}]: " APP_PORT
  APP_PORT=${APP_PORT:-$APP_PORT_DEFAULT}

  sed -i "s/^UP_PASSWORD=.*/UP_PASSWORD=${UP_PWD}/" .env
  sed -i "s/^APP_PORT=.*/APP_PORT=${APP_PORT}/" .env
fi

# ---------- Dirs ----------
mkdir -p data logs web/admin

# ---------- DB ----------
if [ ! -f data/stream_cache.db ]; then
  echo "初始化数据库"
  sqlite3 data/stream_cache.db <<'EOF'
CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  enabled INTEGER DEFAULT 1,
  refresh_enabled INTEGER DEFAULT 1,
  refresh_times TEXT,
  refresh_interval_hours INTEGER,
  manual_refresh_at TEXT,
  last_open_at TEXT,
  last_refresh_at TEXT
);
EOF
fi

# ---------- Start ----------
echo "启动服务..."
$COMPOSE up -d --build

echo "✅ 安装完成"
