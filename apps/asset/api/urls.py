from ..views import AssetViewSet, AssetMaintenanceViewSet, AssetDisposalViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"assets", AssetViewSet, basename="asset")
router.register(r"asset-maintenance", AssetMaintenanceViewSet, basename="asset-maintenance")
router.register(r"asset-disposal", AssetDisposalViewSet, basename="asset-disposal")

urlpatterns = [
    path('', include(router.urls)),
]
