#!/bin/bash
# Rebase PR Branch - GitHub CLI Helper Script
# Usage: ./scripts/rebase-pr.sh [OPTIONS]

set -e

# Default values
BASE_BRANCH="main"
PR_BRANCH=""
PR_NUMBER=""
USE_STAGING="false"
AUTO_APPLY="false"
MERGE_STRATEGY="none"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help message
show_help() {
    cat << EOF
Rebase PR Branch Helper

Usage: 
    $(basename "$0") --pr <number> [OPTIONS]
    $(basename "$0") --branch <name> [OPTIONS]

Options:
    --pr <number>           PR number to rebase
    --branch <name>         PR branch name to rebase
    --base <branch>         Base branch to rebase onto (default: main)
    --staging               Use staging branch for safe rebasing
    --auto-apply            Auto-apply staging branch if rebase succeeds
    --strategy <strategy>   Merge strategy: none, ours, theirs (default: none)
    -h, --help              Show this help message

Examples:
    # Rebase PR #123 onto main
    $(basename "$0") --pr 123

    # Rebase with staging branch (safe mode)
    $(basename "$0") --pr 123 --staging

    # Rebase specific branch
    $(basename "$0") --branch feature/my-feature

    # Rebase with auto-apply staging
    $(basename "$0") --pr 123 --staging --auto-apply

    # Rebase with conflict resolution strategy
    $(basename "$0") --pr 123 --strategy theirs

Requirements:
    - GitHub CLI (gh) must be installed and authenticated
    - Must be in a git repository with GitHub remote

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --pr)
            PR_NUMBER="$2"
            shift 2
            ;;
        --branch)
            PR_BRANCH="$2"
            shift 2
            ;;
        --base)
            BASE_BRANCH="$2"
            shift 2
            ;;
        --staging)
            USE_STAGING="true"
            shift
            ;;
        --auto-apply)
            AUTO_APPLY="true"
            shift
            ;;
        --strategy)
            MERGE_STRATEGY="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Get PR branch from PR number if provided
if [ -n "$PR_NUMBER" ]; then
    echo -e "${BLUE}Fetching PR #${PR_NUMBER} details...${NC}"
    PR_BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName -q .headRefName 2>/dev/null)
    
    if [ -z "$PR_BRANCH" ]; then
        echo -e "${RED}Error: Could not find PR #${PR_NUMBER}${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Found PR branch: ${PR_BRANCH}${NC}"
fi

# Validate required parameters
if [ -z "$PR_BRANCH" ]; then
    echo -e "${RED}Error: Either --pr or --branch must be specified${NC}"
    show_help
    exit 1
fi

# Validate merge strategy
if [[ ! "$MERGE_STRATEGY" =~ ^(none|ours|theirs)$ ]]; then
    echo -e "${RED}Error: Invalid strategy. Must be: none, ours, or theirs${NC}"
    exit 1
fi

# Display configuration
echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  Rebase Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "  PR Branch:        ${GREEN}${PR_BRANCH}${NC}"
echo -e "  Base Branch:      ${GREEN}${BASE_BRANCH}${NC}"
echo -e "  Use Staging:      ${GREEN}${USE_STAGING}${NC}"
echo -e "  Auto-Apply:       ${GREEN}${AUTO_APPLY}${NC}"
echo -e "  Merge Strategy:   ${GREEN}${MERGE_STRATEGY}${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Confirm with user
read -p "Proceed with rebase? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Rebase cancelled${NC}"
    exit 0
fi

# Trigger the workflow
echo -e "${BLUE}Triggering rebase workflow...${NC}"

gh workflow run rebase-pr-branch.yml \
    -f base_branch="$BASE_BRANCH" \
    -f pr_branch="$PR_BRANCH" \
    -f auto_merge_strategy="$MERGE_STRATEGY" \
    -f use_staging_branch="$USE_STAGING" \
    -f auto_apply_staging="$AUTO_APPLY"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Rebase workflow triggered successfully!${NC}"
    echo ""
    echo -e "${BLUE}Monitor workflow progress:${NC}"
    echo "  gh run list --workflow=rebase-pr-branch.yml"
    echo "  gh run watch"
    echo ""
    echo -e "${BLUE}View workflow logs:${NC}"
    echo "  gh run view --log"
    echo ""
    
    # Wait a moment for the run to be created
    sleep 2
    
    # Try to get the latest run
    LATEST_RUN=$(gh run list --workflow=rebase-pr-branch.yml --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null)
    
    if [ -n "$LATEST_RUN" ]; then
        echo -e "${BLUE}Latest run ID: ${LATEST_RUN}${NC}"
        echo ""
        read -p "Watch the workflow run? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            gh run watch "$LATEST_RUN"
        fi
    fi
else
    echo -e "${RED}❌ Failed to trigger rebase workflow${NC}"
    exit 1
fi
