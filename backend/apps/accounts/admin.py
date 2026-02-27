from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminUser, Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "region")
    search_fields = ("code", "name", "region")


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("业务属性", {"fields": ("department", "role")}),)
    list_display = ("id", "username", "email", "department", "role", "is_active", "is_staff")
    list_filter = ("role", "department", "is_active", "is_staff")
