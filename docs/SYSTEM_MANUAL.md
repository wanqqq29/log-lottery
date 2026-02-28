# 抽奖系统说明书

## 1. 文档信息

- 文档名称：项目制抽奖系统说明书
- 适用系统：`log-lottery`
- 版本基线：当前主干代码（Django + PostgreSQL + Vue 抽奖端）
- 更新时间：2026-02-28
- 目标读者：业务运营、部门管理员、系统管理员、开发与运维

## 2. 业务背景与建设目标

### 2.1 组织模型

本系统采用**单公司、多部门**模式：

1. 只有一个公司主体。
2. 公司下有多个部门，部门负责不同区域客户。
3. 客户群可在不同部门项目中存在交叉。

### 2.2 核心目标

1. 抽奖逻辑统一后端化，前端仅作为抽奖操作终端。
2. 登录后先选择项目，所有请求必须带 Token 与项目标识。
3. 手机号全局唯一，视为自然人唯一身份（可跨项目参与）。
4. 支持跨项目排除规则（含按指定奖项排除）。
5. 抽奖结果全量留痕，可确认、作废、撤销、导出。
6. 管理维护以 Django Admin 为主，并落实部门级数据隔离。

## 3. 技术架构

### 3.1 技术栈

1. 后端：Django + Django REST Framework + Token 认证
2. 数据库：PostgreSQL
3. 后台：Django Admin + `django-simpleui`
4. 抽奖端：Vue3 + Vite + Pinia + Axios

### 3.2 部署形态（本地开发）

1. 后端 API：`http://127.0.0.1:8000/api/`
2. Django Admin：`http://127.0.0.1:8000/admin/`
3. 前端开发服务：`http://localhost:6719/log-lottery/`

### 3.3 安全与隔离关键点

1. 认证：`Authorization: Bearer <token>`
2. 项目隔离：`X-Project-Id: <project_uuid>`
3. 防越权：请求头 `X-Project-Id` 与请求参数中的 `project_id` 必须一致。
4. 部门隔离：非超级管理员仅可访问本部门项目与其关联数据。

## 4. 权限模型

### 4.1 角色定义

1. `SUPER_ADMIN`：全局管理权限（跨部门）。
2. `DEPT_ADMIN`：本部门管理权限（含项目维护）。
3. `OPERATOR`：本部门业务操作（抽奖、名单、奖项、规则、导出）。
4. `VIEWER`：只读角色，不允许写操作。

### 4.2 Admin 隔离策略

1. `Department`：仅超级管理员可新增/修改/删除。
2. `AdminUser`：部门管理员仅可维护本部门账号，且不能创建超级管理员。
3. 业务模型（项目、名单、奖项、中奖等）：按部门过滤列表与可见对象。
4. 抽奖批次/中奖记录/导出任务：admin 中默认只读（非超级管理员不可改写）。

## 5. 数据模型（数据库为唯一事实源）

### 5.1 组织与账号

1. `department`：部门字典（`code/name/region`）
2. `admin_user`：后台用户（继承 Django 用户，增加 `department/role`）

### 5.2 业务主数据

1. `project`：项目主表（UUID 主键，归属部门）
2. `customer`：自然人主表（`phone` 为主键，全局唯一）
3. `project_member`：项目成员表（保留前端既有字段 `uid/name/phone`）
4. `prize`：奖项表（`total_count/used_count/is_all/separate_count`）

### 5.3 过程与审计数据

1. `draw_batch`：抽奖批次（`PENDING/CONFIRMED/VOID`）
2. `draw_winner`：中奖明细快照（`PENDING/CONFIRMED/VOID`）
3. `exclusion_rule`：跨项目排除规则（可按来源/目标奖项细化）
4. `export_job`：导出任务（状态、过滤器、文件路径、错误信息）

### 5.4 关键约束

1. 手机号全局唯一：`customer.phone` 为主键。
2. 项目成员唯一：`(project, customer)` 唯一。
3. 奖项名唯一：`(project, name)` 唯一。
4. 已确认中奖约束：同一项目同一奖项同一用户只允许 1 条 `CONFIRMED` 记录。
5. 排除规则唯一：`(source_project, source_prize, target_project, target_prize, mode)` 唯一。

## 6. 核心业务规则

### 6.1 团体定义

不单独新建“团体”字段，**项目内名单即团体**。

### 6.2 中奖限制

1. `is_all = false`：同一项目内，一个手机号只能中奖一次。
2. `is_all = true`：可多次中奖，但同一项目同一奖项不可重复确认。

### 6.3 跨项目排除

1. 可排除“来源项目全部中奖人”。
2. 可排除“来源项目指定奖项中奖人”。
3. 可作用于“目标项目全部奖项”或“目标项目指定奖项”。

### 6.4 不合规中奖处理（可控流程）

针对“某轮抽奖仅允许某范围人群”的场景，系统采用可审计流程：

1. 先 `preview` 生成待确认中奖。
2. 若结果不合规，执行 `void` 作废本批次并记录原因。
3. 再次 `preview`，直到得到合规结果后 `confirm`。

说明：当前不启用黑盒自动重抽循环，避免不可解释结果。

## 7. 数据变更流程（重点）

### 7.1 预抽（`preview`）

事务内操作：

