from __future__ import annotations

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import AdminUser, Department, UserRole
from apps.lottery.models import Customer, Prize, Project, ProjectMember


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
