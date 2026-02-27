from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DrawBatchViewSet,
    DrawWinnerViewSet,
    ExclusionRuleViewSet,
    ExportJobViewSet,
    PrizeViewSet,
    ProjectMemberViewSet,
    ProjectViewSet,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"project-members", ProjectMemberViewSet, basename="project-member")
router.register(r"prizes", PrizeViewSet, basename="prize")
router.register(r"draw-batches", DrawBatchViewSet, basename="draw-batch")
router.register(r"draw-winners", DrawWinnerViewSet, basename="draw-winner")
router.register(r"exclusion-rules", ExclusionRuleViewSet, basename="exclusion-rule")
router.register(r"export-jobs", ExportJobViewSet, basename="export-job")

urlpatterns = [
    path("", include(router.urls)),
]
