#!/usr/bin/env bash
set -e

DEFAULT_PORT=19841
IMAGE_NAME="nastv"

echo "======================================"
echo "   NASTV 一键安装（离线镜像版 / Playwright）"
echo "======================================"

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

# 读取版本（用于提示）
VERSION="$(cat VERSION 2>/dev/null || echo "unknown")"

if [ ! -f .env ]; then
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

echo "▶ 创建运行目录"
mkdir -p data logs web/admin

echo "▶ 检查本地 Docker 镜像（需要先 docker load 离线镜像）"
if ! docker image inspect "${IMAGE_NAME}:${VERSION}" >/dev/null 2>&1; then
  echo "❌ 未检测到镜像 ${IMAGE_NAME}:${VERSION}"
  echo "请先执行："
  echo "  docker load < nastv-image-${VERSION}.tar"
  exit 1
fi

echo "▶ 启动 Docker 容器（不 build）"
$COMPOSE up -d

echo ""
echo "======================================"
echo "✅ NASTV 安装完成（版本：${VERSION}）"
echo "访问地址： http://服务器IP:$(grep '^APP_PORT=' .env | cut -d= -f2)/up.php"
echo "======================================"
