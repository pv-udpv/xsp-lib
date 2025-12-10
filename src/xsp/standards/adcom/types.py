"""AdCOM 1.0 Common Types.

Common types, base models, and shared validators.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdComModel(BaseModel):
    """Base model for all AdCOM objects.

    Configures:
    - Accepts arbitrary extra fields (for future spec extensions)
    - Uses aliases for field names
    - Validates assignments
    """

    model_config = ConfigDict(
        extra="allow",  # Accept unknown fields per spec
        populate_by_name=True,
        validate_assignment=True,
    )

    ext: dict[str, Any] | None = Field(
        default=None,
        description="Optional vendor-specific extensions",
    )


class Metric(AdComModel):
    """Object to define performance metrics.

    Attributes:
        type: Type of metric being presented (e.g., "viewability", "click")
        value: Numerical value of the metric
        vendor: Source of the metric (e.g., "moat", "doubleverify")
    """

    type: str = Field(description="Type of metric")
    value: float = Field(description="Numerical value of the metric")
    vendor: str | None = Field(default=None, description="Source of the metric")
