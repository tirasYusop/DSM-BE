from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        (
            "Role Info",
            {
                "fields": (
                    "role",
                    "kitchen",
                )
            }
        ),
    )


    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Role Info",
            {
                "fields": (
                    "role",
                    "kitchen",
                )
            }
        ),
    )


    list_display = (
        "username",
        "email",
        "role",
        "kitchen",
        "is_staff",
    )