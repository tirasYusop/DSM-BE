from django.contrib import admin
from .models import InventoryItem, InventoryRequest, SourceInventory, StockMovement


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'package_size', 'unit', 'price_per_unit', 'id')
    list_filter = ('unit',)
    search_fields = ('name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("item","kitchen","movement_type","quantity","created_at")
    list_filter = ("kitchen","movement_type",)
    search_fields = ('item__name',)
    ordering = ('-created_at',)

@admin.register(SourceInventory)
class SourceInventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'source', 'quantity')
    list_filter = ('source',)
    search_fields = ('item__name',)

@admin.register(InventoryRequest)
class InventoryRequestAdmin(admin.ModelAdmin):
    list_display = ('item', 'new_item_name', 'new_item_package_size', 'new_item_price_per_unit', 'status', 'quantity', 'created_at')
    list_filter = ('status',)
    search_fields = ('item__name', 'new_item_name')