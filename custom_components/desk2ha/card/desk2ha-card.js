/**
 * Desk2HA Lovelace Card
 *
 * Shows a compact desktop overview: system stats, thermals, battery,
 * displays, and peripherals (including Bluetooth battery levels).
 *
 * Configuration:
 *   type: custom:desk2ha-card
 *   entity: sensor.desk2ha_cpu_usage  # any desk2ha entity to find the device
 *   show_system: true
 *   show_thermals: true
 *   show_battery: true
 *   show_peripherals: true
 *   show_displays: true
 */

const CARD_VERSION = "0.1.0";

class Desk2HACard extends HTMLElement {
  static get properties() {
    return {
      hass: {},
      config: {},
    };
  }

  setConfig(config) {
    this._config = {
      show_system: true,
      show_thermals: true,
      show_battery: true,
      show_peripherals: true,
      show_displays: true,
      ...config,
    };

    if (!this._config.entity) {
      throw new Error("Please define an entity (any desk2ha sensor)");
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  static getConfigElement() {
    return document.createElement("desk2ha-card-editor");
  }

  static getStubConfig() {
    return { entity: "", show_system: true, show_thermals: true, show_battery: true, show_peripherals: true, show_displays: true };
  }

  // ── Helpers ──────────────────────────────────────────────────

  _getDeviceEntities() {
    if (!this._hass || !this._config.entity) return [];
    const stateObj = this._hass.states[this._config.entity];
    if (!stateObj) return [];

    // Find all entities that share the same device
    const deviceId = this._findDeviceId(this._config.entity);
    if (!deviceId) return [];

    return Object.keys(this._hass.states)
      .filter((eid) => eid.startsWith("sensor.desk2ha_") ||
                       eid.startsWith("binary_sensor.desk2ha_") ||
                       eid.startsWith("number.desk2ha_") ||
                       eid.startsWith("light.desk2ha_") ||
                       eid.startsWith("switch.desk2ha_"))
      .map((eid) => this._hass.states[eid])
      .filter((s) => s);
  }

  _findDeviceId(entityId) {
    // Use entity registry if available, fallback to prefix matching
    if (this._hass.devices) {
      for (const [id, dev] of Object.entries(this._hass.devices)) {
        if (dev.identifiers && dev.identifiers.some(([domain]) => domain === "desk2ha")) {
          return id;
        }
      }
    }
    return null;
  }

  _findEntity(suffix) {
    const entities = Object.keys(this._hass.states);
    const match = entities.find((eid) => eid.endsWith(suffix));
    return match ? this._hass.states[match] : null;
  }

  _findEntitiesPrefix(prefix) {
    return Object.keys(this._hass.states)
      .filter((eid) => eid.includes(prefix))
      .map((eid) => this._hass.states[eid])
      .filter((s) => s && s.state !== "unavailable" && s.state !== "unknown");
  }

  _val(entity) {
    if (!entity) return null;
    const s = entity.state;
    if (s === "unavailable" || s === "unknown") return null;
    const n = parseFloat(s);
    return isNaN(n) ? s : n;
  }

  _unit(entity) {
    return entity?.attributes?.unit_of_measurement || "";
  }

  _icon(entity, fallback) {
    return entity?.attributes?.icon || fallback || "mdi:help-circle";
  }

  _friendlyName(entity) {
    return entity?.attributes?.friendly_name || entity?.entity_id || "";
  }

  // ── Rendering ────────────────────────────────────────────────

  _render() {
    if (!this._hass || !this._config) return;

    const stateObj = this._hass.states[this._config.entity];
    if (!stateObj) {
      this.innerHTML = `<ha-card><div class="card-content">Entity not found: ${this._config.entity}</div></ha-card>`;
      return;
    }

    // Gather data
    const hostname = this._findEntity("_os_name");
    const agentVersion = this._findEntity("_agent_version");
    const cpuUsage = this._findEntity("_cpu_usage");
    const ramUsage = this._findEntity("_ram_usage");
    const diskUsage = this._findEntity("_disk_usage");
    const cpuTemp = this._findEntity("_cpu_temperature");
    const gpuTemp = this._findEntity("_gpu_temperature");
    const batteryLevel = this._findEntity("_battery_level");
    const batteryState = this._findEntity("_on_ac_power");
    const wifiSignal = this._findEntity("_wifi_signal");
    const uptime = this._findEntity("_system_uptime");

    // Build device name from config entity
    const deviceName = stateObj.attributes?.friendly_name?.replace(/\s*(CPU Usage|RAM Usage).*/, "") || "Desktop";

    let html = `<ha-card>`;

    // ── Header ──
    html += `<div class="d2h-header">
      <div class="d2h-header-icon">
        <ha-icon icon="mdi:desktop-tower-monitor"></ha-icon>
      </div>
      <div class="d2h-header-info">
        <div class="d2h-device-name">${this._escHtml(deviceName)}</div>
        <div class="d2h-device-sub">`;
    if (agentVersion) html += `Agent v${this._escHtml(String(this._val(agentVersion)))}`;
    if (uptime) {
      const hrs = this._val(uptime);
      if (typeof hrs === "number") html += ` &middot; ${Math.round(hrs)}h uptime`;
    }
    html += `</div></div></div>`;

    // ── System gauges ──
    if (this._config.show_system && (cpuUsage || ramUsage || diskUsage)) {
      html += `<div class="d2h-section"><div class="d2h-gauges">`;
      if (cpuUsage) html += this._gauge("CPU", this._val(cpuUsage), "%", "mdi:cpu-64-bit");
      if (ramUsage) html += this._gauge("RAM", this._val(ramUsage), "%", "mdi:memory");
      if (diskUsage) html += this._gauge("Disk", this._val(diskUsage), "%", "mdi:harddisk");
      if (wifiSignal) html += this._gauge("WiFi", this._val(wifiSignal), "%", "mdi:wifi");
      html += `</div></div>`;
    }

    // ── Thermals ──
    if (this._config.show_thermals && cpuTemp) {
      html += `<div class="d2h-section d2h-row">`;
      if (cpuTemp) html += this._statItem("CPU", this._val(cpuTemp), "°C", "mdi:thermometer", this._tempColor(this._val(cpuTemp)));
      if (gpuTemp) html += this._statItem("GPU", this._val(gpuTemp), "°C", "mdi:thermometer", this._tempColor(this._val(gpuTemp)));

      // Fans
      const cpuFan = this._findEntity("_cpu_fan_speed");
      const gpuFan = this._findEntity("_gpu_fan_speed");
      if (cpuFan) html += this._statItem("CPU Fan", this._val(cpuFan), "/min", "mdi:fan");
      if (gpuFan) html += this._statItem("GPU Fan", this._val(gpuFan), "/min", "mdi:fan");
      html += `</div>`;
    }

    // ── Battery ──
    if (this._config.show_battery && batteryLevel) {
      const level = this._val(batteryLevel);
      const onAc = batteryState ? this._val(batteryState) === "on" : null;
      const batIcon = onAc ? "mdi:battery-charging" : level > 80 ? "mdi:battery" : level > 40 ? "mdi:battery-50" : "mdi:battery-20";
      html += `<div class="d2h-section d2h-battery">
        <ha-icon icon="${batIcon}"></ha-icon>
        <div class="d2h-bar-container">
          <div class="d2h-bar" style="width:${level}%;background:${this._batColor(level)}"></div>
        </div>
        <span class="d2h-battery-text">${Math.round(level)}%${onAc ? " AC" : ""}</span>
      </div>`;
    }

    // ── Peripherals ──
    if (this._config.show_peripherals) {
      const peripherals = this._collectPeripherals();
      if (peripherals.length > 0) {
        html += `<div class="d2h-section"><div class="d2h-section-title">Peripherals</div>`;
        html += `<div class="d2h-peripherals">`;
        for (const p of peripherals) {
          html += `<div class="d2h-periph-item">
            <ha-icon icon="${p.icon}"></ha-icon>
            <span class="d2h-periph-name">${this._escHtml(p.name)}</span>`;
          if (p.battery !== null) {
            html += `<span class="d2h-periph-bat" style="color:${this._batColor(p.battery)}">${Math.round(p.battery)}%</span>`;
          }
          html += `</div>`;
        }
        html += `</div></div>`;
      }
    }

    html += `</ha-card>`;

    this.innerHTML = html + this._styles();
  }

  _collectPeripherals() {
    const peripherals = [];
    const seen = new Set();

    // Find all peripheral battery sensors
    const batteryEntities = Object.keys(this._hass.states)
      .filter((eid) => eid.includes("desk2ha") && eid.includes("battery_level") && !eid.includes("system"))
      .map((eid) => this._hass.states[eid]);

    for (const entity of batteryEntities) {
      const name = this._friendlyName(entity).replace(/ Battery Level$/, "").replace(/^.*? /, "");
      if (seen.has(name)) continue;
      seen.add(name);
      peripherals.push({
        name,
        battery: this._val(entity),
        icon: this._peripheralIcon(name),
      });
    }

    // Find peripherals without battery (connected entities)
    const connectedEntities = Object.keys(this._hass.states)
      .filter((eid) => eid.includes("desk2ha") && eid.includes("_connected") && eid.includes("bt_"))
      .map((eid) => this._hass.states[eid]);

    for (const entity of connectedEntities) {
      const name = this._friendlyName(entity).replace(/ Connected$/, "").replace(/^.*? /, "");
      if (seen.has(name)) continue;
      seen.add(name);
      peripherals.push({
        name,
        battery: null,
        icon: this._peripheralIcon(name),
      });
    }

    return peripherals;
  }

  _peripheralIcon(name) {
    const lower = name.toLowerCase();
    if (lower.includes("keyboard") || lower.includes("kb")) return "mdi:keyboard";
    if (lower.includes("mouse") || lower.includes("ms")) return "mdi:mouse";
    if (lower.includes("headset") || lower.includes("headphone")) return "mdi:headset";
    if (lower.includes("earbud")) return "mdi:earbuds";
    if (lower.includes("speaker") || lower.includes("speak")) return "mdi:speaker";
    if (lower.includes("webcam") || lower.includes("camera")) return "mdi:webcam";
    if (lower.includes("receiver")) return "mdi:antenna";
    if (lower.includes("litra") || lower.includes("light")) return "mdi:desk-lamp";
    return "mdi:bluetooth";
  }

  // ── Component builders ───────────────────────────────────────

  _gauge(label, value, unit, icon) {
    if (value === null) return "";
    const pct = Math.min(100, Math.max(0, value));
    const color = pct > 90 ? "var(--error-color, #db4437)" : pct > 70 ? "var(--warning-color, #ffa726)" : "var(--success-color, #43a047)";
    return `<div class="d2h-gauge">
      <svg viewBox="0 0 36 36" class="d2h-gauge-svg">
        <path class="d2h-gauge-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        <path class="d2h-gauge-fill" stroke="${color}" stroke-dasharray="${pct}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        <text x="18" y="20.5" class="d2h-gauge-text">${Math.round(value)}</text>
      </svg>
      <div class="d2h-gauge-label">${label}</div>
    </div>`;
  }

  _statItem(label, value, unit, icon, color) {
    if (value === null) return "";
    return `<div class="d2h-stat">
      <ha-icon icon="${icon}" ${color ? `style="color:${color}"` : ""}></ha-icon>
      <span class="d2h-stat-val">${typeof value === "number" ? Math.round(value) : value}${unit}</span>
      <span class="d2h-stat-label">${label}</span>
    </div>`;
  }

  _tempColor(temp) {
    if (temp === null) return "";
    if (temp > 85) return "var(--error-color, #db4437)";
    if (temp > 70) return "var(--warning-color, #ffa726)";
    return "";
  }

  _batColor(level) {
    if (level === null) return "";
    if (level > 60) return "var(--success-color, #43a047)";
    if (level > 20) return "var(--warning-color, #ffa726)";
    return "var(--error-color, #db4437)";
  }

  _escHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Styles ───────────────────────────────────────────────────

  _styles() {
    return `<style>
      ha-card {
        padding: 16px;
        overflow: hidden;
      }
      .d2h-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
      .d2h-header-icon {
        background: var(--primary-color);
        color: white;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }
      .d2h-header-icon ha-icon {
        --mdc-icon-size: 22px;
      }
      .d2h-device-name {
        font-size: 1.1em;
        font-weight: 500;
        line-height: 1.2;
      }
      .d2h-device-sub {
        font-size: 0.85em;
        color: var(--secondary-text-color);
      }
      .d2h-section {
        margin-bottom: 12px;
      }
      .d2h-section-title {
        font-size: 0.8em;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--secondary-text-color);
        margin-bottom: 6px;
      }
      /* Gauges */
      .d2h-gauges {
        display: flex;
        justify-content: space-around;
        gap: 8px;
      }
      .d2h-gauge {
        text-align: center;
        flex: 1;
        max-width: 80px;
      }
      .d2h-gauge-svg {
        width: 100%;
      }
      .d2h-gauge-bg {
        fill: none;
        stroke: var(--divider-color, #e0e0e0);
        stroke-width: 3;
      }
      .d2h-gauge-fill {
        fill: none;
        stroke-width: 3;
        stroke-linecap: round;
        transform: rotate(-90deg);
        transform-origin: center;
        transition: stroke-dasharray 0.5s ease;
      }
      .d2h-gauge-text {
        fill: var(--primary-text-color);
        font-size: 9px;
        text-anchor: middle;
        font-weight: 500;
      }
      .d2h-gauge-label {
        font-size: 0.75em;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      /* Stats row */
      .d2h-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
      }
      .d2h-stat {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.9em;
      }
      .d2h-stat ha-icon {
        --mdc-icon-size: 18px;
      }
      .d2h-stat-val {
        font-weight: 500;
      }
      .d2h-stat-label {
        color: var(--secondary-text-color);
        font-size: 0.85em;
      }
      /* Battery bar */
      .d2h-battery {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .d2h-battery ha-icon {
        --mdc-icon-size: 20px;
        flex-shrink: 0;
      }
      .d2h-bar-container {
        flex: 1;
        height: 8px;
        background: var(--divider-color, #e0e0e0);
        border-radius: 4px;
        overflow: hidden;
      }
      .d2h-bar {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
      }
      .d2h-battery-text {
        font-size: 0.85em;
        font-weight: 500;
        min-width: 40px;
        text-align: right;
      }
      /* Peripherals */
      .d2h-peripherals {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .d2h-periph-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 4px 0;
      }
      .d2h-periph-item ha-icon {
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
        flex-shrink: 0;
      }
      .d2h-periph-name {
        flex: 1;
        font-size: 0.9em;
      }
      .d2h-periph-bat {
        font-size: 0.85em;
        font-weight: 500;
        min-width: 35px;
        text-align: right;
      }
    </style>`;
  }
}

// ── Card Editor ──────────────────────────────────────────────────

class Desk2HACardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  _render() {
    this.innerHTML = `
      <div style="padding: 16px;">
        <ha-textfield
          label="Entity (any desk2ha sensor)"
          .value="${this._config.entity || ""}"
          @change="${(e) => this._valueChanged("entity", e.target.value)}"
          style="width: 100%; margin-bottom: 8px;"
        ></ha-textfield>
        ${this._toggle("show_system", "Show System Gauges")}
        ${this._toggle("show_thermals", "Show Thermals")}
        ${this._toggle("show_battery", "Show Battery")}
        ${this._toggle("show_peripherals", "Show Peripherals")}
        ${this._toggle("show_displays", "Show Displays")}
      </div>
    `;

    // Wire up events
    this.querySelectorAll("ha-textfield").forEach((el) => {
      el.addEventListener("change", (e) => this._valueChanged("entity", e.target.value));
    });
    this.querySelectorAll("ha-switch").forEach((el) => {
      el.addEventListener("change", (e) => {
        this._valueChanged(el.dataset.key, e.target.checked);
      });
    });
  }

  _toggle(key, label) {
    const checked = this._config[key] !== false;
    return `<div style="display:flex;align-items:center;justify-content:space-between;margin:8px 0;">
      <span>${label}</span>
      <ha-switch data-key="${key}" ${checked ? "checked" : ""}></ha-switch>
    </div>`;
  }

  _valueChanged(key, value) {
    if (!this._config) return;
    this._config = { ...this._config, [key]: value };
    const event = new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define("desk2ha-card", Desk2HACard);
customElements.define("desk2ha-card-editor", Desk2HACardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "desk2ha-card",
  name: "Desk2HA",
  description: "Desktop overview card with system stats, thermals, battery, and peripheral status",
  preview: true,
  documentationURL: "https://github.com/maximusIIxII/hass-desk2ha",
});

console.info(`%c DESK2HA-CARD %c v${CARD_VERSION} `, "color:white;background:#03A9F4;font-weight:bold;", "");
