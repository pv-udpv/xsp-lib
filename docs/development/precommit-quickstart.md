# Quick Start: Pre-commit Setup

## TL;DR

```bash
# Install and setup (one-time)
pip install pre-commit
pre-commit install

# Done! Now git commit will automatically:
# ✅ Format code (ruff format)
# ✅ Fix linting (ruff check --fix)
# ✅ Check types (mypy)
# ✅ Run tests (pytest)
# ✅ Check security (bandit)
```

## What Happens on Commit

```bash
$ git commit -m "feat: add new feature"

Ruff formatter.............................................Passed
Ruff linter................................................Passed
MyPy type checker.........................................Passed
Pytest....................................................Passed
Trailing whitespace.......................................Passed
End of file fixer.........................................Passed
Check YAML................................................Passed
Bandit security checks....................................Passed

[main 1234567] feat: add new feature
 3 files changed, 42 insertions(+)
```

## If Code Needs Fixing

```bash
$ git commit -m "feat: add new feature"

Ruff formatter.............................................Failed
- hook id: ruff-format
- files were modified by this hook

Fixed 2 files:
  src/xsp/example.py
  tests/test_example.py

# Just add the fixed files and commit again
$ git add .
$ git commit -m "feat: add new feature"
✅ All checks passed!
```

## Skip Checks (Emergency Only)

```bash
# Skip all checks (not recommended)
git commit -m "WIP" --no-verify

# Skip specific check
SKIP=pytest-check git commit -m "fix: quick fix"
```

## Run Manually

```bash
# Run all checks on all files
pre-commit run --all-files

# Run specific check
pre-commit run ruff --all-files
pre-commit run mypy --all-files
pre-commit run pytest-check
```

## Update Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Reinstall hooks
pre-commit clean
pre-commit install
```

## See Also

- [Full Pre-commit Guide](.github/CONTRIBUTING_PRECOMMIT.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
