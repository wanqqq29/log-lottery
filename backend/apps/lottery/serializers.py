from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Department

from .models import (
    Customer,
    DrawBatch,
    DrawWinner,
    ExclusionRule,
    Prize,
    Project,
    ProjectMember,
)
from .services.draw_service import normalize_phone


class DepartmentLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "code", "name", "region")


class ProjectSerializer(serializers.ModelSerializer):
    department_detail = DepartmentLiteSerializer(source="department", read_only=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "code",
            "name",
            "department",
            "department_detail",
            "region",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("phone", "name", "created_at", "updated_at")


class ProjectMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMember
        fields = (
            "id",
            "project",
            "uid",
            "name",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        )

    def validate_phone(self, value: str) -> str:
        normalized = normalize_phone(value)
        if not normalized:
            raise serializers.ValidationError("手机号不能为空")
        return normalized

    def create(self, validated_data):
        phone = validated_data["phone"]
        name = validated_data.get("name", "")
        customer, created = Customer.objects.get_or_create(phone=phone, defaults={"name": name})
        if (not created) and name and customer.name != name:
            customer.name = name
            customer.save(update_fields=["name", "updated_at"])

        validated_data["customer"] = customer
        return super().create(validated_data)

    def update(self, instance, validated_data):
        phone = validated_data.get("phone", instance.phone)
        name = validated_data.get("name", instance.name)
        phone = normalize_phone(phone)
        customer, created = Customer.objects.get_or_create(phone=phone, defaults={"name": name})
        if (not created) and name and customer.name != name:
            customer.name = name
            customer.save(update_fields=["name", "updated_at"])

        validated_data["phone"] = phone
        validated_data["customer"] = customer
        return super().update(instance, validated_data)


class PrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prize
        fields = (
            "id",
            "project",
            "name",
            "sort",
            "is_all",
            "total_count",
            "used_count",
            "separate_count",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("used_count",)


class DrawWinnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrawWinner
        fields = (
            "id",
            "batch",
            "project",
            "prize",
            "uid",
            "name",
            "phone",
            "status",
            "confirmed_at",
            "void_reason",
            "created_at",
        )


class DrawBatchSerializer(serializers.ModelSerializer):
    winners = DrawWinnerSerializer(many=True, read_only=True)

    class Meta:
        model = DrawBatch
        fields = (
            "id",
            "project",
            "prize",
            "requested_by",
            "draw_count",
            "status",
            "draw_scope",
            "void_reason",
            "created_at",
            "updated_at",
            "winners",
        )
        read_only_fields = ("requested_by", "status", "void_reason")


class PreviewDrawSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    prize_id = serializers.UUIDField()
    count = serializers.IntegerField(min_value=1)
    scope = serializers.JSONField(required=False)


class VoidBatchSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=255)


class ExclusionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExclusionRule
        fields = (
            "id",
            "source_project",
            "source_prize",
            "target_project",
            "target_prize",
            "mode",
            "is_enabled",
            "description",
            "created_at",
            "updated_at",
        )
