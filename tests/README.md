# Viu Testing Framework

This directory contains a comprehensive testing framework for the viu project, covering all layers of the application architecture.

## Test Organization

The tests are organized following the project's layered architecture:

```
tests/
├── __init__.py
├── conftest.py              # Base test utilities and fixtures
├── run_tests.py            # Test runner script
├── core/                   # Core layer tests
│   ├── test_config.py     # Configuration loading and validation
│   └── ...
├── libs/                   # Libraries layer tests
│   ├── test_providers.py  # Anime provider tests
│   ├── test_media_api.py  # Media API client tests
│   ├── test_players.py    # Media player tests
│   ├── test_selectors.py  # User selector tests
│   └── ...
├── cli/                    # CLI layer tests
│   ├── test_commands.py   # Command-line interface tests
│   ├── test_session.py    # Interactive session tests
│   └── ...
├── integration/            # Integration tests
│   ├── test_workflows.py  # End-to-end workflow tests
│   └── ...
└── utils/                  # Test utilities
```

## Test Framework

The testing framework uses Python's built-in `unittest` module with the following features:

- **BaseTestCase**: Common base class with utilities for all tests
- **Mock factories**: Pre-configured mocks for all major components
- **Configuration utilities**: Helper methods for creating test configurations
- **HTTP mocking**: Support for mocking external API calls

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test Module
```bash
python -m unittest tests.core.test_config -v
```

### Run Specific Test Class
```bash
python -m unittest tests.libs.test_providers.TestBaseAnimeProvider -v
```

### Run Tests by Layer
```bash
# Core layer tests
python -m unittest discover tests/core -v

# Libraries layer tests  
python -m unittest discover tests/libs -v

# CLI layer tests
python -m unittest discover tests/cli -v
```

## Test Categories

### Core Layer Tests (tests/core/)
- **Configuration**: Loading, validation, and serialization of config files
- **Exceptions**: Custom exception handling
- **Utilities**: Core utility functions

### Libraries Layer Tests (tests/libs/)
- **Providers**: Abstract base class contracts and concrete implementations
- **Media API**: API client interfaces and implementations
- **Players**: Media player wrappers and integrations
- **Selectors**: User input/selection interfaces

### CLI Layer Tests (tests/cli/)
- **Commands**: CLI command parsing and execution
- **Session**: Interactive menu system and state management
- **Configuration**: CLI-specific configuration handling

### Integration Tests (tests/integration/)
- **Workflows**: End-to-end user workflows
- **Component Integration**: Multi-component interactions
- **Error Handling**: Cross-component error scenarios

## Test Utilities

### BaseTestCase
All test classes inherit from `BaseTestCase` which provides:

```python
class YourTestClass(BaseTestCase):
    def setUp(self):
        super().setUp()  # Sets up temp directories and mock HTTP client
        
    def test_something(self):
        # Create mock config
        config = self.create_mock_config(
            **{"stream.quality": "720"}
        )
        
        # Create mock HTTP response
        response = self.create_mock_http_response(
            status_code=200,
            json_data={"result": "success"}
        )
```

### Mock Components
Pre-configured mocks for major components:

- `MockProvider`: Mock anime provider
- `MockMediaApi`: Mock media API client  
- `MockPlayer`: Mock media player
- `MockSelector`: Mock user selector

## Testing Best Practices

### 1. Test Structure
- Use descriptive test method names
- Group related tests in test classes
- Use setUp/tearDown for common initialization

### 2. Mocking
- Mock external dependencies (HTTP, file system, executables)
- Use dependency injection for better testability
- Test both success and failure scenarios

### 3. Assertions
- Use specific assertion methods (`assertEqual`, `assertIsInstance`, etc.)
- Test both positive and negative cases
- Verify mock call counts and arguments

### 4. Error Handling
- Test exception scenarios
- Verify error messages and types
- Test graceful degradation

## Example Test

```python
class TestAnimeProvider(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.provider = MockProvider()
    
    def test_search_returns_results(self):
        """Test that provider search returns expected results."""
        # Arrange
        mock_results = SearchResults(results=[
            SearchResult(id="123", title="Test Anime", url="http://example.com")
        ])
        self.provider.search.return_value = mock_results
        
        # Act
        search_params = SearchParams(query="test anime")
        results = self.provider.search(search_params)
        
        # Assert
        self.assertIsNotNone(results)
        self.assertEqual(len(results.results), 1)
        self.assertEqual(results.results[0].title, "Test Anime")
        
        # Verify mock was called correctly
        self.provider.search.assert_called_once_with(search_params)
```

## Test Coverage

The testing framework covers:

- ✅ Configuration loading and validation
- ✅ Provider abstract interfaces and implementations
- ✅ Media API client interfaces and implementations  
- ✅ Player interfaces and integrations
- ✅ Selector interfaces and implementations
- ✅ CLI command parsing and execution
- ✅ Interactive session and menu system
- ✅ End-to-end workflows
- ✅ Error handling scenarios

## Continuous Integration

The tests are designed to run in CI/CD environments:

- No external dependencies required for core tests
- Mock all network calls and external tools
- Skip tests that require unavailable tools (fzf, rofi)
- Provide clear error messages for failures

## Contributing

When adding new features:

1. Write tests for new functionality
2. Follow existing test patterns and naming conventions
3. Add both positive and negative test cases
4. Update this README if adding new test categories
5. Ensure tests pass in isolation and as part of the full suite