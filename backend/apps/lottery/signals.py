from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.lottery.models import DrawWinner, ProjectMember
from apps.lottery.services.customer_stats import refresh_customer_stats_by_phone


@receiver(pre_save, sender=ProjectMember)
def project_member_pre_save(sender, instance: ProjectMember, **kwargs):
    if not instance.pk:
        instance._old_customer_id = None
        return
    instance._old_customer_id = (
        ProjectMember.objects.filter(pk=instance.pk).values_list("customer_id", flat=True).first()
    )


@receiver(post_save, sender=ProjectMember)
def project_member_post_save(sender, instance: ProjectMember, **kwargs):
    refresh_customer_stats_by_phone(instance.customer_id)
    old_customer_id = getattr(instance, "_old_customer_id", None)
    if old_customer_id and old_customer_id != instance.customer_id:
        refresh_customer_stats_by_phone(old_customer_id)


@receiver(post_delete, sender=ProjectMember)
def project_member_post_delete(sender, instance: ProjectMember, **kwargs):
    refresh_customer_stats_by_phone(instance.customer_id)


@receiver(pre_save, sender=DrawWinner)
def draw_winner_pre_save(sender, instance: DrawWinner, **kwargs):
    if not instance.pk:
        instance._old_customer_id = None
        return
    instance._old_customer_id = (
        DrawWinner.objects.filter(pk=instance.pk).values_list("customer_id", flat=True).first()
    )


@receiver(post_save, sender=DrawWinner)
def draw_winner_post_save(sender, instance: DrawWinner, **kwargs):
    refresh_customer_stats_by_phone(instance.customer_id)
    old_customer_id = getattr(instance, "_old_customer_id", None)
    if old_customer_id and old_customer_id != instance.customer_id:
        refresh_customer_stats_by_phone(old_customer_id)


@receiver(post_delete, sender=DrawWinner)
def draw_winner_post_delete(sender, instance: DrawWinner, **kwargs):
    refresh_customer_stats_by_phone(instance.customer_id)
