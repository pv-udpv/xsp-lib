#!/usr/bin/env python
"""CLI tool to generate configuration templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    """Generate xsp-lib configuration template."""
    parser = argparse.ArgumentParser(
        description="Generate xsp-lib configuration template from @configurable registry",
        epilog="Example: python -m xsp.cli.generate_config --output settings.toml",
    )
    parser.add_argument(
        "--format",
        choices=["toml", "yaml"],
        default="toml",
        help="Output format (default: toml)",
    )
    parser.add_argument(
        "--group-by",
        choices=["namespace", "class"],
        default="namespace",
        help="Grouping strategy (default: namespace)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    # Import all modules with @configurable to populate registry
    # This ensures all decorated classes are registered
    try:
        import xsp.transports.http  # noqa: F401
    except ImportError:
        pass

    try:
        import xsp.transports.file  # noqa: F401
    except ImportError:
        pass

    try:
        import xsp.transports.memory  # noqa: F401
    except ImportError:
        pass

    # Import protocol modules when they exist
    try:
        import xsp.protocols.vast  # noqa: F401
    except ImportError:
        pass

    try:
        import xsp.protocols.openrtb  # noqa: F401
    except ImportError:
        pass

    # Import the generator after modules are loaded
    from xsp.core.config_generator import ConfigGenerator

    # Generate template
    try:
        if args.format == "toml":
            template = ConfigGenerator.generate_toml(group_by=args.group_by)
        elif args.format == "yaml":
            template = ConfigGenerator.generate_yaml(group_by=args.group_by)
        else:
            print(f"Error: Unsupported format {args.format}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error generating configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output:
        try:
            args.output.write_text(template, encoding="utf-8")
            print(f"Configuration template written to {args.output}", file=sys.stderr)
        except OSError as e:
            print(f"Error writing to {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(template)


if __name__ == "__main__":
    main()
