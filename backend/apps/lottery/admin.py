from __future__ import annotations

from django.contrib import admin
from django.db.models import Q

from apps.accounts.models import UserRole

from .models import (
    Customer,
    DrawBatch,
    DrawWinner,
    ExclusionRule,
    ExportJob,
    Prize,
    Project,
    ProjectMember,
)


def _is_super_admin(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and (getattr(user, "is_superuser", False) or getattr(user, "role", None) == UserRole.SUPER_ADMIN)
    )


def _can_write(user) -> bool:
    if not (user and getattr(user, "is_authenticated", False) and getattr(user, "is_active", False)):
        return False
    return _is_super_admin(user) or getattr(user, "role", None) in (UserRole.DEPT_ADMIN, UserRole.OPERATOR)


def _can_manage_projects(user) -> bool:
    if not (user and getattr(user, "is_authenticated", False) and getattr(user, "is_active", False)):
        return False
    return _is_super_admin(user) or getattr(user, "role", None) == UserRole.DEPT_ADMIN


def _department_id(user) -> int | None:
    return getattr(user, "department_id", None)


def _project_in_scope(user, project: Project | None) -> bool:
    if _is_super_admin(user):
        return True
    dept_id = _department_id(user)
    return bool(project and dept_id and project.department_id == dept_id)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "phone",
        "name",
        "participated_project_count",
        "claimed_prize_count",
        "first_project",
        "first_participated_at",
        "created_at",
        "updated_at",
    )
    search_fields = ("phone", "name")
    readonly_fields = (
        "participated_project_count",
        "claimed_prize_count",
        "first_project",
        "first_participated_at",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_super_admin(request.user):
            return qs
        dept_id = _department_id(request.user)
        if not dept_id:
            return qs.none()
        return qs.filter(
            Q(project_members__project__department_id=dept_id)
            | Q(winner_records__project__department_id=dept_id)
        ).distinct()

    def has_module_permission(self, request):
        return _is_super_admin(request.user) or bool(_department_id(request.user))

    def has_view_permission(self, request, obj=None):
        if _is_super_admin(request.user):
            return True
        dept_id = _department_id(request.user)
        if not dept_id:
            return False
        if obj is None:
            return True
        return (
            obj.project_members.filter(project__department_id=dept_id).exists()
            or obj.winner_records.filter(project__department_id=dept_id).exists()
        )

    def has_add_permission(self, request):
        return _is_super_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return _is_super_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_super_admin(request.user)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department", "region", "is_active", "created_at")
    search_fields = ("name", "code", "region")
    list_filter = ("department", "is_active")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_super_admin(request.user):
            return qs
        dept_id = _department_id(request.user)
        if not dept_id:
            return qs.none()
        return qs.filter(department_id=dept_id)

    def has_module_permission(self, request):
        return _is_super_admin(request.user) or bool(_department_id(request.user))

    def has_view_permission(self, request, obj=None):
        if _is_super_admin(request.user):
            return True
        dept_id = _department_id(request.user)
        if not dept_id:
            return False
        if obj is None:
            return True
        return obj.department_id == dept_id

    def has_add_permission(self, request):
        return _can_manage_projects(request.user)

    def has_change_permission(self, request, obj=None):
        if not _can_manage_projects(request.user):
            return False
        if obj is None:
            return True
        return _project_in_scope(request.user, obj)

    def has_delete_permission(self, request, obj=None):
        if not _can_manage_projects(request.user):
            return False
        if obj is None:
            return True
        return _project_in_scope(request.user, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "department" and not _is_super_admin(request.user):
            kwargs["queryset"] = db_field.related_model.objects.filter(id=_department_id(request.user))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not _is_super_admin(request.user) and _department_id(request.user):
            obj.department_id = _department_id(request.user)
        super().save_model(request, obj, form, change)


class _ProjectScopedAdmin(admin.ModelAdmin):
    project_lookup = "project__department_id"

    def _scope_queryset(self, request, qs):
        if _is_super_admin(request.user):
            return qs
        dept_id = _department_id(request.user)
        if not dept_id:
            return qs.none()
        return qs.filter(**{self.project_lookup: dept_id})

    def has_module_permission(self, request):
        return _is_super_admin(request.user) or bool(_department_id(request.user))

    def has_view_permission(self, request, obj=None):
        if _is_super_admin(request.user):
            return True
        dept_id = _department_id(request.user)
        if not dept_id:
            return False
        if obj is None:
            return True
        project = getattr(obj, "project", None)
        return _project_in_scope(request.user, project)

    def has_add_permission(self, request):
        return _can_write(request.user)

    def has_change_permission(self, request, obj=None):
        if not _can_write(request.user):
            return False
        if obj is None:
            return True
        project = getattr(obj, "project", None)
        return _project_in_scope(request.user, project)

    def has_delete_permission(self, request, obj=None):
        if not _can_write(request.user):
            return False
        if obj is None:
            return True
        project = getattr(obj, "project", None)
        return _project_in_scope(request.user, project)


@admin.register(ProjectMember)
class ProjectMemberAdmin(_ProjectScopedAdmin):
    list_display = ("project", "uid", "name", "phone", "is_active", "created_at")
    search_fields = ("uid", "name", "phone")
    list_filter = ("project", "is_active")

    def get_queryset(self, request):
        return self._scope_queryset(request, super().get_queryset(request).select_related("project", "customer"))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not _is_super_admin(request.user) and _department_id(request.user):
            if db_field.name == "project":
                kwargs["queryset"] = Project.objects.filter(department_id=_department_id(request.user))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Prize)
class PrizeAdmin(_ProjectScopedAdmin):
    list_display = ("name", "project", "sort", "is_all", "total_count", "used_count", "is_active")
    search_fields = ("name",)
    list_filter = ("project", "is_active", "is_all")

    def get_queryset(self, request):
        return self._scope_queryset(request, super().get_queryset(request).select_related("project"))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not _is_super_admin(request.user) and _department_id(request.user):
            if db_field.name == "project":
                kwargs["queryset"] = Project.objects.filter(department_id=_department_id(request.user))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(DrawBatch)
class DrawBatchAdmin(_ProjectScopedAdmin):
    list_display = ("id", "project", "prize", "status", "draw_count", "created_at")
    search_fields = ("id", "project__name", "prize__name")
    list_filter = ("status", "project")
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return self._scope_queryset(
            request,
            super().get_queryset(request).select_related("project", "prize", "requested_by"),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return _is_super_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_super_admin(request.user)


@admin.register(DrawWinner)
class DrawWinnerAdmin(_ProjectScopedAdmin):
    list_display = (
        "id",
        "project",
        "prize",
        "uid",
        "name",
        "phone",
        "status",
        "is_visited",
        "is_prize_claimed",
        "confirmed_at",
        "visited_at",
        "prize_claimed_at",
    )
    search_fields = ("uid", "name", "phone", "claim_note")
    list_filter = ("status", "project", "prize", "is_visited", "is_prize_claimed")
    readonly_fields = (
        "batch",
        "project",
        "prize",
        "customer",
        "uid",
        "name",
        "phone",
        "status",
        "confirmed_at",
        "visited_at",
        "prize_claimed_at",
        "void_reason",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return self._scope_queryset(
            request,
            super().get_queryset(request).select_related("project", "prize", "batch", "customer"),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return _is_super_admin(request.user)


@admin.register(ExclusionRule)
class ExclusionRuleAdmin(_ProjectScopedAdmin):
    list_display = ("source_project", "source_prize", "target_project", "target_prize", "is_enabled", "updated_at")
    list_filter = ("is_enabled", "target_project")
    search_fields = ("description", "source_project__name", "target_project__name")
    project_lookup = "target_project__department_id"

    def get_queryset(self, request):
        return self._scope_queryset(
            request,
            super().get_queryset(request).select_related(
                "source_project",
                "source_prize",
                "target_project",
                "target_prize",
            ),
        )

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return True
        if _is_super_admin(request.user):
            return True
        dept_id = _department_id(request.user)
        return bool(
            dept_id
            and obj.source_project.department_id == dept_id
            and obj.target_project.department_id == dept_id
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not _is_super_admin(request.user) and _department_id(request.user):
            if db_field.name in ("source_project", "target_project"):
                kwargs["queryset"] = Project.objects.filter(department_id=_department_id(request.user))
            if db_field.name in ("source_prize", "target_prize"):
                kwargs["queryset"] = Prize.objects.filter(project__department_id=_department_id(request.user))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ExportJob)
class ExportJobAdmin(_ProjectScopedAdmin):
    list_display = ("id", "project", "status", "requested_by", "created_at")
    search_fields = ("id", "project__name", "requested_by__username")
    list_filter = ("status", "project")
    readonly_fields = ("filters", "file_path", "error_message", "created_at", "updated_at")

    def get_queryset(self, request):
        return self._scope_queryset(
            request,
            super().get_queryset(request).select_related("project", "requested_by"),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return _is_super_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_super_admin(request.user)