1. 锁定奖项行（`SELECT ... FOR UPDATE`）。
2. 计算剩余名额：`left = total_count - used_count`。
3. 基于项目成员、中奖历史、排除规则、可选 scope 过滤候选集。
4. 创建 `draw_batch(PENDING)`。
5. 批量创建 `draw_winner(PENDING)`。

特点：不消耗 `used_count`，仅生成待确认结果。

### 7.2 确认（`confirm`）

事务内操作：

1. 锁定批次与奖项。
2. 校验批次状态必须为 `PENDING`。
3. 校验剩余名额足够。
4. 批量更新中奖明细为 `CONFIRMED`，写入 `confirmed_at`。
5. 奖项 `used_count += winner_count`。
6. 批次状态改为 `CONFIRMED`。

### 7.3 作废（`void`）

事务内操作：

1. 批次必须为 `PENDING`。
2. 本批次 `PENDING` 明细改为 `VOID` 并记录原因。
3. 批次改为 `VOID`。

### 7.4 撤销中奖（`revoke`）

事务内操作：

1. 仅允许撤销 `CONFIRMED` 的中奖记录。
2. 中奖记录改为 `VOID`，清空 `confirmed_at`。
3. 对应奖项 `used_count` 回退 1（最小不小于 0）。

### 7.5 项目重置（`reset-project`）

事务内操作：

1. 将项目内 `PENDING/CONFIRMED` 中奖明细置为 `VOID`。
2. 将项目内 `PENDING/CONFIRMED` 批次置为 `VOID`。
3. 逐奖项按当前 `CONFIRMED` 实际数量重算 `used_count`。

### 7.6 清空项目成员（`clear-project`）

1. 先执行项目重置逻辑（避免脏的中奖数据）。
2. 再删除该项目全部成员记录。

### 7.7 导出（`export-jobs`）

1. 创建 `export_job(PENDING)`。
2. 同步生成 CSV（默认 UTF-8 BOM，便于 Excel 打开）。
3. 成功后更新为 `SUCCESS` 并写入 `file_path`。
4. 失败则 `FAILED` 并写入 `error_message`。

## 8. API 概览

说明：认证接口为无尾斜杠，其余 DRF 路由默认带尾斜杠。

### 8.1 认证与组织

1. `POST /api/auth/login`
2. `POST /api/auth/logout`
3. `GET /api/auth/me`
4. `GET/POST/PATCH/DELETE /api/auth/departments/`

### 8.2 项目与名单

1. `GET/POST/PATCH/DELETE /api/projects/`
2. `GET/POST/PATCH/DELETE /api/project-members/`
3. `POST /api/project-members/bulk-upsert/`
4. `POST /api/project-members/clear-project/`

### 8.3 奖项、抽奖、中奖

1. `GET/POST/PATCH/DELETE /api/prizes/`
2. `POST /api/draw-batches/preview/`
3. `POST /api/draw-batches/{id}/confirm/`
4. `POST /api/draw-batches/{id}/void/`
5. `GET /api/draw-winners/`
6. `POST /api/draw-winners/{id}/revoke/`
7. `POST /api/draw-winners/reset-project/`

### 8.4 排除规则与导出

1. `GET/POST/PATCH/DELETE /api/exclusion-rules/`
2. `GET/POST /api/export-jobs/`
3. `GET /api/export-jobs/{id}/download/`

## 9. Django Admin 操作建议

### 9.1 日常维护入口

1. 组织与账号：`Department`、`AdminUser`
2. 项目与配置：`Project`、`ProjectMember`、`Prize`、`ExclusionRule`
3. 过程审计：`DrawBatch`、`DrawWinner`、`ExportJob`

### 9.2 推荐操作分工

1. 部门管理员：维护项目、名单、奖项、规则。
2. 运营：执行抽奖、核对结果、发起导出。
3. 只读账号：查看数据与审计记录。

## 10. 部署与运行

### 10.1 数据库配置

`backend/.env` 建议配置：

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=post-choujiang
DB_USER=post-choujiang
DB_PASSWORD=<your_password>
```

### 10.2 后端启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000 --noreload
```

### 10.3 前端启动（抽奖端）

```bash
cd /home/aris/codeX/log-lottery
pnpm install
pnpm run dev
```

## 11. 验收与回归检查

### 11.1 后端一致性

```bash
cd backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.lottery.tests.test_api_permissions apps.lottery.tests.test_admin_isolation -v 1
```

### 11.2 前端构建

```bash
cd /home/aris/codeX/log-lottery
pnpm run build
```

## 12. 运维与审计建议

1. 每日备份 PostgreSQL（至少全库逻辑备份 + 关键表抽样校验）。
2. 重点监控：`prize.used_count` 与 `draw_winner(CONFIRMED)` 数量一致性。
3. 保留 `draw_batch/draw_winner/export_job` 历史数据用于追责与复盘。
4. 导出目录建议定期归档，避免长期堆积占用磁盘。

## 13. 已知边界

1. 不提供自动无限重抽黑盒逻辑，采用“预抽 -> 人工判定 -> 作废/确认”的可解释流程。
2. 当前管理侧以 Django Admin 为主，前端不承担完整后台配置职责。
3. 导出任务当前为同步执行，未引入 Redis/Celery 等额外基础设施。


1. qa_operator / Qa123456!（超级管理员）
  2. qa_viewer / Qa123456!（只读）