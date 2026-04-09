# Desk2HA — Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/v/release/maximusIIxII/hass-desk2ha)](https://github.com/maximusIIxII/hass-desk2ha/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)
[![CI](https://github.com/maximusIIxII/hass-desk2ha/actions/workflows/ci.yml/badge.svg)](https://github.com/maximusIIxII/hass-desk2ha/actions/workflows/ci.yml)

Multi-vendor desktop monitoring integration for [Home Assistant](https://www.home-assistant.io/).

Brings your entire desk — PC, monitors, peripherals — into Home Assistant. Works with the [Desk2HA Agent](https://github.com/maximusIIxII/desk2ha-agent) running on Windows, Linux, or macOS.

## Screenshots

| Sensors | Controls | Diagnostics | Config |
|---------|----------|-------------|--------|
| ![Sensors](docs/screenshots/sensors.png) | ![Controls](docs/screenshots/controls.png) | ![Diagnostics](docs/screenshots/diagnostics.png) | ![Config](docs/screenshots/config.png) |

| Connected Devices |
|-------------------|
| ![Devices](docs/screenshots/devices.png) |

## What you get

- **80+ sensors**: CPU, RAM, disk, battery, GPU, thermals, fan speeds, network, OS info
- **Display controls**: Brightness, contrast, volume, input source, KVM switch, PBP mode
- **Webcam controls**: Brightness, contrast, saturation, white balance, focus, zoom via UVC
- **Logitech Litra**: Power, brightness, color temperature as HA light entity
- **Bluetooth peripherals**: Paired BLE + Classic devices with battery levels (keyboard, mouse, headset, earbuds)
- **Peripheral detection**: USB devices, wireless receivers (Dell, Logitech, Jabra, Corsair, SteelSeries, Razer)
- **Product images**: Opt-in fetch of real product photos from Dell, Lenovo, HP, Logitech websites
- **Power monitoring**: USB PD charger status, AC adapter wattage, Dell DCM thermals
- **Sub-devices**: Each display, peripheral, and receiver appears as its own HA device
- **Custom Lovelace card**: Dedicated dashboard card with system gauges, thermals, peripherals overview
- **Agent updates**: See available updates + install from HA
- **Auto-discovery**: Zeroconf finds agents on your network
- **Remote install**: Deploy the agent on remote machines via SSH or WinRM
- **Fleet management**: Monitor multiple desks with fleet_status, refresh, restart services
- **Dynamic entities**: Only creates entities for metrics your agent actually reports

## Installation

### HACS (recommended)

1. **HACS** → Integrations → ⋮ → **Custom Repositories**
2. URL: `https://github.com/maximusIIxII/hass-desk2ha`
3. Category: **Integration**
4. Install **Desk2HA** and restart HA
5. **Settings** → **Integrations** → **Add Integration** → **Desk2HA**

### Manual

Copy `custom_components/desk2ha/` to your HA `custom_components/` directory and restart.

## Setup

The [Desk2HA Agent](https://github.com/maximusIIxII/desk2ha-agent) must be running on the target machine.

**Option 1: Manual**
1. Install the agent: `pip install desk2ha-agent`
2. Start it with a config file (see agent README)
3. In HA, add the Desk2HA integration:
   - **URL**: `http://<agent-ip>:9693`
   - **Token**: The auth token from your agent config

**Option 2: Auto-discovery**
The agent advertises via Zeroconf. HA will discover it automatically.

**Option 3: Remote install**
In the integration setup, choose "Install agent on remote machine" and provide SSH (Linux/macOS) or WinRM (Windows) credentials. The integration installs the agent, generates a config, and starts it automatically.

## Entity Platforms

| Platform | Examples |
|----------|---------|
| **Sensor** | CPU Usage, RAM, Battery Level, GPU Model, Fan Speed, Display Model, WiFi RSSI |
| **Binary Sensor** | On AC Power |
| **Number** | Display Brightness, Contrast, Volume (per display) |
| **Select** | Display Input Source, Power State, KVM Switch, PBP Mode, Thermal Profile |
| **Switch** | Auto Brightness, Auto Color Temperature |
| **Light** | Display Brightness (dimmable), Logitech Litra (brightness + color temp) |
| **Media Player** | Display Speaker Volume |
| **Button** | Refresh Data, Restart Agent, Lock Screen, Sleep, Shutdown |
| **Update** | Agent version check + install |

## Services

| Service | Description |
|---------|-------------|
| `desk2ha.fleet_status` | Get status of all configured desks (online/offline, versions, collectors) |
| `desk2ha.refresh` | Force-refresh metrics from one or all desks |
| `desk2ha.restart_agent` | Send restart command to a specific agent |
| `desk2ha.fetch_product_images` | Download product images from manufacturer websites for all desks |

## Options

In the integration options you can configure:
- **Poll interval**: How often to fetch metrics (default: 30s, min: 10s)
- **Fetch product images**: Download product photos from manufacturer websites (opt-in)

## Requirements

- Home Assistant 2024.12.0+
- [Desk2HA Agent](https://github.com/maximusIIxII/desk2ha-agent) running on the target machine
- Network connectivity between HA and the agent (HTTP port 9693 or MQTT)

## Known Issues

| Issue | Workaround | Status |
|-------|------------|--------|
| **Display entities show "not available"** | Display controls require the agent to run interactively (not as service) for DDC/CI access. | By design |
| **MQTT entities duplicate HTTP entities** | If both HTTP polling and MQTT are active, the same metrics appear twice. Use one transport or the other, not both. | Planned fix |

## Custom Lovelace Card

Add the Desk2HA card to any dashboard for a complete desk overview:

```yaml
type: custom:desk2ha-card
entity: sensor.desk2ha_cpu_usage
```

The card shows system gauges (CPU, RAM, disk, WiFi), thermals, battery status, and connected peripherals with Bluetooth battery levels. Registered automatically when the integration loads.

## Upcoming Features

- **Vendor battery levels**: Corsair, SteelSeries, Razer battery via HID
- **Prometheus endpoint**: Metrics in Prometheus scrape format

## License

Apache-2.0
