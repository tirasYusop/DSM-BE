from django.conf import settings
from django.db import models


class InventoryItem(models.Model):
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, default="kg")

    package_size = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="e.g. 5.00 for a 5kg bag, 1.00 for a 1L bottle."
    )

    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Reference/default price per package (or per unit if no package_size). Used to estimate stock value; actual purchase price per movement is tracked on StockMovement.unit_price."
    )

    image = models.ImageField(upload_to='inventory/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def display_name(self):
        if self.package_size:
            size = f"{self.package_size:g}"
            return f"{self.name} ({size}{self.unit})"
        return self.name

    def __str__(self):
        return self.display_name


class SourceInventory(models.Model):

    SOURCE_CHOICES = [
        ('donation', 'Donation'),
        ('purchase', 'Purchase'),
        ('sponsor', 'Sponsor'),
        ('supplier', 'Supplier'),
        ('other', 'Other'),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="source_stocks"
    )

    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("item", "source")

    def __str__(self):
        return f"{self.item.name} - {self.source}"


class StockMovement(models.Model):

    TYPE_CHOICES = [
        ("in", "Stock In"),
        ("out", "Stock Out"),
    ]

    SOURCE_CHOICES = [
        ("donation", "Donation"),
        ("purchase", "Purchase"),
        ("sponsor", "Sponsor"),
        ("supplier", "Supplier"),
        ("other", "Other"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="movements"
    )

    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements"
    )

    transfer_group = models.UUIDField(
        null=True,
        blank=True
    )

    movement_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        null=True,
        blank=True
    )

    reason = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    purpose = models.CharField(
        max_length=255,
        blank=True
    )

    remarks = models.TextField(
        blank=True
    )

    proof_image = models.ImageField(
        upload_to="stock_proofs/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_foodbank = models.BooleanField(default=False)

    def save(self, *args, **kwargs):

        self.total_amount = (
            self.quantity *
            self.unit_price
        )

        super().save(*args, **kwargs)

    def __str__(self):

        return f"{self.item.name} ({self.movement_type})"


class InventoryRequest(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    new_item_name = models.CharField(max_length=255, null=True, blank=True)
    new_item_unit = models.CharField(max_length=50, default="kg")
    new_item_package_size = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    new_item_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    quantity = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_by = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        item_name = (
            self.item.name
            if self.item
            else self.new_item_name
            if self.new_item_name
            else "Unknown Item"
        )

        return f"{item_name} ({self.status})"


class UsageLog(models.Model):

    UNIT_CHOICES = [
        ("cup", "Cup"),
        ("pack", "Pack"),
        ("piece", "Piece"),
        ("bowl", "Bowl"),
        ("plate", "Plate"),
        ("bottle", "Bottle"),
        ("sachet", "Sachet"),
        ("tin", "Tin"),
        ("kg", "Kg"),
        ("g", "Gram"),
        ("l", "Liter"),
        ("ml", "ml"),
        ("other", "Other"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="usage_logs"
    )

    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.CASCADE,
        related_name="usage_logs"
    )

    quantity = models.PositiveIntegerField()

    usage_unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default="cup",
    )

    reason = models.CharField(max_length=255, blank=True)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name} used ({self.quantity} {self.usage_unit}) at {self.kitchen.code}"


class KitchenStockStatus(models.Model):
    
    STATUS_CHOICES = [
        ("available", "Available"),
        ("low", "Low Stock"),
        ("out", "Out of Stock"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="stock_statuses"
    )

    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.CASCADE,
        related_name="stock_statuses"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    last_reported_quantity = models.PositiveIntegerField(null=True, blank=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("item", "kitchen")

    def __str__(self):
        return f"{self.item.name} @ {self.kitchen.code}: {self.status}"