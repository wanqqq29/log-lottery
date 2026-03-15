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
    MustWinEntry,
    Prize,
    Project,
    ProjectMember,
)
from apps.lottery.services.customer_stats import refresh_customer_stats_by_phones

_random = random.SystemRandom()


def normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def _dedupe_keep_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _prioritized_must_win_members(
    *,
    project: Project,
    prize: Prize,
    candidates: list[ProjectMember],
    count: int,
) -> list[ProjectMember]:
    if count <= 0 or not candidates:
        return []
    phone_to_member = {member.phone: member for member in candidates}
    candidate_phones = list(phone_to_member.keys())
    fixed_phones = list(
        MustWinEntry.objects.filter(
            project=project,
            is_active=True,
            target_prize=prize,
            phone__in=candidate_phones,
        )
        .order_by("created_at", "id")
        .values_list("phone", flat=True)
    )
    any_phones = list(
        MustWinEntry.objects.filter(project=project, is_active=True, phone__in=candidate_phones)
        .filter(target_prize__isnull=True)
        .order_by("created_at", "id")
        .values_list("phone", flat=True)
    )
    must_win_phones = fixed_phones + any_phones
    selected: list[ProjectMember] = []
    seen: set[str] = set()
    for phone in must_win_phones:
        member = phone_to_member.get(phone)
        if not member or member.phone in seen:
            continue
        selected.append(member)
        seen.add(member.phone)
        if len(selected) >= count:
            break
    return selected


def _consume_must_win_entries(*, project: Project, prize: Prize, winners: list[DrawWinner]) -> None:
    if not winners:
        return
    winner_by_phone = {winner.phone: winner for winner in winners}
    entries = list(
        MustWinEntry.objects.select_for_update()
        .filter(project=project, is_active=True, phone__in=list(winner_by_phone.keys()))
        .filter(Q(target_prize__isnull=True) | Q(target_prize=prize))
    )
    if not entries:
        return
    now = timezone.now()
    for entry in entries:
        winner = winner_by_phone.get(entry.phone)
        if not winner:
            continue
        entry.is_active = False
        entry.applied_winner = winner
        entry.applied_at = now
    MustWinEntry.objects.bulk_update(entries, ["is_active", "applied_winner", "applied_at"])


