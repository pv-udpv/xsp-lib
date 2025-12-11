# Scripts Directory

This directory contains helper scripts for common development and workflow tasks.

## Available Scripts

### `rebase-pr.sh` - Rebase PR Branch Helper

A CLI helper script for triggering the rebase workflow with an easy-to-use interface.

**Quick Start:**
```bash
# Rebase a PR by number
./scripts/rebase-pr.sh --pr 123

# Rebase with staging branch (safe mode)
./scripts/rebase-pr.sh --pr 123 --staging

# Rebase a specific branch
./scripts/rebase-pr.sh --branch feature/my-feature
```

**Full Usage:**
```bash
./scripts/rebase-pr.sh --pr <number> [OPTIONS]
./scripts/rebase-pr.sh --branch <name> [OPTIONS]

Options:
  --pr <number>           PR number to rebase
  --branch <name>         PR branch name to rebase
  --base <branch>         Base branch to rebase onto (default: main)
  --staging               Use staging branch for safe rebasing
  --auto-apply            Auto-apply staging branch if rebase succeeds
  --strategy <strategy>   Merge strategy: none, ours, theirs (default: none)
  -h, --help              Show help message
```

**Examples:**
```bash
# Simple rebase
./scripts/rebase-pr.sh --pr 123

# Safe rebase with manual review
./scripts/rebase-pr.sh --pr 123 --staging

# Safe rebase with auto-apply
./scripts/rebase-pr.sh --pr 123 --staging --auto-apply

# Rebase with conflict resolution
./scripts/rebase-pr.sh --pr 123 --strategy theirs

# Rebase onto different base branch
./scripts/rebase-pr.sh --pr 123 --base develop
```

**Requirements:**
- GitHub CLI (`gh`) must be installed and authenticated
- Must be run from within the repository

**Direct GitHub CLI Usage:**

If you prefer to use `gh` directly without the helper script:

```bash
# Basic rebase
gh workflow run rebase-pr-branch.yml \
  -f pr_branch="feature/my-branch"

# With staging branch
gh workflow run rebase-pr-branch.yml \
  -f pr_branch="feature/my-branch" \
  -f use_staging_branch=true \
  -f auto_apply_staging=false

# Monitor the workflow
gh run list --workflow=rebase-pr-branch.yml
gh run watch
```

## Adding New Scripts

When adding new scripts to this directory:

1. **Make it executable**: `chmod +x scripts/your-script.sh`
2. **Add shebang**: Start with `#!/bin/bash` or appropriate interpreter
3. **Add help**: Include `-h` or `--help` flag
4. **Document it**: Add description to this README
5. **Test it**: Verify it works in different scenarios

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing scripts.
