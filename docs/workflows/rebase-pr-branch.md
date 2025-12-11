# Rebase PR Branch Workflow

This document describes the reusable GitHub Actions workflow for rebasing PR branches with automatic merge conflict detection and resolution.

## Overview

The `rebase-pr-branch.yml` workflow provides a consistent, reusable way to:
- Check for merge conflicts before rebasing
- Automatically rebase PR branches onto a base branch (e.g., `main`)
- Optionally resolve merge conflicts automatically
- Use staging branches for safe rebasing operations
- Provide clear feedback about conflict status
- Work as a reusable component in other workflows

## Features

- ✅ **Conflict Detection**: Checks for merge conflicts before attempting rebase
- ✅ **Safe Operations**: Uses `--force-with-lease` to prevent accidental overwrites
- ✅ **Staging Branches**: Optional staging branch for safe rebase testing
- ✅ **Automatic Resolution**: Optional strategies for auto-resolving conflicts
- ✅ **Clear Feedback**: Detailed summaries and PR comments about rebase status
- ✅ **Reusable**: Can be called from other workflows via `workflow_call`
- ✅ **Manual Trigger**: Can be triggered manually via `workflow_dispatch`

## Usage

### As a Reusable Workflow

Call the workflow from another workflow file:

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
      auto_merge_strategy: 'none'
```

### With Staging Branch (Recommended for Safety)

Use a staging branch for safe rebasing:

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
      use_staging_branch: true
      auto_apply_staging: false  # Review before applying
```

### CLI Usage (Recommended)

Use the helper script for easy command-line access:

```bash
# Rebase a PR by number
./scripts/rebase-pr.sh --pr 123

# Rebase with staging branch (safe mode)
./scripts/rebase-pr.sh --pr 123 --staging

# Rebase with auto-apply
./scripts/rebase-pr.sh --pr 123 --staging --auto-apply
```

Or use GitHub CLI directly:

```bash
# Basic rebase
gh workflow run rebase-pr-branch.yml -f pr_branch="feature/my-branch"

# With all options
gh workflow run rebase-pr-branch.yml \
  -f pr_branch="feature/my-branch" \
  -f base_branch="main" \
  -f use_staging_branch=true \
  -f auto_apply_staging=false \
  -f auto_merge_strategy="none"

# Monitor the workflow
gh run watch
```

See [`scripts/README.md`](../../scripts/README.md) for more CLI examples.

### Manual Trigger via UI

Trigger manually from the GitHub Actions UI:

1. Go to **Actions** → **Rebase PR Branch**
2. Click **Run workflow**
3. Fill in the inputs:
   - **base_branch**: The branch to rebase onto (default: `main`)
   - **pr_branch**: The PR branch to rebase (required)
   - **auto_merge_strategy**: How to handle conflicts (default: `none`)
   - **use_staging_branch**: Use staging branch for safety (default: `false`)
   - **auto_apply_staging**: Auto-apply staging if successful (default: `false`)

### Automatic Rebasing

The `auto-rebase-pr.yml` example workflow shows how to automatically rebase all open PRs when `main` is updated:

```yaml
# Triggers on push to main or manual dispatch
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  rebase-prs:
    uses: ./.github/workflows/rebase-pr-branch.yml
    # ... configuration
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base_branch` | Base branch to rebase onto (e.g., `main`) | No | `main` |
| `pr_branch` | PR branch to rebase | Yes | - |
| `auto_merge_strategy` | Strategy for auto-resolving conflicts | No | `none` |
| `use_staging_branch` | Use staging branch for safe rebasing | No | `false` |
| `auto_apply_staging` | Auto-apply staging branch if rebase succeeds | No | `false` |

### Auto-Merge Strategies

- **`none`**: Don't auto-resolve conflicts (manual resolution required)
- **`ours`**: Prefer changes from the PR branch
- **`theirs`**: Prefer changes from the base branch

⚠️ **Warning**: Auto-merge strategies should be used with caution and only when you understand the implications.

### Staging Branch Feature

The staging branch feature provides an extra safety layer:

