#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
RUN_DIR="${ROOT_DIR}/.run"
PID_DIR="${RUN_DIR}/pids"
LOG_DIR="${RUN_DIR}/logs"

BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"

BACKEND_PATTERN='[m]anage.py runserver 127.0.0.1:8000 --noreload'
FRONTEND_PATTERN='[v]ite --host 127.0.0.1 --port 6719 --strictPort'

mkdir -p "${PID_DIR}" "${LOG_DIR}"

usage() {
    cat <<USAGE
用法: $(basename "$0") [start|stop|restart|status]

命令:
  start    启动前端+后端（默认）
  stop     停止前端+后端
  restart  重启前端+后端
  status   查看运行状态
USAGE
}

read_pid_file() {
    local pid_file="$1"
    [[ -f "${pid_file}" ]] || return 1
    local pid
    pid="$(cat "${pid_file}" 2>/dev/null || true)"
    [[ -n "${pid}" ]] || return 1
    printf '%s' "${pid}"
}

find_pid_by_pattern() {
    local pattern="$1"
    pgrep -f "${pattern}" | head -n 1 || true
}

is_pid_running() {
    local pid="$1"
    kill -0 "${pid}" >/dev/null 2>&1
}

ensure_pid_file() {
    local pid_file="$1"
    local pattern="$2"

    local pid=""
    if pid="$(read_pid_file "${pid_file}")" && is_pid_running "${pid}"; then
        printf '%s' "${pid}"
        return 0
    fi

    pid="$(find_pid_by_pattern "${pattern}")"
    if [[ -n "${pid}" ]] && is_pid_running "${pid}"; then
        echo "${pid}" > "${pid_file}"
        printf '%s' "${pid}"
        return 0
    fi

    rm -f "${pid_file}"
    return 1
}

start_backend() {
    local pid=""
    if pid="$(ensure_pid_file "${BACKEND_PID_FILE}" "${BACKEND_PATTERN}" 2>/dev/null)"; then
        echo "[backend] 已在运行 (PID: ${pid})"
        return 0
    fi

    if [[ ! -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
        echo "[backend] 未找到虚拟环境: ${BACKEND_DIR}/.venv"
        echo "请先执行: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        return 1
    fi

    (
        cd "${BACKEND_DIR}"
        # 加载环境变量（若存在）
        if [[ -f ".env" ]]; then
            set -a
            # shellcheck disable=SC1091
            source .env
            set +a
        fi

        if command -v pg_isready >/dev/null 2>&1; then
            db_host="${DB_HOST:-127.0.0.1}"
            db_port="${DB_PORT:-5432}"
            db_name="${DB_NAME:-post-choujiang}"
            db_user="${DB_USER:-post-choujiang}"
            if ! pg_isready -h "${db_host}" -p "${db_port}" -U "${db_user}" -d "${db_name}" >/dev/null 2>&1; then
                echo "[backend] PostgreSQL 未就绪: ${db_host}:${db_port}/${db_name} (user=${db_user})"
                exit 1
            fi
        fi

        source .venv/bin/activate
        nohup python manage.py runserver 127.0.0.1:8000 --noreload > "${LOG_DIR}/backend.log" 2>&1 &
        echo $! > "${BACKEND_PID_FILE}"
    )

    sleep 1
    if pid="$(ensure_pid_file "${BACKEND_PID_FILE}" "${BACKEND_PATTERN}" 2>/dev/null)"; then
        echo "[backend] 启动成功 (PID: ${pid})"
    else
        echo "[backend] 启动失败，请查看日志: ${LOG_DIR}/backend.log"
        tail -n 20 "${LOG_DIR}/backend.log" 2>/dev/null || true
        return 1
    fi
}

start_frontend() {
    local pid=""
    if pid="$(ensure_pid_file "${FRONTEND_PID_FILE}" "${FRONTEND_PATTERN}" 2>/dev/null)"; then
        echo "[frontend] 已在运行 (PID: ${pid})"
        return 0
    fi

    if ! command -v pnpm >/dev/null 2>&1; then
        echo "[frontend] 未找到 pnpm，请先安装 pnpm"
        return 1
    fi

    (
        cd "${ROOT_DIR}"
        nohup pnpm exec vite --host 127.0.0.1 --port 6719 --strictPort > "${LOG_DIR}/frontend.log" 2>&1 &
        echo $! > "${FRONTEND_PID_FILE}"
    )

    sleep 1
    if pid="$(ensure_pid_file "${FRONTEND_PID_FILE}" "${FRONTEND_PATTERN}" 2>/dev/null)"; then
        echo "[frontend] 启动成功 (PID: ${pid})"
    else
        echo "[frontend] 启动失败，请查看日志: ${LOG_DIR}/frontend.log"
        tail -n 20 "${LOG_DIR}/frontend.log" 2>/dev/null || true
        return 1
    fi
}

stop_by_file() {
    local name="$1"
    local pid_file="$2"
    local pattern="$3"

    local pid=""
    if pid="$(ensure_pid_file "${pid_file}" "${pattern}" 2>/dev/null)"; then
        echo "[${name}] 停止中 (PID: ${pid})"
        kill "${pid}" >/dev/null 2>&1 || true
        sleep 1
        if is_pid_running "${pid}"; then
            kill -9 "${pid}" >/dev/null 2>&1 || true
        fi
        rm -f "${pid_file}"
        echo "[${name}] 已停止"
    else
        echo "[${name}] 未运行"
    fi
}

status_one() {
    local name="$1"
    local pid_file="$2"
    local pattern="$3"

    local pid=""
    if pid="$(ensure_pid_file "${pid_file}" "${pattern}" 2>/dev/null)"; then
        echo "[${name}] 运行中 (PID: ${pid})"
    else
        echo "[${name}] 未运行"
    fi
}

show_urls() {
    cat <<INFO

访问地址:
- 后端 API:  http://127.0.0.1:8000/api/
- 后台管理:  http://127.0.0.1:8000/admin/
- 前端页面:  http://localhost:6719/log-lottery/

日志文件:
- ${LOG_DIR}/backend.log
- ${LOG_DIR}/frontend.log
INFO
}

cmd="${1:-start}"
case "${cmd}" in
    start)
        start_rc=0
        if ! start_backend; then
            start_rc=1
        fi
        if ! start_frontend; then
            start_rc=1
        fi
        show_urls
        exit "${start_rc}"
        ;;
    stop)
        stop_by_file "frontend" "${FRONTEND_PID_FILE}" "${FRONTEND_PATTERN}"
        stop_by_file "backend" "${BACKEND_PID_FILE}" "${BACKEND_PATTERN}"
        ;;
    restart)
        "$0" stop
        "$0" start
        ;;
    status)
        status_one "backend" "${BACKEND_PID_FILE}" "${BACKEND_PATTERN}"
        status_one "frontend" "${FRONTEND_PID_FILE}" "${FRONTEND_PATTERN}"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
