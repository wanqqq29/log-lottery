from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import AdminUser, Department


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("用户名或密码错误")
        if not user.is_active:
            raise serializers.ValidationError("账号已停用")
        attrs["user"] = user
        return attrs


class AdminUserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = AdminUser
        fields = ("id", "username", "email", "role", "department", "department_name")


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "code", "name", "region")
