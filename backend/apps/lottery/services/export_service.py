from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.lottery.models import DrawWinner, ExportJob, ExportJobStatus, Project


def _resolve_export_root() -> Path:
    export_root = getattr(settings, "EXPORT_ROOT", settings.BASE_DIR / "exports")
    path = Path(export_root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _winner_queryset(*, project: Project, filters: dict[str, Any]):
    qs = DrawWinner.objects.filter(project=project).select_related("project", "prize")

    prize_id = filters.get("prize_id")
    if prize_id:
        qs = qs.filter(prize_id=prize_id)

    status = filters.get("status")
    if status:
        qs = qs.filter(status=status)

    return qs.order_by("created_at")


@transaction.atomic
def create_export_job(*, project: Project, user, filters: dict[str, Any]) -> ExportJob:
    export_job = ExportJob.objects.create(
        project=project,
        requested_by=user,
        filters=filters,
        status=ExportJobStatus.PENDING,
    )

    try:
        export_root = _resolve_export_root()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"winners-{project.code}-{ts}-{str(export_job.id)[:8]}.csv"
        full_path = export_root / file_name

        rows = _winner_queryset(project=project, filters=filters).values(
            "project__code",
            "project__name",
            "prize__name",
            "uid",
            "name",
            "phone",
            "status",
            "confirmed_at",
            "created_at",
            "void_reason",
        )

        with full_path.open("w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "project_code",
                "project_name",
                "prize_name",
                "uid",
                "name",
                "phone",
                "status",
                "confirmed_at",
                "draw_time",
                "void_reason",
            ])
            for row in rows:
                writer.writerow(
                    [
                        row["project__code"],
                        row["project__name"],
                        row["prize__name"],
                        row["uid"],
                        row["name"],
                        row["phone"],
                        row["status"],
                        row["confirmed_at"],
                        row["created_at"],
                        row["void_reason"],
                    ]
                )

        export_job.status = ExportJobStatus.SUCCESS
        export_job.file_path = str(full_path)
        export_job.save(update_fields=["status", "file_path", "updated_at"])
    except Exception as exc:
        export_job.status = ExportJobStatus.FAILED
        export_job.error_message = str(exc)[:255]
        export_job.save(update_fields=["status", "error_message", "updated_at"])
        raise

    return export_job