- **`use_staging_branch: true`**: Creates a temporary branch for the rebase operation
  - Branch naming: `rebase/<sanitized-pr-branch-name>`
  - Slashes in PR branch names are replaced with dashes (e.g., `feature/api/auth` → `rebase/feature-api-auth`)
- **`auto_apply_staging: false`**: Keeps the staging branch separate, allowing manual review before applying
- **`auto_apply_staging: true`**: Automatically applies the staging branch to the PR branch if rebase succeeds

**Benefits:**
- Original PR branch remains untouched during rebase
- Review the rebased code in staging branch before applying
- Safe rollback if issues are found
- Can be tested in CI/CD before merging
- Staging branch is kept for reference (manual deletion if needed)

## Outputs

| Output | Description |
|--------|-------------|
| `has_conflicts` | Whether merge conflicts were detected (`true`/`false`) |
| `staging_branch` | Name of staging branch (if used) |
| `conflict_files` | Comma-separated list of files with conflicts |
| `rebase_status` | Status of rebase operation (`success`, `conflicts`, `failed`) |

## Examples

### Example 1: Safe Rebase with Manual Conflict Resolution

```yaml
jobs:
  rebase:
    uses: ./.github/workflows/rebase-pr-branch.yml
    permissions:
      contents: write
      pull-requests: write
    with:
      base_branch: 'main'
      pr_branch: 'feature/new-protocol'
      auto_merge_strategy: 'none'
```

**Result**: If conflicts are detected, the workflow will:
- Report the conflict status
- List conflicted files
- Provide instructions for manual resolution
- **Not** push any changes

### Example 2: Safe Rebase with Staging Branch

```yaml
jobs:
  rebase:
    uses: ./.github/workflows/rebase-pr-branch.yml
    permissions:
      contents: write
      pull-requests: write
    with:
      base_branch: 'main'
      pr_branch: 'feature/new-protocol'
      use_staging_branch: true
      auto_apply_staging: false
```

**Result**: The workflow will:
- Create a staging branch `rebase/feature/new-protocol`
- Perform rebase on the staging branch
- Original PR branch remains unchanged
- Provides instructions to review and manually apply the staging branch
- Safe to test and review before applying

### Example 3: Rebase with Automatic "Theirs" Resolution

```yaml
jobs:
  rebase:
    uses: ./.github/workflows/rebase-pr-branch.yml
    permissions:
      contents: write
      pull-requests: write
    with:
      base_branch: 'main'
      pr_branch: 'docs/update-readme'
      auto_merge_strategy: 'theirs'
```

**Result**: If conflicts are detected in documentation files, the workflow will:
- Attempt to resolve conflicts by preferring base branch changes
- Push the rebased branch if successful
- Fall back to manual resolution if automatic resolution fails

### Example 4: Staging Branch with Auto-Apply

```yaml
jobs:
  rebase:
    uses: ./.github/workflows/rebase-pr-branch.yml
    permissions:
      contents: write
      pull-requests: write
    with:
      base_branch: 'main'
      pr_branch: 'feature/safe-update'
      use_staging_branch: true
      auto_apply_staging: true
```

**Result**: The workflow will:
- Create a staging branch
- Perform rebase on staging branch
- If successful, automatically apply staging branch to PR branch
- Staging branch is kept for reference

### Example 5: Rebase Multiple PRs After Main Update

```yaml
jobs:
  find-prs:
    # Find all open PRs
    runs-on: ubuntu-latest
    outputs:
      pr_branches: ${{ steps.get_prs.outputs.branches }}
    steps:
      # ... get list of PR branches

  rebase-prs:
    needs: find-prs
    strategy:
      matrix:
        branch: ${{ fromJson(needs.find-prs.outputs.pr_branches) }}
      max-parallel: 1  # One at a time
      fail-fast: false
    
    uses: ./.github/workflows/rebase-pr-branch.yml
    with:
      base_branch: 'main'
      pr_branch: ${{ matrix.branch }}
```

**Result**: All open PRs will be rebased sequentially, with clear feedback for each.

