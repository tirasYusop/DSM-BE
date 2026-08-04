from ..models import Asset, AssetMaintenance, AssetDisposal
from rest_framework import serializers

class AssetSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id", "name_brand", "purchase_date", "warranty", "price","quantity", "available_quantity",
            "source_type", "source_type_display","image",
            "location", "location_name",
            "status", "status_display",
            "created_at", "updated_at",
        ]


class AssetMaintenanceSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name_brand", read_only=True)
    current_location = serializers.CharField(source="asset.location.code", read_only=True)

    class Meta:
        model = AssetMaintenance
        fields = [
            "id", "asset", "asset_name", "current_location","quantity","photo_before","photo_after",
             "start_date", "end_date", "notes", "recorded_by", "created_at",
        ]
        read_only_fields = ["recorded_by", "created_at"]


class AssetDisposalSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name_brand", read_only=True)
    final_location = serializers.CharField(source="asset.location.code", read_only=True)

    class Meta:
        model = AssetDisposal
        fields = [
            "id", "asset", "asset_name", "final_location","quantity","photo",
            "disposal_date", "reason", "recorded_by", "created_at",
        ]
        read_only_fields = ["recorded_by", "created_at"]