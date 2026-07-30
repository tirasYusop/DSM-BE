from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import InventoryItemViewSet, InventoryRequestViewSet, SourceInventoryViewSet,StockMovementViewSet,UsageLogViewSet,KitchenStockStatusViewSet,LandingPageViewSet,VolunteerDashboardView
from ...storage.views import StudentStorageLogViewSet

router = DefaultRouter()
router.register(r'inventory', InventoryItemViewSet)
router.register(r'stock-movements', StockMovementViewSet)
router.register(r'source-inventory', SourceInventoryViewSet)
router.register(r'requests', InventoryRequestViewSet)
router.register(r'usage-logs', UsageLogViewSet)
router.register(r'kitchen-stock-status', KitchenStockStatusViewSet)
router.register(r"landing", LandingPageViewSet, basename="landing")
router.register(r'student-storage', StudentStorageLogViewSet, basename="student-storage")


urlpatterns = [
    path('', include(router.urls)),
    path('volunteer-dashboard/', VolunteerDashboardView.as_view(), name='volunteer-dashboard'),
]




