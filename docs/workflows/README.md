# GitHub Actions Workflows Documentation

This directory contains documentation for the GitHub Actions workflows used in the xsp-lib repository.

## Available Workflows

### [Rebase PR Branch](./rebase-pr-branch.md)

A reusable workflow for rebasing PR branches with automatic merge conflict detection and resolution.

**Key Features:**
- ✅ Detects merge conflicts before rebasing
- ✅ Optional automatic conflict resolution
- ✅ Safe force-push with `--force-with-lease`
- ✅ Reusable across multiple workflows
- ✅ Manual trigger support

**Use Cases:**
- Auto-rebase PRs when main branch is updated
- Manual rebase via GitHub Actions UI
- Pre-merge conflict checks
- Scheduled PR updates

**Quick Start:**
```yaml
jobs:
  rebase:
    uses: ./.github/workflows/rebase-pr-branch.yml
    permissions:
      contents: write
      pull-requests: write
    with:
      base_branch: 'main'
      pr_branch: 'feature/my-feature'
```

See [full documentation](./rebase-pr-branch.md) for detailed usage, examples, and troubleshooting.

## Workflow Files

All workflow files are located in `.github/workflows/`:

| Workflow | Description | Trigger |
|----------|-------------|---------|
| `rebase-pr-branch.yml` | Reusable rebase workflow with conflict detection | `workflow_call`, `workflow_dispatch` |
| `auto-rebase-pr.yml` | Auto-rebase all PRs when main updates | `push` to main, `workflow_dispatch` |
| `ci.yml` | Continuous integration tests and checks | `push`, `pull_request` |
| `codeql.yml` | CodeQL security analysis | `push`, `pull_request`, `schedule` |
| `copilot-setup-steps.yml` | Copilot development environment setup | `workflow_call`, `workflow_dispatch` |
| `linting-fixes.yml` | Automatic linting fixes collection | `pull_request` |
| `pre-commit.yml` | Pre-commit hooks validation | `push`, `pull_request` |
| `release.yml` | Package release automation | `push` (tags) |

## Contributing

When adding new workflows:

1. Create the workflow file in `.github/workflows/`
2. Add documentation in this directory
3. Update this README with a link to the documentation
4. Add usage examples
5. Test the workflow thoroughly

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
