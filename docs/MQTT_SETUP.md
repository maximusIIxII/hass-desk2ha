# MQTT Setup for Desk2HA

MQTT is an **optional** alternative transport for Desk2HA. Use it when your agent PC can't accept incoming connections (e.g., behind NAT, strict firewall, or on a different VLAN).

With MQTT, the agent connects **outbound** to your MQTT broker — no firewall rule needed on the agent PC.

> **Note:** For most setups, HTTP with bearer token is simpler and recommended.
> See the [Getting Started Guide](GETTING_STARTED.md) for the default HTTP setup.

## When to use MQTT

| Scenario | Recommended transport |
|----------|----------------------|
| Agent and HA on the same network | **HTTP** (simplest) |
| Agent behind NAT / no port forwarding | **MQTT** |
| Strict corporate firewall (no inbound) | **MQTT** |
| Multiple agents reporting to one HA | Either (both work) |
| Display/webcam controls needed | **HTTP** (controls use HTTP API) |

> **Tip:** You can enable both HTTP and MQTT simultaneously. MQTT handles metric
> publishing, HTTP handles direct control (display settings, webcam adjustments).

## Prerequisites

- Home Assistant with MQTT broker (Mosquitto add-on or external broker)
- MQTT user credentials

## Step 1: Install the Mosquitto Broker

If you don't have an MQTT broker yet:

1. Go to **Settings** > **Add-ons** > **Add-on Store**
2. Search for **Mosquitto broker** and install it
3. Start the add-on

Or use the direct link: [Install Mosquitto](https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_mosquitto)

## Step 2: Create an MQTT User

1. Go to **Settings** > **People** > **Users** tab
2. Click **+ Add User**
3. Create a user (e.g., `mqttuser` / `your_secure_password`)
4. This user will be used by the agent to authenticate with the broker

> **Note:** Mosquitto uses Home Assistant's user system by default.
> Any HA user can connect to the broker.

## Step 3: Configure the Agent

Add the MQTT section to your agent's `config.toml`:

### MQTT only (no HTTP)

```toml
[http]
enabled = false

[mqtt]
enabled = true
broker = "YOUR_HA_IP"       # e.g., "192.168.1.53"
port = 1883
username = "mqttuser"
password = "your_secure_password"
```

### Both MQTT and HTTP (recommended for full control)

```toml
[http]
enabled = true
auth_token = "YOUR_BEARER_TOKEN"

[mqtt]
enabled = true
broker = "YOUR_HA_IP"
port = 1883
username = "mqttuser"
password = "your_secure_password"
```

With both enabled:
- **MQTT** publishes system metrics to HA
- **HTTP** handles direct control commands (display brightness, webcam settings, etc.)

## Step 4: Restart the Agent

```bash
python -m desk2ha_agent --config config.toml
```

You should see:

```
MQTT transport connected to YOUR_HA_IP:1883
Publishing metrics to desk2ha/ST-XXXXXXX/metrics
```

## Step 5: Verify in Home Assistant

The agent publishes MQTT auto-discovery messages. After connecting:

1. Go to **Settings** > **Devices & Services** > **MQTT**
2. Your PC should appear as a new device automatically
3. Alternatively, add the Desk2HA integration manually — it will detect the MQTT-connected agent

## MQTT Topics

The agent uses these MQTT topics:

| Topic | Purpose |
|-------|---------|
| `homeassistant/sensor/desk2ha_*/config` | Auto-discovery (retained) |
| `desk2ha/{device_key}/metrics` | Metric updates |
| `desk2ha/{device_key}/status` | Online/offline status (LWT) |

## Troubleshooting

### Agent can't connect to broker

- **Connection refused**: Broker not running, wrong IP, or wrong port
- **Authentication failed**: Wrong username/password. Test with: `mosquitto_pub -h YOUR_HA_IP -u mqttuser -P password -t test -m hello`
- **Timeout**: Firewall on HA side blocking port 1883, or wrong IP

### Entities not appearing in HA

- **MQTT integration missing**: Ensure the MQTT integration is configured in HA (**Settings** > **Devices & Services** > **MQTT**)
- **Discovery disabled**: Check that MQTT discovery is enabled (default: on)
- **Check broker logs**: **Settings** > **Add-ons** > **Mosquitto** > **Log** tab

### Cleaning up old MQTT entities

If you reconfigure the agent (new device key, etc.), old auto-discovery messages may linger:

1. Go to **Settings** > **Devices & Services** > **MQTT**
2. Find the old device and click **Delete**
3. Or clear retained messages: `mosquitto_pub -h YOUR_HA_IP -u user -P pass -t "homeassistant/sensor/desk2ha_OLD_KEY/config" -r -n`
