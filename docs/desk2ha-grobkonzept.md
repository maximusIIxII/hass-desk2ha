# Desk2HA — Grobkonzept (High-Level Concept)

Version: 0.1 Draft — 2026-04-08
Basis: Vendor-Analyse (`desk2ha-vendor-analysis.md`), Dell HA Architektur (`ARCHITECTURE.md`), Marktrecherche

---

## 1. Vision

**Desk2HA** macht den Computer-Arbeitsplatz — Host-Rechner UND alle Peripheriegeraete — als vollstaendiges Geraeteensemble in Home Assistant sichtbar und steuerbar.

Nicht nur Dell, nicht nur Laptops: jeder Hersteller, jede Geraeteklasse die am Schreibtisch steht.

### Was Desk2HA NICHT ist

- Kein System-Monitoring-Tool (dafuer gibt es Glances, LibreHWMonitor, Prometheus)
- Kein Remote-Desktop oder KVM
- Kein Geraetemanagement/Fleet-Tool (das machen Dell/HP/Lenovo Cloud-Konsolen)
- Kein RGB-Controller (dafuer gibt es OpenRGB)

### Was Desk2HA IST

- Ein **Arbeitsplatz-zu-Smart-Home-Bridge**: der Schreibtisch wird Teil des Smart Home
- Automatisierung ueber HA: "Wenn ich mich am PC anmelde, Schreibtischlampe an, Monitor-Helligkeit auf Tagesprofil, Heizung runter"
- Peripherie-Status: "Maus-Batterie unter 20% → HA-Notification aufs Handy"
- Energie-Monitoring: "Wie viel verbraucht mein Arbeitsplatz (Rechner + Monitor + Dock) pro Tag?"
- Steuerung: Monitor-Input umschalten, Helligkeit aendern, Webcam-Preset waehlen — alles ueber HA-Dashboard oder Automation

---

## 2. Scope — Geraeteklassen und Feature-Tiers

### 2.1 Geraeteklassen

| Klasse | Beispiele | Primaeres Protokoll |
|--------|-----------|---------------------|
| **Host** | Laptop, Desktop, Workstation | Agent (WMI/sysfs/ioreg) |
| **Monitor** | Jeder DDC/CI-faehige Monitor | DDC/CI (MCCS) |
| **Webcam** | USB-Webcams aller Hersteller | UVC |
| **Tastatur** | USB/BLE Keyboards | HID Battery, BLE GATT |
| **Maus** | USB/BLE Mice | HID Battery, BLE GATT |
| **Headset** | USB/BLE Headsets | HeadsetControl, BLE GATT |
| **Dock** | USB-C/TB Docking Stations | USB PD Info, Agent-seitig |
| **Lautsprecher** | USB/BLE Speaker | HID Battery, BLE GATT |

### 2.2 Feature-Tiers

Jedes Geraet hat Features auf verschiedenen Ebenen:

| Tier | Beschreibung | Voraussetzung | Beispiel |
|------|-------------|---------------|----------|
| **Generic** | Funktioniert herstellerunabhaengig via Standardprotokoll | Nur Desk2HA Agent | Monitor-Helligkeit (DDC/CI), Webcam-Bild (UVC), Batterie (BLE GATT) |
| **Enhanced** | Zusaetzliche Features via herstellerspezifisches Protokoll | Agent + Vendor-Plugin | Logitech DPI (HID++), Dell DCM Thermals (WMI), HP BIOS (WMI) |
| **Software** | Features die eine Vendor-Software auf dem Host voraussetzen | Vendor-App installiert | SteelSeries Sonar EQ (REST API), Corsair iCUE RGB |

Desk2HA liefert im **Generic Tier** sofort Wert fuer JEDEN Arbeitsplatz. Enhanced und Software Tiers sind opt-in Erweiterungen.

---

## 3. Architektur — Zwei Komponenten

