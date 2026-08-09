from django.db.models import Sum, Q
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
import uuid
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.parsers import (MultiPartParser, FormParser, JSONParser)
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.users.permissions import IsManagement, IsManagementOrVolunteer
from config.paginations import DefaultPagination
from .models import (InventoryItem, InventoryRequest, StockMovement, SourceInventory, UsageLog, KitchenStockStatus)
from .api.serializers import (InventoryItemSerializer, InventoryRequestSerializer, StockMovementSerializer, SourceInventorySerializer, UsageLogSerializer, KitchenStockStatusSerializer)
from apps.kitchens.models import Kitchen


def get_current_stock(item, kitchen=None, is_foodbank=None):
    filters = {"item": item, "kitchen": kitchen}
    if is_foodbank is not None:
        filters["is_foodbank"] = is_foodbank

    stock_in = StockMovement.objects.filter(movement_type="in", **filters).aggregate(total=Sum("quantity"))["total"] or 0
    stock_out = StockMovement.objects.filter(movement_type="out", **filters).aggregate(total=Sum("quantity"))["total"] or 0
    return stock_in - stock_out


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.all().order_by("-created_at")
    pagination_class = DefaultPagination 

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request):
        source = request.query_params.get("source")
        if not source:
            return Response([])

        used_items = SourceInventory.objects.filter(source=source).values_list("item_id", flat=True)
        items = InventoryItem.objects.exclude(id__in=used_items)

        return Response(InventoryItemSerializer(items, many=True).data)

    @action(detail=False, methods=["get"], url_path="with-stock")
    def with_stock(self, request):
        items = InventoryItem.objects.all()
        kitchens = Kitchen.objects.filter(is_active=True)
        page = self.paginate_queryset(items)
        records = page if page is not None else items

        data = []
        for item in records:
            kitchen_data = []
            management_stock = get_current_stock(item, None)

            statuses = {
                s.kitchen_id: s
                for s in KitchenStockStatus.objects.filter(item=item, kitchen__in=kitchens)
            }

            for kitchen in kitchens:
                status_record = statuses.get(kitchen.id)
                stock = get_current_stock(item, kitchen)
                status = "out" if stock <= 0 else (status_record.status if status_record else "available")
                kitchen_data.append({
                    "kitchen_id": kitchen.id,
                    "kitchen_name": kitchen.code,
                    "stock": stock,
                    "estimated_value": stock * item.price_per_unit if item.price_per_unit else None,
                    "status": status,
                })

            data.append({
                "id": item.id,
                "name": item.display_name,
                "unit": item.unit,
                "price_per_unit": item.price_per_unit,
                "management_stock": management_stock,
                "management_value": management_stock * item.price_per_unit if item.price_per_unit else None,
                "kitchens": kitchen_data
            })

        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)
    
    @action(detail=False, methods=["get"], url_path="foodbank-stock")
    def foodbank_stock(self, request):
        kitchen_id = request.query_params.get("kitchen")
        if not kitchen_id:
            return Response({"error": "Kitchen is required"}, status=400)

        try:
            kitchen = Kitchen.objects.get(id=kitchen_id)
        except Kitchen.DoesNotExist:
            return Response({"error": "Invalid kitchen"}, status=400)

        data = []
        for item in InventoryItem.objects.all():
            available = get_current_stock(item, kitchen, is_foodbank=True)
            if available > 0:
                data.append({
                    "id": item.id,
                    "name": item.name,
                    "unit": item.unit,
                    "available": available,
                })
        return Response(data)


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all().order_by("-created_at")
    serializer_class = StockMovementSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        kitchen = self.request.query_params.get("kitchen")
        movement_type = self.request.query_params.get("movement_type")
        context = self.request.query_params.get("context")
        search = self.request.query_params.get("search")
        date = self.request.query_params.get("date")
        source = self.request.query_params.get("source")

        if context == "management":
            queryset = queryset.filter(kitchen__isnull=True)
        elif context == "volunteer":
            user_kitchen = getattr(self.request.user, "kitchen", None)
            if not user_kitchen:
                return queryset.none()

            queryset = queryset.filter(kitchen=user_kitchen)
        elif kitchen:
            queryset = queryset.filter(kitchen_id=kitchen)

        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)

        if search:
            queryset = queryset.filter(item__name__icontains=search)

        if date:
            queryset = queryset.filter(created_at__date=date)

        if source:
            queryset = queryset.filter(source=source)

        return queryset

    @action(detail=False, methods=["get"], url_path="total-value")
    def total_value(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.aggregate(total=Sum("total_amount"))["total"] or 0
        count = queryset.count()
        return Response({"total_amount": total, "count": count})

    @action(detail=False, methods=["get"], url_path="my-stock", permission_classes=[IsManagementOrVolunteer])
    def my_stock(self, request):
        kitchen = request.user.kitchen
        if not kitchen:
            return Response({"error": "User has no kitchen assigned"}, status=400)

        items = InventoryItem.objects.all()
        statuses = {
            s.item_id: s
            for s in KitchenStockStatus.objects.filter(kitchen=kitchen)
        }

        data = []
        for item in items:
            status_record = statuses.get(item.id)
            stock = get_current_stock(item, kitchen)
            if stock <= 0:
                status = "out"
            else:
                status = status_record.status if status_record else "available"
            data.append({
                "id": item.id,
                "name": item.display_name,
                "unit": item.unit,
                "price_per_unit": item.price_per_unit,
                "volunteer_stock": stock,
                "estimated_value": (
                    stock * item.price_per_unit if item.price_per_unit else None
                ),
                "status": status,
                "last_reported_quantity": (
                    status_record.last_reported_quantity if status_record else None
                ),
            })

        return Response(data)

    @action(detail=False, methods=["post"], url_path="transfer", permission_classes=[IsManagement])
    def transfer(self, request):

        item_id = request.data.get("item")
        target_kitchen_id = request.data.get("kitchen")
        remarks = request.data.get("remarks", "")
        proof_image = request.FILES.get("proof_image")
        is_foodbank = str(request.data.get("is_foodbank", "false")).lower() == "true"
        transfer_id = uuid.uuid4()

        try:
            quantity = int(request.data.get("quantity", 0))

        except (TypeError, ValueError):
            return Response(
                {"error": "Quantity must be a valid number"},
                status=400
            )

        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than zero"},
                status=400
            )

        try:
            item = InventoryItem.objects.get(id=item_id)
            kitchen = Kitchen.objects.get(id=target_kitchen_id)

        except Exception:
            return Response({"error": "Invalid item or kitchen"}, status=400)

        management_stock = get_current_stock(item, None)

        if quantity > management_stock:
            return Response({"error": "Not enough stock"}, status=400)

        StockMovement.objects.create(
            item=item,
            movement_type="out",
            kitchen=None,
            quantity=quantity,
            transfer_group=transfer_id,
            reason="Transfer to kitchen",
            purpose="Kitchen supply",
            remarks=remarks,
            proof_image=proof_image,
            is_foodbank=is_foodbank
        )

        StockMovement.objects.create(
            item=item,
            movement_type="in",
            kitchen=kitchen,
            quantity=quantity,
            reason="Received from management",
            transfer_group=transfer_id,
            purpose="Kitchen supply",
            remarks=remarks,
            proof_image=proof_image,
            is_foodbank=is_foodbank
        )

        return Response(
            {"message": "Stock transferred successfully"}
        )

    @action(detail=False, methods=["post"], url_path="use", permission_classes=[IsManagementOrVolunteer])
    def use_stock(self, request):
        item_id = request.data.get("item")
        kitchen = request.user.kitchen

        if not kitchen:
            return Response(
                {"error": "No kitchen assigned"},
                status=400
            )

        try:
            quantity = int(request.data.get("quantity", 0))
        except (TypeError, ValueError):
            return Response(
                {"error": "Quantity must be a valid number"},
                status=400
            )

        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than zero"},
                status=400
            )

        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response(
                {"error": "Invalid item"},
                status=400
            )

        usage_unit = request.data.get("usage_unit") or "cup"
        valid_units = dict(UsageLog.UNIT_CHOICES)
        if usage_unit not in valid_units:
            return Response({"error": "Invalid usage unit"}, status=400)

        UsageLog.objects.create(
            item=item,
            kitchen=kitchen,
            quantity=quantity,
            usage_unit=usage_unit,
            reason=request.data.get("reason", "Kitchen usage"),
            recorded_by=request.user,
        )

        return Response({"message": "Usage recorded"})

    @action(detail=False, methods=["get"], url_path="today-summary")
    def today_summary(self, request):
        today = timezone.now().date()

        inventory_in_today = StockMovement.objects.filter(
            movement_type="in", kitchen__isnull=True, created_at__date=today,
        ).aggregate(total=Sum("quantity"))["total"] or 0

        inventory_out_today = StockMovement.objects.filter(
            movement_type="out", created_at__date=today,
        ).aggregate(total=Sum("quantity"))["total"] or 0

        return Response({
            "inventory_in_today": inventory_in_today,
            "inventory_out_today": inventory_out_today,
        })

