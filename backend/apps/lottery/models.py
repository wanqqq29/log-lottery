from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.accounts.models import Department


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Customer(TimestampedModel):
    # 手机号全局唯一，并作为自然人主键
    phone = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=128, default="", blank=True)

    class Meta:
        db_table = "customer"

    def __str__(self) -> str:
        return self.phone


class Project(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="projects")
    region = models.CharField(max_length=128, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "project"
        indexes = [
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name}({self.code})"


class ProjectMember(TimestampedModel):
    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="project_members")

    # 保留你当前前端字段
    uid = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    phone = models.CharField(max_length=20)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "project_member"
        constraints = [
            models.UniqueConstraint(fields=["project", "customer"], name="uniq_project_customer"),
        ]
        indexes = [
            models.Index(fields=["project", "is_active"]),
            models.Index(fields=["project", "uid"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}-{self.phone}"


class Prize(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="prizes")
    name = models.CharField(max_length=128)
    sort = models.IntegerField(default=0)
    is_all = models.BooleanField(default=False)
    total_count = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)
    separate_count = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "prize"
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_project_prize_name"),
        ]
        indexes = [
            models.Index(fields=["project", "sort"]),
            models.Index(fields=["project", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}-{self.name}"


class DrawBatchStatus(models.TextChoices):
    PENDING = "PENDING", "待确认"
    CONFIRMED = "CONFIRMED", "已确认"
    VOID = "VOID", "已作废"


class DrawBatch(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="draw_batches")
    prize = models.ForeignKey(Prize, on_delete=models.PROTECT, related_name="draw_batches")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_draw_batches")
    draw_count = models.IntegerField(default=1)
    status = models.CharField(max_length=16, choices=DrawBatchStatus.choices, default=DrawBatchStatus.PENDING)
    draw_scope = models.JSONField(default=dict, blank=True)
    void_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "draw_batch"
        indexes = [
            models.Index(fields=["project", "prize", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}-{self.prize_id}-{self.status}"


class DrawWinnerStatus(models.TextChoices):
    PENDING = "PENDING", "待确认"
    CONFIRMED = "CONFIRMED", "已确认"
    VOID = "VOID", "已作废"


class DrawWinner(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DrawBatch, on_delete=models.CASCADE, related_name="winners")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="winners")
    prize = models.ForeignKey(Prize, on_delete=models.PROTECT, related_name="winners")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="winner_records")

    # 快照字段：人员被移除后，中奖历史仍可追溯
    uid = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    phone = models.CharField(max_length=20)

    status = models.CharField(max_length=16, choices=DrawWinnerStatus.choices, default=DrawWinnerStatus.PENDING)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "draw_winner"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "prize", "customer"],
                condition=Q(status=DrawWinnerStatus.CONFIRMED),
                name="uniq_confirmed_winner_per_prize",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "prize", "status"]),
            models.Index(fields=["phone"]),
        ]


class RuleMode(models.TextChoices):
    EXCLUDE_SOURCE_WINNERS = "EXCLUDE_SOURCE_WINNERS", "排除来源中奖人"


class ExclusionRule(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="source_rules")
    source_prize = models.ForeignKey(Prize, on_delete=models.CASCADE, related_name="source_rules", null=True, blank=True)
    target_project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="target_rules")
    target_prize = models.ForeignKey(Prize, on_delete=models.CASCADE, related_name="target_rules", null=True, blank=True)
    mode = models.CharField(max_length=64, choices=RuleMode.choices, default=RuleMode.EXCLUDE_SOURCE_WINNERS)
    is_enabled = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "exclusion_rule"
        constraints = [
            models.UniqueConstraint(
                fields=["source_project", "source_prize", "target_project", "target_prize", "mode"],
                name="uniq_exclusion_rule",
            ),
        ]
        indexes = [
            models.Index(fields=["target_project", "target_prize", "is_enabled"]),
        ]


class ExportJobStatus(models.TextChoices):
    PENDING = "PENDING", "待执行"
    SUCCESS = "SUCCESS", "成功"
    FAILED = "FAILED", "失败"


class ExportJob(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="export_jobs")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="export_jobs")
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=ExportJobStatus.choices, default=ExportJobStatus.PENDING)
    file_path = models.CharField(max_length=512, blank=True, default="")
    error_message = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "export_job"
        indexes = [models.Index(fields=["project", "status", "created_at"])]