Die bewaehrte Trennung aus Dell HA bleibt: **Agent auf dem Host** + **Integration in HA**. Beide unabhaengig releasebar, verbunden durch einen API-Vertrag.

```
┌─────────────────────────────────────────────────────────┐
│                    Home Assistant                         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │             hass-desk2ha Integration                │  │
│  │                                                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │  │
│  │  │ Agent    │  │ Agent    │  │ Network          │ │  │
│  │  │ HTTP Src │  │ MQTT Src │  │ Discovery Src    │ │  │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │  │
│  │       │              │                  │           │  │
│  │  ┌────▼──────────────▼──────────────────▼─────────┐│  │
│  │  │         DataUpdateCoordinator                  ││  │
│  │  │    Identity Resolution + Device Merging        ││  │
│  │  └────────────────────┬───────────────────────────┘│  │
│  │                       │                             │  │
│  │  ┌────────────────────▼───────────────────────────┐│  │
│  │  │    Entity Platform (sensor, binary_sensor,     ││  │
│  │  │    number, select, button, switch)             ││  │
│  │  └────────────────────────────────────────────────┘│  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

      ▲ HTTP Poll        ▲ MQTT Push          ▲ ARP/mDNS/SSDP
      │                  │                    │
      │    ┌─────────────┴────────────┐       │
      │    │        MQTT Broker       │       │
      │    └─────────────▲────────────┘       │
      │                  │                    │
┌─────┴──────────────────┴────────────────────┴───────────┐
│                   desk2ha-agent                           │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Collector Framework                   │    │
│  │                                                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │   │
│  │  │ Platform │ │ Generic  │ │ Vendor   │          │    │
│  │  │Collectors│ │Collectors│ │ Plugins  │          │    │
│  │  │          │ │          │ │          │          │    │
│  │  │ Windows  │ │ DDC/CI   │ │ Logitech │          │   │
│  │  │ Linux    │ │ UVC      │ │ Dell DCM │          │   │
│  │  │ macOS    │ │ BLE GATT │ │ HP WMI   │          │   │
│  │  │          │ │ HID Batt │ │ Lenovo   │          │   │
│  │  │          │ │ HeadsetC │ │ Corsair  │          │   │
│  │  │          │ │ USB PD   │ │ SteelS.  │          │   │
│  │  └──────────┘ └──────────┘ └──────────┘          │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │HTTP Transp│ │MQTT Transp│ │Prometheus│               │
│  └──────────┘  └──────────┘  └──────────┘               │
└──────────────────────────────────────────────────────────┘
```

### 3.1 desk2ha-agent (Host-Seite)

Laeuft auf dem Endgeraet. Sammelt Daten, bietet Steuerung, publiziert via HTTP und/oder MQTT.

**Dreischichtiges Collector-Modell:**

1. **Platform Collectors** — OS-spezifisch (Windows WMI, Linux sysfs, macOS ioreg). Liefern Host-Telemetrie: CPU, RAM, Disk, Battery, GPU, OS-Info.

2. **Generic Collectors** — Standardprotokolle, herstellerunabhaengig:
   - `ddcci` — Monitor-Steuerung via DDC/CI (monitorcontrol)
   - `uvc` — Webcam-Steuerung via UVC
   - `ble_battery` — BLE GATT Battery Service 0x180F
   - `hid_battery` — USB HID Power Device Page 0x85
   - `headsetcontrol` — HeadsetControl Library (Logitech/SS/Corsair/HyperX Headsets)
   - `usb_pd` — USB Power Delivery Info (Dock-Leistung, Ladestatus)

3. **Vendor Plugins** — Herstellerspezifische Erweiterungen (optional):
   - `dell_dcm` — Dell Command | Monitor WMI
   - `dell_peripheral` — Dell Peripheral Manager DB
   - `hp_wmi` — HP InstrumentedBIOS WMI
   - `hp_cmsl` — HP CMSL PowerShell Bridge
   - `lenovo_wmi` — Lenovo Battery/Thermal WMI
   - `logitech_hidpp` — Logitech HID++ 2.0 (Battery, DPI, Backlight)
   - `corsair_icue` — Corsair iCUE SDK Bridge
   - `steelseries_sonar` — SteelSeries Sonar REST API