class UsageLogViewSet(viewsets.ModelViewSet):
    serializer_class = UsageLogSerializer
    queryset = UsageLog.objects.all().order_by("-created_at")

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        kitchen = getattr(self.request.user, "kitchen", None)
        if not kitchen:
            return queryset.none()
        return queryset.filter(kitchen=kitchen)


class KitchenStockStatusViewSet(viewsets.ModelViewSet):

    serializer_class = KitchenStockStatusSerializer
    queryset = KitchenStockStatus.objects.all()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        kitchen = getattr(self.request.user, "kitchen", None)
        if not kitchen:
            return queryset.none()
        return queryset.filter(kitchen=kitchen)

    def _compute_status(reported_quantity, item):
        threshold = getattr(item, "low_stock_threshold", 10)
        if reported_quantity <= 0:
            return "out"
        if reported_quantity <= threshold:
            return "low"
        return "available"

    @action(detail=False, methods=["post"], url_path="set", permission_classes=[IsManagementOrVolunteer])
    def set_status(self, request):
        item_id = request.data.get("item")
        reported_quantity = request.data.get("quantity")

        if request.user.role == "management":
            kitchen_id = request.data.get("kitchen")
            if not kitchen_id:
                return Response({"error": "Kitchen required"}, status=400)

            try:
                kitchen = Kitchen.objects.get(id=kitchen_id)
            except Kitchen.DoesNotExist:
                return Response({"error": "Invalid kitchen"}, status=400)

        else:
            kitchen = request.user.kitchen
        if not kitchen:
            return Response({"error": "No kitchen assigned"}, status=400)

        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Invalid item"}, status=400)

        if reported_quantity in (None, ""):
            return Response({"error": "Quantity is required"}, status=400)

        try:
            reported_quantity = int(reported_quantity)
        except (TypeError, ValueError):
            return Response({"error": "Quantity must be a valid number"}, status=400)

        if reported_quantity < 0:
            return Response({"error": "Quantity cannot be negative"}, status=400)

        status_value = _compute_status(reported_quantity, item)

        with transaction.atomic():
            current = get_current_stock(item, kitchen)
            diff = current - reported_quantity

            if diff > 0:
                StockMovement.objects.create(
                    item=item,
                    movement_type="out",
                    kitchen=kitchen,
                    quantity=diff,
                    reason="Stock reconciliation",
                    remarks=f"Volunteer recount: {reported_quantity} (was {current})",
                )
            elif diff < 0:
                StockMovement.objects.create(
                    item=item,
                    movement_type="in",
                    kitchen=kitchen,
                    quantity=abs(diff),
                    reason="Stock reconciliation (correction)",
                    remarks=f"Volunteer recount: {reported_quantity} (was {current})",
                )

            record, _ = KitchenStockStatus.objects.update_or_create(
                item=item,
                kitchen=kitchen,
                defaults={
                    "status": status_value,
                    "last_reported_quantity": reported_quantity,
                    "updated_by": request.user,
                },
            )

        return Response({
            "message": "Stock updated",
            "status": status_value,
            "reconciled_stock": get_current_stock(item, kitchen),
        })

    @action(detail=False, methods=["get"], url_path="alerts", permission_classes=[IsManagementOrVolunteer])
    def alerts(self, request):
        statuses = KitchenStockStatus.objects.filter(
            status__in=["low", "out"]
        ).select_related("item", "kitchen").order_by("-updated_at")

        return Response(KitchenStockStatusSerializer(statuses, many=True).data)


