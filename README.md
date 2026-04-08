# Desk2HA — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Multi-vendor desktop monitoring integration for [Home Assistant](https://www.home-assistant.io/).

Works with the [Desk2HA Agent](https://github.com/maximusIIxII/desk2ha-agent)
running on your Windows, Linux, or macOS machine.

## Features

- **Multi-vendor**: Dell, HP, Lenovo, Logitech, Corsair, SteelSeries
- **Full device tree**: Host PC + monitors + peripherals as HA devices
- **DDC/CI monitor control**: Brightness, input source, power
- **Peripheral batteries**: BLE, HID, and vendor-specific battery levels
- **Agent lifecycle**: Install, update, and configure agents from HA

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
2. Install "Desk2HA"
3. Restart Home Assistant
4. Go to Settings → Integrations → Add Integration → Desk2HA

### Manual

Copy `custom_components/desk2ha/` to your HA `custom_components/` directory.

## Configuration

The integration is configured through the Home Assistant UI (Config Flow).
No YAML configuration needed.

## License

Apache-2.0
