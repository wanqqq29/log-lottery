from __future__ import annotations

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import AdminUser, Department, UserRole
from apps.lottery.models import Customer, DrawWinner, Prize, Project, ProjectMember


@override_settings(ALLOWED_HOSTS=["testserver", "127.0.0.1", "localhost"])
class LotteryApiPermissionTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(code="TEST-DEPT", name="测试部门", region="HZ")
        self.super_admin = AdminUser.objects.create_user(
            username="test_super_admin",
            password="Test123456!",
            role=UserRole.SUPER_ADMIN,
            department=self.department,
            is_staff=True,
        )
        self.viewer = AdminUser.objects.create_user(
            username="test_viewer",
            password="Test123456!",
            role=UserRole.VIEWER,
            department=self.department,
            is_staff=True,
        )
        self.operator = AdminUser.objects.create_user(
            username="test_operator",
            password="Test123456!",
            role=UserRole.OPERATOR,
            department=self.department,
            is_staff=True,
        )
        self.dept_admin = AdminUser.objects.create_user(
            username="test_dept_admin",
            password="Test123456!",
            role=UserRole.DEPT_ADMIN,
            department=self.department,
            is_staff=True,
        )
        self.project = Project.objects.create(
            code="TEST-PROJ-01",
            name="测试项目",
            department=self.department,
            region="HZ",
            description="",
            is_active=True,
        )
        self.prize = Prize.objects.create(
            project=self.project,
            name="一等奖",
            sort=1,
            is_all=False,
            total_count=2,
            used_count=0,
            separate_count={},
            description="",
            is_active=True,
        )
        customer = Customer.objects.create(phone="13800138000", name="张三")
        ProjectMember.objects.create(
            project=self.project,
            customer=customer,
            uid="U001",
            name="张三",
            phone=customer.phone,
            is_active=True,
        )
        self.other_department = Department.objects.create(code="TEST-DEPT-2", name="测试部门2", region="HZ")
        self.other_project = Project.objects.create(
            code="TEST-PROJ-02",
            name="跨部门项目",
            department=self.other_department,
            region="HZ",
            description="",
            is_active=True,
        )

    def _preview_and_confirm(self):
        preview_resp = self.client.post(
            "/api/draw-batches/preview/",
            {
                "project_id": str(self.project.id),
                "prize_id": str(self.prize.id),
                "count": 1,
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(preview_resp.status_code, 201)
        self.assertEqual(len(preview_resp.data["winners"]), 1)
        winner_phone = preview_resp.data["winners"][0]["phone"]
        batch_id = preview_resp.data["id"]

        confirm_resp = self.client.post(
            f"/api/draw-batches/{batch_id}/confirm/",
            {},
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(confirm_resp.status_code, 200)
        return winner_phone

    def test_viewer_can_read_projects(self):
        self.client.force_authenticate(user=self.viewer)
        resp = self.client.get("/api/projects/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_viewer_cannot_create_export_job(self):
        self.client.force_authenticate(user=self.viewer)
        resp = self.client.post(
            "/api/export-jobs/",
            {
                "project_id": str(self.project.id),
                "status": "CONFIRMED",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(resp.status_code, 403)

    def test_operator_cannot_create_project(self):
        self.client.force_authenticate(user=self.operator)
        resp = self.client.post(
            "/api/projects/",
            {
                "code": "TEST-PROJ-OP",
                "name": "运营创建项目",
                "department": self.department.id,
                "region": "HZ",
                "description": "",
                "is_active": True,
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(resp.status_code, 403)

    def test_dept_admin_can_create_project(self):
        self.client.force_authenticate(user=self.dept_admin)
        resp = self.client.post(
            "/api/projects/",
            {
                "code": "TEST-PROJ-DA",
                "name": "部门管理员创建项目",
                "department": self.department.id,
                "region": "HZ",
                "description": "",
                "is_active": True,
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(resp.status_code, 201)

    def test_preview_rejects_mismatched_project_header(self):
        self.client.force_authenticate(user=self.super_admin)
        resp = self.client.post(
            "/api/draw-batches/preview/",
            {
                "project_id": str(self.project.id),
                "prize_id": str(self.prize.id),
                "count": 1,
            },
            format="json",
            HTTP_X_PROJECT_ID="00000000-0000-0000-0000-000000000000",
        )
        self.assertEqual(resp.status_code, 403)

    def test_confirm_then_revoke_updates_used_count(self):
        self.client.force_authenticate(user=self.super_admin)

        preview_resp = self.client.post(
            "/api/draw-batches/preview/",
            {
                "project_id": str(self.project.id),
                "prize_id": str(self.prize.id),
                "count": 1,
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(preview_resp.status_code, 201)
        batch_id = preview_resp.data["id"]

        confirm_resp = self.client.post(
            f"/api/draw-batches/{batch_id}/confirm/",
            {},
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(confirm_resp.status_code, 200)

        self.prize.refresh_from_db()
        self.assertEqual(self.prize.used_count, 1)

        winner_list_resp = self.client.get(
            "/api/draw-winners/",
            {"project_id": str(self.project.id), "status": "CONFIRMED"},
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(winner_list_resp.status_code, 200)
        self.assertEqual(len(winner_list_resp.data), 1)
        winner_id = winner_list_resp.data[0]["id"]

        revoke_resp = self.client.post(
            f"/api/draw-winners/{winner_id}/revoke/",
            {"reason": "测试撤销"},
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(revoke_resp.status_code, 200)

        self.prize.refresh_from_db()
        self.assertEqual(self.prize.used_count, 0)

    def test_register_arrival_marks_claim_and_updates_customer_stats(self):
        self.client.force_authenticate(user=self.super_admin)
        winner_phone = self._preview_and_confirm()

        register_resp = self.client.post(
            "/api/draw-winners/register-arrival/",
            {
                "project_id": str(self.project.id),
                "phone": winner_phone,
                "is_prize_claimed": True,
                "claim_note": "客户到访并已领奖",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(register_resp.status_code, 200)
        self.assertTrue(register_resp.data["is_visited"])
        self.assertTrue(register_resp.data["is_prize_claimed"])
        self.assertEqual(register_resp.data["claim_note"], "客户到访并已领奖")

        customer = Customer.objects.get(phone=winner_phone)
        self.assertEqual(customer.participated_project_count, 1)
        self.assertEqual(customer.claimed_prize_count, 1)
        self.assertEqual(customer.first_project_id, self.project.id)
        self.assertIsNotNone(customer.first_participated_at)

    def test_register_arrival_allows_empty_claim_note(self):
        self.client.force_authenticate(user=self.super_admin)
        winner_phone = self._preview_and_confirm()
        register_resp = self.client.post(
            "/api/draw-winners/register-arrival/",
            {
                "project_id": str(self.project.id),
                "phone": winner_phone,
                "is_prize_claimed": True,
                "claim_note": "",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(register_resp.status_code, 200)
        self.assertEqual(register_resp.data["claim_note"], "")

    def test_viewer_can_register_arrival(self):
        self.client.force_authenticate(user=self.super_admin)
        winner_phone = self._preview_and_confirm()

        self.client.force_authenticate(user=self.viewer)
        register_resp = self.client.post(
            "/api/draw-winners/register-arrival/",
            {
                "project_id": str(self.project.id),
                "phone": winner_phone,
                "is_prize_claimed": True,
                "claim_note": "只读账号登记",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(register_resp.status_code, 200)
        self.assertTrue(register_resp.data["is_prize_claimed"])

    def test_export_arrival_scoped_and_downloadable(self):
        self.client.force_authenticate(user=self.super_admin)
        winner_phone = self._preview_and_confirm()
        self.client.post(
            "/api/draw-winners/register-arrival/",
            {
                "project_id": str(self.project.id),
                "phone": winner_phone,
                "is_prize_claimed": True,
                "claim_note": "导出测试",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )

        self.client.force_authenticate(user=self.viewer)
        resp = self.client.get(
            "/api/draw-winners/export-arrival/",
            {
                "project_id": str(self.project.id),
                "arrival_state": "CLAIMED",
            },
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("winner-arrival", resp["Content-Disposition"])

        cross_resp = self.client.get(
            "/api/draw-winners/export-arrival/",
            {
                "project_id": str(self.other_project.id),
                "arrival_state": "CLAIMED",
            },
            HTTP_X_PROJECT_ID=str(self.other_project.id),
        )
        self.assertEqual(cross_resp.status_code, 403)

    def test_dashboard_returns_metrics(self):
        self.client.force_authenticate(user=self.super_admin)
        winner_phone = self._preview_and_confirm()
        self.client.post(
            "/api/draw-winners/register-arrival/",
            {
                "project_id": str(self.project.id),
                "phone": winner_phone,
                "is_prize_claimed": True,
                "claim_note": "看板测试",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )

        self.client.force_authenticate(user=self.viewer)
        resp = self.client.get(
            "/api/draw-winners/dashboard/",
            {
                "project_id": str(self.project.id),
                "days": 7,
            },
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["project_id"], str(self.project.id))
        self.assertEqual(resp.data["claimed_total"], 1)
        self.assertGreaterEqual(len(resp.data["prize_stats"]), 1)
        self.assertEqual(len(resp.data["daily_stats"]), 7)

    def test_bulk_upsert_accepts_missing_uid_and_defaults_to_phone(self):
        self.client.force_authenticate(user=self.super_admin)
        resp = self.client.post(
            "/api/project-members/bulk-upsert/",
            {
                "project_id": str(self.project.id),
                "members": [
                    {"name": "李四", "phone": "13800138001"},
                ],
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["created_count"], 1)

        member = ProjectMember.objects.get(project=self.project, phone="13800138001")
        self.assertEqual(member.uid, "13800138001")
        self.assertEqual(member.name, "李四")

    def test_bulk_upsert_rejects_duplicate_phone(self):
        self.client.force_authenticate(user=self.super_admin)
        resp = self.client.post(
            "/api/project-members/bulk-upsert/",
            {
                "project_id": str(self.project.id),
                "members": [
                    {"name": "李四", "phone": "13800138001"},
                    {"name": "李四-重复", "phone": "13800138001"},
                ],
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("存在重复手机号", str(resp.data))

    def test_draw_winner_list_supports_phone_filter(self):
        self.client.force_authenticate(user=self.super_admin)
        winner_phone = self._preview_and_confirm()

        filtered = self.client.get(
            "/api/draw-winners/",
            {
                "project_id": str(self.project.id),
                "status": "CONFIRMED",
                "phone": winner_phone,
            },
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.data), 1)
        self.assertEqual(filtered.data[0]["phone"], winner_phone)

        empty = self.client.get(
            "/api/draw-winners/",
            {
                "project_id": str(self.project.id),
                "status": "CONFIRMED",
                "phone": "13999990000",
            },
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(len(empty.data), 0)

    def test_register_visit_allows_non_winner_and_query_arrival_visits(self):
        self.client.force_authenticate(user=self.viewer)
        phone = "13900001111"
        register_resp = self.client.post(
            "/api/draw-winners/register-visit/",
            {
                "project_id": str(self.project.id),
                "phone": phone,
                "name": "到访客户",
                "is_prize_claimed": True,
                "claim_note": "未中奖到访领取礼品",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(register_resp.status_code, 201)
        self.assertEqual(register_resp.data["phone"], phone)
        self.assertEqual(register_resp.data["name"], "到访客户")
        self.assertEqual(register_resp.data["status"], "CONFIRMED")
        self.assertTrue(register_resp.data["is_visited"])
        self.assertTrue(register_resp.data["is_prize_claimed"])
        self.assertEqual(register_resp.data["claim_note"], "未中奖到访领取礼品")

        reward_winner = DrawWinner.objects.get(project=self.project, phone=phone, status="CONFIRMED")
        self.assertEqual(reward_winner.prize.name, "到访奖励")
        self.assertTrue(reward_winner.is_visited)
        self.assertTrue(reward_winner.is_prize_claimed)

        list_resp = self.client.get(
            "/api/draw-winners/arrival-visits/",
            {
                "project_id": str(self.project.id),
                "phone": phone,
                "limit": 10,
            },
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.data), 1)
        self.assertEqual(list_resp.data[0]["phone"], phone)
        self.assertTrue(list_resp.data[0]["is_visited"])
        self.assertEqual(list_resp.data[0]["status"], "CONFIRMED")

    def test_register_visit_syncs_confirmed_winner(self):
        self.client.force_authenticate(user=self.super_admin)
        winner_phone = self._preview_and_confirm()

        register_resp = self.client.post(
            "/api/draw-winners/register-visit/",
            {
                "project_id": str(self.project.id),
                "phone": winner_phone,
                "is_prize_claimed": False,
                "claim_note": "中奖客户到访但暂未领取",
            },
            format="json",
            HTTP_X_PROJECT_ID=str(self.project.id),
        )
        self.assertEqual(register_resp.status_code, 200)
        self.assertEqual(register_resp.data["status"], "CONFIRMED")
        self.assertFalse(register_resp.data["is_prize_claimed"])

        winner = DrawWinner.objects.get(
            project=self.project,
            phone=winner_phone,
            status="CONFIRMED",
        )
        self.assertTrue(winner.is_visited)
        self.assertFalse(winner.is_prize_claimed)
        self.assertEqual(winner.claim_note, "中奖客户到访但暂未领取")