def _reactivate_must_win_entries_by_winner_ids(*, project: Project, winner_ids: list) -> None:
    if not winner_ids:
        return
    MustWinEntry.objects.filter(project=project, applied_winner_id__in=winner_ids).update(
        is_active=True,
        applied_winner=None,
        applied_at=None,
    )


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

    # 指定奖项的内定人，在未抽到指定奖项前，不参与其他奖项抽取
    fixed_other_prize_phones = MustWinEntry.objects.filter(
        project=project,
        is_active=True,
        target_prize__isnull=False,
    ).exclude(target_prize=prize).values_list("phone", flat=True)
    qs = qs.exclude(phone__in=fixed_other_prize_phones)

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
    candidates = list(build_candidate_queryset(project, prize_locked, scope).select_related("customer"))
    if len(candidates) < real_count:
        raise ValueError("符合条件的候选人数不足")

    must_win_members = _prioritized_must_win_members(project=project, prize=prize_locked, candidates=candidates, count=real_count)
    must_win_phones = {member.phone for member in must_win_members}
    left_count = real_count - len(must_win_members)
    random_candidates = [member for member in candidates if member.phone not in must_win_phones]
    random_members = _random.sample(random_candidates, left_count) if left_count > 0 else []
    selected_members = must_win_members + random_members

    draw_scope_payload = dict(scope or {})
    if must_win_members:
        draw_scope_payload["must_win_count"] = len(must_win_members)
        draw_scope_payload["must_win_phones"] = [member.phone for member in must_win_members]

    batch = DrawBatch.objects.create(
        project=project,
        prize=prize_locked,
        requested_by=user,
        draw_count=real_count,
        status=DrawBatchStatus.PENDING,
        draw_scope=draw_scope_payload,
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
def assign_manual_winners(*, project: Project, prize: Prize, phones: list[str], user, reason: str = "后台内定中奖") -> DrawBatch:
    parsed_phones: list[str] = []
    for phone in phones:
        normalized = normalize_phone(phone)
        if normalized:
            parsed_phones.append(normalized)
    normalized_phones = _dedupe_keep_order(parsed_phones)
    if not normalized_phones:
        raise ValueError("请至少提供 1 个有效手机号")

    if prize.project_id != project.id:
        raise ValueError("所选奖项不属于当前项目")

    prize_locked = Prize.objects.select_for_update().get(pk=prize.pk)
    left = prize_locked.total_count - prize_locked.used_count
    if left <= 0:
        raise ValueError("该奖项已抽完")
    if len(normalized_phones) > left:
        raise ValueError(f"奖项剩余名额不足，剩余 {left} 个")

    candidates = list(
        build_candidate_queryset(project, prize_locked)
        .filter(phone__in=normalized_phones)
        .select_related("customer")
    )
    member_by_phone = {member.phone: member for member in candidates}
    ineligible = [phone for phone in normalized_phones if phone not in member_by_phone]
    if ineligible:
        limited = "、".join(ineligible[:10])
        suffix = "..." if len(ineligible) > 10 else ""
        raise ValueError(f"以下手机号不符合当前中奖条件或不在有效名单中: {limited}{suffix}")

    now = timezone.now()
    batch = DrawBatch.objects.create(
        project=project,
        prize=prize_locked,
        requested_by=user,
        draw_count=len(normalized_phones),
        status=DrawBatchStatus.CONFIRMED,
        draw_scope={
            "manual_assign": True,
            "reason": reason or "后台内定中奖",
            "phones": normalized_phones,
        },
    )

    created_winners = DrawWinner.objects.bulk_create(
        [
            DrawWinner(
                batch=batch,
                project=project,
                prize=prize_locked,
                customer=member_by_phone[phone].customer,
                uid=member_by_phone[phone].uid,
                name=member_by_phone[phone].name,
                phone=phone,
                status=DrawWinnerStatus.CONFIRMED,
                confirmed_at=now,
            )
            for phone in normalized_phones
        ]
    )
    created_winners = list(created_winners)
    if created_winners and any(not winner.pk for winner in created_winners):
        created_winners = list(DrawWinner.objects.filter(batch=batch, status=DrawWinnerStatus.CONFIRMED))
    _consume_must_win_entries(project=project, prize=prize_locked, winners=created_winners)

    prize_locked.used_count += len(normalized_phones)
    prize_locked.save(update_fields=["used_count", "updated_at"])
    refresh_customer_stats_by_phones(normalized_phones)
    return batch


@transaction.atomic
def register_must_win_entries(
    *,
    project: Project,
    phones: list[str],
    user,
    reason: str = "后台内定必中奖",
    target_prize: Prize | None = None,
) -> dict[str, int]:
    parsed_phones: list[str] = []
    for phone in phones:
        normalized = normalize_phone(phone)
        if normalized:
            parsed_phones.append(normalized)
    normalized_phones = _dedupe_keep_order(parsed_phones)
    if not normalized_phones:
        raise ValueError("请至少提供 1 个有效手机号")

    members = list(
        ProjectMember.objects.select_related("customer")
        .filter(project=project, is_active=True, phone__in=normalized_phones)
        .order_by("id")
    )
    member_by_phone = {member.phone: member for member in members}
    missing = [phone for phone in normalized_phones if phone not in member_by_phone]
    if missing:
        limited = "、".join(missing[:10])
        suffix = "..." if len(missing) > 10 else ""
        raise ValueError(f"以下手机号不在项目有效成员中: {limited}{suffix}")

    already_won = set(
        DrawWinner.objects.filter(
            project=project,
            status=DrawWinnerStatus.CONFIRMED,
            phone__in=normalized_phones,
        ).values_list("phone", flat=True)
    )
    if already_won:
        limited = "、".join(list(already_won)[:10])
        suffix = "..." if len(already_won) > 10 else ""
        raise ValueError(f"以下手机号已是确认中奖，无需设置必中奖: {limited}{suffix}")

    created_count = 0
    reactivated_count = 0
    existed_count = 0
    for phone in normalized_phones:
        member = member_by_phone[phone]
        entry, created = MustWinEntry.objects.get_or_create(
            project=project,
            customer=member.customer,
            defaults={
                "phone": phone,
                "name": member.name,
                "note": reason or "后台内定必中奖",
                "target_prize": target_prize,
                "created_by": user if getattr(user, "is_authenticated", False) else None,
                "is_active": True,
            },
        )
        if created:
            created_count += 1
            continue

        entry.phone = phone
        entry.name = member.name
        entry.note = reason or entry.note
        entry.target_prize = target_prize
        if not entry.is_active:
            entry.is_active = True
            entry.applied_winner = None
            entry.applied_at = None
            reactivated_count += 1
        else:
            existed_count += 1
        entry.save(
            update_fields=[
                "phone",
                "name",
                "note",
                "target_prize",
                "is_active",
                "applied_winner",
                "applied_at",
                "updated_at",
            ]
        )

    refresh_customer_stats_by_phones(normalized_phones)
    return {
        "total": len(normalized_phones),
        "created": created_count,
        "reactivated": reactivated_count,
        "existed": existed_count,
    }


@transaction.atomic
def confirm_batch(*, batch: DrawBatch, user) -> DrawBatch:
    batch_locked = DrawBatch.objects.select_for_update().select_related("prize").get(pk=batch.pk)
    if batch_locked.status != DrawBatchStatus.PENDING:
        raise ValueError("只有待确认批次可以确认")

    prize_locked = Prize.objects.select_for_update().get(pk=batch_locked.prize_id)
    winners = list(
        DrawWinner.objects.select_for_update().filter(batch=batch_locked, status=DrawWinnerStatus.PENDING)
    )
    winner_count = len(winners)

    left = prize_locked.total_count - prize_locked.used_count
    if winner_count > left:
        raise ValueError("奖项剩余名额不足，无法确认")

    now = timezone.now()
    winner_ids = [winner.id for winner in winners]
    DrawWinner.objects.filter(id__in=winner_ids).update(status=DrawWinnerStatus.CONFIRMED, confirmed_at=now)
    for winner in winners:
        winner.status = DrawWinnerStatus.CONFIRMED
        winner.confirmed_at = now
    _consume_must_win_entries(project=batch_locked.project, prize=prize_locked, winners=winners)
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


@transaction.atomic
def revoke_confirmed_winner(*, winner: DrawWinner, reason: str, user) -> DrawWinner:
    winner_locked = DrawWinner.objects.select_for_update().select_related("prize").get(pk=winner.pk)
    if winner_locked.status != DrawWinnerStatus.CONFIRMED:
        raise ValueError("仅已确认中奖记录可撤销")

    prize_locked = Prize.objects.select_for_update().get(pk=winner_locked.prize_id)
    if prize_locked.used_count > 0:
        prize_locked.used_count -= 1
        prize_locked.save(update_fields=["used_count", "updated_at"])

    winner_locked.status = DrawWinnerStatus.VOID
    winner_locked.void_reason = reason
    winner_locked.confirmed_at = None
    winner_locked.is_prize_claimed = False
    winner_locked.prize_claimed_at = None
    winner_locked.save(
        update_fields=[
            "status",
            "void_reason",
            "confirmed_at",
            "is_prize_claimed",
            "prize_claimed_at",
            "updated_at",
        ]
    )
    _reactivate_must_win_entries_by_winner_ids(project=winner_locked.project, winner_ids=[winner_locked.id])
    return winner_locked


@transaction.atomic
def reset_project_winners(*, project: Project, reason: str, user) -> dict[str, int]:
    winners = DrawWinner.objects.select_for_update().filter(
        project=project,
        status__in=[DrawWinnerStatus.PENDING, DrawWinnerStatus.CONFIRMED],
    )
    affected_phones = set(winners.values_list("phone", flat=True))
    confirmed_winner_ids = list(winners.filter(status=DrawWinnerStatus.CONFIRMED).values_list("id", flat=True))
    affected = winners.count()
    if affected:
        winners.update(
            status=DrawWinnerStatus.VOID,
            void_reason=reason,
            confirmed_at=None,
            is_prize_claimed=False,
            prize_claimed_at=None,
            is_visited=False,
            visited_at=None,
        )
    _reactivate_must_win_entries_by_winner_ids(project=project, winner_ids=confirmed_winner_ids)

    prizes = Prize.objects.select_for_update().filter(project=project)
    for prize in prizes:
        prize.used_count = DrawWinner.objects.filter(
            project=project,
            prize=prize,
            status=DrawWinnerStatus.CONFIRMED,
        ).count()
        prize.save(update_fields=["used_count", "updated_at"])

    batches = DrawBatch.objects.select_for_update().filter(project=project, status__in=[DrawBatchStatus.PENDING, DrawBatchStatus.CONFIRMED])
    batch_affected = batches.count()
    if batch_affected:
        batches.update(status=DrawBatchStatus.VOID, void_reason=reason)

    refresh_customer_stats_by_phones(affected_phones)

    return {
        "winner_affected": affected,
        "batch_affected": batch_affected,
    }
    if target_prize and target_prize.project_id != project.id:
        raise ValueError("所选奖项不属于该项目")
