from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.http import urlencode, url_has_allowed_host_and_scheme

from apps.accounts.models import UserRole

from .models import (
    Customer,
    DrawBatch,
    DrawWinner,
    ExclusionRule,
    ExportJob,
    MustWinEntry,
    Prize,
    Project,
    ProjectMember,
)
from .services.draw_service import normalize_phone, register_must_win_entries


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


class ManualAssignWinnerForm(forms.Form):
    class AssignMode:
        FIXED_PRIZE = "FIXED_PRIZE"
        MUST_WIN_ANY = "MUST_WIN_ANY"
        CHOICES = (
            (FIXED_PRIZE, "固定中奖奖项"),
            (MUST_WIN_ANY, "必中奖（不限奖项）"),
        )

    mode = forms.ChoiceField(
        label="模式",
        choices=AssignMode.CHOICES,
        initial=AssignMode.FIXED_PRIZE,
    )
    project = forms.ModelChoiceField(queryset=Project.objects.none(), label="项目")
    prize = forms.ModelChoiceField(
        queryset=Prize.objects.none(),
        label="奖项",
        required=False,
        help_text="固定中奖奖项模式必填；必中奖模式可留空",
    )
    phones = forms.CharField(
        label="手机号（批量）",
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text="每行/每个空格/英文逗号分隔一个手机号",
    )
    reason = forms.CharField(
        label="说明",
        required=False,
        max_length=255,
        initial="后台内定中奖",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        project_qs = Project.objects.all().select_related("department")
        prize_qs = Prize.objects.all().select_related("project", "project__department")
        if not _is_super_admin(user):
            dept_id = _department_id(user)
            if not dept_id:
                project_qs = project_qs.none()
                prize_qs = prize_qs.none()
            else:
                project_qs = project_qs.filter(department_id=dept_id)
                prize_qs = prize_qs.filter(project__department_id=dept_id)
        self.fields["project"].queryset = project_qs.order_by("department__name", "name")
        self.fields["prize"].queryset = prize_qs.order_by("project__name", "sort", "created_at")

    def clean_phones(self):
        raw = self.cleaned_data["phones"]
        normalized: list[str] = []
        seen: set[str] = set()
        for token in raw.replace("，", ",").replace("；", ",").split(","):
            for piece in token.split():
                phone = normalize_phone(piece)
                if not phone or phone in seen:
                    continue
                seen.add(phone)
                normalized.append(phone)
        if not normalized:
            raise forms.ValidationError("请至少输入一个有效手机号")
        return normalized

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("mode")
        project = cleaned.get("project")
        prize = cleaned.get("prize")
        if mode == self.AssignMode.FIXED_PRIZE:
            if not prize:
                raise forms.ValidationError("固定中奖奖项模式必须选择奖项")
            if project and prize and prize.project_id != project.id:
                raise forms.ValidationError("所选奖项不属于该项目")
        else:
            cleaned["prize"] = None
        return cleaned


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
    change_list_template = "admin/lottery/drawwinner/change_list.html"
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "manual-assign/",
                self.admin_site.admin_view(self.manual_assign_view),
                name="lottery_drawwinner_manual_assign",
            )
        ]
        return custom_urls + urls

    def manual_assign_view(self, request):
        next_url = self._safe_next_url(request, request.POST.get("next") or request.GET.get("next"))
        if not self.has_view_permission(request):
            return self._redirect_to_changelist(request, next_url=next_url)
        if not _can_write(request.user):
            self.message_user(request, "当前账号无权限执行内定中奖", level=messages.ERROR)
            return self._redirect_to_changelist(request, next_url=next_url)

        form = ManualAssignWinnerForm(request.POST or None, user=request.user)
        if request.method == "POST" and form.is_valid():
            mode = form.cleaned_data["mode"]
            project = form.cleaned_data["project"]
            prize = form.cleaned_data["prize"]
            phones = form.cleaned_data["phones"]
            reason = form.cleaned_data["reason"] or "后台内定中奖"
            if not _project_in_scope(request.user, project):
                self.message_user(request, "无权限操作该项目", level=messages.ERROR)
                return self._redirect_to_changelist(request, next_url=next_url)
            try:
                if mode == ManualAssignWinnerForm.AssignMode.FIXED_PRIZE:
                    result = register_must_win_entries(
                        project=project,
                        phones=phones,
                        user=request.user,
                        reason=reason,
                        target_prize=prize,
                    )
                    self.message_user(
                        request,
                        (
                            "固定奖项内定已暂存："
                            f"总计 {result['total']}，新增 {result['created']}，"
                            f"恢复 {result['reactivated']}，已存在 {result['existed']}。"
                            "将在抽取该奖项时生效。"
                        ),
                        level=messages.SUCCESS,
                    )
                else:
                    result = register_must_win_entries(
                        project=project,
                        phones=phones,
                        user=request.user,
                        reason=reason,
                    )
                    self.message_user(
                        request,
                        (
                            "必中奖设置完成："
                            f"总计 {result['total']}，新增 {result['created']}，"
                            f"恢复 {result['reactivated']}，已存在 {result['existed']}"
                        ),
                        level=messages.SUCCESS,
                    )
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                return self._redirect_to_changelist(
                    request,
                    next_url=next_url,
                    project_id=str(project.id),
                )

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "内定中奖",
            "form": form,
            "next_url": next_url,
            "back_url": next_url or self._default_changelist_url(),
            "prize_options": self._build_prize_options(form),
        }
        return TemplateResponse(request, "admin/lottery/drawwinner/manual_assign.html", context)

    def _build_prize_options(self, form: ManualAssignWinnerForm) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        for prize in form.fields["prize"].queryset:
            options.append(
                {
                    "id": str(prize.id),
                    "project_id": str(prize.project_id),
                    "label": str(prize.name),
                }
            )
        return options

    def _default_changelist_url(self, *, project_id: str | None = None):
        changelist_url = reverse("admin:lottery_drawwinner_changelist")
        if not project_id:
            return changelist_url
        query = urlencode({"project__id__exact": project_id})
        return f"{changelist_url}?{query}"

    def _safe_next_url(self, request, next_url: str | None) -> str | None:
        if not next_url:
            return None
        if url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return None

    def _redirect_to_changelist(self, request, *, next_url: str | None = None, project_id: str | None = None):
        return redirect(next_url or self._default_changelist_url(project_id=project_id))


