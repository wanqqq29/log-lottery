from __future__ import annotations

from django.contrib.auth import logout
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AdminUserSerializer, LoginSerializer


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
