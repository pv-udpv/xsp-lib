"""Command-line interface entry point."""

import sys
import asyncio
from pathlib import Path

from .engine import RopeEngine


async def main() -> int:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m rope_toolkit <command>")
        print("Commands: index, analyze, health, refactor")
        return 1
    
    command = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else "."
    
    engine = RopeEngine(project_root)
    
    try:
        if command == "index":
            count = await engine.index_project()
            print(f"Indexed {count} symbols")
            return 0
        elif command == "analyze":
            report = await engine.analyze()
            print(f"Health score: {report.health_score}/100")
            return 0
        elif command == "health":
            health = engine.health_check()
            for service, status in health.items():
                print(f"{service}: {'✓' if status else '✗'}")
            return 0
        else:
            print(f"Unknown command: {command}")
            return 1
    finally:
        await engine.shutdown()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
