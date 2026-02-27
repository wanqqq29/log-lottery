# 细化执行路线（2026-02-27）

## 当前执行状态

1. 阶段 A：已完成。
2. 阶段 B：已完成。
3. 阶段 C：已完成。
4. 阶段 D：已完成。
5. 阶段 E：后端已具备，前端规则管理 UI 待完成。
6. 阶段 F：后端已具备，前端任务列表与更细权限回归待完成。

## 0. 目标与完成定义

目标：实现“项目制 + 后端驱动 + 强数据一致性”的抽奖系统，前端配置页/抽奖页均以后端为唯一事实来源。

完成定义（DoD）：

1. 登录后必须先选项目，所有业务请求带 token 与 `X-Project-Id`。
2. 配置页（人员、已中奖、奖项）完全由后端 API 驱动，无本地持久化真源。
3. 抽奖结果、撤销、重置、导出都能在 PostgreSQL 中追溯并正确回算。
4. 支持跨项目排除规则并完成端到端验证。
5. 不新增 Redis/Celery 等额外部署依赖。

## 1. 阶段 A：后端在途改动收口（必须优先）

### A1. 代码收口

目标文件：

1. `backend/apps/lottery/services/draw_service.py`
2. `backend/apps/lottery/serializers.py`
3. `backend/apps/lottery/views.py`
4. `backend/apps/lottery/urls.py`

确认点：

1. `DrawWinnerViewSet`：list/retrieve/revoke/reset-project 可用。
2. `ProjectMemberViewSet.clear_project` 可用，并联动重置中奖记录。
3. `revoke_confirmed_winner` 会回退 `prize.used_count`。
4. `reset_project_winners` 会将项目内 `PENDING/CONFIRMED` 置 `VOID`，并重新计算各奖项 `used_count`。

### A2. 本地运行验证

```bash
cd /home/aris/codeX/log-lottery/backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations accounts lottery
python manage.py migrate
```

### A3. 数据一致性冒烟（脚本/手工都可）

必测接口：

1. `POST /api/auth/login`
2. `GET /api/draw-winners/?project_id=<id>&status=CONFIRMED`
3. `POST /api/draw-winners/<winner_id>/revoke/`
4. `POST /api/draw-winners/reset-project/`
5. `POST /api/project-members/clear-project/`

必验数据点：

1. 撤销中奖后，对应奖项 `used_count` 减 1。
2. reset 后项目内 `CONFIRMED/PENDING` 记录不再存在（转 `VOID`）。
3. reset 后每个奖项 `used_count == DrawWinner(CONFIRMED)` 数量。
4. clear-project 后成员数量为 0，中奖状态已联动清理。

## 2. 阶段 B：人员配置页后端化

目标文件：

1. `src/views/Config/Person/PersonAll/useViewModel.ts`
2. `src/api/lottery/index.ts`（补齐成员相关 API）

实施步骤：

1. 新增/补齐 API：
   - `GET /project-members/`
   - `POST /project-members/`
   - `DELETE /project-members/{id}/`
   - `POST /project-members/bulk-upsert/`
   - `POST /project-members/clear-project/`
   - `POST /draw-winners/reset-project/`
2. Excel 导入完成后，不再写本地 store，改为构造 `members` 调用 bulk-upsert。
3. 页面列表刷新统一来自后端查询结果。
4. 删除全部人员按钮改调 `clear-project`。
5. 重置已中奖按钮改调 `reset-project`。

验收：

1. 导入同一手机号重复数据不会创建重复自然人。
2. 增删改后刷新页面，数据与 PostgreSQL 一致。
3. 切换项目后，人员列表隔离正确。

## 3. 阶段 C：已中奖页后端化

目标文件：

1. `src/views/Config/Person/PersonAlready/useViewModel.ts`
2. `src/api/lottery/index.ts`（补齐 winner API）

实施步骤：

1. 列表源改为 `GET /draw-winners/?project_id=<id>&status=CONFIRMED`。
2. 构建两个视图数据：
   - 汇总：按手机号聚合。
   - 明细：每条中奖记录。
3. 删除动作改为撤销：
   - 明细：`POST /draw-winners/{id}/revoke/`
   - 汇总：遍历该手机号所有 winner 记录逐条 revoke。

验收：

1. 撤销后页面数据即时减少。
2. 同时验证对应奖项 `used_count` 实时回退。

## 4. 阶段 D：奖项配置页后端化

目标文件：

1. `src/views/Config/Prize/usePrizeConfig.ts`
2. `src/api/lottery/index.ts`（补齐 prize CRUD API）

实施步骤：

1. 列表：`GET /prizes/?project_id=<id>`。
2. 新增：`POST /prizes/`。
3. 编辑：`PATCH /prizes/{id}/`。
4. 删除：`DELETE /prizes/{id}/`。
5. 前后端字段映射统一：
   - `count -> total_count`
   - `isUsedCount -> used_count`（只读）
   - `isAll -> is_all`
   - `desc -> description`
6. `picture` 保留前端展示字段，不入库。

验收：

1. 奖项增删改刷新后一致。
2. 抽奖后 `used_count` 正确显示且不可被手工篡改。

## 5. 阶段 E：跨项目排除规则闭环

目标文件：

1. `src/api/lottery/index.ts`（补齐 exclusion-rules API）
2. `src/views/Config/...`（新增规则管理 UI）

实施步骤：

1. 接入规则 CRUD：
   - list/create/update/delete。
2. 最小 UI 功能：
   - 规则列表
   - 新增规则
   - 启停规则
   - 删除规则
3. 联调两种规则：
   - 目标项目全部奖项排除来源中奖人。
   - 目标项目指定奖项排除来源中奖人。

验收：

1. 命中排除规则的手机号不会进入候选池。
2. 关闭规则后可恢复参与。

## 6. 阶段 F：导出与权限安全闭环

目标文件：

1. `src/api/lottery/index.ts`（补齐 export-jobs API）
2. 可选新增页面或在已中奖页挂载导出入口

实施步骤：

1. 导出任务创建：`POST /export-jobs/`。
2. 导出任务列表：`GET /export-jobs/?project_id=<id>`。
3. 下载：`GET /export-jobs/{id}/download/`。
4. 权限测试：
   - 无 token：401。
   - token 正确但 `X-Project-Id` 不匹配：403。
   - 非本部门账号访问他部门项目：403。

验收：

1. 导出 CSV 行数与数据库中奖记录一致。
2. 权限边界行为符合预期。

## 7. 阶段 G：最终回归与提交策略

### G1. 回归命令

```bash
cd /home/aris/codeX/log-lottery
pnpm run build

cd /home/aris/codeX/log-lottery/backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
```

### G2. 提交拆分

1. Commit 1：后端收口 + API 冒烟通过。
2. Commit 2：人员页（PersonAll + PersonAlready）后端化。
3. Commit 3：奖项页后端化 + 排除规则 + 导出入口。
4. Commit 4：权限回归与文档更新。

### G3. 每个提交必须附带

1. 变更文件列表。
2. 数据影响说明（是否影响 `used_count`、中奖记录状态）。
3. 已执行命令与关键输出摘要。