**Plugin-Discovery:**
Der Agent erkennt automatisch, welche Vendor-Plugins sinnvoll sind:
- Prueft OS (Windows/Linux/macOS)
- Prueft WMI-Namespaces (Dell DCIM, HP InstrumentedBIOS, Lenovo)
- Prueft angeschlossene USB-Geraete (Vendor IDs: Logitech 046D, Corsair 1B1C, SteelSeries 1038, etc.)
- Prueft installierte Software (DCM, iCUE, SteelSeries GG)
- Aktiviert nur relevante Plugins → kein Overhead auf Nicht-Dell-Maschinen

### 3.2 hass-desk2ha (HA-Seite)

Custom Component fuer Home Assistant (HACS → spaeter Core).

**Aenderungen gegenueber hass-dell:**
- Domain: `desk2ha` statt `dell`
- Nicht mehr Dell-spezifisch: Identity Resolution arbeitet mit generischen Identifiern (Serial, MAC, USB-ID) statt nur Service Tag
- Device Registry: `manufacturer` kommt vom Agent (nicht hardcoded "Dell Inc.")
- OUI-Datenbank bleibt, wird aber breiter (nicht nur Dell OUIs)
- Zeroconf Service: `_desk2ha._tcp.local.` statt `_dell-agent._tcp.local.`

**Gleich bleibt:**
- DataUpdateCoordinator-Pattern
- Source-Plugin-Architektur (agent_http, agent_mqtt, network_discovery)
- Config Flow UI
- Dual-Transport (HTTP + MQTT)
- Opaque device_key vom Agent
- Entity-Lifecycle ueber Coordinator

---

## 4. Geraete-Modell (Device Taxonomy)

### 4.1 Device Hierarchy

```
Workspace (logical group)
├── Host: "Markus Precision 5770"
│   ├── [via_device] Monitor: "Dell U3423WE (Serial: ABC123)"
│   ├── [via_device] Monitor: "LG 27UK850 (Serial: DEF456)"
│   ├── [via_device] Webcam: "Logitech MX Brio"
│   ├── [via_device] Keyboard: "Logitech MX Keys S"
│   ├── [via_device] Mouse: "Logitech MX Master 3S"
│   ├── [via_device] Headset: "Jabra Evolve2 75"
│   └── [via_device] Dock: "Dell WD19TBS"
└── Host: "Markus MacBook Pro 14"
    ├── [via_device] Monitor: "Dell U3423WE (Serial: ABC123)"  ← same monitor, shared
    └── [via_device] Keyboard: "Apple Magic Keyboard"
```

- Jedes Peripheriegeraet ist `via_device` dem Host zugeordnet, an dem es gerade haengt
- Monitore koennen an mehreren Hosts haengen (KVM) — `via_device` zeigt den aktiven Host
- Wenn ein Peripheriegeraet den Host wechselt (z.B. Logitech Flow), updated sich `via_device`

### 4.2 Device Identity

| Geraeteklasse | Primaere ID | Fallback ID |
|---------------|------------|-------------|
| Host | Service Tag / DMI Serial | MAC Address |
| Monitor | EDID Serial | DDC/CI Model + Index |
| Webcam | USB Serial + VID:PID | USB Port Path |
| Tastatur | USB/BLE Serial | VID:PID + Receiver Slot |
| Maus | USB/BLE Serial | VID:PID + Receiver Slot |
| Headset | USB Serial | VID:PID |
| Dock | USB Serial + VID:PID | Thunderbolt UUID |

### 4.3 Device Key Format

Erweiterung des bestehenden Formats:

