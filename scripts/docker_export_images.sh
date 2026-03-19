#!/usr/bin/env bash
set -euo pipefail

WEB_IMAGE="${WEB_IMAGE:-log-lottery-web:local}"
BACKEND_IMAGE="${BACKEND_IMAGE:-log-lottery-backend:local}"
OUTPUT_FILE="${1:-/tmp/log-lottery-images-$(date +%Y%m%d-%H%M%S).tar.gz}"

if ! command -v docker >/dev/null 2>&1; then
    echo "未检测到 docker，请先安装 Docker Engine。"
    exit 1
fi

images=("${WEB_IMAGE}" "${BACKEND_IMAGE}")
for img in "${images[@]}"; do
    if ! docker image inspect "${img}" >/dev/null 2>&1; then
        echo "镜像不存在: ${img}"
        echo "请先执行: docker compose -f deploy/docker-compose.local.yml build"
        exit 1
    fi
done

docker save "${images[@]}" | gzip > "${OUTPUT_FILE}"
echo "镜像已导出: ${OUTPUT_FILE}"
