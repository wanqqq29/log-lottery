# 抽奖系统使用文档（测试 + 截图）

更新时间：2026-03-06  
项目路径：`/home/aris/codeX/log-lottery`

## 1. 文档目标

本文件用于指导你从零完成以下工作：

1. 启动前后端服务。
2. 执行基础回归验证。
3. 自动生成前端业务流程截图。
4. 自动生成 Django Admin 管理页面截图。

## 2. 前置要求

1. 操作系统可用 `zsh/bash` 终端。
2. 已安装：
`python3`、`pnpm`、`google-chrome-stable`、`PostgreSQL`。
3. 数据库配置文件存在：
`backend/.env`。

## 3. 首次安装

1. 安装后端依赖：

```bash
cd /home/aris/codeX/log-lottery/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 安装前端依赖：

```bash
cd /home/aris/codeX/log-lottery
pnpm install
```

## 4. 启动与停止

1. 一键启动：

```bash
cd /home/aris/codeX/log-lottery
./scripts/start_all.sh start
```

2. 访问地址：
前端：`http://127.0.0.1:6719/log-lottery/`  
后端 API：`http://127.0.0.1:8000/api/`  
Admin：`http://127.0.0.1:8000/admin/`

3. 一键停止：

```bash
./scripts/start_all.sh stop
```

## 5. 回归验证（建议每次改动后执行）

1. 后端检查：

```bash
cd /home/aris/codeX/log-lottery/backend
source .venv/bin/activate
python manage.py check
python manage.py showmigrations accounts lottery
python manage.py test apps.lottery.tests.test_api_permissions apps.lottery.tests.test_admin_isolation -v 2
```

2. 前端检查：

```bash
cd /home/aris/codeX/log-lottery
pnpm run test -- --run
pnpm run build
```

## 6. 自动生成前端流程截图

1. 确保服务已启动（第 4 节）。
2. 执行命令：

```bash
cd /home/aris/codeX/log-lottery
node scripts/capture_realtime_flow_screenshots.mjs
```

3. 输出目录：
`docs/screenshots/2026-03-06-realtime`

4. 生成内容：
登录页、项目选择、首页、抽奖准备、抽奖中、抽奖结果、人员配置、中奖人员、奖项配置、排除规则、导出任务、界面配置、图片管理、音乐管理、Admin登录页。

## 7. 自动生成 Admin 管理页截图

1. 确保后端已启动（第 4 节）。
2. 执行命令：

```bash
cd /home/aris/codeX/log-lottery
node scripts/capture_admin_management_screenshots.mjs
```

3. 输出目录：
`docs/screenshots/2026-03-06-admin`

4. 生成内容：
Admin 登录页、后台首页、部门、管理员账号、项目、项目成员、客户、奖项、抽奖批次、中奖记录、排除规则、导出任务。

## 8. 关键文件清单

1. 流程文档（详细版）：
`docs/TEST_FLOW_STEP_BY_STEP_2026-03-06.md`
2. 使用文档（本文件）：
`docs/USAGE_GUIDE_2026-03-06.md`
3. 前端截图脚本：
`scripts/capture_realtime_flow_screenshots.mjs`
4. Admin截图脚本：
`scripts/capture_admin_management_screenshots.mjs`

## 9. 常见问题

1. 前端无法访问 `127.0.0.1:6719`：
检查 `./scripts/start_all.sh status` 与 `.run/logs/frontend.log`。

2. 后端无法访问 `127.0.0.1:8000`：
检查 PostgreSQL 是否启动，确认 `backend/.env` 数据库参数正确。

3. 截图脚本失败：
先确认服务在线，再重新执行脚本；若端口冲突，先停止已有进程再启动。

