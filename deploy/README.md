# 生产部署材料（Linux）

本目录提供可直接复用的生产模板：

- `nginx/log-lottery.conf`：Nginx 反向代理（前端 + Django API + `/api/user-msg` + WebSocket）
- `nginx/log-lottery.conf`：已包含 Django `"/static/"` 静态文件映射
- `systemd/log-lottery-backend.service`：Django/Gunicorn 服务
- `systemd/log-lottery-ws.service`：Rust `ws_server` 服务
- `env/backend.env.production.example`：后端生产环境变量模板

详细步骤见：`docs/DEPLOYMENT_MATERIALS_2026-03-12.md`。