@admin.register(ExclusionRule)
class ExclusionRuleAdmin(_ProjectScopedAdmin):
    list_display = ("source_project", "source_prize", "target_project", "target_prize", "is_enabled", "updated_at")
    list_filter = ("is_enabled", "target_project")
    search_fields = ("description", "source_project__name", "target_project__name")
    project_lookup = "target_project__department_id"
    change_list_template = "admin/lottery/exclusionrule/change_list.html"

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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        back_url = self._resolve_back_url(request)
        extra_context["back_url"] = back_url
        return super().changelist_view(request, extra_context=extra_context)

    def _resolve_back_url(self, request) -> str:
        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return reverse("admin:lottery_drawwinner_changelist")

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


@admin.register(MustWinEntry)
class MustWinEntryAdmin(_ProjectScopedAdmin):
    list_display = ("project", "target_prize", "name", "phone", "is_active", "applied_winner", "applied_at", "updated_at")
    list_filter = ("project", "is_active")
    search_fields = ("name", "phone", "note")
    readonly_fields = (
        "project",
        "customer",
        "phone",
        "name",
        "target_prize",
        "created_by",
        "applied_winner",
        "applied_at",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return self._scope_queryset(
            request,
            super().get_queryset(request).select_related("project", "customer", "created_by", "applied_winner"),
        )

    def has_add_permission(self, request):
        return False
