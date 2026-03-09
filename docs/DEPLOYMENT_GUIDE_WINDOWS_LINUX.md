# log-lottery 部署指南（Windows + Linux）

## 1. 适用范围

本文档适用于当前仓库版本（前端 Vue + 后端 Django + PostgreSQL），覆盖：

- Windows 生产部署
- Linux 生产部署
- 版本基线与依赖策略
- 常见坑与排障

默认部署拓扑：

- 前端静态资源由 Nginx 提供（路径前缀 `/log-lottery/`）
- 后端 Django API 运行在 `127.0.0.1:8000`
- PostgreSQL 独立运行

---

## 2. 版本基线（建议）

### 2.1 前端运行时

- Node.js：`>=22`（见 `package.json` engines）
- pnpm：建议 `10.26.1`（见 `packageManager`）

建议：

- 使用 `corepack` 固定 pnpm 版本，避免不同机器构建产物不一致。

### 2.2 后端运行时

- Python：建议 `3.11` 或 `3.12`（Windows/LTS 更稳）
- Django：`5.2.2`
- djangorestframework：`3.16.0`
- psycopg[binary]：`3.2.10`
- PostgreSQL：建议 `14/15/16`

说明：

- 当前 `backend/requirements.txt` 已是精确版本钉死（`==`）。
- 若未来升级依赖，必须先在测试环境完成迁移和回归再上线。

---

## 3. 部署前检查

1. 确认数据库可访问（主机、端口、账号密码）。
2. 确认后端 `.env` 已配置（`DJANGO_SECRET_KEY`、`DJANGO_ALLOWED_HOSTS`、`DB_*`）。
3. 确认前端会部署在 `/log-lottery/` 前缀下。
4. 确认服务器时区（建议 `Asia/Shanghai`，与项目设置一致）。
5. 确认文件写权限：`backend/exports` 可写（CSV 导出依赖）。

---

## 4. 环境变量说明（后端）

文件：`backend/.env`

至少需要：

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

生产建议：

- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS` 写真实域名/IP，逗号分隔
- `DJANGO_SECRET_KEY` 使用高强度随机值

---

## 5. Linux 部署路线（推荐 Ubuntu 22.04+）

### 5.1 安装系统依赖

```bash
sudo apt update
sudo apt install -y git curl nginx postgresql postgresql-contrib python3.11 python3.11-venv python3-pip
```

### 5.2 拉取代码并构建前端

```bash
cd /opt
sudo git clone <你的仓库地址> log-lottery
cd /opt/log-lottery
sudo corepack enable
sudo corepack prepare pnpm@10.26.1 --activate
pnpm install
pnpm build
```

### 5.3 配置后端

```bash
cd /opt/log-lottery/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env` 后执行：

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py check
```

### 5.4 使用 Gunicorn + systemd 运行 Django

安装 Gunicorn：

```bash
source /opt/log-lottery/backend/.venv/bin/activate
pip install gunicorn
```

创建 `/etc/systemd/system/log-lottery-backend.service`：

```ini
[Unit]
Description=log-lottery Django backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/log-lottery/backend
Environment="PATH=/opt/log-lottery/backend/.venv/bin"
ExecStart=/opt/log-lottery/backend/.venv/bin/gunicorn lottery_backend.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now log-lottery-backend
sudo systemctl status log-lottery-backend
```

### 5.5 配置 Nginx

创建 `/etc/nginx/sites-available/log-lottery.conf`：

```nginx
server {
    listen 80;
    server_name _;

    location = / {
        return 301 /log-lottery/;
    }

    location /log-lottery/ {
        alias /opt/log-lottery/dist/;
        index index.html;
        try_files $uri $uri/ /log-lottery/index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用并重载：

```bash
sudo ln -s /etc/nginx/sites-available/log-lottery.conf /etc/nginx/sites-enabled/log-lottery.conf
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. Windows 部署路线（Server 2019/2022）

### 6.1 安装依赖

1. 安装 Node.js 22+
2. 安装 Git
3. 安装 Python 3.11/3.12（勾选 Add to PATH）
4. 安装 PostgreSQL
5. 安装 Nginx for Windows（或 IIS 反代）

