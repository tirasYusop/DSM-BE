from django.contrib import admin
from .models import Kitchen,VolunteerProfile


@admin.register(Kitchen)
class KitchenAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "location","status", "is_active"]
    list_editable = ["status", "is_active"]
    list_filter = ["status", "is_active"]
    search_fields = ["name", "code"]

@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display =["name","kitchen"]