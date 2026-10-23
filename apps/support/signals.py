import logging
import os

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import SupportAttachment

logger = logging.getLogger(__name__)


def _delete_file(storage, name):
    try:
        storage.delete(name)
    except Exception:
        logger.exception("No se pudo borrar el archivo %s", name)
        return
    # En disco local, quita también la carpeta del ticket si quedó vacía.
    try:
        folder = os.path.dirname(storage.path(name))
    except NotImplementedError:
        return
    try:
        os.rmdir(folder)
    except OSError:
        pass  # aún tiene archivos o ya no existe


@receiver(post_delete, sender=SupportAttachment)
def delete_attachment_file(sender, instance, **kwargs):
    """Al borrar una imagen (o su ticket) desde Django, borra también el archivo.

    Se hace al confirmar la transacción: si el borrado en BD falla, el archivo se conserva.
    """
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: _delete_file(storage, name))
