# 下一次会话行动路线图（项目制抽奖后端化）

更新时间：2026-02-27

## 0. 会话入口索引

建议按以下顺序阅读并执行：

1. `docs/REQUIREMENTS_PROGRESS_2026-02-27.md`（需求与完成度对账）
2. `docs/DETAILED_EXECUTION_ROADMAP_2026-02-27.md`（细化执行路线）
3. 本文档（当前会话快速操作指引）

## 1. 当前状态（已完成）

1. 后端 Django + PostgreSQL 主体已落地，核心模型与迁移已存在并已可执行。
2. 登录 -> 选项目 -> 进入业务页面的前端链路已上线。
3. 前端请求已自动携带 `Authorization: Bearer <token>` 与 `X-Project-Id`。
4. 后端已加项目隔离校验（请求头项目与请求体项目一致性检查）。
5. 首页抽奖主流程已改为后端驱动（预抽、确认、作废）。

## 2. 当前未提交改动（需要先收口验证）

后端以下文件处于进行中状态：

- `backend/apps/lottery/services/draw_service.py`
- `backend/apps/lottery/serializers.py`
- `backend/apps/lottery/views.py`
- `backend/apps/lottery/urls.py`

这些改动目标是补齐：

1. 中奖记录查询与撤销（`draw-winners`）。
2. 项目级中奖结果重置（`draw-winners/reset-project`）。
3. 项目成员清空（`project-members/clear-project`，并联动清空中奖状态）。

## 3. 下一步执行顺序（严格按顺序）

### Step A：先收口后端接口并做数据库级验证

1. 语法与配置检查

```bash
cd /home/aris/codeX/log-lottery/backend
python manage.py check
python manage.py makemigrations --check --dry-run
```

2. 数据库连通与迁移状态复核（PostgreSQL）

```bash
cd /home/aris/codeX/log-lottery/backend
python manage.py showmigrations accounts lottery
python manage.py migrate
```

3. API 冒烟（重点验证数据变更准确性）

- 登录拿 token。
- 带 `X-Project-Id` 请求：
  - `GET /api/draw-winners/?project_id=<id>&status=CONFIRMED`
  - `POST /api/draw-winners/<winner_id>/revoke/`
  - `POST /api/draw-winners/reset-project/`
  - `POST /api/project-members/clear-project/`
- 校验点：
  - 撤销后对应 `prize.used_count` 正确回退。
  - reset 后项目内 `PENDING/CONFIRMED` 赢家应被置为 `VOID`。
  - reset 后所有奖项 `used_count` 与已确认中奖记录数一致。
  - clear-project 后项目成员数为 0，且中奖状态已同步清理。

### Step B：迁移“人员配置页”到后端

目标文件：

- `src/views/Config/Person/PersonAll/useViewModel.ts`

改造要求：

1. 去掉对本地 `personConfig` 作为真数据源的依赖（可以保留 UI 映射层）。
2. 全量改为后端 API：
   - 成员列表：`GET /project-members/`
   - 批量导入：`POST /project-members/bulk-upsert/`
   - 单人新增：`POST /project-members/`
   - 单人删除：`DELETE /project-members/{id}/`
   - 重置中奖：`POST /draw-winners/reset-project/`
   - 清空项目：`POST /project-members/clear-project/`
3. Excel 导入逻辑保留，但导入结果改为提交后端批量 upsert。

### Step C：迁移“已中奖人员页”到后端

目标文件：

- `src/views/Config/Person/PersonAlready/useViewModel.ts`

改造要求：

1. 数据源改为 `GET /draw-winners/?status=CONFIRMED`。
2. 同时支持：
   - 汇总视图（按手机号聚合）
   - 明细视图（每条中奖记录）
3. 删除动作改为后端撤销：
   - 明细删除：撤销单条 `winner_id`
   - 汇总删除：按手机号撤销该手机号全部 confirmed 记录

### Step D：迁移“奖项配置页”到后端

目标文件：

- `src/views/Config/Prize/usePrizeConfig.ts`

改造要求：

1. 改为后端 CRUD：
   - 列表：`GET /prizes/`
   - 新增：`POST /prizes/`
   - 编辑：`PATCH /prizes/{id}/`
   - 删除：`DELETE /prizes/{id}/`
2. 字段映射：
   - `count <-> total_count`
   - `isUsedCount <-> used_count`
   - `isAll <-> is_all`
   - `desc <-> description`
3. `picture` 字段若后端无对应，项目模式下禁用或仅做前端临时字段，不参与后端写入。

### Step E：一致性和回归

1. 确保所有请求都自动带 `token + X-Project-Id`。
2. 首页、配置页、导出页全部基于当前选中项目。
3. 对“抽奖范围内若抽到不合规人员则作废重抽”的场景：
   - 使用 `scope` + 撤销 + 重新 preview/confirm 组合实现。
4. 运行前端构建与基础检查：

```bash
cd /home/aris/codeX/log-lottery
pnpm run build
```

### Step F：跨项目互动规则（排除规则）闭环

目标：

1. 支持“项目 B 排除项目 A 已中奖手机号”。
2. 支持“项目 B 仅对某奖项排除项目 A 的某奖项中奖手机号”（指定奖项自由组合）。

执行项：

1. 后端确认并验证 `exclusion-rules` 的 CRUD 与权限校验（目标项目与请求头项目一致）。
2. 前端配置页补充规则管理入口（至少支持列表、新增、启停、删除）。
3. 冒烟验证两类规则：
   - `target_prize = null`：排除目标项目所有奖项抽奖。
   - `target_prize != null`：仅排除目标项目指定奖项抽奖。
4. 校验“多轮作废重抽”可用：当命中不合规人群时，允许撤销并再次 preview/confirm 直到命中合规名单。

### Step G：导出、项目管理、后台用户隔离闭环

执行项：

1. 导出链路验证：
   - `POST /api/export-jobs/` 创建导出任务
   - `GET /api/export-jobs/{id}/download/` 下载结果
   - 校验导出内容与数据库中奖记录一致
2. 项目管理链路验证：
   - 项目创建、编辑、列表按部门权限隔离
   - 进入业务前必须先登录再选项目
3. 后台用户隔离验证：
   - 不同部门账号无法访问非本部门项目数据
   - 超级管理员可跨部门查看
4. 安全验证：
   - 仅携带项目 ID、未携带合法 token 时必须被拒绝
   - token 正确但 `X-Project-Id` 与请求体 `project_id` 不一致时必须 403

## 4. 关键业务口径（必须遵守）

1. 只有一个公司主体；隔离维度是“部门（不同区域）”。
2. 手机号全平台唯一，可视为自然人唯一标识。
3. 不新建“团体”字段，项目内名单即团体范围。
4. 不引入 Redis 等额外部署依赖。
5. 迁移文件尽量通过 `makemigrations` 生成，不手写迁移。
6. 数据库连接以 `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` 为优先环境变量来源。

## 5. 本次会话结束前建议提交策略

1. 第一提交：仅后端收口 + 后端冒烟通过。
2. 第二提交：PersonAll/PersonAlready 迁移。
3. 第三提交：Prize 配置迁移 + 前端回归。
4. 每次提交都附带“已验证命令”和“影响范围”。

## 6. 快速定位命令

```bash
cd /home/aris/codeX/log-lottery

git status --short
rg "draw-winners|clear-project|reset-project" backend/apps/lottery -n
rg "personConfig|prizeConfig|apiPrizeList|apiProjectMemberList" src/views/Config -n
```
