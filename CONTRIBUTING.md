# Contributing to Desk2HA Integration

Thanks for your interest in contributing!

## Setup

```bash
git clone https://github.com/maximusIIxII/hass-desk2ha.git
cd hass-desk2ha
pip install pytest pytest-asyncio aiohttp ruff pre-commit
pre-commit install
```

## Before submitting a PR

Run these checks locally:

```bash
ruff check custom_components/desk2ha/ tests/
ruff format custom_components/desk2ha/ tests/
pytest tests/ -x --tb=short
```

## Commit guidelines

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `ci:`, `test:`, `chore:`
- Update `CHANGELOG.md` under `[Unreleased]` with emoji categories
- For user-facing changes, update `README.md`

## Adding a new entity platform

1. Create `custom_components/desk2ha/{platform}.py`
2. Implement `async_setup_entry()` following HA patterns
3. Add platform to `PLATFORMS` in `const.py`
4. Add UI strings in `strings.json` and `translations/`
5. Add tests if pure-Python logic is involved

## Reporting bugs

1. Check existing issues first
2. Include: integration version, HA version, agent version
3. Attach diagnostics: **Settings** → **Integrations** → **Desk2HA** → **Diagnostics**

## License

By contributing, you agree that your contributions are licensed under the Apache-2.0 License.
