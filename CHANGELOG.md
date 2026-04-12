# Changelog

All notable changes to the Desk2HA HA Integration will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/) with emoji categories.

## [1.0.2] - 2026-04-12

### 🔧 Improvements
- **Pre-commit hook**: ruff lint + format + pytest before every commit
- **bind = 0.0.0.0**: Added to Getting Started minimal config (fixes new install connectivity)
- **Git history scrubbed**: All leaked credentials removed from repo history

### 📖 Documentation
- Migrated Peripheral Controls Concept from old repo (DDPM roadmap)
- Migrated Grobkonzept + Vendor Analysis (Lenovo/HP/Logitech integration reference)

## [1.0.1] - 2026-04-12

### 🐛 Bug fixes
- **Card popup-close**: Fixed backdrop click and X button not reliably closing popups
- **Card thermal/fan lookup**: Added fallback entity suffixes for correct matching
- **Update entity**: Fixed false "up to date" status when update check hasn't run yet
- **Charging/USB-PD**: Moved from sensor (showing "True"/"False") to binary_sensor with proper device classes

### 📖 Documentation
- **Getting Started**: Added Windows Firewall instructions, bind config, connectivity verification
- **MQTT Setup Guide**: New standalone guide with Mosquitto setup and troubleshooting

### 🔧 Improvements
- Brand icon registered as static path for update entity
- Old charging/USB-PD sensor entities auto-removed on upgrade
- Pre-commit hook: ruff lint + format + pytest before every commit

## [1.0.0] - 2026-04-12

### ✨ New features
- **Lovelace Card v1.1**: Auto-discovery (no entity config needed), device list with MDI icons, control popup with inline sliders/toggles/dropdowns/buttons, SVG product images in popup header
- **Device Health Check service** (`desk2ha.device_health_check`): 7 automated checks — stale devices, orphan entities, missing manufacturers, duplicate names. Auto-fix mode + persistent notification with results
- **Device Registry Auto-Sync**: Automatically updates device names and manufacturers when agent reports better metadata
- **Product Image serving**: `/desk2ha/images/{device_key}` endpoint with Tier 3 cache (vendor photos) + Tier 1/2 SVG proxy from agent
- **Per-device-type SVG icons**: Webcam, keyboard, mouse, headset, dock, speaker, light, monitor — each with distinct icon
- **BT manufacturer enrichment**: 37 name patterns (Dell, Jabra, Logitech, Bose, Sony, etc.) auto-detect manufacturer from device name
- **Webcam name resolution**: Camera names resolved from OS APIs (WMI, sysfs, system_profiler) instead of raw index IDs

### 🐛 Bug fixes
- **Disconnected BT devices hidden**: Paired-but-not-connected Bluetooth devices no longer appear as HA devices
- **USB error devices filtered**: "Unbekanntes USB-Geraet" / descriptor failures no longer create entities
- **Scanner/printer filter**: HP OfficeJet and other scanners no longer detected as webcams by UVC collector
- **Orphan entity cleanup**: Disabled entities are deleted (not accumulated) on startup. Stale entity patterns removed
- **Host device rename prevented**: Health check no longer strips manufacturer prefix from host device name

### 📚 Documentation
- **Getting Started Guide**: Complete zero-to-working walkthrough (Prerequisites, Agent install, Config, Autostart for Win/Linux/macOS, HA setup, Card, Updating, Troubleshooting)
- **Architecture diagram**: System overview, data flow, device hierarchy, API contract, security model
- **Improved error messages**: Config flow errors now include specific troubleshooting steps

### 🔒 Security
- Pre-release security scanner (`scripts/security-scan.py`) with git history scanning
- Git history scrubber (`scripts/scrub-history.ps1`) for removing leaked secrets
- Pre-push git hook blocks pushes with critical security issues
- All hardcoded credentials, service tags, and personal data removed

## [0.9.0] - 2026-04-12

