# Contributing to Spry

Thank you for considering contributing to Spry! We welcome contributions of all kinds: bug reports, feature requests, documentation improvements, and code changes.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/anomalyco/spry.git
cd spry

# Install in editable mode
pip install -e .

# Install optional dependencies for development
pip install -e ".[all]"

# Run tests
python -m unittest discover -s tests
```

## Code Style

- Python 3.11+ with type hints for all public APIs
- Follow existing patterns (see `src/spry/` for examples)
- Use `from __future__ import annotations` at the top of every file
- Prefer dataclasses with `slots=True` for data containers
- Zero external runtime dependencies (optional extras only)
- Keep functions short and focused

## Testing

- All tests use `unittest.TestCase`
- New features must include tests
- Run the full test suite before submitting:
  ```bash
  python -m unittest discover -s tests
  ```

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for your changes
3. Ensure all existing tests pass
4. Update documentation if needed
5. Add a changelog entry in `CHANGELOG.md`
6. Submit a pull request

## Reporting Issues

- Use the GitHub issue tracker
- Include Python version, OS, and framework version
- Provide a minimal reproduction example

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
