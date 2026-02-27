from __future__ import annotations

from django.contrib.auth import logout
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Department
from .serializers import AdminUserSerializer, DepartmentSerializer, LoginSerializer


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": AdminUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response({"message": "退出成功"}, status=status.HTTP_200_OK)


class MeView(APIView):
    def get(self, request):
        return Response(AdminUserSerializer(request.user).data, status=status.HTTP_200_OK)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.all().order_by("id")
    permission_classes = [permissions.IsAuthenticated]

    def _assert_write_permission(self):
        user = self.request.user
        if not (user.is_superuser or getattr(user, "role", "") == "SUPER_ADMIN"):
            raise PermissionDenied("仅超级管理员可维护部门")

    def perform_create(self, serializer):
        self._assert_write_permission()
        serializer.save()

    def perform_update(self, serializer):
        self._assert_write_permission()
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_write_permission()
        super().perform_destroy(instance)
