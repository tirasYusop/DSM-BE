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
        ("disposed", "Dilupuskan"),
    ]

    name_brand = models.CharField(max_length=255, help_text="Nama Asset & Jenama")
    purchase_date = models.DateField()
    warranty = models.CharField(max_length=100, blank=True, help_text="Cth: 1 Tahun")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="purchase")

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


class AssetMaintenance(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_records")
    maintenance_date = models.DateField()
    notes = models.TextField(blank=True)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asset.name_brand} - diselenggara {self.maintenance_date}"


class AssetDisposal(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name="disposal_record")
    disposal_date = models.DateField()
    reason = models.TextField()

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.asset.status != "disposed":
            self.asset.status = "disposed"
            self.asset.save(update_fields=["status"])

    def __str__(self):
        return f"{self.asset.name_brand} dilupuskan {self.disposal_date}"
