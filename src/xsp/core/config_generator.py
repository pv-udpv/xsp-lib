"""Generate configuration templates from @configurable registry."""

import enum
import tomllib
from collections import defaultdict
from typing import Any

import tomlkit

from .configurable import ConfigMetadata, get_configurable_registry


class ConfigGenerator:
    """Generate configuration files from @configurable registry."""

    @staticmethod
    def generate_toml(group_by: str = "namespace", validate: bool = True) -> str:
        """
        Generate TOML configuration template.

        Args:
            group_by: Grouping strategy ("namespace" or "class")
            validate: Validate generated TOML (default: True)

        Returns:
            TOML configuration string

        Raises:
            ValueError: If group_by is invalid or generated TOML is invalid
        """
        registry = get_configurable_registry()

        if group_by == "namespace":
            grouped = ConfigGenerator._group_by_namespace(registry)
        elif group_by == "class":
            grouped = ConfigGenerator._group_by_class(registry)
        else:
            raise ValueError(f"Unknown group_by: {group_by}")

        # Create TOML document using tomlkit
        doc = tomlkit.document()
        doc.add(tomlkit.comment("XSP-lib Configuration Template"))
        doc.add(tomlkit.comment("Auto-generated from @configurable registry"))
        doc.add(tomlkit.comment(""))
        doc.add(tomlkit.comment("This file contains all configurable parameters from xsp-lib."))
        doc.add(tomlkit.comment("Uncomment and modify values as needed."))
        doc.add(tomlkit.nl())

        for section, metadata_list in sorted(grouped.items()):
            # Create section table
            section_table = tomlkit.table()

            for metadata in metadata_list:
                if metadata.description:
                    section_table.add(tomlkit.comment(metadata.description))

                section_table.add(tomlkit.comment(f"Source: {metadata.cls.__name__}"))
                section_table.add(tomlkit.nl())

                for param_name, param_info in metadata.parameters.items():
                    # Add parameter description
                    if param_info.description:
                        section_table.add(tomlkit.comment(param_info.description))

                    # Add type hint as comment
                    type_str = ConfigGenerator._format_type(param_info.type)
                    section_table.add(tomlkit.comment(f"Type: {type_str}"))

                    # Add parameter with default value
                    # Convert enum values to their string representation
                    value = param_info.default
                    if isinstance(value, enum.Enum):
                        value = value.value
                    # Handle None values - represent as empty string in TOML
                    elif value is None:
                        value = ""

                    section_table[param_name] = value
                    section_table.add(tomlkit.nl())

            doc[section] = section_table
            doc.add(tomlkit.nl())

        toml_str = tomlkit.dumps(doc)

        # Validate if requested
        if validate:
            ConfigGenerator._validate_toml(toml_str)

        return toml_str

    @staticmethod
    def generate_yaml(group_by: str = "namespace") -> str:
        """Generate YAML configuration template."""
        # Similar implementation for YAML
        raise NotImplementedError("YAML generation coming in future PR")

    @staticmethod
    def _group_by_namespace(
        registry: dict[str, ConfigMetadata]
    ) -> dict[str, list[ConfigMetadata]]:
        """Group metadata by namespace."""
        grouped: dict[str, list[ConfigMetadata]] = defaultdict(list)

        for metadata in registry.values():
            grouped[metadata.namespace].append(metadata)

        return grouped

    @staticmethod
    def _group_by_class(
        registry: dict[str, ConfigMetadata]
    ) -> dict[str, list[ConfigMetadata]]:
        """Group metadata by class name (lowercased)."""
        grouped: dict[str, list[ConfigMetadata]] = defaultdict(list)

        for metadata in registry.values():
            key = metadata.cls.__name__.lower()
            grouped[key].append(metadata)

        return grouped

    @staticmethod
    def _format_type(type_hint: type | str) -> str:
        """Format type hint for display."""
        if isinstance(type_hint, str):
            return type_hint

        if hasattr(type_hint, "__name__"):
            return type_hint.__name__

        return str(type_hint)

    @staticmethod
    def _validate_toml(toml_str: str) -> None:
        """
        Validate TOML syntax.

        Args:
            toml_str: TOML string to validate

        Raises:
            ValueError: If TOML is invalid
        """
        try:
            tomllib.loads(toml_str)
        except Exception as e:
            raise ValueError(f"Generated TOML is invalid: {e}\n\n{toml_str}") from e
