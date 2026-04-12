# Getting Started with Desk2HA

This guide walks you through setting up Desk2HA from scratch. By the end, your desktop PC will appear as a fully controllable device in Home Assistant — with system stats, display controls, webcam settings, and peripheral monitoring.

## Overview

Desk2HA has two components:

```
Your PC                          Home Assistant
+-----------------+              +------------------+
| desk2ha-agent   |  HTTP/MQTT   | hass-desk2ha     |
| (Python service)|  -------->   | (HA integration) |
+-----------------+              +------------------+
```

- **Agent**: runs on your desktop (Windows/Linux/macOS), collects hardware data
- **Integration**: runs in Home Assistant, creates entities and controls

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Home Assistant** | 2024.12.0 or newer |
| **Python** | 3.11+ on the target PC |
| **Network** | Agent and HA on the same network, port 9693 (TCP) open |
| **OS** | Windows 10+, Ubuntu 20.04+, macOS 11+ |

### Optional dependencies (for additional features)

| Feature | Windows | Linux | macOS |
|---------|---------|-------|-------|
| Display control (DDC/CI) | Built-in | `ddcutil` | Built-in |
| Webcam control | `opencv-python` | `opencv-python` + `libv4l-dev` | `opencv-python` |
| Headset control | — | `headsetcontrol` | `headsetcontrol` |
| Bluetooth battery | Built-in (WinRT) | `bleak` | `bleak` |
| Dell thermals/fans | Dell Command Monitor | — | — |

## Step 1: Install the Agent

On the PC you want to monitor:

```bash
pip install desk2ha-agent
```

Windows users — install with extras for WMI support:

```bash
pip install desk2ha-agent[windows]
```

## Step 2: Configure the Agent

Create a config file. Start with the minimal version:

```bash
# Generate a secure token
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Create `config.toml` next to your agent installation (e.g., `C:\desk2ha\config.toml`
on Windows or `~/desk2ha/config.toml` on Linux/macOS):

```toml
[http]
enabled = true
auth_token = "PASTE_YOUR_GENERATED_TOKEN_HERE"
```

That's it for a basic setup. The agent auto-detects everything else.

### Full config (optional)

For MQTT, custom intervals, or disabling collectors, see the
[full config example](https://github.com/maximusIIxII/desk2ha-agent/blob/main/examples/full-config.toml).

## Step 3: Start the Agent

```bash
python -m desk2ha_agent --config config.toml
```

You should see output like:

```
Desk2HA Agent 1.0.0 starting
Config loaded from config.toml
Activated collector: windows_platform (platform tier)
Activated collector: ddcci (generic tier)
Activated collector: uvc (generic tier)
HTTP transport listening on 0.0.0.0:9693
```

Verify the agent is running:

```bash
curl -H "Authorization: Bearer PASTE_YOUR_GENERATED_TOKEN_HERE" http://localhost:9693/v1/health
```

### Autostart

**Windows** — Create a shortcut to the agent in your Startup folder:

```
Win+R → shell:startup → create shortcut:
pythonw -m desk2ha_agent --config "C:\path\to\config.toml"
```

Or install as a Windows Service (see `scripts/install-service.ps1`).

**Linux** — Create a systemd unit:

```ini
# /etc/systemd/system/desk2ha-agent.service
[Unit]
Description=Desk2HA Agent
After=network-online.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/desk2ha
ExecStart=/usr/bin/python3 -m desk2ha_agent --config config.toml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now desk2ha-agent
```

**macOS** — Create a launchd plist:

```xml
<!-- ~/Library/LaunchAgents/com.desk2ha.agent.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.desk2ha.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>-m</string>
        <string>desk2ha_agent</string>
        <string>--config</string>
        <string>/Users/YOU/desk2ha/config.toml</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.desk2ha.agent.plist
```

## Step 4: Install the HA Integration

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Click **Integrations** > **...** (top right) > **Custom repositories**
3. Add URL: `https://github.com/maximusIIxII/hass-desk2ha` — Category: **Integration**
4. Click **+ Explore & Download Repositories**, search for **Desk2HA**, install
5. Restart Home Assistant

### Manual install

Copy `custom_components/desk2ha/` to your HA `config/custom_components/` directory and restart.

## Step 5: Add the Integration

1. Go to **Settings** > **Devices & Services** > **+ Add Integration**
2. Search for **Desk2HA**
3. Choose your setup method:

### Option A: Manual URL (simplest)

