from __future__ import annotations

from django.test import TestCase

from apps.accounts.models import AdminUser, Department, UserRole
from apps.lottery.models import (
    Customer,
    DrawBatchStatus,
    DrawWinner,
    DrawWinnerStatus,
    MustWinEntry,
    Prize,
    Project,
    ProjectMember,
)
from apps.lottery.services.draw_service import assign_manual_winners, confirm_batch, preview_draw, register_must_win_entries


class ManualAssignWinnerServiceTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="MANUAL-DEPT", name="内定部门", region="HZ")
        self.user = AdminUser.objects.create_user(
            username="manual_super",
            password="Test123456!",
            role=UserRole.SUPER_ADMIN,
            department=self.department,
            is_staff=True,
            is_superuser=True,
        )
        self.project = Project.objects.create(
            code="MANUAL-PROJECT",
            name="内定测试项目",
            department=self.department,
            region="HZ",
            description="",
        )
        self.prize = Prize.objects.create(
            project=self.project,
            name="一等奖",
            sort=1,
            is_all=False,
            total_count=3,
            used_count=0,
        )
        self.prize_second = Prize.objects.create(
            project=self.project,
            name="二等奖",
            sort=2,
            is_all=False,
            total_count=3,
            used_count=0,
        )
        self.customer_a = Customer.objects.create(phone="13800001001", name="甲")
        self.customer_b = Customer.objects.create(phone="13800001002", name="乙")
        ProjectMember.objects.create(
            project=self.project,
            customer=self.customer_a,
            uid="UA001",
            name="甲",
            phone=self.customer_a.phone,
            is_active=True,
        )
        ProjectMember.objects.create(
            project=self.project,
            customer=self.customer_b,
            uid="UB001",
            name="乙",
            phone=self.customer_b.phone,
            is_active=True,
        )

    def test_assign_manual_winners_creates_confirmed_batch_and_winners(self):
        batch = assign_manual_winners(
            project=self.project,
            prize=self.prize,
            phones=[self.customer_a.phone, self.customer_b.phone],
            user=self.user,
            reason="测试内定",
        )

        self.assertEqual(batch.status, DrawBatchStatus.CONFIRMED)
        self.assertEqual(batch.draw_count, 2)
        self.assertTrue(batch.draw_scope.get("manual_assign"))

        winners = DrawWinner.objects.filter(batch=batch).order_by("phone")
        self.assertEqual(winners.count(), 2)
        self.assertTrue(all(winner.status == DrawWinnerStatus.CONFIRMED for winner in winners))

        self.prize.refresh_from_db()
        self.assertEqual(self.prize.used_count, 2)

    def test_assign_manual_winners_rejects_phone_not_in_project_member(self):
        with self.assertRaisesMessage(ValueError, "不符合当前中奖条件或不在有效名单中"):
            assign_manual_winners(
                project=self.project,
                prize=self.prize,
                phones=[self.customer_a.phone, "13899990000"],
                user=self.user,
                reason="测试",
            )

    def test_register_must_win_entries_then_preview_prioritizes_it(self):
        customer_c = Customer.objects.create(phone="13800001003", name="丙")
        ProjectMember.objects.create(
            project=self.project,
            customer=customer_c,
            uid="UC001",
            name="丙",
            phone=customer_c.phone,
            is_active=True,
        )

        result = register_must_win_entries(
            project=self.project,
            phones=[self.customer_b.phone],
            user=self.user,
            reason="必中奖测试",
        )
        self.assertEqual(result["created"], 1)
        self.assertTrue(MustWinEntry.objects.filter(project=self.project, phone=self.customer_b.phone, is_active=True).exists())

        batch = preview_draw(
            project=self.project,
            prize=self.prize_second,
            count=1,
            user=self.user,
            scope={},
        )
        winner = DrawWinner.objects.get(batch=batch)
        self.assertEqual(winner.phone, self.customer_b.phone)
        self.assertEqual(batch.status, DrawBatchStatus.PENDING)
        self.assertEqual(batch.draw_scope.get("must_win_count"), 1)

        confirm_batch(batch=batch, user=self.user)
        entry = MustWinEntry.objects.get(project=self.project, phone=self.customer_b.phone)
        self.assertFalse(entry.is_active)
        self.assertIsNotNone(entry.applied_winner_id)

    def test_fixed_prize_setting_is_staged_until_target_prize_draw(self):
        register_must_win_entries(
            project=self.project,
            phones=[self.customer_a.phone],
            user=self.user,
            reason="固定一等奖",
            target_prize=self.prize,
        )

        self.prize.refresh_from_db()
        self.assertEqual(self.prize.used_count, 0)
        self.assertEqual(DrawWinner.objects.count(), 0)

        second_batch = preview_draw(
            project=self.project,
            prize=self.prize_second,
            count=1,
            user=self.user,
            scope={},
        )
        second_winner = DrawWinner.objects.get(batch=second_batch)
        self.assertNotEqual(second_winner.phone, self.customer_a.phone)
        confirm_batch(batch=second_batch, user=self.user)

        self.prize.refresh_from_db()
        self.assertEqual(self.prize.used_count, 0)

        first_batch = preview_draw(
            project=self.project,
            prize=self.prize,
            count=1,
            user=self.user,
            scope={},
        )
        first_winner = DrawWinner.objects.get(batch=first_batch)
        self.assertEqual(first_winner.phone, self.customer_a.phone)
        confirm_batch(batch=first_batch, user=self.user)

        self.prize.refresh_from_db()
        self.assertEqual(self.prize.used_count, 1)
