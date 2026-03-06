# 抽奖系统给非技术同事的使用手册（超详细版）

更新时间：2026-03-06  
适用目录：`/home/aris/codeX/log-lottery`

---

## 0. 这份手册能帮你做什么

按本手册操作，你可以完成 4 件事：

1. 启动系统（前端页面 + 后端服务）。
2. 正常使用抽奖系统（登录、选项目、抽奖、看配置页）。
3. 自动生成前端流程截图。
4. 自动生成 Admin（后台管理）页面截图。

你不需要会编程，只需要“复制命令并回车”。

---

## 1. 先记住这 4 条

1. **每条命令都可以直接复制粘贴。**
2. **一次只执行一条命令**，不要把多条粘一起。
3. 如果看到报错，不要慌，先看本手册“常见问题”部分。
4. 你的所有操作都在这个目录里完成：  
`/home/aris/codeX/log-lottery`

---

## 2. 第一次使用前准备（只做一次）

> 如果你以前已经成功运行过本系统，可以跳到第 3 节。

### 步骤 2.1：打开终端

1. 在电脑上打开“终端（Terminal）”。
2. 看到一个可以输入命令的黑/白窗口即可。

### 步骤 2.2：进入项目目录

复制下面命令，粘贴到终端，按回车：

```bash
cd /home/aris/codeX/log-lottery
```

### 步骤 2.3：安装前端依赖

```bash
pnpm install
```

说明：
第一次安装会比较慢（几分钟）。
看到命令执行结束并回到可输入状态即可。

### 步骤 2.4：安装后端依赖

```bash
cd /home/aris/codeX/log-lottery/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd /home/aris/codeX/log-lottery
```

说明：
这些命令是“准备后端环境”，通常只需首次执行。

---

## 3. 日常启动（每次使用都要做）

### 步骤 3.1：进入项目目录

```bash
cd /home/aris/codeX/log-lottery
```

### 步骤 3.2：启动系统

```bash
./scripts/start_all.sh start
```

### 步骤 3.3：判断是否启动成功

启动成功时，终端会看到类似信息：

1. `后端 API:  http://127.0.0.1:8000/api/`
2. `后台管理:  http://127.0.0.1:8000/admin/`
3. `前端页面:  http://localhost:6719/log-lottery/`

### 步骤 3.4：打开页面

1. 前端抽奖页面：  
`http://127.0.0.1:6719/log-lottery/`
2. Admin后台页面：  
`http://127.0.0.1:8000/admin/`

---

## 4. 前端系统怎么用（业务同事看这个）

### 步骤 4.1：登录

在登录页输入账号密码后点击“登录”。

示例图：  
`docs/screenshots/2026-03-06-realtime/01-login.png`

### 步骤 4.2：选择项目

登录后会看到“选择抽奖项目”页面，点击对应项目行的“进入项目”。

示例图：  
`docs/screenshots/2026-03-06-realtime/02-project-select.png`

### 步骤 4.3：进入抽奖

进入首页后，先点击 `Enter Lottery`，再点击 `Start` 开始抽奖，再点击 `Draw the Lucky` 出结果。

示例图：

1. 首页：`docs/screenshots/2026-03-06-realtime/03-home.png`
2. 抽奖准备：`docs/screenshots/2026-03-06-realtime/04-ready-start.png`
3. 抽奖进行中：`docs/screenshots/2026-03-06-realtime/05-draw-running.png`
4. 抽奖结果：`docs/screenshots/2026-03-06-realtime/06-draw-result.png`

### 步骤 4.4：配置页面入口（常用）

1. 人员配置：`07-config-person-all.png`
2. 中奖人员：`08-config-person-already.png`
3. 奖项配置：`09-config-prize.png`
4. 排除规则：`10-config-exclusion-rules.png`
5. 导出任务：`11-config-export-jobs.png`
6. 界面配置：`12-config-global-face.png`
7. 图片管理：`13-config-global-image.png`
8. 音乐管理：`14-config-global-music.png`

所在目录：`docs/screenshots/2026-03-06-realtime`

---

## 5. 一键生成“前端流程截图”

> 用于写汇报、流程说明、培训材料。

### 步骤 5.1：先确保系统已经启动

如果不确定，先执行：

```bash
cd /home/aris/codeX/log-lottery
./scripts/start_all.sh status
```

如果显示 `backend 运行中`、`frontend 运行中`，就可以继续。

### 步骤 5.2：执行截图命令

```bash
cd /home/aris/codeX/log-lottery
node scripts/capture_realtime_flow_screenshots.mjs
```

### 步骤 5.3：查看截图结果

生成目录：

`/home/aris/codeX/log-lottery/docs/screenshots/2026-03-06-realtime`

这批图包含完整流程（登录、选项目、抽奖、配置页、admin登录页）。

---

## 6. 一键生成“Admin管理页截图”

> 用于后台管理流程汇报、权限审计留档。

### 步骤 6.1：先确保后端已启动

```bash
cd /home/aris/codeX/log-lottery
./scripts/start_all.sh status
```

### 步骤 6.2：执行 Admin 截图命令

```bash
cd /home/aris/codeX/log-lottery
node scripts/capture_admin_management_screenshots.mjs
```

### 步骤 6.3：查看截图结果

生成目录：

`/home/aris/codeX/log-lottery/docs/screenshots/2026-03-06-admin`

包含 12 张图：

1. admin登录页
2. admin首页
3. 部门列表
4. 管理员账号列表
5. 项目列表
6. 项目成员列表
7. 客户列表
8. 奖项列表
9. 抽奖批次列表
10. 中奖记录列表
11. 排除规则列表
12. 导出任务列表

---

## 7. 账号信息（测试环境）

前端/后台可用测试账号：

1. 用户名：`qa_operator`
2. 密码：`Qa123456!`

---

## 8. 用完后如何关闭

```bash
cd /home/aris/codeX/log-lottery
./scripts/start_all.sh stop
```

看到“已停止”即表示关闭完成。

---

## 9. 常见问题（按这个顺序排查）

### 问题 1：页面打不开（127.0.0.1 连不上）

处理步骤：

1. 先看状态：

```bash
cd /home/aris/codeX/log-lottery
./scripts/start_all.sh status
```

2. 如果显示“未运行”，执行启动：

```bash
./scripts/start_all.sh start
```

3. 还不行就重启：

```bash
./scripts/start_all.sh restart
```

### 问题 2：后端启动失败（数据库相关）

常见现象：提示 PostgreSQL 未就绪。

处理建议：

1. 确认数据库服务是否启动。
2. 确认文件 `backend/.env` 中数据库参数正确。

### 问题 3：截图脚本报错

处理步骤：

1. 先执行 `./scripts/start_all.sh status` 看服务是否在线。
2. 在线后重新执行截图脚本。
3. 如果依然失败，先 `restart` 再重试。

### 问题 4：不知道错误信息发给谁

请把下面 2 个日志文件一起发给技术同事：

1. `/home/aris/codeX/log-lottery/.run/logs/backend.log`
2. `/home/aris/codeX/log-lottery/.run/logs/frontend.log`

---

## 10. 最短操作清单（给日常使用）

1. 启动：
`./scripts/start_all.sh start`
2. 用前端：
打开 `http://127.0.0.1:6719/log-lottery/`
3. 生成前端截图：
`node scripts/capture_realtime_flow_screenshots.mjs`
4. 生成admin截图：
`node scripts/capture_admin_management_screenshots.mjs`
5. 关闭：
`./scripts/start_all.sh stop`

