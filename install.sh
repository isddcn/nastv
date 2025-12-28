#!/usr/bin/env bash
set -e

APP_NAME="nastv"
DEFAULT_PORT=19841

echo "======================================"
echo "   NASTV 一键安装程序"
echo "======================================"

# -----------------------------
# 基础检查
# -----------------------------

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ 未检测到 Docker，请先安装 Docker"
  exit 1
fi

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  echo "❌ 未检测到 docker compose / docker-compose"
  exit 1
fi

# -----------------------------
# .env 初始化
# -----------------------------

if [ ! -f .env ]; then
  echo ""
  echo "▶ 首次安装，初始化配置"

  cp .env.example .env

  read -p "设置 UP_PASSWORD（管理密码）: " UP_PASSWORD
  while [ -z "$UP_PASSWORD" ]; do
    read -p "UP_PASSWORD 不能为空，请重新输入: " UP_PASSWORD
  done

  read -p "设置对外端口 [默认 ${DEFAULT_PORT}]: " APP_PORT
  APP_PORT=${APP_PORT:-$DEFAULT_PORT}

  sed -i "s/^UP_PASSWORD=.*/UP_PASSWORD=${UP_PASSWORD}/" .env
  sed -i "s/^APP_PORT=.*/APP_PORT=${APP_PORT}/" .env

  echo "✔ 已生成 .env"
else
  echo "✔ 检测到 .env，跳过初始化"
fi

# -----------------------------
# 运行态目录
# -----------------------------

echo "▶ 创建运行目录"
mkdir -p data logs web/admin

# -----------------------------
# 数据库初始化
# -----------------------------

if [ ! -f data/stream_cache.db ]; then
  echo "▶ 初始化 SQLite 数据库"
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
  echo "✔ 数据库初始化完成"
else
  echo "✔ 数据库已存在，跳过初始化"
fi

# -----------------------------
# 启动服务
# -----------------------------

echo "▶ 构建并启动 Docker 容器"
$COMPOSE up -d --build

echo ""
echo "======================================"
echo "✅ NASTV 安装完成"
echo "--------------------------------------"
echo "访问地址： http://服务器IP:${APP_PORT}/up.php"
echo "管理入口： up.php"
echo "======================================"