Enter the agent URL and token:

- **URL**: `http://YOUR_PC_IP:9693`
- **Token**: the token from your `config.toml`

### Option B: Auto-Discovery (Zeroconf)

If your agent is running with Zeroconf enabled (default), HA will
auto-discover it. You'll see a notification — click **Configure** and
enter the token.

### Option C: Distribute (Phone-Home)

For remote machines without direct network access:

1. HA generates an install URL with a pairing code
2. Open the URL on the target machine
3. The agent installs itself and phones home to HA

## Step 6: Verify

After setup, go to **Settings** > **Devices & Services** > **Desk2HA**.
You should see your PC with all detected peripherals:

![Connected Devices](screenshots/devices.png)

- System sensors (CPU, RAM, Disk, Network, Battery)
- Display controls (Brightness, Contrast, Input Source, etc.)
- Webcam controls (if detected)
- Bluetooth peripherals (keyboard, mouse battery levels)
- USB devices (dock, speakerphone, etc.)

## Step 7: Add the Dashboard Card

1. Go to your dashboard > **Edit** > **+ Add Card**
2. Search for **Desk2HA** or add manually:

First, register the card resource:

1. Go to **Settings** > **Dashboards** > **Resources** (top right: three dots)
2. Click **+ Add Resource**
3. URL: `/desk2ha/desk2ha-card.js` — Type: **JavaScript Module**

Then add the card to your dashboard:

```yaml
type: custom:desk2ha-card
show_system: true
show_thermals: true
show_battery: true
show_peripherals: true
show_displays: true
```

The card auto-discovers your Desk2HA entities. Click any device to
open its control popup:

![Monitor Controls](screenshots/popup-monitor.png) Click any device to
open its control popup with sliders, toggles, and settings.

## Updating

### Agent updates

The agent can self-update via the HA integration:

- An **Update** entity appears when a new version is available on PyPI
- Click **Install** in HA, or manually: `pip install --upgrade desk2ha-agent`
- Restart the agent process

### Integration updates

- **HACS**: Updates appear automatically. Click **Update** and restart HA.
- **Manual**: Replace `custom_components/desk2ha/` and restart HA.

### Version compatibility

The agent and integration communicate via a versioned API (`/v1/`).
Minor version differences are compatible. Check the
[CHANGELOG](../CHANGELOG.md) for breaking changes.

## Troubleshooting

### Agent won't start

- **Port in use**: Another process uses port 9693. Change in config: `port = 9694`
- **Python not found**: Ensure Python 3.11+ is in your PATH
- **Permission denied**: On Linux, ensure the user can access USB/HID devices

### Integration can't connect

- **Firewall**: Ensure port 9693 is open on the agent PC
- **Wrong token**: The token in HA must match `auth_token` in config.toml exactly
- **Different network**: Agent and HA must be on the same network (or have routing)

### No display controls

- **DDC/CI disabled**: Enable DDC/CI in your monitor's OSD menu
- **Laptop screen**: Built-in laptop displays don't support DDC/CI (only external monitors)
- **Session 0**: On Windows, DDC/CI only works in interactive sessions (not as a headless service)

### No webcam controls

- **OpenCV not installed**: `pip install opencv-python`
- **Camera in use**: Another app (Teams, Zoom) may have exclusive access
- **Linux permissions**: Add your user to the `video` group

### No Bluetooth peripherals

- **Not connected**: Only connected (not just paired) BT devices are shown
- **BLE scanning**: Enable via the BLE Scanning switch in HA, or `bleak` on Linux/macOS

### Health Check

Run the built-in health check to diagnose device issues:

1. Go to **Developer Tools** > **Services**
2. Call `desk2ha.device_health_check`
3. Check the persistent notification for results

## Uninstalling

### Remove the integration

1. **Settings** > **Devices & Services** > **Desk2HA** > **Delete**
2. Remove `custom_components/desk2ha/` (or uninstall via HACS)
3. Restart HA

### Remove the agent

```bash
pip uninstall desk2ha-agent
```

Windows Service: `nssm remove Desk2HAAgent confirm`
Linux: `sudo systemctl disable --now desk2ha-agent`

## Next Steps

- Set up **automations** using Desk2HA entities (e.g., dim display at sunset)
- Add more PCs to create a **fleet** (each PC gets its own agent)
- Use **blueprints** for common alert patterns (battery low, CPU overheating)
- Call `desk2ha.fetch_product_images` to download device photos for the card