### ✨ New features
- **Color Preset select**: sRGB, native, 4000K–11500K, user1–3 per display
- **Sharpness number**: 0–100% per display via DDC/CI
- **RGB Gain numbers**: Red, Green, Blue gain (0–100%) per display
- **Black Level numbers**: Red, Green, Blue black level (0–100%) per display
- **Audio Mute switch**: Per-display audio mute toggle
- **Usage Hours sensor**: Display operating hours (diagnostic)
- **Firmware Version sensor**: Display firmware level (diagnostic)
- **Factory Reset buttons**: Per-display factory reset + factory color reset (config category)
- **Sidetone number**: Headset sidetone level (0–128) via HeadsetControl
- **Chat Mix number**: Headset chat/game balance (0–128) via HeadsetControl
- **Headset LED switch**: Toggle headset LED via HeadsetControl
- **UVC webcam controls**: 13 number entities (brightness, contrast, saturation, sharpness, gain, gamma, zoom, focus, exposure, white balance, pan, tilt, backlight compensation) + 3 switch entities (autofocus, auto white balance, auto exposure)

### 🐛 Bug fixes
- **Webcam sensor duplicates**: Webcam control metrics no longer create duplicate sensor entities — excluded via `_WEBCAM_CONTROL_KEYS` (analogous to display controls)

## [0.8.7] - 2026-04-10

### ✨ New features
- **Restart button**: OS reboot via `system.restart` command
- **Hibernate button**: System hibernate via `system.hibernate` command
- **High CPU Temperature Alert blueprint**: Notification when CPU exceeds threshold (default 90°C, 2 min sustained)
- **Disk Space Low Alert blueprint**: Notification when disk usage exceeds threshold (default 90%)
- **High RAM Usage Alert blueprint**: Notification when RAM exceeds threshold (default 90%, 5 min sustained)

### 📖 Documentation
- **Blueprints section** added to README with all 7 automation blueprints
- Updated upcoming features (removed Energy Dashboard, added HACS PR status)

## [0.8.6] - 2026-04-09

### 🔧 Improvements
- **CI version consistency checks**: Release workflow now blocks if git tag ≠ manifest.json version or CHANGELOG entry missing; also reports latest agent version on PyPI
- **Entity availability tests**: 25 tests verify action entities stay available, metric resolution works for all key patterns, and `available` property is correct
- **Version consistency tests**: CI validates manifest.json is valid semver with matching dated CHANGELOG entry

## [0.8.5] - 2026-04-09

### 🐛 Bug fixes
- **Buttons/controls disabled**: `available` check incorrectly applied to command entities (buttons, update) that don't have metric data — added `_check_metric_available = False` for action-only entities

## [0.8.4] - 2026-04-09

### 🐛 Bug fixes
- **Device firmware version stuck**: `sw_version` in device info never updated after initial setup — coordinator now refreshes `agent_info` when agent reports a new version

## [0.8.3] - 2026-04-09

### 🔒 Security
- **SSH host key verification**: Changed from disabled (`known_hosts=None`) to trust-on-first-use — prevents MITM on remote agent install
- **WinRM TLS validation**: Documented risk (self-signed certs still accepted for Windows remote install)
- **Install page XSS prevention**: HTML-escape `base_url` and `token` in install page template
- **Pairing code hardening**: CSPRNG (`secrets.choice`) replaces `random.choices`; rate limiting (10 attempts/min per IP, HTTP 429)
- **Image cache path traversal**: `device_key` sanitized to `[a-zA-Z0-9_-]` before file path construction
- **Install script permissions**: `chmod 600 config.toml` (Linux), `icacls` restriction (Windows)

## [0.8.2] - 2026-04-09

### 🐛 Bug fixes
- **Metric resolution for dotted sub-keys**: `thermals.fan.gpu`, `system.network.wlan.*`, and similar 3+-part keys were never resolved — GPU Fan Speed, WiFi SSID/Signal, WLAN throughput always showed "Unbekannt"
- **Entity availability**: Entities now show "nicht verfügbar" instead of "Unbekannt" when the agent stops reporting a metric (e.g. WiFi metrics when on Ethernet)
- **Sensor/binary_sensor duplicates**: `lid_open` and `battery.state` no longer created as both sensor AND binary_sensor — orphan sensor entities auto-cleaned on startup

### 🔧 Improvements
- **Device removal support**: `async_remove_config_entry_device` allows manual removal of orphaned devices via HA UI
- **Zero-entity device cleanup**: Sub-devices with 0 entities are automatically removed on startup

## [0.8.1] - 2026-04-09

### 🐛 Bug fixes
- **Entity ID migration**: Old index-based USB/receiver entities (`peripheral_usb_0_*`, `peripheral_receiver_0_*`) auto-cleaned on startup — fixes entity name mismatches after v0.8.0 device reordering

