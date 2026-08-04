from django.shortcuts import render

from .models import Asset, AssetMaintenance, AssetDisposal
from .api.serializers import AssetSerializer, AssetMaintenanceSerializer, AssetDisposalSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsManagement

def _image_url(request, image_field):
    if not image_field:
        return None
    try:
        return request.build_absolute_uri(image_field.url)
    except ValueError:
        return None


class AssetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManagement]
    queryset = Asset.objects.all().order_by("-created_at")
    serializer_class = AssetSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        quantity = request.data.get("quantity")

        if quantity is not None:
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return Response({"error": "Quantity must be a whole number"}, status=400)

            committed = instance.disposed_quantity + instance.in_maintenance_quantity
            if quantity < committed:
                return Response(
                    {
                        "error": f"Kuantiti tidak boleh kurang daripada {committed} "
                                 f"(jumlah unit yang sudah direkodkan dalam penyelenggaraan/pelupusan)"
                    },
                    status=400,
                )

        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        candidates = Asset.objects.exclude(status="disposed").order_by("name_brand")
        assets = [a for a in candidates if a.available_quantity > 0]
        return Response(AssetSerializer(assets, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="overview")
    def overview(self, request):
        assets = Asset.objects.all().select_related("location").order_by("-created_at")
        data = []

        for asset in assets:
            transactions = []

            for m in asset.maintenance_records.all().order_by("-start_date"):
                transactions.append({
                    "type": "maintenance",
                    "date": m.start_date,
                    "end_date": m.end_date,
                    "quantity": m.quantity,
                    "notes": m.notes,
                    "photo_before": _image_url(request, m.photo_before),
                    "photo_after": _image_url(request, m.photo_after),
                })

            for d in asset.disposal_records.all().order_by("-disposal_date"):
                transactions.append({
                    "type": "disposal",
                    "date": d.disposal_date,
                    "end_date": None,
                    "quantity": d.quantity,
                    "notes": d.reason,
                    "photo": _image_url(request, d.photo),
                })

            transactions.sort(key=lambda t: t["date"], reverse=True)

            data.append({
                "id": asset.id,
                "name_brand": asset.name_brand,
                "purchase_date": asset.purchase_date,
                "original_location": asset.location.code if asset.location else None,
                "status": asset.status,
                "status_display": asset.get_status_display(),
                "quantity": asset.quantity,
                "available_quantity": asset.available_quantity,
                "in_maintenance_quantity": asset.in_maintenance_quantity,
                "disposed_quantity": asset.disposed_quantity,
                "image": _image_url(request, asset.image),
                "transactions": transactions,
            })

        return Response(data)

    @action(detail=False, methods=["get"], url_path="annual-report")
    def annual_report(self, request):
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
                start_date__year=year
            ).order_by("start_date")
            disposals = asset.disposal_records.filter(
                disposal_date__year=year
            ).order_by("disposal_date")

            if not maintenance.exists() and not disposals.exists() and asset.purchase_date.year != year:
                continue

            events = []
            if asset.purchase_date.year == year:
                events.append({
                    "type": "purchase",
                    "date": asset.purchase_date,
                    "notes": f"Dibeli {asset.quantity} unit - RM{asset.price}",
                })
            for m in maintenance:
                end_label = m.end_date.isoformat() if m.end_date else "belum pulang"
                note = f"{m.quantity} unit"
                if m.notes:
                    note += f" — {m.notes}"
                note += f" (pulang: {end_label})"
                events.append({"type": "maintenance", "date": m.start_date, "notes": note})
            for d in disposals:
                events.append({
                    "type": "disposal",
                    "date": d.disposal_date,
                    "notes": f"{d.quantity} unit — {d.reason}",
                })

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
    permission_classes = [IsManagement]
    queryset = AssetMaintenance.objects.all().order_by("-start_date")
    serializer_class = AssetMaintenanceSerializer

    def create(self, request, *args, **kwargs):
        asset_id = request.data.get("asset")
        quantity = request.data.get("quantity", 1)

        try:
            asset = Asset.objects.get(id=asset_id)
        except Asset.DoesNotExist:
            return Response({"error": "Invalid asset"}, status=400)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"error": "Quantity must be a whole number"}, status=400)

        if quantity < 1:
            return Response({"error": "Quantity must be at least 1"}, status=400)

        if quantity > asset.available_quantity:
            return Response(
                {"error": f"Hanya {asset.available_quantity} unit tersedia untuk dihantar"},
                status=400,
            )

        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="ongoing")
    def ongoing(self, request):
        records = self.get_queryset().filter(end_date__isnull=True).select_related("asset")
        return Response(AssetMaintenanceSerializer(records, many=True, context={"request": request}).data)

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

class AssetDisposalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManagement]
    queryset = AssetDisposal.objects.all().order_by("-disposal_date")
    serializer_class = AssetDisposalSerializer

    def create(self, request, *args, **kwargs):
        asset_id = request.data.get("asset")
        quantity = request.data.get("quantity", 1)

        try:
            asset = Asset.objects.get(id=asset_id)
        except Asset.DoesNotExist:
            return Response({"error": "Invalid asset"}, status=400)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"error": "Quantity must be a whole number"}, status=400)

        if quantity < 1:
            return Response({"error": "Quantity must be at least 1"}, status=400)

        if asset.status == "disposed":
            return Response({"error": "Asset already fully disposed"}, status=400)

        if quantity > asset.available_quantity:
            return Response(
                {"error": f"Hanya {asset.available_quantity} unit tersedia untuk dilupuskan"},
                status=400,
            )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)