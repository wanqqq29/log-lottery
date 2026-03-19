# 生产部署材料（Linux）

本目录提供可直接复用的生产模板：

- `nginx/log-lottery.conf`：Nginx 反向代理（前端 + Django API）
- `nginx/log-lottery.conf`：已包含 Django `"/static/"` 静态文件映射
- `systemd/log-lottery-backend.service`：Django/Gunicorn 服务
- `env/backend.env.production.example`：后端生产环境变量模板

## Docker 低配部署（推荐）

新增文件：

- `docker-compose.local.yml`：本地构建+联调（包含构建指令）
- `docker-compose.server.yml`：服务器启动（仅使用已加载镜像，不在服务器构建）
- `docker/backend/Dockerfile` + `docker/backend/entrypoint.sh`：Django 容器
- `docker/nginx/Dockerfile` + `docker/nginx/default.conf`：前端+反代容器
- `env/backend.env`：Docker 默认后端参数（当前已配置外部 PG：`172.18.0.3:5432/xfcj`）

详细步骤见：`docs/DEPLOYMENT_MATERIALS_2026-03-12.md`。
