#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/deploy/docker-compose.local.yml"
APP_PORT="${APP_PORT:-9279}"
KEEP_RUNNING=1
COMPOSE_BIN=""

if [[ "${1:-}" == "--down" ]]; then
    KEEP_RUNNING=0
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

echo "[1/5] 构建镜像"
${COMPOSE_BIN} -f "${COMPOSE_FILE}" build

echo "[2/5] 启动服务"
${COMPOSE_BIN} -f "${COMPOSE_FILE}" up -d

echo "[3/5] 等待服务就绪"
ready=0
for _ in $(seq 1 90); do
    if curl -fsS "http://127.0.0.1:${APP_PORT}/log-lottery/" >/dev/null 2>&1 \
      && curl -fsS "http://127.0.0.1:${APP_PORT}/admin/login/" >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 2
done

if [[ "${ready}" -ne 1 ]]; then
    echo "服务未在预期时间内就绪，输出最近日志："
    ${COMPOSE_BIN} -f "${COMPOSE_FILE}" ps || true
    ${COMPOSE_BIN} -f "${COMPOSE_FILE}" logs --tail=200 || true
    exit 1
fi

echo "[4/5] 烟雾测试"
login_status="$(curl -sS -o /tmp/log-lottery-login-smoke.json -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -X POST "http://127.0.0.1:${APP_PORT}/api/auth/login" \
  -d '{"username":"docker-smoke-user","password":"wrong-password"}')"
if [[ "${login_status}" != "400" && "${login_status}" != "401" ]]; then
    echo "登录接口状态码异常: ${login_status}"
    cat /tmp/log-lottery-login-smoke.json || true
    exit 1
fi

echo "[5/5] 测试通过"
${COMPOSE_BIN} -f "${COMPOSE_FILE}" ps

if [[ "${KEEP_RUNNING}" -eq 0 ]]; then
    echo "按参数要求停止容器"
    ${COMPOSE_BIN} -f "${COMPOSE_FILE}" down
fi
