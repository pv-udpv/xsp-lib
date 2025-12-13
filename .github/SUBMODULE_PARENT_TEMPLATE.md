# Submodule Auto-Update Setup

Для репозиториев, использующих `xsp-lib` как **git submodule** (например, `zbst-tech`).

## 🎯 Два режима обновления

### 1. Scheduled (ежедневная проверка)
- Cron: каждый день в 03:00 MSK
- Обновляет до последнего stable tag

### 2. Instant (triggered by xsp-lib release)
- Срабатывает при релизе xsp-lib
- Получает конкретную версию из payload
- Мгновенное обновление

## 📝 Workflow для родительского репо

Создай `.github/workflows/update-submodules.yml` в **zbst-tech** (или другом родительском репо):

```yaml
name: Update Submodules

on:
  schedule:
    # Ежедневно в 03:00 UTC (06:00 MSK)
    - cron: '0 3 * * *'
  repository_dispatch:
    types: [submodule-update]
  workflow_dispatch:
    inputs:
      target_repo:
        description: 'Target repo URL (e.g., pv-udpv/xsp-lib) or "all"'
        required: false
        default: 'all'
      version:
        description: 'Target version/tag (empty = latest)'
        required: false
        default: ''

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  detect-submodules:
    runs-on: ubuntu-latest
    outputs:
      submodules: ${{ steps.parse.outputs.submodules }}
      has_submodules: ${{ steps.parse.outputs.has_submodules }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Parse .gitmodules
        id: parse
        run: |
          echo "🔍 Detecting git submodules..."
          
          if [ ! -f .gitmodules ]; then
            echo "has_submodules=false" >> $GITHUB_OUTPUT
            echo "⚠️  No .gitmodules found"
            exit 0
          fi
          
          # Parse .gitmodules into JSON array
          SUBMODULES=$(git config -f .gitmodules --get-regexp '^submodule\..+\.(path|url)$' | \
            awk '
              BEGIN { print "[" }
              /\.path/ { path = $2 }
              /\.url/ { 
                url = $2
                gsub(/.*\//, "", url)  # Extract repo name from URL
                gsub(/\.git$/, "", url)
                if (path && url) {
                  if (NR > 2) print ","
                  printf "{\"path\":\"%s\",\"url\":\"%s\",\"repo\":\"%s\"}", path, $2, url
                  path = ""
                }
              }
              END { print "\n]" }
            ')
          
          echo "submodules=$SUBMODULES" >> $GITHUB_OUTPUT
          echo "has_submodules=true" >> $GITHUB_OUTPUT
          
          echo "📋 Found submodules:"
          echo "$SUBMODULES" | jq -r '.[] | "  - \(.path) (\(.repo))"'

  update-submodules:
    needs: detect-submodules
    if: needs.detect-submodules.outputs.has_submodules == 'true'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        submodule: ${{ fromJSON(needs.detect-submodules.outputs.submodules) }}
      fail-fast: false
      max-parallel: 3
    
    steps:
      - name: Checkout with submodules
        uses: actions/checkout@v4
        with:
          submodules: recursive
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Determine if should update this submodule
        id: should_update
        run: |
          SUBMODULE_URL="${{ matrix.submodule.url }}"
          SUBMODULE_REPO="${{ matrix.submodule.repo }}"
          
          # Check if triggered by specific repo
          if [ "${{ github.event_name }}" == "repository_dispatch" ]; then
            TRIGGER_REPO="${{ github.event.client_payload.triggeredBy }}"
            if [[ ! "$SUBMODULE_URL" =~ "$TRIGGER_REPO" ]] && [ "$TRIGGER_REPO" != "all" ]; then
              echo "skip=true" >> $GITHUB_OUTPUT
              echo "⏭️  Skipping $SUBMODULE_REPO - not triggered by this repo"
              exit 0
            fi
          fi
          
          # Check manual input filter
          if [ -n "${{ inputs.target_repo }}" ] && [ "${{ inputs.target_repo }}" != "all" ]; then
            if [[ ! "$SUBMODULE_URL" =~ "${{ inputs.target_repo }}" ]]; then
              echo "skip=true" >> $GITHUB_OUTPUT
              echo "⏭️  Skipping $SUBMODULE_REPO - not matching filter"
              exit 0
            fi
          fi
          
          echo "skip=false" >> $GITHUB_OUTPUT
          echo "✅ Will update $SUBMODULE_REPO"

      - name: Update submodule
        if: steps.should_update.outputs.skip == 'false'
        id: update
        run: |
          SUBMODULE_PATH="${{ matrix.submodule.path }}"
          
          cd "$SUBMODULE_PATH"
          
          # Текущая версия
          CURRENT_SHA=$(git rev-parse HEAD)
          CURRENT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "${CURRENT_SHA:0:7}")
          
          echo "📌 Current: $CURRENT_TAG ($CURRENT_SHA)"
          
          # Fetch latest
          git fetch origin --tags --prune
          
          # Определить целевую версию
          if [ -n "${{ github.event.client_payload.version }}" ]; then
            TARGET_REF="${{ github.event.client_payload.version }}"
          elif [ -n "${{ inputs.version }}" ]; then
            TARGET_REF="${{ inputs.version }}"
          else
            # Latest stable tag (vX.Y.Z format)
            TARGET_REF=$(git tag -l 'v[0-9]*' --sort=-version:refname | head -n1)
            if [ -z "$TARGET_REF" ]; then
              TARGET_REF="origin/main"
            fi
          fi
          
          echo "🎯 Target: $TARGET_REF"
          
          # Checkout новой версии
          git checkout "$TARGET_REF"
          NEW_SHA=$(git rev-parse HEAD)
          NEW_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "${NEW_SHA:0:7}")
          
          cd ..
          
          # Git add submodule change
          git add "$SUBMODULE_PATH"
          
          # Проверить есть ли изменения
          if git diff --cached --quiet; then
            echo "has_changes=false" >> $GITHUB_OUTPUT
            echo "✅ Already up to date: $CURRENT_TAG"
          else
            echo "has_changes=true" >> $GITHUB_OUTPUT
            echo "current_version=$CURRENT_TAG" >> $GITHUB_OUTPUT
            echo "new_version=$NEW_TAG" >> $GITHUB_OUTPUT
            echo "current_sha=${CURRENT_SHA:0:7}" >> $GITHUB_OUTPUT
            echo "new_sha=${NEW_SHA:0:7}" >> $GITHUB_OUTPUT
            echo "submodule_path=$SUBMODULE_PATH" >> $GITHUB_OUTPUT
            echo "submodule_repo=${{ matrix.submodule.repo }}" >> $GITHUB_OUTPUT
            
            # Get changelog between commits
            CHANGELOG=$(cd "$SUBMODULE_PATH" && git log --oneline "$CURRENT_SHA..$NEW_SHA" | head -n 20)
            echo "changelog<<EOF" >> $GITHUB_OUTPUT
            echo "$CHANGELOG" >> $GITHUB_OUTPUT
            echo "EOF" >> $GITHUB_OUTPUT
            
            echo "📦 Update available: $CURRENT_TAG → $NEW_TAG"
          fi

      - name: Install uv
        if: steps.update.outputs.has_changes == 'true'
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Set up Python
        if: steps.update.outputs.has_changes == 'true'
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Run integration tests
        if: steps.update.outputs.has_changes == 'true'
        id: tests
        continue-on-error: true
        run: |
          echo "🧪 Running integration tests with updated submodule..."
          
          # Install parent project dependencies
          uv pip install --system -e .[dev]
          
          # Run tests
          if pytest tests/ --maxfail=3 -v --tb=short; then
            echo "status=passing" >> $GITHUB_OUTPUT
            echo "✅ Tests passed"
          else
            echo "status=failing" >> $GITHUB_OUTPUT
            echo "⚠️  Tests failed"
          fi

      - name: Create Pull Request
        if: steps.update.outputs.has_changes == 'true'
        id: create_pr
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: |
            chore(deps): update ${{ steps.update.outputs.submodule_repo }} submodule ${{ steps.update.outputs.current_version }} → ${{ steps.update.outputs.new_version }}
            
            Submodule: ${{ steps.update.outputs.submodule_path }}
            Commit: ${{ steps.update.outputs.current_sha }} → ${{ steps.update.outputs.new_sha }}
          branch: auto/update-${{ steps.update.outputs.submodule_repo }}-${{ steps.update.outputs.new_sha }}
          delete-branch: true
          title: "⬆️ Update ${{ steps.update.outputs.submodule_repo }} to ${{ steps.update.outputs.new_version }}"
          body: |
            ## 📦 Submodule Update
            
            **Submodule:** `${{ steps.update.outputs.submodule_path }}`  
            **Repository:** `${{ steps.update.outputs.submodule_repo }}`  
            
            | | Current | New |
            |---|---|---|
            | **Version** | `${{ steps.update.outputs.current_version }}` | `${{ steps.update.outputs.new_version }}` |
            | **Commit** | `${{ steps.update.outputs.current_sha }}` | `${{ steps.update.outputs.new_sha }}` |
            | **Tests** | - | ${{ steps.tests.outputs.status == 'passing' && '✅ Passing' || '⚠️ Failing' }} |
            
            ### 📝 Changes
            
            <details>
            <summary>Changelog (${{ steps.update.outputs.current_sha }}..${{ steps.update.outputs.new_sha }})</summary>
            
            ```
            ${{ steps.update.outputs.changelog }}
            ```
            
            </details>
            
            ### 🔗 Links
            
            - [Compare commits](https://github.com/${{ github.event.client_payload.triggeredBy || 'pv-udpv/xsp-lib' }}/compare/${{ steps.update.outputs.current_sha }}...${{ steps.update.outputs.new_sha }})
            ${{ github.event.client_payload.releaseUrl && format('- [Release notes]({0})', github.event.client_payload.releaseUrl) || '' }}
            
            ### ✅ Checklist
            
            - [ ] Review submodule changes
            - [ ] Verify integration tests (${{ steps.tests.outputs.status }})
            - [ ] Check for breaking changes
            - [ ] Update parent code if needed
            - [ ] Test critical user paths
            
            ---
            
            <sub>🤖 Auto-generated ([run](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}))</sub>
          labels: |
            dependencies
            submodule
            ${{ steps.update.outputs.submodule_repo }}
            ${{ steps.tests.outputs.status == 'passing' && 'tests-passing' || 'tests-failing' }}
          assignees: ${{ github.repository_owner }}

      - name: Handle test failures
        if: steps.update.outputs.has_changes == 'true' && steps.tests.outputs.status == 'failing'
        uses: actions/github-script@v7
        with:
          script: |
            const prNumber = '${{ steps.create_pr.outputs.pull-request-number }}';
            if (prNumber) {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: prNumber,
                body: `⚠️ **Integration tests failed**\n\n` +
                  `This submodule update caused test failures. ` +
                  `Please review the changes and fix integration issues before merging.\n\n` +
                  `**Actions:**\n` +
                  `1. Check [test logs](https://github.com/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId})\n` +
                  `2. Review [changes](https://github.com/${{ github.event.client_payload.triggeredBy || 'pv-udpv/xsp-lib' }}/compare/${{ steps.update.outputs.current_sha }}...${{ steps.update.outputs.new_sha }})\n` +
                  `3. Update parent code to match new API\n` +
                  `4. Re-run tests locally`
              });
            }

  summary:
    needs: [detect-submodules, update-submodules]
    if: always()
    runs-on: ubuntu-latest
    
    steps:
      - name: Generate summary
        run: |
          echo "### 📦 Submodule Update Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          
          if [ "${{ needs.detect-submodules.outputs.has_submodules }}" == "false" ]; then
            echo "⚠️ No .gitmodules found in this repository" >> $GITHUB_STEP_SUMMARY
          else
            echo "**Detected submodules:**" >> $GITHUB_STEP_SUMMARY
            echo '${{ needs.detect-submodules.outputs.submodules }}' | jq -r '.[] | "- `\(.path)` (\(.repo))"' >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "**Update status:** Check individual job logs above" >> $GITHUB_STEP_SUMMARY
          fi
