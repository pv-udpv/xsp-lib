#!/usr/bin/env python3
"""Validate GitHub Copilot agent configuration files.

This script validates that all agent files in .github/agents/ have:
1. Valid YAML frontmatter
2. Required fields (name, description, tools, target)
3. Proper markdown structure
"""

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install PyYAML")
    sys.exit(1)


def validate_agent_file(filepath: Path) -> tuple[bool, list[str]]:
    """Validate a single agent file.
    
    Args:
        filepath: Path to the agent file
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check file exists
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]
    
    # Read file content
    try:
        content = filepath.read_text()
    except Exception as e:
        return False, [f"Failed to read file: {e}"]
    
    # Check frontmatter exists
    if not content.startswith("---"):
        errors.append("Missing YAML frontmatter (should start with ---)")
        return False, errors
    
    # Extract and parse frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("Invalid frontmatter structure (missing closing ---)")
        return False, errors
    
    frontmatter_text = parts[1]
    
    try:
        frontmatter: dict[str, Any] = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {e}")
        return False, errors
    
    # Validate required fields
    required_fields = ["name", "description", "tools", "target"]
    for field in required_fields:
        if field not in frontmatter:
            errors.append(f"Missing required field: {field}")
    
    # Validate field values
    if "name" in frontmatter and not isinstance(frontmatter["name"], str):
        errors.append("Field 'name' must be a string")
    
    if "description" in frontmatter and not isinstance(frontmatter["description"], str):
        errors.append("Field 'description' must be a string")
    
    if "tools" in frontmatter:
        if not isinstance(frontmatter["tools"], list):
            errors.append("Field 'tools' must be a list")
        elif not all(isinstance(t, str) for t in frontmatter["tools"]):
            errors.append("All items in 'tools' must be strings")
    
    if "target" in frontmatter:
        if frontmatter["target"] != "github-copilot":
            errors.append(f"Field 'target' should be 'github-copilot', got '{frontmatter['target']}'")
    
    # Check markdown content exists
    markdown_content = parts[2].strip()
    if not markdown_content:
        errors.append("Missing markdown content after frontmatter")
    
    return len(errors) == 0, errors


def main() -> int:
    """Main validation function."""
    agents_dir = Path(__file__).parent.parent / ".github" / "agents"
    
    if not agents_dir.exists():
        print(f"❌ Agents directory not found: {agents_dir}")
        return 1
    
    # Find all agent files
    agent_files = list(agents_dir.glob("*.md"))
    
    if not agent_files:
        print(f"❌ No agent files found in {agents_dir}")
        return 1
    
    print(f"Validating {len(agent_files)} agent file(s)...\n")
    
    all_valid = True
    for agent_file in sorted(agent_files):
        is_valid, errors = validate_agent_file(agent_file)
        
        if is_valid:
            print(f"✅ {agent_file.name}")
        else:
            print(f"❌ {agent_file.name}")
            for error in errors:
                print(f"   - {error}")
            all_valid = False
    
    print()
    if all_valid:
        print("✅ All agent files are valid!")
        return 0
    else:
        print("❌ Some agent files have errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
