from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "超级管理员"
    DEPT_ADMIN = "DEPT_ADMIN", "部门管理员"
    OPERATOR = "OPERATOR", "运营"
    VIEWER = "VIEWER", "只读"


class Department(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128, unique=True)
    region = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "department"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name}({self.code})"


class AdminUser(AbstractUser):
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.CharField(max_length=32, choices=UserRole.choices, default=UserRole.OPERATOR)

    class Meta:
        db_table = "admin_user"

    def __str__(self) -> str:
        return self.username