class SourceInventoryViewSet(viewsets.ModelViewSet):
    queryset = SourceInventory.objects.all()
    serializer_class = SourceInventorySerializer
    pagination_class = DefaultPagination

    def get_permissions(self):
        return [IsManagement()]

    def create(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        source = request.data.get("source")
        remarks = request.data.get("remarks", "")
        proof_image = request.FILES.get("proof_image")

        if not source:
            return Response({"error": "Source is required"}, status=400)

        try:
            quantity = int(request.data.get("quantity", 0))
        except (TypeError, ValueError):
            return Response({"error": "Quantity must be a valid number"}, status=400)

        if quantity <= 0:
            return Response({"error": "Quantity must be greater than zero"}, status=400)

        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Invalid item"}, status=400)

        unit_price_raw = request.data.get("unit_price")
        if unit_price_raw in (None, ""):
            unit_price = item.price_per_unit or 0
        else:
            try:
                unit_price = float(unit_price_raw)
            except (TypeError, ValueError):
                return Response({"error": "unit_price must be a valid number"}, status=400)

            if unit_price <= 0:
                unit_price = item.price_per_unit or 0

        SourceInventory.objects.get_or_create(item=item, source=source)

        StockMovement.objects.create(
            item=item,
            movement_type="in",
            kitchen=None,
            quantity=quantity,
            unit_price=unit_price,
            source=source,
            reason="Initial stock from source",
            remarks=remarks,
            proof_image=proof_image
        )

        return Response({"message": "Inventory added successfully"})

    def list(self, request, *args, **kwargs):
        source = request.query_params.get("source")
        queryset = SourceInventory.objects.all()

        if source:
            queryset = queryset.filter(source=source)

        page = self.paginate_queryset(queryset)
        records = page if page is not None else queryset

        data = []
        for record in records:
            stock_in = StockMovement.objects.filter(
                item=record.item,
                movement_type="in",
                source=record.source,
                kitchen__isnull=True
            ).order_by("-created_at")
            summary = stock_in.aggregate(
                total_received=Sum("quantity"),
                total_amount=Sum("total_amount"),
            )
            latest = stock_in.first()
            data.append({
                "id": record.id,
                "item": record.item.id,
                "item_name": record.item.display_name,
                "price_per_unit": record.item.price_per_unit,
                "source": record.source,
                "total_received": summary["total_received"] or 0,
                "total_amount": summary["total_amount"] or 0,
                "latest_added": latest.quantity if latest else 0,
                "last_updated": latest.created_at if latest else None
            })

        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):

        summary = (
            StockMovement.objects
            .filter(movement_type="in", kitchen__isnull=True)
            .values("source")
            .annotate(
                total_quantity=Sum("quantity"),
                total_amount=Sum("total_amount"),
            )
        )

        return Response(summary)