## [0.8.0] - 2026-04-09

### ✨ New features
- **Peripheral Availability**: Sub-device entities go `unavailable` when BT peripheral reports `connected: false`

### 🔧 Improvements
- **Orphaned Device Cleanup**: Removes devices with Windows driver class manufacturer names (WinUsb-Gerät, etc.)
- **Generic USB Filter Extended**: 8 new patterns including USB-Massenspeichergerät, Microchip USB Hub, WinUsb-Gerät
- **Universal Receiver Cleanup**: Removed as standalone device (suppressed on agent side)

## [0.7.1] - 2026-04-09

### 🐛 Bug fixes
- **Lovelace card registration**: `register_static_path` replaced with `async_register_static_paths` — fixes `AttributeError` on HA 2025.x+ that caused integration setup to fail
- **Duplicate Zeroconf discovery**: Agent appeared as "Entdeckt" despite being configured — `unique_id` migration + `device_key` check in Zeroconf flow

## [0.7.0] - 2026-04-09

### ✨ New features
- **Agent Distribution (Phone Home)**: New "Distribute agent" option in config flow — generates install URL + 6-character pairing code
- **Install Page Server**: Self-contained HTML page at `/desk2ha/install/{token}` with OS-detection and platform-specific install scripts (macOS/Linux/Windows)
- **Pairing Code**: Setup wizard on agent uses pairing code to securely connect to HA — no manual URL/token entry needed
- **Auto Config Entry**: Agent phones home after install → HA creates integration entry automatically

## [0.6.1] - 2026-04-09

### 🐛 Bug fixes
- **CI test fix**: Added `homeassistant.exceptions` mock stub to test conftest — fixes `ConfigEntryNotReady` import error in CI

## [0.6.0] - 2026-04-09

### ✨ New features
- **Network Throughput Sensors**: Per-interface TX/RX bytes/s with DATA_RATE device class
- **Wake-on-LAN Service**: `desk2ha.wake_on_lan` sends magic packet via agent
- **Lid Open Binary Sensor**: Laptop lid state as opening binary sensor
- **Battery Charge Mode Select**: Lenovo conservation/normal/express mode selector
- **BLE Scanning Switch**: Enable/disable BLE battery scanning at runtime
- **Keyboard Backlight Number**: Slider control for keyboard backlight (0-100%)
- **HID++ Peripheral Sensors**: Battery, DPI, backlight, device type for Logitech wireless devices
- **HID++ DPI/Backlight Numbers**: Slider controls for mouse DPI (200-25600) and keyboard backlight

### 🔧 Improvements
- Suffix enrichment extended: `tx_bytes_per_sec`, `rx_bytes_per_sec`, `dpi`, `backlight_level`, `battery_state`, `device_type`
- Switch entity `turn_on`/`turn_off` uses `True`/`False` params instead of `1`/`0`

## [0.5.1] - 2026-04-09

### 🐛 Bug fixes
- **Litra light wake-up**: `assumed_state = True` prevents HA from sending turn_on on state restore (was turning physical Litra on at every HA restart)
- **Litra light entity always created**: No longer requires brightness data at setup time — entity is created even when the light is off, allowing HA control at all times
- **manifest.json**: Removed empty arrays (`requirements`, `ssdp`, `dependencies`)

## [0.5.0] - 2026-04-09

### ✨ New features
- **Custom Lovelace Card**: `desk2ha-card` with system gauges (CPU/RAM/Disk/WiFi), thermals, battery, peripherals with BT battery levels
- **Product Images Tier 3**: opt-in vendor image fetch (Dell, Lenovo, HP, Logitech) with local cache (1MB/image, 100MB total)
- **Bluetooth Peripheral Enrichment**: entity type, transport, and connected status for BT devices
- **Network Host Discovery**: scan LAN for SSH/WinRM hosts during remote agent installation
- **Workspace Blueprints**: Morning Routine, Lock on Away, Low Battery Alert, Night Shutdown
- **`fetch_product_images` service**: download product images on demand
- **Options Flow**: toggle for product image fetching

### 🐛 Bug fixes
- KNOWN_SENSORS prefix fallback: `thermals.fan.cpu` now matches `fan.cpu` definition (fixes "Unbekannt" fan + missing °C on thermals)
- Removed verbose debug logging from device cleanup

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
