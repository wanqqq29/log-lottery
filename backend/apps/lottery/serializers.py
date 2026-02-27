from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Department

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

    def validate(self, attrs):
        total_count = attrs.get("total_count", getattr(self.instance, "total_count", 0))
        if total_count <= 0:
            raise serializers.ValidationError("奖项总人数必须大于0")
        return attrs


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
    def validate(self, attrs):
        source_project = attrs.get("source_project", getattr(self.instance, "source_project", None))
        target_project = attrs.get("target_project", getattr(self.instance, "target_project", None))
        source_prize = attrs.get("source_prize", getattr(self.instance, "source_prize", None))
        target_prize = attrs.get("target_prize", getattr(self.instance, "target_prize", None))

        if source_project and target_project and source_project.id == target_project.id:
            raise serializers.ValidationError("来源项目和目标项目不能相同")
        if source_prize and source_project and source_prize.project_id != source_project.id:
            raise serializers.ValidationError("source_prize 不属于 source_project")
        if target_prize and target_project and target_prize.project_id != target_project.id:
            raise serializers.ValidationError("target_prize 不属于 target_project")
        return attrs

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


class ProjectMemberBulkItemSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=128)
    phone = serializers.CharField(max_length=20)
    is_active = serializers.BooleanField(default=True)

    def validate_phone(self, value: str) -> str:
        normalized = normalize_phone(value)
        if not normalized:
            raise serializers.ValidationError("手机号不能为空")
        return normalized


class ProjectMemberBulkUpsertSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    members = ProjectMemberBulkItemSerializer(many=True, allow_empty=False)

    def validate_members(self, members):
        seen = set()
        for item in members:
            key = (item["phone"], item["uid"])
            if key in seen:
                raise serializers.ValidationError(f"存在重复成员: {item['uid']} / {item['phone']}")
            seen.add(key)
        return members


class ExportWinnersRequestSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    prize_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=["CONFIRMED", "PENDING", "VOID"],
        required=False,
        default="CONFIRMED",
    )


class ExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportJob
        fields = (
            "id",
            "project",
            "requested_by",
            "filters",
            "status",
            "file_path",
            "error_message",
            "created_at",
            "updated_at",
        )
