import base64
import io
import re
from dataclasses import dataclass

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.app.errors import ApiException


ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_FILENAME_LENGTH = 100
IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF")


@dataclass(frozen=True)
class DecodedImage:
    image: Image.Image
    raw_size: int
    image_format: str
    filename: str


def sanitize_filename(filename: str | None) -> str:
    candidate = (filename or "upload").replace("\\", "/").split("/")[-1]
    candidate = re.sub(r"[\x00-\x1f<>:\"|?*]", "_", candidate).strip(" .")
    return (candidate or "upload")[:MAX_FILENAME_LENGTH]


async def read_upload(upload: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(min(64 * 1024, max_bytes + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ApiException(413, "file_too_large", f"Image exceeds the {max_bytes // (1024 * 1024)} MB upload limit.")
        chunks.append(chunk)
    if not chunks:
        raise ApiException(400, "no_file", "Choose an image to analyze.")
    return b"".join(chunks)


def decode_image(data: bytes, filename: str | None) -> DecodedImage:
    try:
        with Image.open(io.BytesIO(data)) as probe:
            image_format = (probe.format or "").upper()
            probe.verify()
        if image_format not in ALLOWED_FORMATS:
            raise ApiException(400, "invalid_file_type", "Only JPEG, PNG and WebP images are allowed.")
        with Image.open(io.BytesIO(data)) as decoded:
            oriented = ImageOps.exif_transpose(decoded)
            if oriented.width < 32 or oriented.height < 32:
                raise ApiException(422, "corrupt_image", "Image dimensions must be at least 32 by 32 pixels.")
            image = oriented.convert("RGB")
            image.load()
    except ApiException:
        raise
    except UnidentifiedImageError as exc:
        if not data.startswith(IMAGE_SIGNATURES):
            raise ApiException(400, "invalid_file_type", "Only JPEG, PNG and WebP images are allowed.") from exc
        raise ApiException(422, "corrupt_image", "The image could not be decoded. Please choose a valid image.") from exc
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ApiException(422, "corrupt_image", "The image could not be decoded. Please choose a valid image.") from exc
    return DecodedImage(image, len(data), image_format, sanitize_filename(filename))


def image_data_url(image: Image.Image, format_name: str, quality: int | None = None) -> str:
    buffer = io.BytesIO()
    save_options = {"quality": quality} if quality is not None else {}
    image.save(buffer, format=format_name, **save_options)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    mime = "image/jpeg" if format_name.upper() == "JPEG" else "image/png"
    return f"data:{mime};base64,{encoded}"


def make_original(image: Image.Image) -> bytes:
    preview = image.copy()
    preview.thumbnail((512, 512), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    preview.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()


def make_thumbnail(image: Image.Image) -> bytes:
    thumbnail = image.copy()
    thumbnail.thumbnail((96, 96), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    thumbnail.save(buffer, format="JPEG", quality=80, optimize=True)
    return buffer.getvalue()
