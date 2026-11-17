"""
Photos of the workers (profile) and of the spare parts.

What comes in is untrusted, so it is never stored as it arrives: the content is checked,
turned upright (EXIF orientation), shrunk and saved again as a JPEG under a random name.
Workers' photos are also cropped to a square; a spare part keeps its proportions (cropping
could cut off the piece). Both drop the metadata (camera, GPS position...) of the original.
"""

import os
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # the file the person picks
MAX_PIXELS = 50_000_000  # protects the server from huge images that fit in few bytes
SIZE = 512  # side of the stored square, in pixels
PART_MAX_SIDE = 800  # longest side of a spare part photo (never enlarged)
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}  # detected from the content, not from the file name


class PhotoError(Exception):
    """The photo cannot be used; the message is shown to the person."""


def process_photo(file, square=True):
    """
    Returns a ContentFile with the processed photo, or raises PhotoError.
    square=True crops to SIZE x SIZE (people); False only shrinks it (things).
    """
    if file.size > MAX_UPLOAD_BYTES:
        raise PhotoError(f"La fotografía pesa más de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    try:
        with Image.open(file) as probe:
            probe.verify()
        file.seek(0)
        with Image.open(file) as image:
            if image.format not in ALLOWED_FORMATS:
                raise PhotoError("La fotografía debe ser JPG, PNG o WebP.")
            if image.width * image.height > MAX_PIXELS:
                raise PhotoError("La fotografía es demasiado grande en píxeles.")
            image = ImageOps.exif_transpose(image)
            if image.mode in ("RGBA", "LA", "P"):
                # Transparent areas become white (JPEG has no transparency)
                rgba = image.convert("RGBA")
                flat = Image.new("RGB", rgba.size, "white")
                flat.paste(rgba, mask=rgba.split()[-1])
                image = flat
            else:
                image = image.convert("RGB")
            if square:
                image = ImageOps.fit(image, (SIZE, SIZE), method=Image.LANCZOS, centering=(0.5, 0.4))
            else:
                image.thumbnail((PART_MAX_SIDE, PART_MAX_SIDE), Image.LANCZOS)
    except PhotoError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, ValueError):
        raise PhotoError("El archivo no es una imagen válida.")

    from io import BytesIO

    out = BytesIO()
    image.save(out, format="JPEG", quality=85, optimize=True)  # no EXIF is written
    return ContentFile(out.getvalue(), name=f"{uuid.uuid4().hex}.jpg")


def photo_url(obj, route="trabajadores"):
    """API path of the photo of a worker (or of a part: route="refacciones"), or None.
    The version changes with each new photo, so the browser never keeps an old one."""
    if not obj.photo:
        return None
    version = os.path.splitext(os.path.basename(obj.photo.name))[0]
    return f"{route}/{obj.pk}/foto/?v={version}"


def remove_photo_file(obj):
    """Deletes the stored file (the database field is cleared by the caller)."""
    if obj.photo:
        try:
            obj.photo.storage.delete(obj.photo.name)
        except OSError:
            pass
