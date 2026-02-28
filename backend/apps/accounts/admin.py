from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminUser, Department, UserRole


def _is_super_admin(user) -> bool:
    return bool(user and user.is_active and (user.is_superuser or user.role == UserRole.SUPER_ADMIN))


def _is_dept_admin(user) -> bool:
    return bool(user and user.is_active and user.role == UserRole.DEPT_ADMIN)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "region")
    search_fields = ("code", "name", "region")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_super_admin(request.user):
            return qs
        if not request.user.department_id:
            return qs.none()
        return qs.filter(id=request.user.department_id)

    def has_module_permission(self, request):
        return _is_super_admin(request.user) or bool(request.user.department_id)

    def has_view_permission(self, request, obj=None):
        if _is_super_admin(request.user):
            return True
        if obj is None:
            return bool(request.user.department_id)
        return obj.id == request.user.department_id

    def has_add_permission(self, request):
        return _is_super_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return _is_super_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_super_admin(request.user)


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("业务属性", {"fields": ("department", "role")}),)
    list_display = ("id", "username", "email", "department", "role", "is_active", "is_staff")
    list_filter = ("role", "department", "is_active", "is_staff")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_super_admin(request.user):
            return qs
        if not request.user.department_id:
            return qs.none()
        return qs.filter(department_id=request.user.department_id)

    def has_module_permission(self, request):
        return _is_super_admin(request.user) or _is_dept_admin(request.user)

    def has_view_permission(self, request, obj=None):
        if _is_super_admin(request.user):
            return True
        if not _is_dept_admin(request.user):
            return False
        if obj is None:
            return bool(request.user.department_id)
        return obj.department_id == request.user.department_id

    def has_add_permission(self, request):
        return _is_super_admin(request.user) or _is_dept_admin(request.user)

    def has_change_permission(self, request, obj=None):
        if _is_super_admin(request.user):
            return True
        if not _is_dept_admin(request.user):
            return False
        if obj is None:
            return bool(request.user.department_id)
        return obj.department_id == request.user.department_id and obj.role != UserRole.SUPER_ADMIN

    def has_delete_permission(self, request, obj=None):
        if _is_super_admin(request.user):
            return True
        if not _is_dept_admin(request.user):
            return False
        if obj is None:
            return bool(request.user.department_id)
        return obj.department_id == request.user.department_id and obj.role != UserRole.SUPER_ADMIN

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "department" and not _is_super_admin(request.user):
            kwargs["queryset"] = Department.objects.filter(id=request.user.department_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if _is_dept_admin(request.user) and not _is_super_admin(request.user):
            obj.department = request.user.department
            if obj.role == UserRole.SUPER_ADMIN:
                obj.role = UserRole.OPERATOR
            if not obj.is_staff:
                obj.is_staff = True
        super().save_model(request, obj, form, change)
