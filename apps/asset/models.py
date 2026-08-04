from django.db import models
from django.conf import settings


class Asset(models.Model):

    SOURCE_CHOICES = [
        ("purchase", "Pembelian"),
        ("donation", "Sumbangan"),
        ("sponsor", "Sponsor"),
        ("other", "Lain-lain"),
    ]

    STATUS_CHOICES = [
        ("active", "Aktif"),
        ("maintenance", "Dalam Penyelenggaraan"),
        ("disposed", "Dilupuskan"),
    ]

    name_brand = models.CharField(max_length=255, help_text="Nama Asset & Jenama")
    purchase_date = models.DateField()
    warranty = models.CharField(max_length=100, blank=True, help_text="Cth: 1 Tahun")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="purchase")

    image = models.ImageField(
        upload_to="assets/",
        null=True,
        blank=True,
        help_text="Gambar rujukan aset ini",
    )

    location = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.SET_NULL,
        null=True,
        related_name="assets"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name_brand

    @property
    def disposed_quantity(self):
        return self.disposal_records.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def in_maintenance_quantity(self):
        return (
            self.maintenance_records.filter(end_date__isnull=True)
            .aggregate(total=models.Sum("quantity"))["total"]
            or 0
        )

    @property
    def available_quantity(self):
        return self.quantity - self.disposed_quantity - self.in_maintenance_quantity

    def refresh_status(self):
        if self.disposed_quantity >= self.quantity:
            new_status = "disposed"
        elif self.in_maintenance_quantity > 0:
            new_status = "maintenance"
        else:
            new_status = "active"

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status"])


class AssetMaintenance(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_records")
    quantity = models.PositiveIntegerField(default=1, help_text="Bilangan unit dihantar untuk penyelenggaraan")
    start_date = models.DateField(help_text="Tarikh aset dibawa keluar dari dapur untuk penyelenggaraan")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Tarikh aset dipulangkan selepas penyelenggaraan selesai. "
                   "Kosongkan jika aset masih dalam penyelenggaraan.",
    )
    notes = models.TextField(blank=True)

    photo_before = models.ImageField(
        upload_to="asset_maintenance/before/",
        null=True,
        blank=True,
        help_text="Gambar keadaan aset semasa dihantar untuk penyelenggaraan",
    )
    photo_after = models.ImageField(
        upload_to="asset_maintenance/after/",
        null=True,
        blank=True,
        help_text="Gambar bukti selepas aset dipulangkan / diselenggara",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    @property
    def is_ongoing(self):
        return self.end_date is None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.asset.refresh_status()

    def __str__(self):
        end = self.end_date.isoformat() if self.end_date else "belum pulang"
        return f"{self.asset.name_brand} - {self.quantity} unit - {self.start_date} -> {end}"


class AssetDisposal(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="disposal_records")
    quantity = models.PositiveIntegerField(default=1, help_text="Bilangan unit dilupuskan")
    disposal_date = models.DateField()
    reason = models.TextField()
    photo = models.ImageField(
        upload_to="asset_disposal/",
        null=True,
        blank=True,
        help_text="Gambar bukti pelupusan",
    )
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.asset.refresh_status()

    def __str__(self):
        return f"{self.asset.name_brand} - {self.quantity} unit dilupuskan {self.disposal_date}"