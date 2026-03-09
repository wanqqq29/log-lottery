from __future__ import annotations

import csv
import io
from datetime import timedelta
from pathlib import Path

from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import AdminUser, UserRole

from .models import (
    Customer,
    DrawBatch,
    DrawWinner,
    DrawWinnerStatus,
    ExclusionRule,
    ExportJob,
    Prize,
    Project,
    ProjectMember,
)
from .serializers import (
    ClearProjectMembersSerializer,
    DrawBatchSerializer,
    DrawWinnerDashboardSerializer,
    DrawWinnerSerializer,
    ExportArrivalWinnersSerializer,
    ExclusionRuleSerializer,
    ExportJobSerializer,
    ExportWinnersRequestSerializer,
    PreviewDrawSerializer,
    PrizeSerializer,
    ProjectMemberBulkUpsertSerializer,
    ProjectMemberSerializer,
    ProjectSerializer,
    RegisterWinnerArrivalSerializer,
    ResetProjectWinnersSerializer,
    RevokeWinnerSerializer,
    VoidBatchSerializer,
)
from .services.draw_service import (
    confirm_batch,
    preview_draw,
    reset_project_winners,
    revoke_confirmed_winner,
    void_batch,
)
from .services.export_service import create_export_job


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
        raise PermissionDenied("无权限访问该项目")


def _assert_can_write(user: AdminUser) -> None:
    if _is_super_admin(user):
        return
    if user.role == UserRole.VIEWER:
        raise PermissionDenied("当前账号为只读角色，禁止写操作")


def _assert_can_register_arrival(user: AdminUser) -> None:
    if _is_super_admin(user):
        return
    if user.role not in (UserRole.DEPT_ADMIN, UserRole.OPERATOR, UserRole.VIEWER):
        raise PermissionDenied("当前账号无权限登记到访/领奖")


def _assert_can_manage_projects(user: AdminUser) -> None:
    if _is_super_admin(user):
        return
    if user.role != UserRole.DEPT_ADMIN:
        raise PermissionDenied("仅超级管理员或部门管理员可维护项目")


def _header_project_id(request) -> str:
    return (request.headers.get("X-Project-Id") or "").strip()


def _assert_header_project_match(request, project_id: str, *, required: bool = True) -> None:
    header_project_id = _header_project_id(request)
    if required and not header_project_id:
        raise PermissionDenied("缺少 X-Project-Id")
    if header_project_id and header_project_id != str(project_id):
        raise PermissionDenied("X-Project-Id 与请求项目不一致")


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _department_scoped_projects(self.request.user)

    def perform_create(self, serializer):
        _assert_can_manage_projects(self.request.user)
        department = serializer.validated_data["department"]
        if not _is_super_admin(self.request.user) and self.request.user.department_id != department.id:
            raise PermissionDenied("无权限在该部门下创建项目")
        serializer.save()

    def perform_update(self, serializer):
        _assert_can_manage_projects(self.request.user)
        department = serializer.validated_data.get("department", serializer.instance.department)
        if not _is_super_admin(self.request.user) and self.request.user.department_id != department.id:
            raise PermissionDenied("无权限修改为该部门项目")
        serializer.save()

    def perform_destroy(self, instance):
        _assert_can_manage_projects(self.request.user)
        super().perform_destroy(instance)


class ProjectMemberViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ProjectMember.objects.all().select_related("project", "customer")
        allowed_projects = _department_scoped_projects(self.request.user)
        project_id = self.request.query_params.get("project_id") or _header_project_id(self.request)
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))

    def perform_create(self, serializer):
        _assert_can_write(self.request.user)
        project = serializer.validated_data["project"]
        _assert_header_project_match(self.request, str(project.id))
        _assert_project_access(self.request.user, project)
        serializer.save()

    def perform_update(self, serializer):
        _assert_can_write(self.request.user)
        project = serializer.validated_data.get("project", serializer.instance.project)
        _assert_header_project_match(self.request, str(project.id))
        _assert_project_access(self.request.user, project)
        serializer.save()

    def perform_destroy(self, instance):
        _assert_can_write(self.request.user)
        super().perform_destroy(instance)

    @action(detail=False, methods=["post"], url_path="bulk-upsert")
    def bulk_upsert(self, request):
        _assert_can_write(request.user)
        serializer = ProjectMemberBulkUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = get_object_or_404(Project, pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)

        created_count = 0
        updated_count = 0
        for item in serializer.validated_data["members"]:
            phone = item["phone"]
            name = item["name"]
            customer, customer_created = Customer.objects.get_or_create(
                phone=phone,
                defaults={"name": name},
            )
            if (not customer_created) and name and customer.name != name:
                customer.name = name
                customer.save(update_fields=["name", "updated_at"])

            _, created = ProjectMember.objects.update_or_create(
                project=project,
                customer=customer,
                defaults={
                    "uid": item["uid"],
                    "name": name,
                    "phone": phone,
                    "is_active": item.get("is_active", True),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        return Response(
            {
                "project_id": str(project.id),
                "created_count": created_count,
                "updated_count": updated_count,
                "total": created_count + updated_count,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="clear-project")
    def clear_project(self, request):
        _assert_can_write(request.user)
        serializer = ClearProjectMembersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(Project, pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)

        reset_result = reset_project_winners(
            project=project,
            reason=serializer.validated_data["reason"],
            user=request.user,
        )
        deleted_count, _ = ProjectMember.objects.filter(project=project).delete()
        return Response(
            {
                "project_id": str(project.id),
                "deleted_member_count": deleted_count,
                **reset_result,
            },
            status=status.HTTP_200_OK,
        )


class PrizeViewSet(viewsets.ModelViewSet):
    serializer_class = PrizeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Prize.objects.all().select_related("project")
        allowed_projects = _department_scoped_projects(self.request.user)
        project_id = self.request.query_params.get("project_id") or _header_project_id(self.request)
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))

    def perform_create(self, serializer):
        _assert_can_write(self.request.user)
        project = serializer.validated_data["project"]
        _assert_header_project_match(self.request, str(project.id))
        _assert_project_access(self.request.user, project)
        serializer.save()

    def perform_update(self, serializer):
        _assert_can_write(self.request.user)
        project = serializer.validated_data.get("project", serializer.instance.project)
        _assert_header_project_match(self.request, str(project.id))
        _assert_project_access(self.request.user, project)
        serializer.save()

    def perform_destroy(self, instance):
        _assert_can_write(self.request.user)
        super().perform_destroy(instance)


class ExclusionRuleViewSet(viewsets.ModelViewSet):
    serializer_class = ExclusionRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ExclusionRule.objects.all().select_related(
            "source_project", "source_prize", "target_project", "target_prize"
        )
        allowed_projects = _department_scoped_projects(self.request.user)
        allowed_ids = allowed_projects.values_list("id", flat=True)
        header_project_id = _header_project_id(self.request)
        if header_project_id:
            qs = qs.filter(target_project_id=header_project_id)
        return qs.filter(target_project_id__in=allowed_ids)

    def perform_create(self, serializer):
        _assert_can_write(self.request.user)
        source_project = serializer.validated_data["source_project"]
        target_project = serializer.validated_data["target_project"]
        _assert_header_project_match(self.request, str(target_project.id))
        _assert_project_access(self.request.user, source_project)
        _assert_project_access(self.request.user, target_project)
        serializer.save()

    def perform_update(self, serializer):
        _assert_can_write(self.request.user)
        source_project = serializer.validated_data.get("source_project", serializer.instance.source_project)
        target_project = serializer.validated_data.get("target_project", serializer.instance.target_project)
        _assert_header_project_match(self.request, str(target_project.id))
        _assert_project_access(self.request.user, source_project)
        _assert_project_access(self.request.user, target_project)
        serializer.save()

    def perform_destroy(self, instance):
        _assert_can_write(self.request.user)
        super().perform_destroy(instance)


class DrawBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DrawBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DrawBatch.objects.all().select_related("project", "prize", "requested_by").prefetch_related("winners")
        allowed_projects = _department_scoped_projects(self.request.user)
        qs = qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))
        project_id = self.request.query_params.get("project_id") or _header_project_id(self.request)
        prize_id = self.request.query_params.get("prize_id")
        draw_status = self.request.query_params.get("status")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if prize_id:
            qs = qs.filter(prize_id=prize_id)
        if draw_status:
            qs = qs.filter(status=draw_status)
        return qs

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        _assert_can_write(request.user)
        serializer = PreviewDrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = get_object_or_404(Project.objects.select_related("department"), pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)
        prize = get_object_or_404(Prize, pk=serializer.validated_data["prize_id"], project=project)

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

        batch = DrawBatch.objects.select_related("project", "prize", "requested_by").prefetch_related("winners").get(pk=batch.pk)
        return Response(DrawBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        _assert_can_write(request.user)
        batch = self.get_object()
        _assert_header_project_match(request, str(batch.project_id))
        try:
            batch = confirm_batch(batch=batch, user=request.user)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DrawBatchSerializer(batch).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, pk=None):
        _assert_can_write(request.user)
        batch = self.get_object()
        _assert_header_project_match(request, str(batch.project_id))
        serializer = VoidBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        try:
            batch = void_batch(batch=batch, reason=reason, user=request.user)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DrawBatchSerializer(batch).data, status=status.HTTP_200_OK)


class DrawWinnerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DrawWinnerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DrawWinner.objects.all().select_related("project", "prize", "batch")
        allowed_projects = _department_scoped_projects(self.request.user)
        qs = qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))

        project_id = self.request.query_params.get("project_id") or _header_project_id(self.request)
        prize_id = self.request.query_params.get("prize_id")
        winner_status = self.request.query_params.get("status")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if prize_id:
            qs = qs.filter(prize_id=prize_id)
        if winner_status:
            qs = qs.filter(status=winner_status)
        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        _assert_can_write(request.user)
        winner = self.get_object()
        _assert_header_project_match(request, str(winner.project_id))
        serializer = RevokeWinnerSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            winner = revoke_confirmed_winner(
                winner=winner,
                reason=serializer.validated_data["reason"],
                user=request.user,
            )
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DrawWinnerSerializer(winner).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="register-arrival")
    def register_arrival(self, request):
        _assert_can_register_arrival(request.user)
        serializer = RegisterWinnerArrivalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = get_object_or_404(Project, pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)

        qs = DrawWinner.objects.filter(
            project=project,
            phone=serializer.validated_data["phone"],
            status=DrawWinnerStatus.CONFIRMED,
        )
        prize_id = serializer.validated_data.get("prize_id")
        if prize_id:
            qs = qs.filter(prize_id=prize_id)

        winner = qs.order_by("is_prize_claimed", "-confirmed_at", "-created_at").first()
        if not winner:
            return Response({"message": "未找到该手机号对应的已确认中奖记录"}, status=status.HTTP_404_NOT_FOUND)

        winner.is_visited = True
        winner.is_prize_claimed = serializer.validated_data["is_prize_claimed"]
        winner.claim_note = serializer.validated_data.get("claim_note", "").strip()
        winner.save()
        return Response(DrawWinnerSerializer(winner).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="export-arrival")
    def export_arrival(self, request):
        serializer = ExportArrivalWinnersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(Project, pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)

        winners = DrawWinner.objects.filter(project=project, status=DrawWinnerStatus.CONFIRMED).select_related("prize")
        if serializer.validated_data.get("prize_id"):
            winners = winners.filter(prize_id=serializer.validated_data["prize_id"])

        arrival_state = serializer.validated_data["arrival_state"]
        if arrival_state == "CLAIMED":
            winners = winners.filter(is_visited=True, is_prize_claimed=True)
        else:
            winners = winners.filter(Q(is_visited=False) | Q(is_prize_claimed=False))

        winners = winners.order_by("-confirmed_at", "-created_at")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "project_id",
                "project_name",
                "prize_name",
                "uid",
                "name",
                "phone",
                "status",
                "confirmed_at",
                "is_visited",
                "visited_at",
                "is_prize_claimed",
                "prize_claimed_at",
                "claim_note",
            ]
        )
        for winner in winners:
            writer.writerow(
                [
                    str(project.id),
                    project.name,
                    winner.prize.name,
                    winner.uid,
                    winner.name,
                    winner.phone,
                    winner.status,
                    winner.confirmed_at.isoformat() if winner.confirmed_at else "",
                    "Y" if winner.is_visited else "N",
                    winner.visited_at.isoformat() if winner.visited_at else "",
                    "Y" if winner.is_prize_claimed else "N",
                    winner.prize_claimed_at.isoformat() if winner.prize_claimed_at else "",
                    winner.claim_note,
                ]
            )

        state_label = "claimed" if arrival_state == "CLAIMED" else "unclaimed"
        ts = timezone.now().strftime("%Y%m%d%H%M%S")
        file_name = f"winner-arrival-{project.code}-{state_label}-{ts}.csv"
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        serializer = DrawWinnerDashboardSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(Project, pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)

        days = serializer.validated_data["days"]
        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)

        members_total = ProjectMember.objects.filter(project=project, is_active=True).count()
        confirmed_qs = DrawWinner.objects.filter(project=project, status=DrawWinnerStatus.CONFIRMED)
        confirmed_total = confirmed_qs.count()
        arrival_total = confirmed_qs.filter(is_visited=True).count()
        claimed_total = confirmed_qs.filter(is_prize_claimed=True).count()
        unclaimed_total = confirmed_total - claimed_total

        def _rate(numerator: int, denominator: int) -> float:
            if denominator <= 0:
                return 0.0
            return round((numerator / denominator) * 100, 2)

        prize_rows = (
            Prize.objects.filter(project=project)
            .values("id", "name", "total_count", "used_count")
            .order_by("sort", "created_at")
        )
        prize_stats = []
        for prize in prize_rows:
            prize_winners = confirmed_qs.filter(prize_id=prize["id"])
            prize_confirmed = prize_winners.count()
            prize_arrival = prize_winners.filter(is_visited=True).count()
            prize_claimed = prize_winners.filter(is_prize_claimed=True).count()
            prize_unclaimed = prize_confirmed - prize_claimed
            prize_stats.append(
                {
                    "prize_id": str(prize["id"]),
                    "prize_name": prize["name"],
                    "total_quota": prize["total_count"],
                    "used_quota": prize["used_count"],
                    "confirmed_winner_count": prize_confirmed,
                    "arrival_count": prize_arrival,
                    "claimed_count": prize_claimed,
                    "unclaimed_count": prize_unclaimed,
                    "claim_rate": _rate(prize_claimed, prize_confirmed),
                }
            )

        daily_raw = (
            confirmed_qs.filter(created_at__date__gte=start_date, created_at__date__lte=today)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                confirmed_count=Count("id"),
                arrival_count=Count("id", filter=Q(is_visited=True)),
                claimed_count=Count("id", filter=Q(is_prize_claimed=True)),
            )
            .order_by("day")
        )

        daily_stats_map = {
            row["day"]: {
                "date": row["day"].isoformat(),
                "confirmed_count": row["confirmed_count"],
                "arrival_count": row["arrival_count"],
                "claimed_count": row["claimed_count"],
            }
            for row in daily_raw
        }

        daily_stats = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            daily_stats.append(
                daily_stats_map.get(
                    d,
                    {
                        "date": d.isoformat(),
                        "confirmed_count": 0,
                        "arrival_count": 0,
                        "claimed_count": 0,
                    },
                )
            )

        return Response(
            {
                "project_id": str(project.id),
                "project_name": project.name,
                "days": days,
                "members_total": members_total,
                "confirmed_winner_total": confirmed_total,
                "arrival_total": arrival_total,
                "claimed_total": claimed_total,
                "unclaimed_total": unclaimed_total,
                "arrival_rate": _rate(arrival_total, confirmed_total),
                "claim_rate": _rate(claimed_total, confirmed_total),
                "member_win_rate": _rate(confirmed_total, members_total),
                "prize_stats": prize_stats,
                "daily_stats": daily_stats,
                "generated_at": timezone.now().isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="reset-project")
    def reset_project(self, request):
        _assert_can_write(request.user)
        serializer = ResetProjectWinnersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(Project, pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)
        result = reset_project_winners(
            project=project,
            reason=serializer.validated_data["reason"],
            user=request.user,
        )
        return Response(
            {
                "project_id": str(project.id),
                **result,
            },
            status=status.HTTP_200_OK,
        )


class ExportJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ExportJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ExportJob.objects.all().select_related("project", "requested_by")
        allowed_projects = _department_scoped_projects(self.request.user)
        qs = qs.filter(project_id__in=allowed_projects.values_list("id", flat=True))
        project_id = self.request.query_params.get("project_id") or _header_project_id(self.request)
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.order_by("-created_at")

    def create(self, request):
        _assert_can_write(request.user)
        serializer = ExportWinnersRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(Project, pk=serializer.validated_data["project_id"])
        _assert_header_project_match(request, str(project.id))
        _assert_project_access(request.user, project)

        filters = {"status": serializer.validated_data.get("status", "CONFIRMED")}
        if serializer.validated_data.get("prize_id"):
            prize = get_object_or_404(Prize, pk=serializer.validated_data["prize_id"], project=project)
            filters["prize_id"] = str(prize.id)

        try:
            export_job = create_export_job(project=project, user=request.user, filters=filters)
        except Exception as exc:
            return Response({"message": f"导出失败: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(ExportJobSerializer(export_job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        export_job = self.get_object()
        _assert_header_project_match(request, str(export_job.project_id))
        file_path = Path(export_job.file_path)
        if export_job.status != "SUCCESS":
            return Response({"message": "导出任务尚未成功完成"}, status=status.HTTP_400_BAD_REQUEST)
        if not export_job.file_path or not file_path.exists():
            return Response({"message": "导出文件不存在"}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(
            file_path.open("rb"),
            as_attachment=True,
            filename=file_path.name,
            content_type="text/csv",
        )