```
ST-{service_tag}          — Host mit Service Tag (Dell/Lenovo/HP)
SN-{serial}               — Host mit DMI Serial (generisch)
MAC-{mac_nocolons}        — Host nur mit MAC
MON-{edid_serial}         — Monitor mit EDID Serial
USB-{vid}_{pid}_{serial}  — USB-Peripherie mit Serial
BLE-{mac_nocolons}        — BLE-Peripherie
HOST-{hostname_slug}      — Last-Resort Fallback
```

---

## 5. API-Vertrag (OpenAPI Evolution)

### 5.1 Erweiterte Metric Categories

Bisherige Dell HA Kategorien plus neue:

| Category | Inhalte | Quelle |
|----------|---------|--------|
| `system` | CPU, RAM, Disk, OS | Platform Collector |
| `battery` | Charge %, Health, Power Source | Platform Collector |
| `thermal` | CPU/GPU Temp, Fan RPM | Platform + Vendor |
| `display` | Brightness, Contrast, Input, Power | DDC/CI Collector |
| `webcam` | Brightness, Contrast, WB, FOV | UVC Collector |
| `peripheral` | Battery %, Connection Type, FW Version | Generic + Vendor |
| `audio` | Headset Battery, Sidetone Level | HeadsetControl + Vendor |
| `dock` | USB PD Watt, Connected Ports | USB PD Collector |
| `power` | AC Adapter Watt, System Power Draw | Platform + Vendor |
| `network` | WiFi RSSI, Ethernet Speed | Platform Collector |

### 5.2 Commands (Erweitert)

| Command | Target | Protokoll |
|---------|--------|-----------|
| `display.set_brightness` | Monitor | DDC/CI |
| `display.set_contrast` | Monitor | DDC/CI |
| `display.set_input` | Monitor | DDC/CI |
| `display.set_power` | Monitor | DDC/CI |
| `webcam.set_brightness` | Webcam | UVC |
| `webcam.set_white_balance` | Webcam | UVC |
| `webcam.set_fov` | Webcam | UVC |
| `peripheral.set_dpi` | Maus | Vendor (HID++) |
| `peripheral.set_backlight` | Tastatur | Vendor (HID++) |
| `audio.set_sidetone` | Headset | HeadsetControl |
| `audio.set_led` | Headset | HeadsetControl |
| `host.set_thermal_profile` | Host | Vendor (DCM/HP/Lenovo WMI) |
| `host.set_battery_mode` | Host | Vendor (DCM/HP/Lenovo WMI) |

Alle Commands bleiben async (202 + command_id) wie in Dell HA.

---

## 6. Was wird uebernommen, was aendert sich

### Direkt uebernommen aus Dell HA (bewaehrt)

| Komponente | Aenderungen |
|------------|-------------|
| HTTP Transport (aiohttp) | Keine — funktioniert |
| MQTT Transport + HA Discovery | Topic-Prefix `desk2ha/` statt `dell/` |
| OpenAPI-basiertes Modell (Pydantic) | Erweitert, nicht ersetzt |
| DataUpdateCoordinator Pattern | Keine |
| Config Flow | Erweitert (Vendor-Erkennung) |
| Identity Resolution Logik | Erweitert (mehr ID-Typen) |
| Async Command Pattern (202) | Keine |
| NSSM Windows Service | Service-Name `Desk2HAAgent` |
| Tray Helper | Rebranding |
| DDC/CI Monitor Collector | Keine — bereits herstellerunabhaengig |
| UVC Webcam Collector | Keine — bereits herstellerunabhaengig |
| Log Rotation, Graceful Shutdown | Keine |

### Neu zu entwickeln

| Komponente | Aufwand | Prioritaet |
|------------|---------|------------|
| Collector Plugin-System (Auto-Discovery) | Mittel | Phase 1 |
| BLE GATT Battery Collector | Mittel | Phase 1 |
| HID Battery Collector (USB) | Klein | Phase 1 |
| Logitech HID++ Plugin | Gross | Phase 2 |
| HP WMI Plugin | Mittel | Phase 2 |
| Lenovo WMI Plugin | Mittel | Phase 2 |
| HeadsetControl Integration | Klein | Phase 2 |
| USB PD Dock Collector | Mittel | Phase 3 |
| Corsair iCUE Bridge | Klein | Phase 3 |
| SteelSeries Sonar Bridge | Klein | Phase 3 |
| Multi-Host Device Tracking | Gross | Phase 3 |
| Erweiterte HA Card (Multi-Device) | Mittel | Phase 2 |

