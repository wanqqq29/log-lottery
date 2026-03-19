# log-lottery Docker 低配部署说明（2026-03-19）

目标：优先在本地打包镜像并完成烟雾测试，服务器只做镜像加载和启动，不做构建。

## 1. 数据库参数

当前默认已配置为外部 PostgreSQL：

- `DB_NAME=xfcj`
- `DB_USER=xfcj`
- `DB_PASSWORD=xfcj`
- `DB_HOST=172.18.0.3`
- `DB_PORT=5432`

对应文件：`deploy/env/backend.env`

## 2. 本地构建并联调

```bash
# 在仓库根目录执行
bash scripts/docker_local_build_test.sh
```

如需测试后自动停容器：

```bash
bash scripts/docker_local_build_test.sh --down
```

默认访问地址：`http://127.0.0.1:9279/log-lottery/`

上线前建议至少调整：

- `deploy/env/backend.env` 中 `DJANGO_SECRET_KEY`
- `deploy/env/backend.env` 中 `DJANGO_ALLOWED_HOSTS`（改成你的域名/IP）

## 3. 导出镜像包

```bash
bash scripts/docker_export_images.sh
```

脚本会输出镜像包路径，例如：`/tmp/log-lottery-images-20260319-220000.tar.gz`。

## 4. 传输到服务器并启动

```bash
scp /tmp/log-lottery-images-*.tar.gz <user>@<server-ip>:/opt/log-lottery/
```

服务器上执行：

```bash
cd /opt/log-lottery
bash scripts/docker_server_load_and_up.sh /opt/log-lottery/log-lottery-images-20260319-220000.tar.gz
```

服务编排文件：`deploy/docker-compose.server.yml`

## 5. 服务器验收

```bash
curl -I http://127.0.0.1:9279/log-lottery/
curl -I http://127.0.0.1:9279/admin/login/
```

## 6. 资源建议（低配机器）

- Gunicorn：`1 worker + 2 threads`（已写入 `deploy/env/backend.env`）
- 所有容器日志滚动：`max-size=10m`、`max-file=3`（已在 compose 中配置）
- 数据库使用外部实例，避免在同机额外启动 PostgreSQL 容器
