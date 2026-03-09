from __future__ import annotations

from apps.lottery.models import Customer, DrawWinner, DrawWinnerStatus, ProjectMember


def refresh_customer_stats_by_phone(phone: str) -> None:
    customer = Customer.objects.filter(phone=phone).first()
    if not customer:
        return

    participated_project_count = (
        ProjectMember.objects.filter(customer=customer).values("project_id").distinct().count()
    )

    claimed_prize_count = DrawWinner.objects.filter(
        customer=customer,
        status=DrawWinnerStatus.CONFIRMED,
        is_prize_claimed=True,
    ).count()

    first_member = (
        ProjectMember.objects.filter(customer=customer)
        .select_related("project")
        .order_by("created_at", "id")
        .first()
    )

    customer.participated_project_count = participated_project_count
    customer.claimed_prize_count = claimed_prize_count
    customer.first_project = first_member.project if first_member else None
    customer.first_participated_at = first_member.created_at if first_member else None
    customer.save(
        update_fields=[
            "participated_project_count",
            "claimed_prize_count",
            "first_project",
            "first_participated_at",
            "updated_at",
        ]
    )


def refresh_customer_stats_by_phones(phones: list[str] | set[str]) -> None:
    for phone in {phone for phone in phones if phone}:
        refresh_customer_stats_by_phone(phone)
