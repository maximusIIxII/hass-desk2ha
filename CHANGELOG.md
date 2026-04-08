# Changelog

All notable changes to the Desk2HA HA Integration will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/) with emoji categories.

## [Unreleased]

## [0.4.4] - 2026-04-09

### 🐛 Bug fixes
- **number.py sub_device_id**: Used `display.0` (dot) instead of `display_0` (underscore), causing display number entities (brightness, contrast, volume) to create a separate HA device

## [0.4.3] - 2026-04-09

### 🔧 Improvements
- Debug logging added to device cleanup for troubleshooting dedup issues

## [0.4.2] - 2026-04-09

### 🐛 Bug fixes
- Device dedup now normalizes names by stripping manufacturer prefix before comparing (fixes U5226KW duplicate with/without "Dell" prefix)

## [0.4.1] - 2026-04-09

### 🐛 Bug fixes
- Extended generic USB filter: German device names (USB-Eingabegeraet, USB-Verbundgeraet)
- Manufacturer prefix stripped from sub-device names (fixes "Dell Dell KM7321W Keyboard")
- Orphaned device cleanup: removes bare manufacturer-only devices (e.g. "Logitech")
- Duplicate device detection: removes devices with same model but fewer entities

## [0.4.0] - 2026-04-09

### ✨ New features
- **Remote Agent Installation**: SSH (Linux/macOS) + WinRM (Windows) via Config Flow — auto-generates token, deploys config, starts agent
- **Fleet Management Services**: `desk2ha.fleet_status` (aggregated desk status), `desk2ha.refresh` (force-refresh), `desk2ha.restart_agent` (remote restart)
- **services.yaml**: Service descriptions for HA Developer Tools UI

### 🔧 Improvements
- `agent_url` and `agent_token` properties on coordinator for service access
- Services registered on first entry setup, removed on last entry unload
- CI test job with `aiohttp` dependency
- HACS release workflow generates zip asset automatically

## [0.3.0] - 2026-04-09

### ✨ New features
- **HA Mock Test Harness**: conftest.py with stub classes for CoordinatorEntity, DataUpdateCoordinator, DeviceInfo — enables testing without HA installed
- **22 unit tests**: helpers (11) + sensor utils (11)

### 🔧 Improvements
- CI: test job added (pytest without HA dependency), lint covers `tests/`

## [0.2.1] - 2026-04-08

### ✨ New features
- **Sub-Device Architecture**: Displays and peripherals as separate HA devices (via_device)
- **Logitech Litra Light Entity**: Brightness + color temperature + power control
- **Media Player Entity**: Display speaker volume control
- **Switch Entities**: Auto brightness, auto color temperature
- **Light Entity**: Display brightness as dimmable light
- **Entity Categories**: 12 diagnostic sensors
- **Sensor Suffix-Enrichment**: Peripherals, webcams, headsets, Litra, network
- **System Action Buttons**: Lock screen, sleep, shutdown
- **Thermal Profile Select**: Dell/HP/Lenovo

### 🐛 Bug fixes
- Sub-device names and generic USB filter

## [0.2.0] - 2026-04-08

### ✨ New features
- **9 Entity Platforms**: sensor, binary_sensor, number, select, switch, light, media_player, button, update
- **Light Entity**: Display as dimmable light
- **Media Player Entity**: Display speaker volume
- **Switch Entities**: Auto brightness, auto color temperature
- **Entity Categories**: 12 diagnostic sensors
- **Thermal Profile Select**
- **HACS Validation Action**

## [0.1.1] - 2026-04-08

### ✨ New features
- **Zeroconf Config Flow**: Auto-discovery of agents via mDNS
- **HACS**: Custom repository configuration, hacs.json

### 🐛 Bug fixes
- CI simplified (mypy removed), hassfest passing

## [0.1.0] - 2026-04-08

### ✨ New features
- **Initial release**
- 3-path Config Flow: Manual URL + Zeroconf + Method Selection
- Options Flow: Poll interval configuration
- DataUpdateCoordinator: Polling /v1/info + /v1/metrics
- 5 Entity Platforms: sensor, binary_sensor, number, select, button
- Base Entity with device info + nested metric resolution
- Dynamic Entity Creation: Only entities for reported metrics
- Diagnostics Support
- Integration Logo (brand/ directory)
