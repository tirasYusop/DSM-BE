from rest_framework.routers import DefaultRouter
from django.urls import path, include
from ..views import (
    KitchenViewSet,
    VolunteerShiftViewSet,
    VolunteerProfileViewSet,
    ShiftSlotViewSet,
    ScheduledShiftViewSet,
)


router = DefaultRouter()


router.register(r"kitchens", KitchenViewSet, basename="kitchen")
router.register(r"volunteer-shifts", VolunteerShiftViewSet, basename="volunteer-shift")
router.register(r"volunteer-profiles", VolunteerProfileViewSet, basename="volunteer-profile")
router.register(r"shift-slots", ShiftSlotViewSet, basename="shift-slot")
router.register(r"scheduled-shifts", ScheduledShiftViewSet, basename="scheduled-shift")


urlpatterns = [
    path('', include(router.urls)),
]