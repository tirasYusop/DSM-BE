from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement, SourceInventory


@receiver(post_save, sender=StockMovement)
def update_stock(sender, instance, created, **kwargs):

    if not created:
        return

    item = instance.item
    source = instance.source

    if not source:
        return

    source_stock, created_obj = SourceInventory.objects.get_or_create(
        item=item,
        source=source
    )

    if instance.movement_type == "in":
        source_stock.quantity += instance.quantity
    elif instance.movement_type == "out":
        source_stock.quantity -= instance.quantity

    source_stock.save()

    