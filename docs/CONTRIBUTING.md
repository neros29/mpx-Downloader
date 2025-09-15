# Contributing to yt-dlp Wrapper

Thank you for your interest in contributing to this project! We welcome contributions of all kinds.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** first to see if the bug has already been reported
2. **Use the issue template** when creating a new bug report
3. **Include as much detail as possible**:
   - Your operating system and Python version
   - The exact command you ran
   - The full error message
   - Steps to reproduce the issue

### Suggesting Features

1. **Check existing issues** to see if the feature has been requested
2. **Describe the feature** in detail, including:
   - Why it would be useful
   - How it should work
   - Any potential challenges or considerations

### Contributing Code

#### Setting Up Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/yt-dlp-wrapper.git
   cd yt-dlp-wrapper
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Linux/Mac
   ```

4. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

#### Making Changes

1. **Create a new branch** for your feature/fix:
   ```bash
   git checkout -b feature-name
   ```

2. **Make your changes** following the coding standards below

3. **Add tests** for any new functionality

4. **Run the test suite** to ensure everything works:
   ```bash
   python -m pytest
   ```

5. **Run code formatting** (if available):
   ```bash
   black download.py tests/
   flake8 download.py tests/
   ```

#### Coding Standards

- **Follow PEP 8** Python style guidelines
- **Use meaningful variable and function names**
- **Add docstrings** to all functions and classes
- **Handle errors gracefully** with try/except blocks
- **Use type hints** where appropriate
- **Keep functions focused** and relatively small
- **Add comments** for complex logic

#### Testing

- **Write tests** for new functionality
- **Ensure all tests pass** before submitting
- **Test on Windows** if possible (primary target platform)
- **Test with various input types** (URLs, playlists, etc.)

#### Commit Messages

Use clear, descriptive commit messages:

```
Add support for batch URL processing

- Implement --file flag for loading URLs from text files
- Add error handling for invalid file paths
- Update documentation with usage examples
```

#### Pull Request Process

1. **Update documentation** if needed
2. **Ensure all tests pass**
3. **Create a pull request** with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues

## Development Guidelines

### Project Structure

```
yt-dlp-wrapper/
├── download.py           # Main application code
├── tests/                # Test files
│   ├── test_archive.py   # Archive-related tests
│   ├── test_download.py  # Download-related tests
│   └── test_utils.py     # Utility function tests
├── examples/             # Example files
└── docs/                 # Documentation
```

### Key Areas for Contribution

1. **Error Handling**: Improving robustness and user feedback
2. **Platform Support**: Adding Linux/Mac support
3. **Testing**: Expanding test coverage
4. **Documentation**: Improving user guides and API docs
5. **Performance**: Optimizing download speeds and memory usage
6. **Features**: Adding new functionality (see issues for ideas)

### Testing Guidelines

- **Unit tests** should be isolated and fast
- **Mock external dependencies** (yt-dlp, file system operations)
- **Test edge cases** and error conditions
- **Use meaningful test names** that describe what is being tested

Example test structure:
```python
class TestFeatureName:
    def setup_method(self):
        """Setup for each test."""
        pass
    
    def test_specific_functionality(self):
        """Test description of what this verifies."""
        # Arrange
        # Act
        # Assert
        pass
```

### Documentation Standards

- **Keep README.md updated** with new features
- **Document all command-line options**
- **Include examples** for complex features
- **Update CHANGELOG.md** for each release

## Getting Help

- **Create an issue** for questions about development
- **Check existing documentation** first
- **Look at similar projects** for inspiration

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in the project's README.md file and release notes.

Thank you for helping to improve this project!
