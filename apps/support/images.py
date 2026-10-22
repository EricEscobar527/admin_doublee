from django.conf import settings
from PIL import Image, UnidentifiedImageError

# Formato real detectado por Pillow -> (extensión, content-type)
ALLOWED_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
    "GIF": ("gif", "image/gif"),
}


class InvalidImage(ValueError):
    pass


def inspect_image(upload):
    """Valida tamaño y tipo real (por contenido, no por extensión).

    Regresa (extensión, content_type) o lanza InvalidImage.
    """
    if upload.size > settings.SUPPORT_MAX_FILE_SIZE:
        max_mb = settings.SUPPORT_MAX_FILE_SIZE // (1024 * 1024)
        raise InvalidImage(f"'{upload.name}' supera el máximo de {max_mb} MB.")
    try:
        upload.seek(0)
        with Image.open(upload) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise InvalidImage(f"'{upload.name}' no es una imagen válida.")
    finally:
        upload.seek(0)
    if fmt not in ALLOWED_FORMATS:
        raise InvalidImage(f"'{upload.name}': formato {fmt} no permitido.")
    return ALLOWED_FORMATS[fmt]
