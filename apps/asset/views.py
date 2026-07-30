from django.shortcuts import render

from .models import Asset, AssetMaintenance, AssetDisposal
from .api.serializers import AssetSerializer, AssetMaintenanceSerializer, AssetDisposalSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated



class AssetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Asset.objects.all().order_by("-created_at")
    serializer_class = AssetSerializer

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """For dropdowns in Maintenance/Disposal forms — excludes already-disposed assets."""
        assets = Asset.objects.filter(status="active").order_by("name_brand")
        return Response(AssetSerializer(assets, many=True).data)

    @action(detail=False, methods=["get"], url_path="overview")
    def overview(self, request):
        """
        Full status table: ID, name, purchase date, original location,
        current status, and full transaction history per asset.
        """
        assets = Asset.objects.all().select_related("location").order_by("-created_at")
        data = []

        for asset in assets:
            transactions = []

            for m in asset.maintenance_records.all().order_by("-maintenance_date"):
                transactions.append({
                    "type": "maintenance",
                    "date": m.maintenance_date,
                    "notes": m.notes,
                })

            if hasattr(asset, "disposal_record"):
                d = asset.disposal_record
                transactions.append({
                    "type": "disposal",
                    "date": d.disposal_date,
                    "notes": d.reason,
                })

            transactions.sort(key=lambda t: t["date"], reverse=True)

            data.append({
                "id": asset.id,
                "name_brand": asset.name_brand,
                "purchase_date": asset.purchase_date,
                "original_location": asset.location.code if asset.location else None,
                "status": asset.status,
                "status_display": asset.get_status_display(),
                "transactions": transactions,
            })

        return Response(data)

    @action(detail=False, methods=["get"], url_path="annual-report")
    def annual_report(self, request):
        """
        Query params:
          - year (required): e.g. 2026
          - asset (optional): filter to one asset id
        """
        year = request.query_params.get("year")
        if not year:
            return Response({"error": "Year is required"}, status=400)

        try:
            year = int(year)
        except ValueError:
            return Response({"error": "Year must be a valid number"}, status=400)

        asset_id = request.query_params.get("asset")
        assets = Asset.objects.all().select_related("location")
        if asset_id:
            assets = assets.filter(id=asset_id)

        data = []
        for asset in assets:
            maintenance = asset.maintenance_records.filter(
                maintenance_date__year=year
            ).order_by("maintenance_date")

            disposal = None
            if hasattr(asset, "disposal_record") and asset.disposal_record.disposal_date.year == year:
                disposal = asset.disposal_record

            # Skip assets with zero activity in this year AND weren't purchased this year
            if not maintenance.exists() and not disposal and asset.purchase_date.year != year:
                continue

            events = []
            if asset.purchase_date.year == year:
                events.append({"type": "purchase", "date": asset.purchase_date, "notes": f"Dibeli - RM{asset.price}"})
            for m in maintenance:
                events.append({"type": "maintenance", "date": m.maintenance_date, "notes": m.notes})
            if disposal:
                events.append({"type": "disposal", "date": disposal.disposal_date, "notes": disposal.reason})

            events.sort(key=lambda e: e["date"])

            data.append({
                "id": asset.id,
                "name_brand": asset.name_brand,
                "location": asset.location.code if asset.location else None,
                "status_display": asset.get_status_display(),
                "events": events,
            })

        return Response(data)


class AssetMaintenanceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AssetMaintenance.objects.all().order_by("-maintenance_date")
    serializer_class = AssetMaintenanceSerializer

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class AssetDisposalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AssetDisposal.objects.all().order_by("-disposal_date")
    serializer_class = AssetDisposalSerializer

    def create(self, request, *args, **kwargs):
        asset_id = request.data.get("asset")
        try:
            asset = Asset.objects.get(id=asset_id)
        except Asset.DoesNotExist:
            return Response({"error": "Invalid asset"}, status=400)

        if asset.status == "disposed":
            return Response({"error": "Asset already disposed"}, status=400)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)