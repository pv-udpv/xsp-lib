# Tests

This directory contains the test suite for xsp-lib.

## Test Structure

- `unit/` - Unit tests that don't require external dependencies
- `integration/` - Integration tests that may require external services
- `fixtures/` - Test fixtures and sample data
- `conftest.py` - Shared pytest configuration and fixtures

## Running Tests

### Run all tests (excluding network tests)
```bash
pytest
```

### Run only unit tests
```bash
pytest tests/unit/
```

### Run integration tests (non-network)
```bash
pytest tests/integration/test_workflow.py
```

### Run network tests (requires internet)
```bash
pytest -m network
```

### Run all tests including network tests
```bash
pytest -m ""
```

## Test Markers

- `network` - Tests that require network access to external services (e.g., httpbin.org)

Network tests are **skipped by default** because they:
- Require internet connectivity
- Depend on external services being available
- May fail in CI/CD environments with restricted network access

To run network tests in CI, use:
```bash
pytest -m network
```

## Coverage

To generate a coverage report:
```bash
pytest --cov=xsp --cov-report=html
```

Then open `htmlcov/index.html` in your browser.
