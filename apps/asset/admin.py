from django.contrib import admin
from .models import Asset, AssetMaintenance, AssetDisposal


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name_brand', 'purchase_date', 'location', 'price', 'source_type')

@admin.register(AssetMaintenance)
class AssetMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('asset', 'notes','recorded_by' )

@admin.register(AssetDisposal)
class AssetDisposalAdmin(admin.ModelAdmin):
    list_display = ('asset','disposal_date','reason')

