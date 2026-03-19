# log-lottery 生产部署材料（2026-03-12）

> 说明（2026-03-19）：WebSocket/弹幕服务已下线，本文件中涉及 `ws_server`、`/echo`、`/api/user-msg` 的章节为历史内容，可忽略。

本次已在仓库内准备好可直接落地的部署材料，面向 Linux + Nginx + systemd。

## 1. 已准备文件

- `deploy/nginx/log-lottery.conf`
- `deploy/systemd/log-lottery-backend.service`
- `deploy/systemd/log-lottery-ws.service`
- `deploy/env/backend.env.production.example`

## 2. 推荐部署拓扑

- 前端静态资源：`/opt/log-lottery/dist`
- Django（Gunicorn）：`127.0.0.1:8000`
- Rust `ws_server`：`127.0.0.1:8080`
- Nginx 对外统一入口：`80/443`

关键路由：

- `/log-lottery/` -> 前端静态资源
- `/static/` -> Django collectstatic 产物（admin/simpleui）
- `/api/` -> Django
- `/admin/` -> Django Admin
- `/api/user-msg` -> `ws_server` HTTP 接口
- `/echo` -> `ws_server` WebSocket

## 3. 上线步骤

### 3.1 构建前端

```bash
cd /opt/log-lottery
corepack enable
corepack prepare pnpm@10.26.1 --activate
pnpm install --frozen-lockfile
pnpm build
```

### 3.2 配置后端 Python 环境

```bash
cd /opt/log-lottery/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
cp /opt/log-lottery/deploy/env/backend.env.production.example /opt/log-lottery/backend/.env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py check
```

### 3.3 构建 ws_server

```bash
cd /opt/log-lottery/ws_server
cargo build --release
```

### 3.4 安装 systemd 服务

```bash
sudo cp /opt/log-lottery/deploy/systemd/log-lottery-backend.service /etc/systemd/system/
sudo cp /opt/log-lottery/deploy/systemd/log-lottery-ws.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now log-lottery-backend
sudo systemctl enable --now log-lottery-ws
sudo systemctl status log-lottery-backend --no-pager
sudo systemctl status log-lottery-ws --no-pager
```

### 3.5 安装 Nginx 配置

```bash
sudo cp /opt/log-lottery/deploy/nginx/log-lottery.conf /etc/nginx/sites-available/log-lottery.conf
sudo ln -sf /etc/nginx/sites-available/log-lottery.conf /etc/nginx/sites-enabled/log-lottery.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 4. 部署后验证

```bash
curl -I http://127.0.0.1/log-lottery/
curl -I http://127.0.0.1/static/admin/css/base.css
curl -I http://127.0.0.1/api/auth/me
curl -I http://127.0.0.1/admin/
sudo journalctl -u log-lottery-backend -n 80 --no-pager
sudo journalctl -u log-lottery-ws -n 80 --no-pager
```

浏览器验证：

- 打开 `http://<你的域名>/log-lottery/`
- 进入“配置 -> 服务配置”，点击连接弹幕服务，确认状态为“已连接”

## 5. 说明

- 前端 WebSocket 连接已改为根据“弹幕服务地址”动态生成，不再固定 `localhost:8080`。
- 如果启用 HTTPS，请在 Nginx 加证书并保持反代到本机 `127.0.0.1`，前端会自动使用 `wss://`。
