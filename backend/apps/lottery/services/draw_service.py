from __future__ import annotations

import random
from typing import Iterable

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.lottery.models import (
    DrawBatch,
    DrawBatchStatus,
    DrawWinner,
    DrawWinnerStatus,
    ExclusionRule,
    Prize,
    Project,
    ProjectMember,
)

_random = random.SystemRandom()


def normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def _excluded_phones_by_rule(project: Project, prize: Prize) -> set[str]:
    rules = ExclusionRule.objects.filter(target_project=project, is_enabled=True).filter(
        Q(target_prize__isnull=True) | Q(target_prize=prize)
    )
    if not rules.exists():
        return set()

    excluded: set[str] = set()
    for rule in rules:
        source_winners = DrawWinner.objects.filter(
            project=rule.source_project,
            status=DrawWinnerStatus.CONFIRMED,
        )
        if rule.source_prize_id:
            source_winners = source_winners.filter(prize_id=rule.source_prize_id)

        excluded.update(source_winners.values_list("phone", flat=True))

    return excluded


def build_candidate_queryset(project: Project, prize: Prize, scope: dict | None = None) -> QuerySet[ProjectMember]:
    scope = scope or {}
    qs = ProjectMember.objects.filter(project=project, is_active=True)

    include_uids: Iterable[str] = scope.get("include_uids") or []
    if include_uids:
        qs = qs.filter(uid__in=list(include_uids))

    include_phones: Iterable[str] = scope.get("include_phones") or []
    if include_phones:
        normalized = [normalize_phone(p) for p in include_phones]
        qs = qs.filter(phone__in=normalized)

    # 默认逻辑:
    # is_all=False -> 一个项目内只能中一次
    # is_all=True  -> 可以中多次，但不能重复中同一奖项
    if not prize.is_all:
        confirmed_project_phones = DrawWinner.objects.filter(
            project=project,
            status=DrawWinnerStatus.CONFIRMED,
        ).values_list("phone", flat=True)
        qs = qs.exclude(phone__in=confirmed_project_phones)
    else:
        confirmed_prize_phones = DrawWinner.objects.filter(
            project=project,
            prize=prize,
            status=DrawWinnerStatus.CONFIRMED,
        ).values_list("phone", flat=True)
        qs = qs.exclude(phone__in=confirmed_prize_phones)

    cross_project_excluded = _excluded_phones_by_rule(project, prize)
    if cross_project_excluded:
        qs = qs.exclude(phone__in=list(cross_project_excluded))

    return qs


@transaction.atomic
def preview_draw(*, project: Project, prize: Prize, count: int, user, scope: dict | None = None) -> DrawBatch:
    if count <= 0:
        raise ValueError("抽奖人数必须大于0")

    # 锁定奖项，避免并发超额
    prize_locked = Prize.objects.select_for_update().get(pk=prize.pk)
    left = prize_locked.total_count - prize_locked.used_count
    if left <= 0:
        raise ValueError("该奖项已抽完")

    real_count = min(count, left)
    candidates = list(build_candidate_queryset(project, prize_locked, scope))
    if len(candidates) < real_count:
        raise ValueError("符合条件的候选人数不足")

    selected_members = _random.sample(candidates, real_count)

    batch = DrawBatch.objects.create(
        project=project,
        prize=prize_locked,
        requested_by=user,
        draw_count=real_count,
        status=DrawBatchStatus.PENDING,
        draw_scope=scope or {},
    )

    DrawWinner.objects.bulk_create(
        [
            DrawWinner(
                batch=batch,
                project=project,
                prize=prize_locked,
                customer=member.customer,
                uid=member.uid,
                name=member.name,
                phone=member.phone,
                status=DrawWinnerStatus.PENDING,
            )
            for member in selected_members
        ]
    )

    return batch


@transaction.atomic
def confirm_batch(*, batch: DrawBatch, user) -> DrawBatch:
    batch_locked = DrawBatch.objects.select_for_update().select_related("prize").get(pk=batch.pk)
    if batch_locked.status != DrawBatchStatus.PENDING:
        raise ValueError("只有待确认批次可以确认")

    prize_locked = Prize.objects.select_for_update().get(pk=batch_locked.prize_id)
    winners = DrawWinner.objects.select_for_update().filter(batch=batch_locked, status=DrawWinnerStatus.PENDING)
    winner_count = winners.count()

    left = prize_locked.total_count - prize_locked.used_count
    if winner_count > left:
        raise ValueError("奖项剩余名额不足，无法确认")

    now = timezone.now()
    winners.update(status=DrawWinnerStatus.CONFIRMED, confirmed_at=now)
    prize_locked.used_count += winner_count
    prize_locked.save(update_fields=["used_count", "updated_at"])

    batch_locked.status = DrawBatchStatus.CONFIRMED
    batch_locked.save(update_fields=["status", "updated_at"])
    return batch_locked


@transaction.atomic
def void_batch(*, batch: DrawBatch, reason: str, user) -> DrawBatch:
    batch_locked = DrawBatch.objects.select_for_update().get(pk=batch.pk)
    if batch_locked.status != DrawBatchStatus.PENDING:
        raise ValueError("只有待确认批次可以作废")

    DrawWinner.objects.filter(batch=batch_locked, status=DrawWinnerStatus.PENDING).update(
        status=DrawWinnerStatus.VOID,
        void_reason=reason,
    )
    batch_locked.status = DrawBatchStatus.VOID
    batch_locked.void_reason = reason
    batch_locked.save(update_fields=["status", "void_reason", "updated_at"])
    return batch_locked
