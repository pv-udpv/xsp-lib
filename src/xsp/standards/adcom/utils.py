"""AdCOM 1.0 Utility Functions.

Helper utilities for AdCOM object handling.
"""

from typing import Any


def get_ext(obj: Any, key: str, default: Any = None) -> Any:
    """Get value from ext object.

    Args:
        obj: AdCOM object with ext field
        key: Key to retrieve
        default: Default value if not found

    Returns:
        Value from ext or default
    """
    if not hasattr(obj, "ext") or obj.ext is None:
        return default
    return obj.ext.get(key, default)


def set_ext(obj: Any, key: str, value: Any) -> None:
    """Set value in ext object.

    Args:
        obj: AdCOM object with ext field
        key: Key to set
        value: Value to set
    """
    if not hasattr(obj, "ext"):
        raise ValueError("Object does not have ext field")
    if obj.ext is None:
        obj.ext = {}
    obj.ext[key] = value


def merge_ext(obj: Any, extensions: dict[str, Any]) -> None:
    """Merge extensions into ext object.

    Args:
        obj: AdCOM object with ext field
        extensions: Dictionary of extensions to merge
    """
    if not hasattr(obj, "ext"):
        raise ValueError("Object does not have ext field")
    if obj.ext is None:
        obj.ext = {}
    obj.ext.update(extensions)


def has_ext(obj: Any, key: str) -> bool:
    """Check if ext object has key.

    Args:
        obj: AdCOM object with ext field
        key: Key to check

    Returns:
        True if key exists in ext
    """
    if not hasattr(obj, "ext") or obj.ext is None:
        return False
    return key in obj.ext


__all__ = ["get_ext", "set_ext", "merge_ext", "has_ext"]
