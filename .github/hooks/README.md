# Pre-commit Hooks Guide

This repository uses [pre-commit](https://pre-commit.com/) to enforce code quality standards **before** commits are created.

## 🎯 Why Pre-commit Hooks?

- ✅ **Instant feedback**: Catch issues locally, not in CI
- ✅ **Auto-formatting**: Code is automatically formatted before commit
- ✅ **Prevent broken commits**: Type errors and test failures caught early
- ✅ **Faster workflow**: No waiting for CI to run, then fix, then push again

## 📦 Installation

### One-time Setup

```bash
# Install pre-commit (already in dev dependencies)
pip install -e .[dev]

# Install the git hooks
pre-commit install

# (Optional) Run on all files to test
pre-commit run --all-files
```

That's it! Now hooks will run automatically on `git commit`.

## 🔧 What Hooks Do

### 1. Standard Checks (Fast)
- Remove trailing whitespace
- Fix end-of-file newlines
- Validate YAML/TOML syntax
- Check for merge conflicts
- Prevent large files (>1MB)

### 2. Ruff (Auto-fix)
- **Lint**: `ruff check --fix` - Auto-fixes common issues
- **Format**: `ruff format` - Formats code to project style

### 3. MyPy (Type Check)
- Runs `mypy --strict` on `src/` only
- Validates type hints and type safety
- Skips tests (they have looser typing)

### 4. Pytest (Unit Tests)
- Runs `pytest tests/unit/` - Fast unit tests only
- Skips slow integration/e2e tests
- Only runs if Python files changed

## 🚀 Workflow

### Normal Commit (Hooks Auto-run)

```bash
# Make changes
vim src/xsp/core/upstream.py

# Stage changes
git add src/xsp/core/upstream.py

# Commit (hooks run automatically)
git commit -m "feat(core): add new upstream method"
```

**What happens:**
1. Standard checks run (whitespace, yaml, etc.)
2. Ruff auto-formats your code
3. Ruff auto-fixes lint issues
4. MyPy checks types in `src/`
5. Pytest runs unit tests

If any hook fails, the commit is **aborted** and you see the error.

### Fixing Hook Failures

If a hook fails:

```bash
# Example: MyPy found type error
$ git commit -m "feat: add feature"
MyPy type check..............................................Failed
- hook id: mypy
- exit code: 1

src/xsp/core/upstream.py:45: error: Missing return type

# Fix the error
vim src/xsp/core/upstream.py

# Stage fix
git add src/xsp/core/upstream.py

# Try commit again
git commit -m "feat: add feature"
```

### Skipping Hooks (When Needed)

```bash
# Skip hooks for this commit (use sparingly!)
git commit --no-verify -m "wip: temp commit"

# Or skip specific files
git commit --no-verify -- docs/README.md
```

**When to skip:**
- WIP commits in feature branch
- Emergency hotfixes
- Documentation-only changes (though hooks are fast)

⚠️ **Warning**: CI will still run full checks, so skipped hooks may cause CI failures.

## 🧪 Testing Hooks

### Run All Hooks Manually

```bash
# Run on all files (useful after setup)
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
pre-commit run mypy --all-files
pre-commit run pytest-unit --all-files
```

### Run Hooks on Staged Files

```bash
# Stage some files
git add src/xsp/core/upstream.py tests/unit/test_upstream.py

# Run hooks (same as during commit)
pre-commit run
```

### Update Hook Versions

```bash
# Update to latest hook versions
pre-commit autoupdate

# Review changes in .pre-commit-config.yaml
git diff .pre-commit-config.yaml
```

## 🐛 Troubleshooting

### Hooks Not Running

```bash
# Verify hooks are installed
pre-commit install

# Check git hooks directory
ls -la .git/hooks/

# Should see: pre-commit (file exists and executable)
```

### Hook Failures

**MyPy fails with "module not found":**
```bash
# MyPy needs additional dependencies
pip install -e .[dev]  # Reinstall with all deps
```

**Pytest runs too slow:**
- Hooks only run unit tests (`tests/unit/`)
- Integration/e2e tests run in CI only
- If still slow, check if you added a slow test to `tests/unit/`

**Ruff format conflicts with my editor:**
- Configure your editor to use `ruff format` on save
- VS Code: Install Ruff extension, enable format on save
- See: [docs/development/editor-setup.md](../development/editor-setup.md)

### Disabling Hooks Temporarily

```bash
# Disable all hooks
pre-commit uninstall

# Re-enable later
pre-commit install
```

## 📋 Hook Configuration

Hooks are configured in [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) at repository root.

### Customizing Hooks

To skip a specific hook, add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        # Add this to skip:
        stages: [manual]  # Only run with --all-files
```

### Adding New Hooks

```yaml
repos:
  # Add a new hook
  - repo: https://github.com/someorg/some-hook
    rev: v1.0.0
    hooks:
      - id: some-hook
        name: Some Hook Name
```

See [pre-commit.com](https://pre-commit.com/hooks.html) for available hooks.

## 🎓 Best Practices

### DO:
- ✅ Run `pre-commit install` immediately after cloning repo
- ✅ Let hooks auto-fix formatting issues
- ✅ Fix type errors and test failures before committing
- ✅ Run `pre-commit run --all-files` after major changes

### DON'T:
- ❌ Skip hooks habitually with `--no-verify`
- ❌ Commit without running hooks and rely on CI
- ❌ Disable hooks globally (only skip when truly needed)
- ❌ Add slow tests to `tests/unit/` (use `tests/integration/`)

## 🔗 Resources

- [pre-commit documentation](https://pre-commit.com/)
- [Ruff pre-commit integration](https://docs.astral.sh/ruff/integrations/#pre-commit)
- [MyPy pre-commit integration](https://github.com/pre-commit/mirrors-mypy)
- [xsp-lib Contributing Guide](../../CONTRIBUTING.md)

## 🆘 Getting Help

If hooks are causing issues:

1. Check this README
2. Run `pre-commit run --all-files --verbose` for details
3. Check CI logs (hooks should match CI checks)
4. Ask in team chat or GitHub discussions
5. Open an issue: [github.com/pv-udpv/xsp-lib/issues](https://github.com/pv-udpv/xsp-lib/issues)
