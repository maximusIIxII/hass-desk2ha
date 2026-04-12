# Contributing to Desk2HA

Thanks for helping improve Desk2HA! Here's how you can contribute.

## Reporting Bugs

1. **Check existing issues** — your problem may already be reported
2. **Use the bug report template** — [New Bug Report](https://github.com/maximusIIxII/hass-desk2ha/issues/new?template=bug_report.yml)
3. **Include versions** — Integration version, Agent version, HA version, OS
4. **Include logs** — Agent console output, HA logs (Settings > System > Logs)
5. **Include diagnostics** — Settings > Devices > Desk2HA > your device > Download Diagnostics

## Requesting Features

Use the [Feature Request template](https://github.com/maximusIIxII/hass-desk2ha/issues/new?template=feature_request.yml). Describe the problem you're solving, not just the solution you want.

## Asking Questions

Use [GitHub Discussions](https://github.com/maximusIIxII/hass-desk2ha/discussions) for:
- Setup help and troubleshooting
- Sharing your dashboard/automation setups
- General feedback and ideas

## Testing a Pre-Release

1. Install the latest main branch via HACS (or manual copy)
2. Update the agent: `pip install --upgrade desk2ha-agent`
3. Test your specific hardware setup
4. Report any issues with the bug template

### What to test

- [ ] Agent starts and connects to HA
- [ ] All your peripherals appear as devices
- [ ] Display controls work (brightness, input source, etc.)
- [ ] Webcam controls work (if applicable)
- [ ] BT peripherals show battery levels
- [ ] Lovelace card renders correctly
- [ ] Card popup shows correct controls per device
- [ ] Health check service runs without errors

## Submitting Code

1. Fork the repo
2. Create a feature branch (`feat/my-feature`)
3. Run `ruff check` and `ruff format` before committing
4. Write tests for new functionality
5. Submit a PR with a clear description

## Code Style

- Python: `ruff` for linting and formatting (config in `pyproject.toml`)
- JavaScript: Standard ES6, no build step
- Commit messages: `feat:`, `fix:`, `docs:`, `style:`, `test:`, `chore:`
