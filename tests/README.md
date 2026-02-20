# Running Tests

This project uses pytest for unit testing. The tests are located in the `tests/` directory.

## Prerequisites

Make sure you have the test dependencies installed:

```bash
pip install -r requirements_test.txt
```

## Running Tests

Run all tests:
```bash
pytest tests/ -v
```

Run a specific test file:
```bash
pytest tests/test_config_flow.py -v
```

Run a specific test class:
```bash
pytest tests/test_config_flow.py::TestConfigFlow -v
```

Run a specific test:
```bash
pytest tests/test_config_flow.py::TestConfigFlow::test_user_step_shows_vendor_selection -v
```

## Test Coverage

Run tests with coverage:
```bash
pytest tests/ --cov=custom_components.ppc_smgw --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_config_flow.py      # Config flow tests
└── test_init.py             # Integration setup and coordinator tests
```

## What's Tested

### Config Flow (`test_config_flow.py`)
- Vendor selection (PPC, Theben, EMH)
- Connection information validation
- Duplicate host/username detection
- Connection error handling
- Options flow updates

### Integration Setup (`test_init.py`)
- Gateway creation for each vendor
- Debug mode configuration
- Coordinator data updates
- Error handling in coordinator
- Entry unloading

## Writing New Tests

When adding new tests:
1. Add fixtures to `conftest.py` if they're reusable
2. Use `@pytest.mark.asyncio` for async tests
3. Mock external dependencies (HTTP clients, Home Assistant core)
4. Follow the AAA pattern (Arrange, Act, Assert)

Example:
```python
@pytest.mark.asyncio
async def test_something(hass: HomeAssistant, mock_gateway):
    # Arrange
    expected_value = "test"

    # Act
    result = await some_function(hass, mock_gateway)

    # Assert
    assert result == expected_value
```
