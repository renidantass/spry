# Contributing to Spry

Thank you for considering contributing to Spry! We welcome contributions of all kinds: bug reports, feature requests, documentation improvements, and code changes.

## Development setup

```bash
git clone https://github.com/renidantass/spry.git
cd spry
pip install -e .
pip install -e ".[all]"
python -m unittest discover -s tests
```

## Code style

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

## Branch naming

| Branch | Base | Merge to | Description |
|--------|------|----------|-------------|
| `feat/*` | `main` | `main` via PR | New feature |
| `fix/*` | `main` | `main` via PR | Bug fix |
| `docs/*` | `main` | `main` via PR | Documentation |
| `chore/*` | `main` | `main` via PR | Maintenance (CI, deps) |

## Pull request process

1. Create a feature branch from `main` following the naming convention above
2. Write tests for your changes
3. Ensure all existing tests pass
4. Update documentation if needed
5. Add a changelog entry in `CHANGELOG.md`
6. Submit a pull request to `main`

## Release flow

1. Create a `release/vX.Y.Z` branch from `main`
2. Update version and changelog
3. Merge to `main` and tag as `vX.Y.Z`
4. Create a GitHub Release from the tag

## Reporting issues

- Use the GitHub issue tracker
- Include Python version, OS, and framework version
- Provide a minimal reproduction example

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