---

## 7. Phasenplan

### Phase 1 — Foundation (v0.1.0)

**Ziel:** Lauffaehige Multi-Vendor-Basis, sofort nutzbar fuer jeden Arbeitsplatz.

- Neues Repo `desk2ha-agent` mit refactored Collector-Framework
- Neues Repo `hass-desk2ha` mit erweiterter Identity Resolution
- Platform Collectors portiert (Windows, Linux, macOS)
- Generic Collectors: DDC/CI, UVC, HID Battery, BLE Battery
- Erweiterte OpenAPI Spec (`/v2/` oder additive `/v1/` Extension)
- Config Flow: "Add Workspace" → Agent-URL oder Auto-Discovery
- Grundlegende HA Card (Host + Peripherie-Liste)
- HACS-kompatibel ab Tag 1

**Ergebnis:** Jeder Monitor, jede Webcam, jedes USB-Geraet mit Standard-Batterie wird erkannt — unabhaengig vom Hersteller.

### Phase 2 — Vendor Intelligence (v0.2.0)

**Ziel:** Herstellerspezifische Tiefe fuer die grossen Oekosysteme.

- Vendor Plugin System mit Auto-Detection
- Logitech HID++ Plugin (Battery, DPI, Backlight — groesstes Oekosystem)
- Dell DCM Plugin (portiert aus dell-ha-agent)
- HP WMI + CMSL Plugin
- Lenovo WMI Plugin
- HeadsetControl Plugin (multi-vendor Headset-Support)
- Erweiterte HA Card mit Vendor-spezifischen Controls
- Peripherie-Automations-Beispiele in Doku

**Ergebnis:** Logitech-Nutzer sehen DPI und Backlight, Dell-Nutzer Thermals und Fan-Kurven, HP-Nutzer BIOS-Settings.

### Phase 3 — Advanced Features (v0.3.0+)

**Ziel:** Komplexere Szenarien und Nischen-Oekosysteme.

- Multi-Host Device Tracking (Monitor/Peripherie wechselt zwischen Hosts)
- USB PD Dock Collector (Lade-Leistung, Port-Belegung)
- Corsair iCUE Bridge
- SteelSeries Sonar Bridge
- Energy Dashboard Integration (Arbeitsplatz-Verbrauch als HA Energy Entity)
- Workspace Automations (HA Blueprints: "Arbeitsplatz Morgenroutine")
- HA Core Contribution vorbereiten

---

## 8. Technische Entscheidungen

### E1. Neue Repos, kein Rename

`dell-ha-agent` und `hass-dell` bleiben als stabile Dell-only-Version erhalten. Neue Repos `desk2ha-agent` und `hass-desk2ha`. Gruende:
- HA Domain `dell` ist in Entity-IDs, MQTT Topics, Device Registry eingebrannt
- Sauberer Neustart ermoeglicht besseres API-Design
- Dell HA bleibt fuer existierende Nutzer funktional

### E2. Agent bleibt Pflicht fuer Peripherie-Telemetrie

HA allein kann keine USB-HID-Geraete oder BLE-Peripherie lesen — das muss ein Prozess auf dem Host tun. Der Agent ist die Bridge. Ohne Agent: nur Network Discovery (Praesenz).

### E3. Vendor Plugins sind lazy-loaded

Vendor-spezifischer Code wird nur importiert, wenn der Agent erkennt, dass relevante Hardware/Software vorhanden ist. Kein `import logitech_hidpp` auf einer HP-Maschine ohne Logitech-Geraete.

