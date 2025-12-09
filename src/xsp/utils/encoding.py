"""Encoding utilities."""

import json
from typing import Any


def encode_json(data: Any) -> bytes:
    """
    Encode data as JSON bytes.

    Args:
        data: Data to encode

    Returns:
        JSON-encoded bytes
    """
    return json.dumps(data).encode("utf-8")


def decode_json(data: bytes) -> Any:
    """
    Decode JSON bytes.

    Args:
        data: JSON bytes to decode

    Returns:
        Decoded data
    """
    return json.loads(data)


def decode_text(data: bytes, encoding: str = "utf-8") -> str:
    """
    Decode bytes to text.

    Args:
        data: Bytes to decode
        encoding: Text encoding

    Returns:
        Decoded text
    """
    return data.decode(encoding)


def encode_text(text: str, encoding: str = "utf-8") -> bytes:
    """
    Encode text to bytes.

    Args:
        text: Text to encode
        encoding: Text encoding

    Returns:
        Encoded bytes
    """
    return text.encode(encoding)
