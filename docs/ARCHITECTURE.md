# Desk2HA Architecture

## System Overview

```
+---------------------------+          +---------------------------+
|     Your Desktop PC       |          |     Home Assistant        |
|                           |          |                           |
|  +---------------------+ |  HTTP    |  +---------------------+ |
|  | desk2ha-agent       | | -------> |  | hass-desk2ha        | |
|  |                     | |  :9693   |  | (custom component)  | |
|  | Platform Collectors | |          |  |                     | |
|  | - Windows/Linux/Mac | |  MQTT    |  | Coordinator         | |
|  |                     | | -------> |  | - Polls /v1/metrics | |
|  | Generic Collectors  | |  :1883   |  | - Sends commands    | |
|  | - DDC/CI (displays) | |          |  |                     | |
|  | - UVC (webcams)     | |          |  | Entity Platforms    | |
|  | - Bluetooth         | |          |  | - sensor (80+)      | |
|  | - USB devices       | |          |  | - number (sliders)  | |
|  | - USB Power Delivery| |          |  | - select (dropdowns)| |
|  | - HeadsetControl    | |          |  | - switch (toggles)  | |
|  | - Network           | |          |  | - button (actions)  | |
|  |                     | |          |  | - light             | |
|  | Vendor Plugins      | |          |  | - media_player      | |
|  | - Dell DCM          | |          |  | - binary_sensor     | |
|  | - Logitech Litra    | |          |  | - update            | |
|  | - Logitech HID++    | |          |  |                     | |
|  +---------------------+ |          |  | Services            | |
|                           |          |  | - fleet_status      | |
|  +---------------------+ |          |  | - device_health_check|
|  | desk2ha-helper      | |          |  | - fetch_product_images|
|  | (elevated, :9694)   | |          |  | - wake_on_lan       | |
|  | - Dell DCM WMI      | |          |  |                     | |
|  | - Thermals/Fans     | |          |  | Lovelace Card       | |
|  +---------------------+ |          |  | - System gauges     | |
+---------------------------+          |  | - Device list       | |
                                       |  | - Control popups    | |
                                       |  +---------------------+ |
                                       +---------------------------+
```

## Data Flow

```
Collectors (every 30-60s)
    |
    v
StateCache (in-memory)
    |
    +---> HTTP /v1/metrics (JSON) ---> HA Coordinator ---> Entity updates
    |
    +---> MQTT desk2ha/{key}/state ---> HA MQTT Discovery ---> Sensors
```

## Device Hierarchy in HA

```
Host Device (Dell Inc. Example Workstation)
  |
  +-- U5226KW (Monitor)           34 entities, DDC/CI controls
  +-- Keyboard KB900 (BT)          7 entities, battery level
  +-- Mouse MS900 (BT)             7 entities, battery level
  +-- Litra Glow (USB)             7 entities, light control
  +-- Webcam (IR / Windows Hello)  13 entities, UVC controls
  +-- Webcam (RGB)                 14 entities, UVC controls
  +-- Webcam WB7022 (USB)          3 entities, USB info
  +-- Speak2 75 (USB)              3 entities, USB info
  +-- DA305 USB-C Hub (USB)        3 entities, USB info
  +-- KM7321W Keyboard (USB)       3 entities, USB info
```

## Product Image Tiers

```
Tier 1: Generic SVG icons (keyboard, mouse, monitor, dock, ...)
    Always available, built into the agent
    |
Tier 2: Vendor-specific SVGs (Dell notebook, HP workstation, ...)
    Pattern-matched by manufacturer + model
    |
Tier 3: Product photos (JPEG/PNG from vendor websites)
    Fetched on demand via desk2ha.fetch_product_images service
    Cached locally in HA (max 100MB LRU cache)
```

## API Contract

Agent and Integration communicate via a versioned REST API:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/health` | GET | Agent health + uptime |
| `/v1/info` | GET | Hardware, identity, collectors, config |
| `/v1/metrics` | GET | All current sensor values |
| `/v1/commands` | POST | Send control commands |
| `/v1/config` | GET | Redacted config summary |
| `/v1/image/{key}` | GET | Device icon SVG |
| `/v1/update/check` | GET | Check for agent updates |
| `/v1/update/install` | POST | Install agent update |

Schema version: `2.0.0` (defined in `shared/openapi.yaml`)

## Security Model

- **Authentication**: Bearer token on all HTTP endpoints
- **MQTT**: Username/password authentication
- **Helper**: Shared secret on localhost-only connection
- **Rate limiting**: On pairing endpoint and install server
- **Input validation**: On all command parameters
- **No cloud**: All communication is local network only