### E4. HeadsetControl als primaerer Headset-Weg

HeadsetControl (C-Library, GPL v3) deckt Logitech, SteelSeries, Corsair, HyperX Headsets ab. Besser als 4 separate Vendor-Implementierungen. Jabra bleibt problematisch (kein API fuer Battery/EQ).

### E5. BLE erfordert Host-Bluetooth

BLE GATT Battery Reading setzt voraus, dass der Host Bluetooth hat UND der Agent Zugriff darauf bekommt. Unter Windows: `winrt` BLE API. Unter Linux: `bleak`. Opt-in per Config, da BLE-Scanning Privacy-Implikationen hat.

### E6. Kein Cloud, kein Phone-Home

Wie bei Dell HA: alles lokal. Keine Vendor-Cloud-APIs. Keine Analytics. Keine Telemetrie ausserhalb LAN.

### E7. OpenAPI Spec bleibt der Vertrag

Die OpenAPI Spec wird erweitert (neue Metric Categories, neue Device Types), aber das Grundprinzip bleibt: Spec first, dann Codegen, dann Implementation.

### E8. Python bleibt

Kein Sprachwechsel. Python fuer Agent und Integration. Gruende:
- HA ist Python
- Alle relevanten Libraries (monitorcontrol, bleak, paho-mqtt, hidapi) haben Python-Bindings
- HeadsetControl ist C, aber via subprocess/ctypes einbindbar
- HP CMSL ist PowerShell, aber via subprocess aufrufbar
- Bestehendes Team-Wissen

---

## 9. Abgrenzung — Was Desk2HA NICHT uebernimmt

| Feature | Grund | Alternative |
|---------|-------|-------------|
| RGB-Steuerung | OpenRGB macht das besser, eigene HA Integration | OpenRGB + HA OpenRGB |
| Fleet Management | Vendor-Cloud, nicht lokal moeglich | Dell/HP/Lenovo Cloud-Konsolen |
| Button-Remapping | Per-Vendor-Software noetig, hohe Komplexitaet, wenig HA-Nutzen | Options+, G HUB, etc. |
| Audio-EQ/ANC | Nur wenige APIs (SteelSeries Sonar), sehr nischig | Native Vendor-Apps |
| BIOS-Updates | Sicherheitskritisch, nicht remote automatisieren | Vendor-Tools |
| Remote Desktop/KVM | Anderes Problemfeld | RDP, VNC, etc. |
| Corporate Geraete ohne Admin | Kein Agent installierbar | IT-Abteilung |

**Ausnahme-Kandidaten fuer spaeter:** Sidetone-Steuerung (HeadsetControl kann's), Thermal-Profile umschalten (Dell/HP/Lenovo WMI kann's, HA-Automation-Nutzen hoch).

---

## 10. Zusammenfassung — Warum Desk2HA

| Aspekt | Status Quo | Mit Desk2HA |
|--------|-----------|-------------|
| Monitor-Helligkeit | Manuell am Monitor oder Vendor-App | HA-Automation: abends dimmen, morgens aufhellen |
| Maus-Batterie | Zufaellig bemerkt wenn leer | HA-Notification bei 20% |
| Arbeitsplatz-Praesenz | Smart Home weiss nicht ob ich am PC sitze | Agent meldet aktive Session → Licht/Heizung reagiert |
| Energie-Verbrauch | Unbekannt | Rechner + Monitor + Dock als HA Energy Entity |
| Multi-Monitor-Setup | Jeden Monitor einzeln einstellen | Eine HA-Automation steuert alle gleichzeitig |
| Peripherie-Firmware | Manuell pruefen | HA zeigt FW-Versionen, Notification bei Updates |

**Desk2HA schliesst die Luecke zwischen Computer-Arbeitsplatz und Smart Home.**

---

*Naechster Schritt: Freigabe durch User → Feinkonzept (detaillierte API-Spec, Entity-Definitionen, Collector-Interfaces, Config-Flow-Design)*
