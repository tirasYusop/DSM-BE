from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import (StudentViewSet,FeedbackViewSet)

router = DefaultRouter()
router.register(r"students",StudentViewSet)
router.register(r"feedback", FeedbackViewSet, basename="feedback")

urlpatterns = [path("",include(router.urls)),]