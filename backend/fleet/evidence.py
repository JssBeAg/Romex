"""Rules and helpers for the photos attached to fault reports."""
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

MAX_IMAGES = 5
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB per photo
# Pillow's detected format -> file extension. The content is checked, not the file name.
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
# A little more than the photos themselves, for the other form fields
MAX_REQUEST_BYTES = MAX_IMAGES * MAX_IMAGE_BYTES + 1024 * 1024


def check_images(files, already_kept, errors, add_error):
    """
    Validate uploaded photos. `already_kept` is how many photos the report keeps from before.
    Returns a list of (file, extension) ready to save; problems go into `errors["images"]`.
    """
    if already_kept + len(files) > MAX_IMAGES:
        add_error(errors, "images", f"Máximo {MAX_IMAGES} imágenes por reporte.")
        return []

    checked = []
    for file in files:
        if file.size > MAX_IMAGE_BYTES:
            add_error(
                errors,
                "images",
                f"«{file.name}» pesa más de {MAX_IMAGE_BYTES // (1024 * 1024)} MB.",
            )
            continue
        try:
            with Image.open(file) as image:
                image.verify()
                image_format = image.format
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
            add_error(errors, "images", f"«{file.name}» no es una imagen válida.")
            continue
        finally:
            file.seek(0)
        extension = ALLOWED_FORMATS.get(image_format)
        if extension is None:
            add_error(errors, "images", f"«{file.name}» no es JPG, PNG ni WebP.")
            continue
        checked.append((file, extension))
    return checked


def to_content_file(file, extension):
    """The photo's bytes under a random, safe name (the original name is stored apart)."""
    import uuid

    return ContentFile(file.read(), name=f"{uuid.uuid4().hex}.{extension}")
