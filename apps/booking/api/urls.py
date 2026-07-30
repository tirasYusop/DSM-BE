from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import (
    KitchenSlotViewSet,
    KitchenBookingViewSet,
)
router = DefaultRouter()
router.register(r'kitchen-slots',KitchenSlotViewSet)
router.register(r'kitchen-bookings',KitchenBookingViewSet)

urlpatterns = [
    path('',include(router.urls)),
]