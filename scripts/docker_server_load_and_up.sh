#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "用法: $0 <images.tar.gz>"
    exit 1
fi

ARCHIVE_PATH="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/deploy/docker-compose.server.yml"
COMPOSE_BIN=""

if [[ ! -f "${ARCHIVE_PATH}" ]]; then
    echo "镜像包不存在: ${ARCHIVE_PATH}"
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "未检测到 docker，请先安装 Docker Engine + Docker Compose。"
    exit 1
fi

if docker compose version >/dev/null 2>&1; then
    COMPOSE_BIN="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_BIN="docker-compose"
else
    echo "未检测到 docker compose 或 docker-compose。"
    exit 1
fi

cd "${ROOT_DIR}"

docker load -i "${ARCHIVE_PATH}"
${COMPOSE_BIN} -f "${COMPOSE_FILE}" up -d
${COMPOSE_BIN} -f "${COMPOSE_FILE}" ps
