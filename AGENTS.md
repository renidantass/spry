# Spry — Agent Instructions

## Project Overview

Spry is an opinionated Python web framework inspired by ASP.NET Core, with an EF Core-inspired ORM, WSGI/ASGI support, and a CLI for scaffolding, migrations, and seeding.

- **PyPI package:** `spry-core`
- **Python:** 3.11+
- **Dependencies:** Zero runtime deps (optional extras: postgres, mysql, sqlserver, jinja2)

## Commit Convention

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Bump | Example |
|--------|------|---------|
| `feat:` | minor | `feat: add pagination support to DbSet` |
| `fix:` | patch | `fix: handle null values in auth middleware` |
| `BREAKING CHANGE:` / `feat!:` | major | `feat!: rename save_changes to save` |
| `docs:`, `chore:`, `refactor:`, `test:`, `style:`, `perf:` | none | `docs: update quickstart example` |

The version is **automatically calculated** from these commits — do not edit `pyproject.toml` version manually.

## Branch Strategy

| Branch | Base | Merges to | Description |
|--------|------|-----------|-------------|
| `feat/*` | `main` | `main` via PR | New feature |
| `fix/*` | `main` | `main` via PR | Bug fix |
| `docs/*` | `main` | `main` via PR | Documentation |
| `chore/*` | `main` | `main` via PR | Maintenance (CI, deps) |
| `release/v*` | `main` | `main` via PR | Release preparation |

## CI/CD Workflow

### 1. PR opened → `test.yml`
- **Trigger:** `pull_request` to `main`
- **Runs:** Full test matrix — Python 3.11, 3.12, 3.13 × Linux, Windows, macOS
- **Purpose:** Validate code before merge

### 2. PR merged → `publish.yml` (automatic)
- **Trigger:** `push` to `main`
- **Jobs:**
  1. `test` — full matrix test suite
  2. `publish` (depends on test) — creates the release:
     - Analyzes Conventional Commits since last tag
     - Determines bump (major/minor/patch)
     - Updates `pyproject.toml` version
     - Commits with `[skip ci]` and creates tag `vX.Y.Z`
     - Creates GitHub Release with auto-generated release notes
     - Publishes to PyPI (`pip install spry-core`)

**No manual version editing or tagging needed.**

## Pre-commit

The repository uses `commitizen` to validate commit messages:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.29.0
    hooks:
      - id: commitizen
        stages: [commit-msg]
```

Setup:
```bash
pip install pre-commit
pre-commit install --hook-type commit-msg
```

## Code Conventions

- Python 3.11+ with type hints
- `from __future__ import annotations` at the top of every file
- Prefer dataclasses with `slots=True`
- Tests use `unittest.TestCase`
- Zero external runtime dependencies (optional extras only)
- DI via `AppBuilder`
- Controllers: `@controller("/prefix")` with `@get`, `@post`, `@put`, `@patch`, `@delete`
- ORM: `DbContext` + `DbSet` with `dbset(Todo)` and `key()` for primary key
- Architecture: `AppBuilder` → register middlewares, DbContexts, CORS → `build()` → `run()`

## Testing

```bash
python -m unittest discover -s tests -v
```

Every PR should include tests. CI runs the full suite across 3 Python versions × 3 OS.

## Repository Structure

- `src/spry/` — framework core
- `src/spry/templates/` — scaffold templates (`api/`, `mvc/`)
- `examples/` — example projects
- `docs/` — documentation site
- `tests/` — test suite
- `.github/workflows/` — CI/CD
