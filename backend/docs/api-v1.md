# API V1 Draft

## Auth

### Login
`POST /api/auth/login`

```json
{
  "username": "admin",
  "password": "***"
}
```

### Me
`GET /api/auth/me`

### Logout
`POST /api/auth/logout`

## Projects

### Departments
`GET /api/auth/departments/`

### Create project
`POST /api/projects/`

```json
{
  "code": "HZ-2026-NEWYEAR",
  "name": "2026杭州新春引流",
  "department": 1,
  "region": "杭州",
  "description": "活动项目",
  "is_active": true
}
```

## Members

### Bulk upsert project members
`POST /api/project-members/bulk-upsert/`

```json
{
  "project_id": "project-uuid",
  "members": [
    {"uid": "A001", "name": "张三", "phone": "13800000001", "is_active": true},
    {"uid": "A002", "name": "李四", "phone": "13800000002", "is_active": true}
  ]
}
```

## Draw

### Preview draw
`POST /api/draw-batches/preview/`

```json
{
  "project_id": "project-uuid",
  "prize_id": "prize-uuid",
  "count": 3,
  "scope": {
    "include_uids": ["A001", "A002"],
    "include_phones": ["13800000001"]
  }
}
```

### Confirm draw
`POST /api/draw-batches/{batch_id}/confirm/`

### Void draw
`POST /api/draw-batches/{batch_id}/void/`

```json
{
  "reason": "抽到非本次活动范围用户，作废重抽"
}
```

## Cross-project exclusion rules

### Create rule
`POST /api/exclusion-rules/`

```json
{
  "source_project": "project-a-uuid",
  "source_prize": "prize-a1-uuid",
  "target_project": "project-b-uuid",
  "target_prize": "prize-b2-uuid",
  "mode": "EXCLUDE_SOURCE_WINNERS",
  "is_enabled": true,
  "description": "B项目二等奖排除A项目一等奖中奖者"
}
```

## Export winners

### Create export job
`POST /api/export-jobs/`

```json
{
  "project_id": "project-uuid",
  "prize_id": "optional-prize-uuid",
  "status": "CONFIRMED"
}
```

### Download exported file
`GET /api/export-jobs/{job_id}/download/`
