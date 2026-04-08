# hass-desk2ha — Development Guide

You are working on the **Desk2HA Integration**, a custom HA component that
manages endpoint devices and their peripherals across all vendors.

## Quick Reference

- HA domain: `desk2ha`
- Package path: `custom_components/desk2ha/`
- Config: Config Flow (no YAML)
- HACS compatible

## Autonomie-Regeln

Du darfst OHNE Rueckfrage:
- Code, Tests, Doku auf Feature-Branches schreiben, committen und pushen
- Draft-PRs erstellen
- Lint/Format/Type-Fehler fixen
- Dependencies in pyproject.toml hinzufuegen (mit Begruendung im Commit)

Du MUSST den User fragen fuer:
- PR auf main mergen (ausser docs/*)
- Release taggen
- Deploy auf Live-HA
- OpenAPI Spec oder ARCHITECTURE.md aendern
- CLAUDE.md aendern

## Kritische HA-Konventionen

1. Kein blocking I/O im Event Loop — use `hass.async_add_executor_job()`
2. Jede Entity hat eine `unique_id`
3. `DataUpdateCoordinator` fuer Polling
4. Config Flow, kein YAML
5. Strings in `strings.json` + `translations/`
6. Device Registry korrekt befuellt (identifiers, manufacturer, model)

## Vor jedem Commit

```bash
ruff check . && ruff format --check . && mypy custom_components/desk2ha/ && pytest tests/ -x
```

## Projektstruktur

- `custom_components/desk2ha/` — Integration root
- `custom_components/desk2ha/sources/` — HTTP pull, MQTT push, network discovery
- `custom_components/desk2ha/lifecycle/` — Agent install/update/config
- `custom_components/desk2ha/images/` — Product image resolution + cache
- `tests/` — pytest-homeassistant-custom-component tests

## Commit Convention

Format: `{type}: {description}`
Types: feat, fix, refactor, test, docs, ci, chore
All commits end with: `Co-Authored-By: Claude <noreply@anthropic.com>`
