from __future__ import annotations

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from apps.accounts.admin import AdminUserAdmin, DepartmentAdmin
from apps.accounts.models import AdminUser, Department, UserRole
from apps.lottery.admin import DrawWinnerAdmin, ProjectAdmin, ProjectMemberAdmin
from apps.lottery.models import (
    Customer,
    DrawBatch,
    DrawBatchStatus,
    DrawWinner,
    DrawWinnerStatus,
    Prize,
    Project,
    ProjectMember,
)


class AdminIsolationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()

        self.dept_a = Department.objects.create(code="A", name="部门A", region="HZ-A")
        self.dept_b = Department.objects.create(code="B", name="部门B", region="HZ-B")

        self.super_admin = AdminUser.objects.create_user(
            username="super_admin",
            password="Test123456!",
            role=UserRole.SUPER_ADMIN,
            department=self.dept_a,
            is_staff=True,
            is_superuser=True,
        )
        self.dept_admin_a = AdminUser.objects.create_user(
            username="dept_admin_a",
            password="Test123456!",
            role=UserRole.DEPT_ADMIN,
            department=self.dept_a,
            is_staff=True,
        )
        self.operator_a = AdminUser.objects.create_user(
            username="operator_a",
            password="Test123456!",
            role=UserRole.OPERATOR,
            department=self.dept_a,
            is_staff=True,
        )
        self.viewer_a = AdminUser.objects.create_user(
            username="viewer_a",
            password="Test123456!",
            role=UserRole.VIEWER,
            department=self.dept_a,
            is_staff=True,
        )
        self.dept_admin_b = AdminUser.objects.create_user(
            username="dept_admin_b",
            password="Test123456!",
            role=UserRole.DEPT_ADMIN,
            department=self.dept_b,
            is_staff=True,
        )

        self.project_a = Project.objects.create(
            code="PA",
            name="项目A",
            department=self.dept_a,
            region="A",
            description="",
        )
        self.project_b = Project.objects.create(
            code="PB",
            name="项目B",
            department=self.dept_b,
            region="B",
            description="",
        )

        customer_a = Customer.objects.create(phone="13800000001", name="甲")
        customer_b = Customer.objects.create(phone="13800000002", name="乙")
        self.member_a = ProjectMember.objects.create(
            project=self.project_a,
            customer=customer_a,
            uid="UA001",
            name="甲",
            phone=customer_a.phone,
            is_active=True,
        )
        self.member_b = ProjectMember.objects.create(
            project=self.project_b,
            customer=customer_b,
            uid="UB001",
            name="乙",
            phone=customer_b.phone,
            is_active=True,
        )
        self.prize_a = Prize.objects.create(project=self.project_a, name="奖项A", total_count=10, used_count=0)
        self.prize_b = Prize.objects.create(project=self.project_b, name="奖项B", total_count=10, used_count=0)
        self.batch_a = DrawBatch.objects.create(
            project=self.project_a,
            prize=self.prize_a,
            requested_by=self.super_admin,
            draw_count=1,
            status=DrawBatchStatus.CONFIRMED,
        )
        self.batch_b = DrawBatch.objects.create(
            project=self.project_b,
            prize=self.prize_b,
            requested_by=self.super_admin,
            draw_count=1,
            status=DrawBatchStatus.CONFIRMED,
        )
        self.winner_a = DrawWinner.objects.create(
            batch=self.batch_a,
            project=self.project_a,
            prize=self.prize_a,
            customer=customer_a,
            uid="UA001",
            name="甲",
            phone=customer_a.phone,
            status=DrawWinnerStatus.CONFIRMED,
        )
        self.winner_b = DrawWinner.objects.create(
            batch=self.batch_b,
            project=self.project_b,
            prize=self.prize_b,
            customer=customer_b,
            uid="UB001",
            name="乙",
            phone=customer_b.phone,
            status=DrawWinnerStatus.CONFIRMED,
        )

    def _request(self, user):
        request = self.factory.get("/admin/")
        request.user = user
        return request

    def test_project_admin_queryset_scoped_by_department(self):
        admin_obj = ProjectAdmin(Project, self.site)

        super_qs = admin_obj.get_queryset(self._request(self.super_admin))
        self.assertEqual(super_qs.count(), 2)

        dept_admin_qs = admin_obj.get_queryset(self._request(self.dept_admin_a))
        self.assertEqual(list(dept_admin_qs.values_list("id", flat=True)), [self.project_a.id])

    def test_project_admin_permission_matrix(self):
        admin_obj = ProjectAdmin(Project, self.site)

        req_dept_admin = self._request(self.dept_admin_a)
        self.assertTrue(admin_obj.has_add_permission(req_dept_admin))
        self.assertTrue(admin_obj.has_change_permission(req_dept_admin, self.project_a))
        self.assertFalse(admin_obj.has_change_permission(req_dept_admin, self.project_b))

        req_operator = self._request(self.operator_a)
        self.assertFalse(admin_obj.has_add_permission(req_operator))
        self.assertFalse(admin_obj.has_change_permission(req_operator, self.project_a))

    def test_project_member_admin_scope_and_write_control(self):
        admin_obj = ProjectMemberAdmin(ProjectMember, self.site)

        operator_qs = admin_obj.get_queryset(self._request(self.operator_a))
        self.assertEqual(list(operator_qs.values_list("id", flat=True)), [self.member_a.id])
        self.assertTrue(admin_obj.has_add_permission(self._request(self.operator_a)))
        self.assertFalse(admin_obj.has_add_permission(self._request(self.viewer_a)))

        self.assertTrue(admin_obj.has_change_permission(self._request(self.operator_a), self.member_a))
        self.assertFalse(admin_obj.has_change_permission(self._request(self.operator_a), self.member_b))

    def test_admin_user_admin_scope_and_protection(self):
        admin_obj = AdminUserAdmin(AdminUser, self.site)

        dept_qs = admin_obj.get_queryset(self._request(self.dept_admin_a))
        self.assertTrue(all(user.department_id == self.dept_a.id for user in dept_qs))

        self.assertTrue(admin_obj.has_add_permission(self._request(self.dept_admin_a)))
        self.assertFalse(admin_obj.has_change_permission(self._request(self.dept_admin_a), self.super_admin))
        self.assertFalse(admin_obj.has_change_permission(self._request(self.dept_admin_a), self.dept_admin_b))

        super_qs = admin_obj.get_queryset(self._request(self.super_admin))
        self.assertEqual(super_qs.count(), 5)

    def test_department_admin_permissions(self):
        admin_obj = DepartmentAdmin(Department, self.site)

        req_dept_admin = self._request(self.dept_admin_a)
        self.assertTrue(admin_obj.has_module_permission(req_dept_admin))
        self.assertTrue(admin_obj.has_view_permission(req_dept_admin, self.dept_a))
        self.assertFalse(admin_obj.has_view_permission(req_dept_admin, self.dept_b))
        self.assertFalse(admin_obj.has_add_permission(req_dept_admin))
        self.assertFalse(admin_obj.has_change_permission(req_dept_admin, self.dept_a))

        self.assertTrue(admin_obj.has_add_permission(self._request(self.super_admin)))

    def test_admin_login_page_accessible_for_anonymous(self):
        # 回归测试: 匿名访问 /admin/login 不应触发 department_id 属性异常
        response = self.client.get("/admin/login/?next=/admin/")
        self.assertEqual(response.status_code, 200)

        request = self.factory.get("/admin/login/?next=/admin/")
        request.user = AnonymousUser()
        dept_admin = DepartmentAdmin(Department, self.site)
        user_admin = AdminUserAdmin(AdminUser, self.site)

        self.assertFalse(dept_admin.has_module_permission(request))
        self.assertFalse(user_admin.has_module_permission(request))

    def test_draw_winner_admin_scope_and_write_control(self):
        admin_obj = DrawWinnerAdmin(DrawWinner, self.site)

        operator_qs = admin_obj.get_queryset(self._request(self.operator_a))
        self.assertEqual(list(operator_qs.values_list("id", flat=True)), [self.winner_a.id])

        self.assertTrue(admin_obj.has_change_permission(self._request(self.operator_a), self.winner_a))
        self.assertFalse(admin_obj.has_change_permission(self._request(self.operator_a), self.winner_b))
        self.assertFalse(admin_obj.has_change_permission(self._request(self.viewer_a), self.winner_a))
