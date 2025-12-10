#!/usr/bin/env python
"""CLI tool to generate configuration templates."""

import argparse
import sys
from pathlib import Path

# Import all modules with @configurable to populate registry
# These imports ensure decorated classes are registered even if not currently used
import xsp.protocols.vast  # noqa: F401
import xsp.transports.http  # noqa: F401

# Add more as protocols are implemented
from xsp.core.config_generator import ConfigGenerator


def main() -> None:
    """Generate xsp-lib configuration template."""
    parser = argparse.ArgumentParser(
        description="Generate xsp-lib configuration template from @configurable registry"
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

    # Generate template
    if args.format == "toml":
        template = ConfigGenerator.generate_toml(group_by=args.group_by)
    elif args.format == "yaml":
        template = ConfigGenerator.generate_yaml(group_by=args.group_by)
    else:
        print(f"Error: Unsupported format {args.format}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output:
        args.output.write_text(template)
        print(f"Configuration template written to {args.output}", file=sys.stderr)
    else:
        print(template)


if __name__ == "__main__":
    main()
