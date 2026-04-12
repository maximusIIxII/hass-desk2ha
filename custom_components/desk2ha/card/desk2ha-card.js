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

const CARD_VERSION = "1.1.2";

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
    // entity is optional — auto-discovered if not set
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

  static getStubConfig(hass) {
    // Auto-discover a desk2ha entity for the stub config
    // hass may be undefined when HA calls this during card picker
    return { show_system: true, show_thermals: true, show_battery: true, show_peripherals: true, show_displays: true };
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

  _findScopedEntity(suffix) {
    if (!this._entityPrefix) return this._findEntity(`_${suffix}`);
    // Look for entity matching this device's prefix (e.g. "sensor.dell_inc_latitude_5550_cpu_usage")
    const target = `sensor.${this._entityPrefix}_${suffix}`;
    if (this._hass.states[target]) return this._hass.states[target];
    // Fallback: binary_sensor prefix
    const bsTarget = `binary_sensor.${this._entityPrefix}_${suffix}`;
    if (this._hass.states[bsTarget]) return this._hass.states[bsTarget];
    // Fallback: generic suffix match
    return this._findEntity(`_${suffix}`);
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

  _autoDiscoverEntity() {
    if (!this._hass) return null;
    // If entity is configured and exists, use it
    if (this._config.entity && this._hass.states[this._config.entity]) {
      return this._hass.states[this._config.entity];
    }
    // Auto-discover: find any CPU usage sensor ending with _cpu_usage
    // Entity IDs may start with desk2ha_ or the device name (e.g. dell_inc_latitude_5550_)
    const cpuEntity = Object.keys(this._hass.states).find(
      (eid) => eid.endsWith("_cpu_usage") && eid.startsWith("sensor.") &&
               this._hass.states[eid]?.attributes?.friendly_name?.includes("CPU Usage")
    );
    if (cpuEntity) return this._hass.states[cpuEntity];
    // Fallback: any entity with desk2ha in its attributes
    const anyEntity = Object.keys(this._hass.states).find(
      (eid) => eid.includes("desk2ha") && eid.startsWith("sensor.")
    );
    return anyEntity ? this._hass.states[anyEntity] : null;
  }

  _render() {
    if (!this._hass || !this._config) return;
    // Don't re-render while popup is open (would destroy it)
    if (this.querySelector("#d2h-popup-container")) return;

    const stateObj = this._autoDiscoverEntity();
    if (!stateObj) {
      this.innerHTML = `<ha-card><div class="card-content" style="padding:16px;">
        <p><b>Desk2HA</b> — No entities found.</p>
        <p style="font-size:0.85em;color:var(--secondary-text-color)">
          Make sure the Desk2HA integration is configured and the agent is running.
        </p>
      </div></ha-card>`;
      return;
    }

    // Derive entity prefix for scoped lookups
    // e.g. "sensor.dell_inc_latitude_5550_cpu_usage" → "dell_inc_latitude_5550"
    const entityId = stateObj.entity_id;
    const prefixMatch = entityId.match(/^sensor\.(.+?)_(?:cpu_usage|ram_usage|disk_usage|os_name|agent_version)$/);
    this._entityPrefix = prefixMatch ? prefixMatch[1] : null;

    // Gather data — use prefix-scoped lookup
    const hostname = this._findScopedEntity("os_name");
    const agentVersion = this._findScopedEntity("agent_version");
    const cpuUsage = this._findScopedEntity("cpu_usage");
    const ramUsage = this._findScopedEntity("ram_usage");
    const diskUsage = this._findScopedEntity("disk_usage");
    const cpuTemp = this._findScopedEntity("cpu_temperature");
    const gpuTemp = this._findScopedEntity("gpu_temperature");
    const batteryLevel = this._findScopedEntity("battery_level");
    const batteryState = this._findScopedEntity("on_ac_power");
    const wifiSignal = this._findScopedEntity("wifi_signal");
    const uptime = this._findScopedEntity("system_uptime");

    // Build device name from friendly_name (contains HA device name)
    // e.g. "Dell Inc. Latitude 5550 CPU Usage" → "Dell Inc. Latitude 5550"
    const fn = stateObj.attributes?.friendly_name || "";
    let deviceName = fn.replace(/\s*(CPU Usage|RAM Usage|Disk Usage|Agent Version|OS Name).*/, "").trim() || "Desktop";
    // Remove "Desk2HA " prefix if present
    deviceName = deviceName.replace(/^Desk2HA\s+/, "").trim() || deviceName;

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
      const cpuFan = this._findScopedEntity("cpu_fan_speed");
      const gpuFan = this._findScopedEntity("gpu_fan_speed");
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

    // ── Peripherals (all connected Desk2HA sub-devices) ──
    if (this._config.show_peripherals) {
      const peripherals = this._collectPeripherals();
      if (peripherals.length > 0) {
        html += `<div class="d2h-section"><div class="d2h-section-title">Devices</div>`;
        html += `<div class="d2h-peripherals">`;
        for (const p of peripherals) {
          const clickAttr = p.deviceId ? `data-device="${p.deviceId}" class="d2h-periph-item d2h-clickable"` : `class="d2h-periph-item"`;
          html += `<div ${clickAttr}>
            <ha-icon icon="${p.icon}"></ha-icon>
            <span class="d2h-periph-name">${this._escHtml(p.name)}</span>`;
          if (p.status) {
            html += `<span class="d2h-periph-status">${this._escHtml(p.status)}</span>`;
          }
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

    // Bind click handlers — open device popup
    this.querySelectorAll(".d2h-clickable").forEach((el) => {
      el.addEventListener("click", () => {
        const deviceId = el.dataset.device;
        if (deviceId) this._showDevicePopup(deviceId);
      });
    });

    // Close popup on backdrop click
    this.addEventListener("click", (e) => {
      if (e.target.classList.contains("d2h-popup-backdrop")) {
        this._closePopup();
      }
    });
  }

  _collectPeripherals() {
    const peripherals = [];
    if (!this._hass.devices || !this._hass.entities) return peripherals;

    // Find the host device ID (the one without via_device)
    let hostDevId = null;
    for (const [devId, dev] of Object.entries(this._hass.devices)) {
      const isDesk2HA = dev.identifiers?.some(([domain]) => domain === "desk2ha");
      if (isDesk2HA && !dev.via_device_id) {
        hostDevId = devId;
        break;
      }
    }

    // Collect all Desk2HA sub-devices (peripherals, monitors, webcams, etc.)
    for (const [devId, dev] of Object.entries(this._hass.devices)) {
      if (devId === hostDevId) continue; // Skip host device
      const isDesk2HA = dev.identifiers?.some(([domain]) => domain === "desk2ha");
      if (!isDesk2HA) continue;

      const name = dev.name || "Unknown";

      // Collect this device's entities
      const devEntities = [];
      for (const [eid, ent] of Object.entries(this._hass.entities)) {
        if (ent.device_id === devId) devEntities.push(eid);
      }

      // Find battery level entity
      let battery = null;
      const batEid = devEntities.find((e) => e.endsWith("_battery_level"));
      if (batEid) {
        const batState = this._hass.states[batEid];
        if (batState && batState.state !== "unavailable") {
          battery = parseFloat(batState.state);
          if (isNaN(battery)) battery = null;
        }
      }

      // Find a "primary" entity for click action (prefer light, number, select, switch)
      let primaryEntity = devEntities.find((e) => e.startsWith("light."));
      if (!primaryEntity) primaryEntity = devEntities.find((e) => e.startsWith("number."));
      if (!primaryEntity) primaryEntity = devEntities.find((e) => e.startsWith("select."));
      if (!primaryEntity) primaryEntity = devEntities.find((e) => e.startsWith("switch."));
      if (!primaryEntity) primaryEntity = devEntities.find((e) => e.startsWith("sensor."));

      // Determine status text
      let status = "";
      const powerEid = devEntities.find((e) => e.endsWith("_power"));
      if (powerEid) {
        const ps = this._hass.states[powerEid];
        if (ps) status = ps.state === "True" || ps.state === "on" ? "On" : "Off";
      }

      // Count available controls (numbers, selects, switches, lights, buttons)
      const controlCount = devEntities.filter((e) =>
        e.startsWith("number.") || e.startsWith("select.") ||
        e.startsWith("switch.") || e.startsWith("light.") ||
        e.startsWith("button.") || e.startsWith("media_player.")
      ).length;
      if (!status && controlCount > 0) {
        status = `${controlCount} controls`;
      }

      // Extract image key from device identifier (e.g. "ST-ABC1234_peripheral.litra_0" → "peripheral.litra_0")
      let imageKey = "";
      for (const [domain, identifier] of (dev.identifiers || [])) {
        if (domain === "desk2ha") {
          // Remove host prefix: "ST-ABC1234_display.0" → "display.0"
          const parts = identifier.split("_");
          imageKey = parts.length > 1 ? parts.slice(1).join("_") : identifier;
          break;
        }
      }

      peripherals.push({
        name,
        battery,
        icon: this._peripheralIcon(name),
        entityId: primaryEntity || null,
        status,
        deviceId: devId,
        imageKey,
      });
    }

    // Sort: devices with battery first, then alphabetically
    peripherals.sort((a, b) => {
      if (a.battery !== null && b.battery === null) return -1;
      if (a.battery === null && b.battery !== null) return 1;
      return a.name.localeCompare(b.name);
    });

    return peripherals;
  }

  _peripheralIcon(name) {
    const lower = name.toLowerCase();
    if (lower.includes("keyboard") || lower.includes("kb")) return "mdi:keyboard";
    if (lower.includes("mouse") || lower.includes("ms9")) return "mdi:mouse";
    if (lower.includes("headset") || lower.includes("headphone")) return "mdi:headset";
    if (lower.includes("earbud")) return "mdi:earbuds";
    if (lower.includes("speak")) return "mdi:speaker";
    if (lower.includes("webcam") || lower.includes("camera") || lower.includes("ir")) return "mdi:webcam";
    if (lower.includes("monitor") || lower.includes("u52") || lower.includes("u27") || lower.includes("u32") || lower.includes("u24") || lower.includes("u34") || lower.includes("p27") || lower.includes("p32")) return "mdi:monitor";
    if (lower.includes("dock") || lower.includes("hub") || lower.includes("da3") || lower.includes("wd1") || lower.includes("wd2")) return "mdi:dock-window";
    if (lower.includes("litra") || lower.includes("light") || lower.includes("lamp")) return "mdi:desk-lamp";
    if (lower.includes("receiver")) return "mdi:antenna";
    return "mdi:devices";
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

  // ── Device Popup ─────────────────────────────────────────────

  _showDevicePopup(deviceId) {
    const dev = this._hass.devices?.[deviceId];
    if (!dev) return;

    // Collect entities for this device
    const entities = [];
    if (this._hass.entities) {
      for (const [eid, ent] of Object.entries(this._hass.entities)) {
        if (ent.device_id === deviceId && !ent.disabled_by && !ent.hidden_by) {
          const state = this._hass.states[eid];
          entities.push({ eid, ent, state });
        }
      }
    }

    // Build a set of control suffixes to deduplicate sensors
    const controlSuffixes = new Set();
    entities.forEach(({ eid }) => {
      if (eid.startsWith("number.") || eid.startsWith("select.") || eid.startsWith("switch.")) {
        const suffix = eid.split(".").pop().split("_").slice(-2).join("_");
        controlSuffixes.add(suffix);
      }
    });

    // Group: controls first, then sensors (deduped), skip diagnostics by default
    const controls = entities.filter(({ eid }) =>
      eid.startsWith("light.") || eid.startsWith("number.") ||
      eid.startsWith("select.") || eid.startsWith("switch.") ||
      eid.startsWith("button.") || eid.startsWith("media_player.")
    );
    const sensors = entities.filter(({ eid, ent }) => {
      if (!eid.startsWith("sensor.") && !eid.startsWith("binary_sensor.")) return false;
      if (ent.entity_category === "diagnostic") return false;
      // Skip sensors that duplicate a control (e.g. sensor.red_gain when number.red_gain exists)
      const suffix = eid.split(".").pop().split("_").slice(-2).join("_");
      if (controlSuffixes.has(suffix)) return false;
      return true;
    });

    const deviceName = dev.name || "Device";
    const mfg = dev.manufacturer || "";
    this._popupDeviceName = deviceName; // For _shortName() prefix stripping

    // Resolve image key for popup header
    let popupImageKey = "";
    for (const [domain, identifier] of (dev.identifiers || [])) {
      if (domain === "desk2ha") {
        const parts = identifier.split("_");
        popupImageKey = parts.length > 1 ? parts.slice(1).join("_") : identifier;
        break;
      }
    }
    const popupImgUrl = popupImageKey ? `/desk2ha/images/${encodeURIComponent(popupImageKey)}?v=${CARD_VERSION}` : "";

    let popup = `<div class="d2h-popup-backdrop">
      <div class="d2h-popup">
        <div class="d2h-popup-header">
          ${popupImgUrl ? `<img class="d2h-popup-img" src="${popupImgUrl}" onerror="this.style.display='none'" loading="lazy">` : ""}
          <div>
            <div class="d2h-popup-title">${this._escHtml(deviceName)}</div>
            ${mfg ? `<div class="d2h-popup-subtitle">${this._escHtml(mfg)}</div>` : ""}
          </div>
          <div class="d2h-popup-close" id="d2h-popup-close">✕</div>
        </div>
        <div class="d2h-popup-body">`;

    // Render inline controls
    for (const { eid, state } of controls) {
      if (!state || state.state === "unavailable") continue;
      popup += this._renderControl(eid, state);
    }

    // Render sensor values
    if (sensors.length > 0) {
      popup += `<div class="d2h-popup-divider"></div>`;
      for (const { eid, state } of sensors) {
        if (!state || state.state === "unavailable") continue;
        const name = this._shortName(state);
        const icon = state.attributes?.icon || "mdi:information";
        const val = state.state;
        const unit = state.attributes?.unit_of_measurement || "";
        const display = isNaN(parseFloat(val)) ? val : `${Math.round(parseFloat(val) * 10) / 10}${unit ? " " + unit : ""}`;
        popup += `<div class="d2h-popup-sensor">
          <ha-icon icon="${icon}" style="--mdc-icon-size:18px"></ha-icon>
          <span>${this._escHtml(name)}</span>
          <span class="d2h-popup-sensor-val">${this._escHtml(display)}</span>
        </div>`;
      }
    }

    if (controls.length === 0 && sensors.length === 0) {
      popup += `<div style="padding:20px;color:var(--secondary-text-color);text-align:center">No data available</div>`;
    }

    popup += `</div></div></div>`;

    this._closePopup();
    const container = document.createElement("div");
    container.id = "d2h-popup-container";
    container.innerHTML = popup;
    this.appendChild(container);

    // Bind close
    this.querySelector("#d2h-popup-close")?.addEventListener("click", () => this._closePopup());

    // Bind controls
    this._bindPopupControls();
  }

  _shortName(state) {
    // "U5226KW Brightness" → "Brightness"
    // "Dell Inc. Latitude 5550 CPU Usage" → "CPU Usage"
    // "Red Black Level" → "Red Black Level" (keep color prefix)
    const fn = state?.attributes?.friendly_name || "";
    if (!fn) return "";

    let name = fn;

    // Strip device model prefix (e.g. "U5226KW Brightness" → "Brightness")
    // But keep multi-word names like "Red Gain", "Auto Brightness"
    if (this._popupDeviceName) {
      const devPrefix = this._popupDeviceName + " ";
      if (name.startsWith(devPrefix)) {
        name = name.slice(devPrefix.length);
      }
    }

    return name || fn;
  }

  _renderControl(eid, state) {
    const name = this._shortName(state);
    const icon = state.attributes?.icon || this._defaultIcon(eid);
    const val = state.state;

    // Number → Slider
    if (eid.startsWith("number.")) {
      const min = state.attributes?.min ?? 0;
      const max = state.attributes?.max ?? 100;
      const step = state.attributes?.step ?? 1;
      const unit = state.attributes?.unit_of_measurement || "";
      const numVal = parseFloat(val) || 0;
      return `<div class="d2h-ctrl">
        <div class="d2h-ctrl-header">
          <ha-icon icon="${icon}" style="--mdc-icon-size:18px"></ha-icon>
          <span class="d2h-ctrl-name">${this._escHtml(name)}</span>
          <span class="d2h-ctrl-val" id="val-${eid.replace(/\./g, "_")}">${Math.round(numVal)}${unit ? " " + unit : ""}</span>
        </div>
        <input type="range" class="d2h-slider" data-entity="${eid}" data-domain="number"
               min="${min}" max="${max}" step="${step}" value="${numVal}">
      </div>`;
    }

    // Select → Dropdown
    if (eid.startsWith("select.")) {
      const options = state.attributes?.options || [];
      const optHtml = options.map((o) =>
        `<option value="${this._escHtml(o)}" ${o === val ? "selected" : ""}>${this._escHtml(o)}</option>`
      ).join("");
      return `<div class="d2h-ctrl">
        <div class="d2h-ctrl-header">
          <ha-icon icon="${icon}" style="--mdc-icon-size:18px"></ha-icon>
          <span class="d2h-ctrl-name">${this._escHtml(name)}</span>
        </div>
        <select class="d2h-select" data-entity="${eid}" data-domain="select">${optHtml}</select>
      </div>`;
    }

    // Switch → Toggle
    if (eid.startsWith("switch.")) {
      const isOn = val === "on" || val === "True";
      return `<div class="d2h-ctrl d2h-ctrl-toggle">
        <ha-icon icon="${icon}" style="--mdc-icon-size:18px"></ha-icon>
        <span class="d2h-ctrl-name">${this._escHtml(name)}</span>
        <label class="d2h-toggle">
          <input type="checkbox" data-entity="${eid}" data-domain="switch" ${isOn ? "checked" : ""}>
          <span class="d2h-toggle-slider"></span>
        </label>
      </div>`;
    }

    // Light → Toggle
    if (eid.startsWith("light.")) {
      const isOn = val === "on";
      return `<div class="d2h-ctrl d2h-ctrl-toggle">
        <ha-icon icon="${icon}" style="--mdc-icon-size:18px"></ha-icon>
        <span class="d2h-ctrl-name">${this._escHtml(name)}</span>
        <label class="d2h-toggle">
          <input type="checkbox" data-entity="${eid}" data-domain="light" ${isOn ? "checked" : ""}>
          <span class="d2h-toggle-slider"></span>
        </label>
      </div>`;
    }

    // Button → Action button
    if (eid.startsWith("button.")) {
      return `<div class="d2h-ctrl d2h-ctrl-toggle">
        <ha-icon icon="${icon}" style="--mdc-icon-size:18px"></ha-icon>
        <span class="d2h-ctrl-name">${this._escHtml(name)}</span>
        <button class="d2h-btn" data-entity="${eid}" data-domain="button">Run</button>
      </div>`;
    }

    return "";
  }

  _bindPopupControls() {
    // Sliders (number entities)
    this.querySelectorAll(".d2h-slider").forEach((slider) => {
      const eid = slider.dataset.entity;
      const valLabel = this.querySelector(`#val-${eid.replace(/\./g, "_")}`);
      slider.addEventListener("input", () => {
        if (valLabel) valLabel.textContent = slider.value;
      });
      slider.addEventListener("change", () => {
        this._hass.callService("number", "set_value", {
          entity_id: eid,
          value: parseFloat(slider.value),
        });
      });
    });

    // Selects
    this.querySelectorAll(".d2h-select").forEach((sel) => {
      sel.addEventListener("change", () => {
        this._hass.callService("select", "select_option", {
          entity_id: sel.dataset.entity,
          option: sel.value,
        });
      });
    });

    // Toggles (switches + lights)
    this.querySelectorAll('.d2h-toggle input[type="checkbox"]').forEach((cb) => {
      cb.addEventListener("change", () => {
        const domain = cb.dataset.domain;
        const service = cb.checked ? "turn_on" : "turn_off";
        this._hass.callService(domain, service, { entity_id: cb.dataset.entity });
      });
    });

    // Buttons
    this.querySelectorAll(".d2h-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._hass.callService("button", "press", { entity_id: btn.dataset.entity });
        btn.textContent = "✓";
        setTimeout(() => { btn.textContent = "Run"; }, 1500);
      });
    });
  }

  _defaultIcon(eid) {
    if (eid.startsWith("light.")) return "mdi:lightbulb";
    if (eid.startsWith("switch.")) return "mdi:toggle-switch";
    if (eid.startsWith("number.")) return "mdi:tune";
    if (eid.startsWith("select.")) return "mdi:form-dropdown";
    if (eid.startsWith("button.")) return "mdi:gesture-tap-button";
    if (eid.startsWith("media_player.")) return "mdi:speaker";
    if (eid.startsWith("binary_sensor.")) return "mdi:checkbox-marked-circle";
    if (eid.startsWith("update.")) return "mdi:package-up";
    return "mdi:information";
  }

  _closePopup() {
    const existing = this.querySelector("#d2h-popup-container");
    if (existing) existing.remove();
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
      .d2h-periph-status {
        font-size: 0.8em;
        color: var(--secondary-text-color);
        margin-left: auto;
      }
      .d2h-periph-bat {
        font-size: 0.85em;
        font-weight: 500;
        min-width: 35px;
        text-align: right;
      }
      .d2h-periph-img {
        width: 28px;
        height: 28px;
        object-fit: contain;
        flex-shrink: 0;
        border-radius: 4px;
      }
      .d2h-popup-img {
        width: 48px;
        height: 48px;
        object-fit: contain;
        border-radius: 8px;
        flex-shrink: 0;
      }
      .d2h-clickable {
        cursor: pointer;
        border-radius: 8px;
        padding: 6px 4px;
        transition: background 0.15s;
      }
      .d2h-clickable:hover {
        background: var(--secondary-background-color, rgba(255,255,255,0.05));
      }
      /* Popup */
      .d2h-popup-backdrop {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.6);
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: d2h-fade-in 0.15s ease;
      }
      @keyframes d2h-fade-in {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      .d2h-popup {
        background: var(--card-background-color, #1c1c1c);
        border-radius: 16px;
        width: min(420px, 90vw);
        max-height: 80vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
      }
      .d2h-popup-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px 12px;
        border-bottom: 1px solid var(--divider-color, #333);
      }
      .d2h-popup-title {
        font-size: 1.2em;
        font-weight: 600;
      }
      .d2h-popup-subtitle {
        font-size: 0.8em;
        color: var(--secondary-text-color);
      }
      .d2h-popup-close {
        cursor: pointer;
        font-size: 1.2em;
        padding: 4px 8px;
        border-radius: 8px;
        color: var(--secondary-text-color);
      }
      .d2h-popup-close:hover {
        background: var(--secondary-background-color, rgba(255,255,255,0.1));
      }
      .d2h-popup-body {
        overflow-y: auto;
        padding: 8px 0;
      }
      .d2h-popup-divider {
        height: 1px;
        background: var(--divider-color, #333);
        margin: 8px 20px;
      }
      /* Controls */
      .d2h-ctrl {
        padding: 10px 20px;
      }
      .d2h-ctrl-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
      }
      .d2h-ctrl-name {
        flex: 1;
        font-size: 0.9em;
      }
      .d2h-ctrl-val {
        font-size: 0.85em;
        font-weight: 500;
        color: var(--primary-color);
        min-width: 50px;
        text-align: right;
      }
      .d2h-slider {
        width: 100%;
        height: 6px;
        -webkit-appearance: none;
        appearance: none;
        background: var(--divider-color, #444);
        border-radius: 3px;
        outline: none;
        cursor: pointer;
      }
      .d2h-slider::-webkit-slider-thumb {
        -webkit-appearance: none;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: var(--primary-color);
        cursor: pointer;
      }
      .d2h-select {
        width: 100%;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid var(--divider-color, #444);
        background: var(--secondary-background-color, #2a2a2a);
        color: var(--primary-text-color);
        font-size: 0.9em;
        cursor: pointer;
      }
      .d2h-ctrl-toggle {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .d2h-toggle {
        position: relative;
        width: 42px;
        height: 24px;
        flex-shrink: 0;
      }
      .d2h-toggle input {
        opacity: 0;
        width: 0;
        height: 0;
      }
      .d2h-toggle-slider {
        position: absolute;
        cursor: pointer;
        top: 0; left: 0; right: 0; bottom: 0;
        background: var(--divider-color, #555);
        border-radius: 24px;
        transition: 0.2s;
      }
      .d2h-toggle-slider:before {
        content: "";
        position: absolute;
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background: white;
        border-radius: 50%;
        transition: 0.2s;
      }
      .d2h-toggle input:checked + .d2h-toggle-slider {
        background: var(--primary-color);
      }
      .d2h-toggle input:checked + .d2h-toggle-slider:before {
        transform: translateX(18px);
      }
      .d2h-btn {
        padding: 4px 14px;
        border-radius: 8px;
        border: 1px solid var(--divider-color, #444);
        background: var(--secondary-background-color, #2a2a2a);
        color: var(--primary-text-color);
        cursor: pointer;
        font-size: 0.85em;
        flex-shrink: 0;
      }
      .d2h-btn:hover {
        background: var(--primary-color);
        color: white;
      }
      /* Sensor rows */
      .d2h-popup-sensor {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 20px;
        font-size: 0.85em;
        color: var(--secondary-text-color);
      }
      .d2h-popup-sensor-val {
        margin-left: auto;
        font-weight: 500;
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
    if (!this._rendered) this._render();
  }

  _getDesk2HAEntities() {
    if (!this._hass) return [];
    return Object.keys(this._hass.states)
      .filter((eid) => eid.endsWith("_cpu_usage") && eid.startsWith("sensor.") &&
                       this._hass.states[eid]?.attributes?.friendly_name?.includes("CPU Usage"))
      .sort();
  }

  _render() {
    if (!this._config) return;
    this._rendered = true;
    const entities = this._getDesk2HAEntities();
    const currentEntity = this._config.entity || "";

    let entitySelector;
    if (entities.length > 0) {
      const options = entities.map(
        (eid) => `<option value="${eid}" ${eid === currentEntity ? "selected" : ""}>${eid}</option>`
      ).join("");
      entitySelector = `
        <div style="margin-bottom: 12px;">
          <label style="display:block;font-size:0.85em;margin-bottom:4px;color:var(--secondary-text-color)">
            Desktop (leave empty for auto-discovery)
          </label>
          <select id="d2h-entity-select" style="width:100%;padding:8px;border-radius:4px;border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--primary-text-color)">
            <option value="" ${!currentEntity ? "selected" : ""}>Auto-discover</option>
            ${options}
          </select>
        </div>`;
    } else {
      entitySelector = `
        <div style="margin-bottom: 12px;">
          <ha-textfield
            label="Entity (optional — auto-discovers if empty)"
            value="${currentEntity}"
            style="width: 100%;"
          ></ha-textfield>
        </div>`;
    }

    this.innerHTML = `
      <div style="padding: 16px;">
        ${entitySelector}
        ${this._toggle("show_system", "Show System Gauges")}
        ${this._toggle("show_thermals", "Show Thermals")}
        ${this._toggle("show_battery", "Show Battery")}
        ${this._toggle("show_peripherals", "Show Peripherals")}
        ${this._toggle("show_displays", "Show Displays")}
      </div>
    `;

    // Wire up events
    const select = this.querySelector("#d2h-entity-select");
    if (select) {
      select.addEventListener("change", (e) => this._valueChanged("entity", e.target.value));
    }
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
