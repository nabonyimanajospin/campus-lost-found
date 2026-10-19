"""Keep the media folder in step with the database: no orphaned photos."""
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Item


@receiver(post_delete, sender=Item)
def delete_image_with_item(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(pre_save, sender=Item)
def delete_replaced_image(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = Item.objects.filter(pk=instance.pk).values_list("image", flat=True).first()
    if old and old != (instance.image.name if instance.image else None):
        Item._meta.get_field("image").storage.delete(old)
