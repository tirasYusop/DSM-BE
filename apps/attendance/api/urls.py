from django.urls import path
from apps.attendance.views import mark_attendance, submit_activity, activity_list,my_activity

from ..views import (
    management_walkin,
    management_booking
)

urlpatterns = [
    path("mark/", mark_attendance),
    path("management/walk-in/", management_walkin),
    path("management/booking/", management_booking),
    path("activity/submit/", submit_activity),
    path("activity/list/", activity_list),
    path("my-activity/", my_activity, name="my-activity"),
]