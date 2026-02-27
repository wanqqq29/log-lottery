from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import AdminUser, Department, UserRole

from .models import DrawBatch, ExclusionRule, Prize, Project, ProjectMember
from .serializers import (
    DrawBatchSerializer,
    ExclusionRuleSerializer,
    PreviewDrawSerializer,
    PrizeSerializer,
    ProjectMemberSerializer,
    ProjectSerializer,
    VoidBatchSerializer,
)
from .services.draw_service import confirm_batch, preview_draw, void_batch


def _is_super_admin(user: AdminUser) -> bool:
    return user.is_superuser or user.role == UserRole.SUPER_ADMIN


def _department_scoped_projects(user: AdminUser) -> QuerySet[Project]:
    qs = Project.objects.all().select_related("department")
    if _is_super_admin(user):
        return qs
    if not user.department_id:
        return qs.none()
    return qs.filter(department_id=user.department_id)


def _assert_project_access(user: AdminUser, project: Project) -> None:
    if _is_super_admin(user):
        return
    if not user.department_id or project.department_id != user.department_id:
        raise PermissionError("无权限访问该项目")


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _department_scoped_projects(self.request.user)


class ProjectMemberViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ProjectMember.objects.all().select_related("project", "customer")
        allowed_projects = _department_scoped_projects(self.request.user)
        return qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))


class PrizeViewSet(viewsets.ModelViewSet):
    serializer_class = PrizeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Prize.objects.all().select_related("project")
        allowed_projects = _department_scoped_projects(self.request.user)
        return qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))


class ExclusionRuleViewSet(viewsets.ModelViewSet):
    serializer_class = ExclusionRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ExclusionRule.objects.all().select_related(
            "source_project", "source_prize", "target_project", "target_prize"
        )
        allowed_projects = _department_scoped_projects(self.request.user)
        allowed_ids = allowed_projects.values_list("id", flat=True)
        return qs.filter(target_project_id__in=allowed_ids)


class DrawBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DrawBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DrawBatch.objects.all().select_related("project", "prize", "requested_by").prefetch_related("winners")
        allowed_projects = _department_scoped_projects(self.request.user)
        return qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        serializer = PreviewDrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = Project.objects.select_related("department").get(pk=serializer.validated_data["project_id"])
        _assert_project_access(request.user, project)
        prize = Prize.objects.get(pk=serializer.validated_data["prize_id"], project=project)

        try:
            batch = preview_draw(
                project=project,
                prize=prize,
                count=serializer.validated_data["count"],
                user=request.user,
                scope=serializer.validated_data.get("scope") or {},
            )
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DrawBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        batch = self.get_object()
        try:
            batch = confirm_batch(batch=batch, user=request.user)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DrawBatchSerializer(batch).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, pk=None):
        batch = self.get_object()
        serializer = VoidBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        try:
            batch = void_batch(batch=batch, reason=reason, user=request.user)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DrawBatchSerializer(batch).data, status=status.HTTP_200_OK)
