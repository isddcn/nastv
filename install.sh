#!/bin/sh
set -e

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已生成 .env，请确认端口"
fi

PORT=$(grep APP_PORT .env | cut -d= -f2)
PORT=${PORT:-19841}

if ss -lnt | grep -q ":$PORT "; then
  echo "❌ 端口 $PORT 已被占用，请修改 .env"
  exit 1
fi

docker compose up -d --build
echo "✅ NASTV 已启动：http://localhost:$PORT"
