"""Generate TOML configuration template from @configurable registry.

Usage:
    python -m xsp.cli.generate_config [options]

Example:
    python -m xsp.cli.generate_config --output settings.toml
    python -m xsp.cli.generate_config --group-by class
"""

import argparse
import sys
from pathlib import Path

from xsp.core.config_generator import ConfigGenerator


def main() -> None:
    """Generate TOML configuration template."""
    parser = argparse.ArgumentParser(
        description="Generate TOML configuration template from @configurable registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (default: stdout)",
    )

    parser.add_argument(
        "--group-by",
        choices=["namespace", "class"],
        default="namespace",
        help="How to group configuration sections (default: namespace)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate generated TOML (default: true)",
    )

    parser.add_argument(
        "--no-validate",
        dest="validate",
        action="store_false",
        help="Skip TOML validation (faster, less safe)",
    )

    args = parser.parse_args()

    try:
        # Generate TOML
        template = ConfigGenerator.generate_toml(
            group_by=args.group_by,
            validate=args.validate,
        )

        # Write to file or stdout
        if args.output:
            args.output.write_text(template)
            print(f"Configuration template written to {args.output}", file=sys.stderr)
        else:
            print(template)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
