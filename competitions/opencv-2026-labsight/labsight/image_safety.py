from __future__ import annotations

from dataclasses import dataclass
import struct

MAX_ENCODED_BYTES = 8 * 1024 * 1024
MAX_BASE64_CHARS = 4 * ((MAX_ENCODED_BYTES + 2) // 3)
MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGE_DIMENSION = 8192


class ImageSafetyError(ValueError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class ImageHeader:
    format: str
    width: int
    height: int

    @property
    def pixels(self) -> int:
        return self.width * self.height


def _validate_dimensions(fmt: str, width: int, height: int) -> ImageHeader:
    if width <= 0 or height <= 0:
        raise ImageSafetyError(400, "image dimensions must be positive")
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ImageSafetyError(413, "image dimension exceeds safety limit")
    if width * height > MAX_IMAGE_PIXELS:
        raise ImageSafetyError(413, "image pixel count exceeds safety limit")
    return ImageHeader(fmt, width, height)


def _png_header(raw: bytes) -> ImageHeader:
    if len(raw) < 24 or raw[12:16] != b"IHDR":
        raise ImageSafetyError(400, "malformed PNG header")
    width, height = struct.unpack(">II", raw[16:24])
    return _validate_dimensions("png", width, height)


_JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
}


def _jpeg_header(raw: bytes) -> ImageHeader:
    offset = 2
    while offset < len(raw):
        if raw[offset] != 0xFF:
            raise ImageSafetyError(400, "malformed JPEG marker stream")
        while offset < len(raw) and raw[offset] == 0xFF:
            offset += 1
        if offset >= len(raw):
            break
        marker = raw[offset]
        offset += 1
        if marker == 0x00:
            raise ImageSafetyError(400, "malformed JPEG marker stream")
        if marker == 0xD9:
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            continue
        if offset + 2 > len(raw):
            raise ImageSafetyError(400, "truncated JPEG segment")
        segment_length = struct.unpack(">H", raw[offset:offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(raw):
            raise ImageSafetyError(400, "invalid JPEG segment length")
        if marker in _JPEG_SOF_MARKERS:
            if segment_length < 7:
                raise ImageSafetyError(400, "truncated JPEG frame header")
            height = struct.unpack(">H", raw[offset + 3:offset + 5])[0]
            width = struct.unpack(">H", raw[offset + 5:offset + 7])[0]
            return _validate_dimensions("jpeg", width, height)
        if marker == 0xDA:
            break
        offset += segment_length
    raise ImageSafetyError(400, "JPEG frame dimensions not found")


def inspect_image_bytes(raw: bytes) -> ImageHeader:
    """Validate encoded image size/type/dimensions before OpenCV decoding."""
    if not raw:
        raise ImageSafetyError(400, "empty image payload")
    if len(raw) > MAX_ENCODED_BYTES:
        raise ImageSafetyError(413, "encoded image exceeds safety limit")
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png_header(raw)
    if raw.startswith(b"\xff\xd8"):
        return _jpeg_header(raw)
    raise ImageSafetyError(415, "only PNG and JPEG images are accepted")


def validate_decoded_shape(shape: tuple[int, ...], header: ImageHeader) -> None:
    if len(shape) not in (2, 3):
        raise ImageSafetyError(400, "decoded image has unsupported shape")
    height, width = int(shape[0]), int(shape[1])
    if (width, height) != (header.width, header.height):
        raise ImageSafetyError(400, "decoded dimensions do not match image header")
    if len(shape) == 3 and int(shape[2]) not in (1, 3, 4):
        raise ImageSafetyError(415, "decoded image has unsupported channel count")