### 6.2 拉取代码并构建前端（PowerShell）

```powershell
cd D:\apps
git clone <你的仓库地址> log-lottery
cd D:\apps\log-lottery
corepack enable
corepack prepare pnpm@10.26.1 --activate
pnpm install
pnpm build
```

### 6.3 配置后端（PowerShell）

```powershell
cd D:\apps\log-lottery\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env` 后执行：

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py check
```

### 6.4 运行 Django（Windows 推荐 Waitress）

```powershell
.\.venv\Scripts\Activate.ps1
pip install waitress
waitress-serve --listen=127.0.0.1:8000 lottery_backend.wsgi:application
```

生产建议：

- 使用 NSSM/WinSW 将 Waitress 注册为 Windows 服务，避免窗口关闭进程退出。

### 6.5 Nginx（Windows）反向代理示例

```nginx
server {
    listen 80;
    server_name localhost;

    location = / {
        return 301 /log-lottery/;
    }

    location /log-lottery/ {
        alias D:/apps/log-lottery/dist/;
        index index.html;
        try_files $uri $uri/ /log-lottery/index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 7. Windows / Linux 关键差异

1. 进程托管
- Linux：`systemd + gunicorn`。
- Windows：`NSSM + waitress` 更直接。

2. 路径与权限
- Linux：关注目录属主和 `exports` 写权限。
- Windows：关注盘符路径、反斜杠与服务账号权限。

3. Python 扩展包兼容
- `psycopg[binary]` 依赖预编译 wheel。
- 新版 Python 在 Windows 上可能出现 wheel 滞后，优先用 3.11/3.12。

4. 日志查看方式
- Linux：`journalctl -u 服务名 -f`。
- Windows：服务管理器 + 应用日志 + 自定义文件日志。

---

## 8. 依赖版本策略（requirements / lock）

当前状态：

- 后端 `requirements.txt` 为精确版本（`==`）。
- 前端由 `pnpm-lock.yaml` 锁依赖树。

建议策略：

1. 生产部署严格使用 lock/pin，不做线上临时升级。
2. 升级流程：开发环境升级 -> 测试环境迁移回归 -> 生产灰度。
3. Python 小版本升级时，先验证 `psycopg[binary]` 兼容性。
4. Node 升级时，先执行 `pnpm build` 与关键流程回归。

---

## 9. 升级发布流程（推荐）

1. 备份 PostgreSQL 数据库。
2. 拉取新代码并检查变更（尤其迁移文件）。
3. 后端执行 `python manage.py migrate`。
4. 前端重新 `pnpm build` 并替换 `dist`。
5. 重启后端服务，重载 Nginx。
6. 执行上线验收。

---

## 10. 上线验收清单

1. `GET /admin/` 可打开登录页。
2. 前端 `http(s)://host/log-lottery/` 可访问。
3. 登录后可选择项目。
4. 到访登记页面可登记手机号领奖。
5. 到访导出页面可导出“已到访领奖/未到访领奖”。
6. 运营看板可看到“近14天到访趋势”。
7. 只读角色可登记到访领奖，但不能执行其他写操作。
8. CSV 导出文件可正常下载。

---

## 11. 常见问题排查

1. 页面刷新 404
- 原因：Nginx 未配置 `try_files ... /log-lottery/index.html`。

2. 前端能打开但 API 全 401/403
- 检查登录 token 是否有效。
- 检查请求头 `X-Project-Id` 与当前项目是否一致。
- 检查账号角色与部门权限边界。

3. 导出失败
- 检查 `backend/exports` 目录写权限。
- 检查磁盘空间。

4. `Invalid HTTP_HOST header`
- 检查 `DJANGO_ALLOWED_HOSTS` 是否包含访问域名/IP。

5. PostgreSQL 连接失败
- 检查 `DB_*` 配置。
- 检查数据库监听地址、防火墙和 pg_hba.conf。

---

## 12. 安全建议（生产）

1. 使用 HTTPS（Nginx 配置证书）。
2. `DJANGO_DEBUG=false`。
3. 管理员密码强度和定期轮换。
4. 数据库最小权限原则。
5. 定期备份数据库与导出目录。
6. 限制服务器对公网暴露端口，仅开放必要端口。