## Workflow Steps

1. **Checkout**: Fetches the PR branch with full history
2. **Check Conflicts**: Tests for merge conflicts using `git merge --no-commit --no-ff`
3. **Rebase**: Performs the actual rebase operation
4. **Auto-Resolve**: Applies merge strategy if conflicts detected (optional)
5. **Push**: Force-pushes rebased branch using `--force-with-lease`
6. **Summary**: Creates detailed summary and PR comment

## Conflict Resolution

### When Conflicts Are Detected

The workflow will:
- Report the number of conflicted files
- List each conflicted file
- Provide clear instructions for manual resolution
- Skip pushing if `auto_merge_strategy` is `none`

### Manual Resolution Instructions

If conflicts require manual resolution:

```bash
# Fetch latest changes
git fetch origin main

# Start rebase
git rebase origin/main

# Git will pause at conflicts
# Edit conflicted files in your editor
# Look for conflict markers: <<<<<<< ======= >>>>>>>

# Stage resolved files
git add <resolved-file>

# Continue rebase
git rebase --continue

# Push rebased branch
git push --force-with-lease origin <your-branch>
```

## Best Practices

### DO ✅

- Use `auto_merge_strategy: 'none'` by default (safest option)
- Review the workflow summary before merging
- Use `--force-with-lease` for pushing (built-in)
- Test manual conflict resolution in a local clone first
- Monitor the workflow output for unexpected issues

### DON'T ❌

- Use `ours` or `theirs` strategy without understanding the changes
- Auto-rebase critical branches without review
- Ignore conflict warnings in the workflow output
- Force-push without `--force-with-lease`
- Run concurrent rebases on the same branch

## Integration with Other Workflows

### Pre-Merge Checks

Add rebase check before merging:

```yaml
jobs:
  check-rebase:
    uses: ./.github/workflows/rebase-pr-branch.yml
    with:
      base_branch: 'main'
      pr_branch: ${{ github.head_ref }}
      auto_merge_strategy: 'none'
  
  merge:
    needs: check-rebase
    if: needs.check-rebase.outputs.rebase_status == 'success'
    # ... merge job
```

### Scheduled Rebasing

Keep PRs up-to-date automatically:

```yaml
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  rebase-all:
    uses: ./.github/workflows/auto-rebase-pr.yml
```

## Troubleshooting

### Issue: Rebase fails with "fatal: invalid upstream"

**Solution**: Ensure the `base_branch` exists and is spelled correctly.

### Issue: Conflicts not detected but rebase fails

**Solution**: The test merge and actual rebase may differ. Check the workflow logs for details.

### Issue: Force-push fails with "stale info"

**Solution**: The branch was updated externally. The workflow uses `--force-with-lease` to prevent accidental overwrites. Re-run the workflow.

### Issue: Auto-merge strategy doesn't resolve all conflicts

**Solution**: Some conflicts are too complex for automatic resolution. Use `auto_merge_strategy: 'none'` and resolve manually.

## Security Considerations

- **Permissions**: Workflow requires `contents: write` and `pull-requests: write`
- **Force-Push Safety**: Uses `--force-with-lease` to prevent accidental overwrites
- **Auto-Merge Risk**: Automatic conflict resolution may produce incorrect merges
- **Branch Protection**: Compatible with branch protection rules

## Contributing

When modifying the rebase workflow:

1. Test with a test PR first
2. Verify conflict detection works correctly
3. Test all auto-merge strategies
4. Update this documentation
5. Add examples for new features

## Related Files

- `.github/workflows/rebase-pr-branch.yml` - Main reusable workflow
- `.github/workflows/auto-rebase-pr.yml` - Example auto-rebase workflow
- `.github/workflows/ci.yml` - CI workflow
- `.github/workflows/linting-fixes.yml` - Linting workflow

## Questions?

For questions or issues with the rebase workflow:
1. Check the workflow logs in the Actions tab
2. Review this documentation
3. Open an issue with the `workflow` label
4. Tag workflow maintainers for workflow-related questions
