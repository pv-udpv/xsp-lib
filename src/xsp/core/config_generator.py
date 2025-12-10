"""Configuration template generator for xsp-lib.

Generates TOML configuration templates from @configurable registry with
proper syntax validation.
"""

from typing import Any

import tomlkit
from tomlkit import comment, document, nl, table

from xsp.core.configurable import get_configurable_registry

# Use tomllib for validation on Python 3.11+, or fallback to tomli
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


class ConfigGenerator:
    """Generate TOML configuration templates from @configurable registry."""

    @staticmethod
    def generate_toml(group_by: str = "namespace", validate: bool = True) -> str:
        """
        Generate TOML configuration template.

        Uses tomlkit for proper TOML serialization with comment preservation.
        Automatically validates generated TOML syntax.

        Args:
            group_by: How to group configuration ("namespace" or "class")
            validate: Whether to validate generated TOML (default: True)

        Returns:
            TOML configuration string

        Raises:
            ValueError: If group_by is invalid or generated TOML is invalid
        """
        registry = get_configurable_registry()

        if not registry:
            return "# No configurable classes found\n"

        # Build TOML document
        if group_by == "namespace":
            toml_str = ConfigGenerator._generate_by_namespace(registry)
        elif group_by == "class":
            toml_str = ConfigGenerator._generate_by_class(registry)
        else:
            raise ValueError(f"Unknown group_by: {group_by}")

        # Validate by parsing
        if validate:
            ConfigGenerator._validate_toml(toml_str)

        return toml_str

    @staticmethod
    def _generate_by_namespace(registry: dict[str, Any]) -> str:
        """Generate TOML grouped by namespace."""
        doc = document()
        doc.add(comment("XSP-lib Configuration Template"))
        doc.add(comment("Auto-generated from @configurable registry"))
        doc.add(nl())

        # Group by namespace
        grouped: dict[str, list[Any]] = {}
        for metadata in registry.values():
            grouped.setdefault(metadata.namespace, []).append(metadata)

        # Generate sections
        for namespace in sorted(grouped.keys()):
            metadata_list = grouped[namespace]
            section_table = table()

            for metadata in metadata_list:
                # Add class description as comment
                if metadata.description:
                    section_table.add(comment(metadata.description))
                section_table.add(comment(f"Source: {metadata.cls.__name__}"))
                section_table.add(nl())

                # Add parameters
                for param_name, param_info in metadata.parameters.items():
                    # Add parameter description as comment
                    if param_info.description:
                        section_table.add(comment(param_info.description))

                    # Add type information as comment
                    type_str = ConfigGenerator._format_type(param_info.type)
                    section_table.add(comment(f"Type: {type_str}"))

                    # Add parameter with default value
                    # Handle None values - tomlkit doesn't support None, so comment them out
                    if param_info.default is None:
                        section_table.add(comment(f"{param_name} = null  # None value"))
                    else:
                        section_table[param_name] = param_info.default
                    section_table.add(nl())

            doc[namespace] = section_table
            doc.add(nl())

        return tomlkit.dumps(doc)

    @staticmethod
    def _generate_by_class(registry: dict[str, Any]) -> str:
        """Generate TOML grouped by class name."""
        doc = document()
        doc.add(comment("XSP-lib Configuration Template"))
        doc.add(comment("Auto-generated from @configurable registry"))
        doc.add(nl())

        # Generate sections by class
        for key in sorted(registry.keys()):
            metadata = registry[key]
            section_name = f"{metadata.namespace}.{metadata.cls.__name__}"
            section_table = table()

            # Add class description as comment
            if metadata.description:
                section_table.add(comment(metadata.description))
            section_table.add(nl())

            # Add parameters
            for param_name, param_info in metadata.parameters.items():
                # Add parameter description as comment
                if param_info.description:
                    section_table.add(comment(param_info.description))

                # Add type information as comment
                type_str = ConfigGenerator._format_type(param_info.type)
                section_table.add(comment(f"Type: {type_str}"))

                # Add parameter with default value
                # Handle None values - tomlkit doesn't support None, so comment them out
                if param_info.default is None:
                    section_table.add(comment(f"{param_name} = null  # None value"))
                else:
                    section_table[param_name] = param_info.default
                section_table.add(nl())

            doc[section_name] = section_table
            doc.add(nl())

        return tomlkit.dumps(doc)

    @staticmethod
    def _format_type(type_hint: Any) -> str:
        """Format type hint as string."""
        if type_hint is Any:
            return "Any"
        if hasattr(type_hint, "__name__"):
            return str(type_hint.__name__)
        return str(type_hint)

    @staticmethod
    def _validate_toml(toml_str: str) -> None:
        """
        Validate TOML syntax by parsing.

        Args:
            toml_str: TOML string to validate

        Raises:
            ValueError: If TOML is invalid
        """
        if tomllib is None:
            # Skip validation if tomli/tomllib not available
            return

        try:
            tomllib.loads(toml_str)
        except Exception as e:
            raise ValueError(f"Generated TOML is invalid: {e}\n\n{toml_str}") from e
