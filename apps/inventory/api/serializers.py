
from rest_framework import serializers
from ..models import InventoryItem, InventoryRequest, SourceInventory,StockMovement,UsageLog, KitchenStockStatus

class UsageLogSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.display_name", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)

    class Meta:
        model = UsageLog
        fields = [
            "id", "item", "item_name", "unit", "usage_unit", "kitchen",
            "quantity", "reason", "recorded_by", "created_at",
        ]
        read_only_fields = ["recorded_by", "created_at"]


class KitchenStockStatusSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.display_name", read_only=True)
    kitchen_name = serializers.CharField(source="kitchen.code", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)

    class Meta:
        model = KitchenStockStatus
        fields = [
            "id", "item", "item_name", "unit", "kitchen", "kitchen_name",
            "status", "last_reported_quantity", "updated_by", "updated_at",
        ]
        read_only_fields = ["updated_by", "updated_at"]

class InventoryItemSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id", "name", "package_size", "unit", "price_per_unit",
            "display_name", "image", "created_at", "updated_at",
        ]

class SourceInventorySerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = SourceInventory
        fields = '__all__'

class StockMovementSerializer(serializers.ModelSerializer):

    item_name = serializers.CharField(
        source="item.name",
        read_only=True
    )
    display_name = serializers.CharField(
        source="item.display_name",
        read_only=True
    )

    kitchen_name = serializers.CharField(
        source="kitchen.code",
        read_only=True
    )

    destination = serializers.SerializerMethodField()

    def get_destination(self, obj):
        if obj.movement_type == "out" and obj.transfer_group:
            received = StockMovement.objects.filter(
                transfer_group=obj.transfer_group,
                movement_type="in",
                kitchen__isnull=False
            ).first()

            if received and received.kitchen:
                return received.kitchen.code

        return None


    class Meta:
        model = StockMovement

        fields = [
            "id",
            "item",
            "item_name",
            "display_name",
            "movement_type",
            "quantity",
            "source",
            "reason",
            "remarks",
            "purpose",
            "kitchen",
            "destination",
            "kitchen_name",
            "unit_price",
            "total_amount",
            "proof_image",
            "created_at",
        ]
class InventoryRequestSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.display_name", read_only=True)
    kitchen_name = serializers.CharField(source="kitchen.code", read_only=True)
    

    class Meta:
        model = InventoryRequest
        fields = "__all__"

class VolunteerDashboardSerializer(serializers.Serializer):
    summary = serializers.DictField()
    low_stock = serializers.ListField()
    recent_usage = serializers.ListField()
    pending_requests = serializers.ListField()
    stock = serializers.ListField()