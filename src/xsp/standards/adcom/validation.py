"""AdCOM 1.0 Validation Functions.

Validation and schema compliance checks for AdCOM objects.
"""

from typing import Any

from .context import App, Device, Dooh, Regs, Site, User
from .media import Ad
from .placement import Placement


def validate_ad(data: dict[str, Any]) -> Ad:
    """Validate and parse an Ad object.

    Args:
        data: Dictionary representation of an Ad

    Returns:
        Validated Ad object

    Raises:
        ValidationError: If validation fails
    """
    return Ad.model_validate(data)


def validate_placement(data: dict[str, Any]) -> Placement:
    """Validate and parse a Placement object.

    Args:
        data: Dictionary representation of a Placement

    Returns:
        Validated Placement object

    Raises:
        ValidationError: If validation fails
    """
    return Placement.model_validate(data)


def validate_context(
    data: dict[str, Any], context_type: str = "site"
) -> Site | App | Dooh:
    """Validate and parse a context object.

    Args:
        data: Dictionary representation of a context
        context_type: Type of context ('site', 'app', or 'dooh')

    Returns:
        Validated context object

    Raises:
        ValidationError: If validation fails
        ValueError: If context_type is invalid
    """
    if context_type == "site":
        return Site.model_validate(data)
    elif context_type == "app":
        return App.model_validate(data)
    elif context_type == "dooh":
        return Dooh.model_validate(data)
    else:
        raise ValueError(f"Invalid context_type: {context_type}")


def validate_user(data: dict[str, Any]) -> User:
    """Validate and parse a User object.

    Args:
        data: Dictionary representation of a User

    Returns:
        Validated User object

    Raises:
        ValidationError: If validation fails
    """
    return User.model_validate(data)


def validate_device(data: dict[str, Any]) -> Device:
    """Validate and parse a Device object.

    Args:
        data: Dictionary representation of a Device

    Returns:
        Validated Device object

    Raises:
        ValidationError: If validation fails
    """
    return Device.model_validate(data)


def validate_regs(data: dict[str, Any]) -> Regs:
    """Validate and parse a Regs object.

    Args:
        data: Dictionary representation of Regs

    Returns:
        Validated Regs object

    Raises:
        ValidationError: If validation fails
    """
    return Regs.model_validate(data)


__all__ = [
    "validate_ad",
    "validate_placement",
    "validate_context",
    "validate_user",
    "validate_device",
    "validate_regs",
]
