from django.contrib import admin

from .models import (
    Student,Feedback
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = (
        "student_id",
        "name",
        "faculty",
        "category",
        "course",
    )

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):

    list_display = ("student","rating","comment","created_at" )

