from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, LoginView, LogoutView, MeView

router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="department")

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("me", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