class InventoryRequestViewSet(viewsets.ModelViewSet):
    queryset = InventoryRequest.objects.all().order_by("-created_at")
    serializer_class = InventoryRequestSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = getattr(user, "role", None)

        if role == "volunteer":
            user_kitchen = getattr(user, "kitchen", None)
            if not user_kitchen:
                return queryset.none()
            return queryset.filter(kitchen=user_kitchen)

        kitchen = self.request.query_params.get("kitchen")
        if kitchen:
            queryset = queryset.filter(kitchen_id=kitchen)

        return queryset

    def perform_create(self, serializer):
        kitchen = getattr(self.request.user, "kitchen", None)
        serializer.save(kitchen=kitchen)

    @action(detail=True, methods=["post"], permission_classes=[IsManagementOrVolunteer])
    def cancel(self, request, pk=None):
        request_obj = self.get_object()

        if request_obj.status != "pending":
            return Response({"error": "Only pending requests can be cancelled"}, status=400)

        request_obj.status = "cancelled"
        request_obj.save()

        return Response({"message": "Request cancelled"})

    @action(detail=True, methods=["post"], permission_classes=[IsManagement])
    def approve(self, request, pk=None):
        request_obj = self.get_object()

        if request_obj.status != "pending":
            return Response({"error": "Request already processed"}, status=400)

        if not request_obj.kitchen:
            return Response({"error": "Request has no kitchen assigned"}, status=400)

        with transaction.atomic():
            item = request_obj.item
            if not item:
                item = InventoryItem.objects.create(
                    name=request_obj.new_item_name,
                    unit=request_obj.new_item_unit,
                    package_size=request_obj.new_item_package_size,
                    price_per_unit=request_obj.new_item_price_per_unit,
                )
                request_obj.item = item

            source = getattr(request_obj, "source", None) or "purchase"
            quantity = request_obj.quantity
            unit_price = item.price_per_unit or 0
            transfer_id = uuid.uuid4()

            SourceInventory.objects.get_or_create(item=item, source=source)

            StockMovement.objects.create(
                item=item, movement_type="in", kitchen=None, quantity=quantity,
                unit_price=unit_price,
                source=source, transfer_group=transfer_id,
                reason="Approved request - purchased",
                remarks="Approved request - purchased",
                purpose=f"Fulfilling request from {request_obj.kitchen.code}",
            )
            StockMovement.objects.create(
                item=item, movement_type="in", kitchen=request_obj.kitchen, quantity=quantity,
                unit_price=unit_price,
                transfer_group=transfer_id,
                reason="Received from management (request fulfilled)",
                purpose=f"Fulfilling request from {request_obj.kitchen.code}",
            )
            StockMovement.objects.create(
                item=item, movement_type="out", kitchen=None, quantity=quantity,
                unit_price=unit_price,
                transfer_group=transfer_id,
                reason="Transferred to kitchen (request fulfilled)",
                remarks="Approved request - purchased",
                purpose=f"Fulfilling request from {request_obj.kitchen.code}",
            )

            request_obj.status = "approved"
            request_obj.save()

        return Response({"message": "Request approved and stock transferred"})

    @action(detail=True, methods=["post"], permission_classes=[IsManagement])
    def reject(self, request, pk=None):
        request_obj = self.get_object()

        if request_obj.status != "pending":
            return Response({"error": "Request already processed"}, status=400)

        request_obj.status = "rejected"
        request_obj.save()
        return Response({"message": "Request rejected"})

    @action(detail=True, methods=["post"], permission_classes=[IsManagement])
    def fulfill_from_stock(self, request, pk=None):
        request_obj = self.get_object()

        if request_obj.status != "pending":
            return Response({"error": "Request already processed"}, status=400)

        if not request_obj.kitchen:
            return Response({"error": "Request has no kitchen assigned"}, status=400)

        item = request_obj.item
        if not item:
            return Response(
                {"error": "Cannot fulfill a new-item request from stock — approve it instead"},
                status=400
            )

        quantity = request_obj.quantity
        management_stock = get_current_stock(item, None)

        if quantity > management_stock:
            return Response(
                {"error": f"Not enough stock ({management_stock} available, {quantity} requested)"},
                status=400
            )

        with transaction.atomic():
            transfer_id = uuid.uuid4()

            StockMovement.objects.create(
                item=item,
                movement_type="out",
                kitchen=None,
                quantity=quantity,
                transfer_group=transfer_id,
                reason="Transfer to kitchen (request fulfilled from stock)",
                purpose=f"Fulfilling request from {request_obj.kitchen.code}",
            )
            StockMovement.objects.create(
                item=item,
                movement_type="in",
                kitchen=request_obj.kitchen,
                quantity=quantity,
                transfer_group=transfer_id,
                reason="Received from management (request fulfilled from stock)",
                purpose=f"Fulfilling request from {request_obj.kitchen.code}",
            )

            request_obj.status = "approved"
            request_obj.save()

        return Response({"message": "Request fulfilled from existing stock"})


class LandingPageViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"], url_path="inventory-summary")
    def inventory_summary(self, request):
        items = InventoryItem.objects.all()
        kitchens = Kitchen.objects.filter(is_active=True)

        total_items = items.count()
        total_management_stock = 0
        total_management_value = 0

        for item in items:
            stock = get_current_stock(item, None)
            total_management_stock += stock
            if item.price_per_unit:
                total_management_value += stock * item.price_per_unit

        alerts_count = KitchenStockStatus.objects.filter(
            status__in=["low", "out"]
        ).count()

        source_summary = (
            StockMovement.objects
            .filter(movement_type="in", kitchen__isnull=True)
            .values("source")
            .annotate(
                total_quantity=Sum("quantity"),
                total_amount=Sum("total_amount"),
            )
        )
        total_amount_received = sum(
            (s["total_amount"] or 0) for s in source_summary
        )

        return Response({
            "total_items": total_items,
            "total_management_stock": total_management_stock,
            "total_management_value": total_management_value,
            "total_amount_received": total_amount_received,
            "alerts_count": alerts_count,
            "kitchens_covered": kitchens.count(),
            "sources": list(source_summary),
        })


class VolunteerDashboardView(APIView):
    permission_classes = [IsManagementOrVolunteer]

    def get(self, request):
        kitchen = request.user.kitchen
        if not kitchen:
            return Response({"error": "User has no kitchen assigned"}, status=400)

        items = InventoryItem.objects.all()
        stock_data = []
        low_stock_data = []

        for item in items:
            stock_in = StockMovement.objects.filter(
                item=item, kitchen=kitchen, movement_type="in"
            ).aggregate(total=Sum("quantity"))["total"] or 0

            stock_out = StockMovement.objects.filter(
                item=item, kitchen=kitchen, movement_type="out"
            ).aggregate(total=Sum("quantity"))["total"] or 0

            current_stock = stock_in - stock_out

            stock_data.append({
                "id": item.id,
                "item": item.display_name,
                "quantity": current_stock,
                "unit": item.unit
            })

            if current_stock <= 10:
                low_stock_data.append({
                    "id": item.id,
                    "item": item.display_name,
                    "quantity": current_stock,
                    "unit": item.unit
                })

        recent_usage = UsageLog.objects.filter(
            kitchen=kitchen
        ).select_related("item").order_by("-created_at")[:10]

        recent_usage_data = []
        for usage in recent_usage:
            recent_usage_data.append({
                "id": usage.id,
                "item": usage.item.display_name,
                "quantity": usage.quantity,
                "unit": usage.usage_unit,
                "reason": usage.reason,
                "date": usage.created_at
            })

        requests = InventoryRequest.objects.filter(
            kitchen=kitchen
        ).order_by("-created_at")[:10]

        request_data = []
        for req in requests:
            request_data.append({
                "id": req.id,
                "item": (req.item.display_name if req.item else req.new_item_name),
                "quantity": req.quantity,
                "status": req.status,
                "created_at": req.created_at
            })

        today = timezone.now().date()
        today_usage = UsageLog.objects.filter(
            kitchen=kitchen,
            created_at__date=today
        ).count()

        return Response({
            "summary": {
                "total_inventory_items": len(stock_data),
                "low_stock_items": len(low_stock_data),
                "pending_requests": InventoryRequest.objects.filter(
                    kitchen=kitchen, status="pending"
                ).count(),
                "today_usage": today_usage,
            },
            "low_stock": low_stock_data,
            "recent_usage": recent_usage_data,
            "pending_requests": request_data,
            "stock": stock_data
        })