# Setting Up Pre-commit Hooks

Pre-commit hooks автоматически проверяют и форматируют код перед каждым коммитом.

## Установка

```bash
# 1. Установить pre-commit
pip install pre-commit

# 2. Установить хуки в репозиторий
pre-commit install

# 3. (Опционально) Запустить на всех файлах
pre-commit run --all-files
```

## Что делают хуки

### 1. **Ruff** - Линтер и форматер
- Автоматически исправляет проблемы кода
- Форматирует код (замена black, isort)
- Проверяет стиль кода (PEP 8)

### 2. **MyPy** - Проверка типов
- Строгая проверка типов (`--strict`)
- Проверяет только `src/` (не тесты)
- Требует type hints для всех функций

### 3. **Pytest** - Запуск тестов
- Запускает все тесты перед коммитом
- Останавливается на первой ошибке (`--maxfail=1`)
- Можно пропустить: `git commit --no-verify`

### 4. **Standard hooks**
- Удаление trailing whitespace
- Фикс окончания файлов (LF)
- Проверка YAML/TOML/JSON
- Проверка больших файлов (>1MB)
- Проверка merge conflicts

### 5. **Bandit** - Проверка безопасности
- Поиск уязвимостей в коде
- Проверка небезопасных функций

## Workflow разработчика

### Обычный коммит
```bash
git add .
git commit -m "feat: add new feature"
# Pre-commit автоматически:
# 1. Форматирует код (ruff format)
# 2. Исправляет линтинг (ruff check --fix)
# 3. Проверяет типы (mypy)
# 4. Запускает тесты (pytest)
# 5. Проверяет безопасность (bandit)
```

### Если хуки изменили файлы
```bash
git add .
git commit -m "feat: add new feature"
# Если ruff изменил файлы:
# > Fixing files...
# > Fixed 3 files
# > [ERROR] Files were modified by this hook
git add .  # Добавить исправленные файлы
git commit -m "feat: add new feature"  # Коммит пройдет
```

### Пропустить проверки (НЕ рекомендуется)
```bash
git commit -m "WIP: work in progress" --no-verify
```

### Запустить проверки вручную
```bash
# Все хуки на измененных файлах
pre-commit run

# Все хуки на всех файлах
pre-commit run --all-files

# Конкретный хук
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

## Обновление хуков

```bash
# Обновить до последних версий
pre-commit autoupdate

# Переустановить хуки
pre-commit install --install-hooks
```

## Конфигурация

См. [.pre-commit-config.yaml](../.pre-commit-config.yaml) для настройки:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
```

## Troubleshooting

### Pre-commit слишком медленный
```bash
# Отключить pytest в pre-commit
git config hooks.pytest false

# Или пропустить тесты для быстрых коммитов
SKIP=pytest-check git commit -m "fix: quick fix"
```

### MyPy ошибки в тестах
MyPy по умолчанию проверяет только `src/`, не `tests/`.

### Конфликт с IDE
Настройте IDE на использование тех же инструментов:
- **VSCode**: Установите расширения Ruff и MyPy
- **PyCharm**: Настройте External Tools для ruff и mypy

## CI/CD Integration

Pre-commit также запускается в GitHub Actions:
- Файл: `.github/workflows/pre-commit.yml`
- Запускается на каждом PR
- Блокирует merge при ошибках

## Best Practices

1. **Commit often**: Маленькие коммиты быстрее проходят проверки
2. **Fix issues locally**: Не полагайтесь на CI для поиска проблем
3. **Run tests before push**: `pre-commit run --all-files`
4. **Update regularly**: `pre-commit autoupdate` раз в месяц
5. **Don't skip checks**: `--no-verify` только для WIP коммитов

## Что изменилось

**До (плохо):**
- CI коммитил auto-fixes обратно в ветку
- Разработчик видел изменения только после push
- Множество мелких коммитов от бота

**После (хорошо):**
- Все проверки и исправления локально
- Код форматируется перед коммитом
- CI только проверяет, не изменяет
- Чистая история коммитов

## См. также

- [Pre-commit documentation](https://pre-commit.com/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [MyPy documentation](https://mypy.readthedocs.io/)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