```

## 🎯 Фишки auto-detection

### 1. **Парсит .gitmodules автоматически**
```bash
git config -f .gitmodules --get-regexp '^submodule\..+\.(path|url)$'
# Выход:
# submodule.xsp-lib.path xsp-lib
# submodule.xsp-lib.url https://github.com/pv-udpv/xsp-lib.git
```

### 2. **Matrix strategy для параллельных обновлений**
```yaml
strategy:
  matrix:
    submodule: ${{ fromJSON(needs.detect-submodules.outputs.submodules) }}
  max-parallel: 3  # До 3 submodules одновременно
```

### 3. **Умная фильтрация**
```yaml
# Обновить только xsp-lib при релизе
if [[ "$SUBMODULE_URL" =~ "pv-udpv/xsp-lib" ]]; then
  update_it
fi
```

## 🚀 Setup для zbst-tech

```bash
# 1. Скопировать workflow
cd /path/to/zbst-tech
curl -o .github/workflows/update-submodules.yml \
  https://raw.githubusercontent.com/pv-udpv/xsp-lib/main/.github/SUBMODULE_PARENT_TEMPLATE.md

# 2. ВСЁ! Никаких правок не нужно - auto-detect сам найдёт все submodules

# 3. Test
gh workflow run update-submodules.yml --repo pv-udpv/zbst-tech

# 4. Проверить что нашло
gh run list --workflow=update-submodules.yml --repo pv-udpv/zbst-tech
```

## 📋 Примеры использования

### Обновить все submodules
```bash
gh workflow run update-submodules.yml
```

### Обновить только xsp-lib
```bash
gh workflow run update-submodules.yml -f target_repo=pv-udpv/xsp-lib
```

### Обновить до конкретной версии
```bash
gh workflow run update-submodules.yml \
  -f target_repo=pv-udpv/xsp-lib \
  -f version=v1.2.0
```

## 🔧 Несколько submodules

Если в zbst-tech есть:
```
.gitmodules:
  [submodule "xsp-lib"]
    path = libs/xsp-lib
    url = https://github.com/pv-udpv/xsp-lib.git
  [submodule "utils-lib"]
    path = libs/utils
    url = https://github.com/pv-udpv/utils-lib.git
```

Workflow **автоматически**:
1. Найдёт оба submodule
2. Запустит параллельно (max-parallel: 3)
3. Создаст отдельные PR для каждого
4. При релизе xsp-lib обновит только его (фильтрация по URL)

---

**Статус:** Production ready ✅  
**Zero configuration** - просто скопируй workflow  
**Last updated:** 2025-12-14
