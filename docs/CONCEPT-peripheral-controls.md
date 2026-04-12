# Konzept: Erweiterte Peripherie-Datenpunkte und Steuerung

## Ziel

Alle Einstellungen und Datenpunkte, die Dell Display and Peripheral Manager
(DDPM) für die angeschlossene Peripherie anbietet, sollen auch in Home
Assistant sichtbar und steuerbar sein.

## Geräte und ihre Datenpunkte

### 1. Dell Monitor (U5226KW) — DDC/CI

**Bereits implementiert:**
- Helligkeit (%)
- Kontrast (%)
- Input Source (Code)
- Power State (on/off)

**Zusätzlich möglich via DDC/CI VCP Codes:**

| Datenpunkt | VCP Code | HA Entity-Typ | Lesen | Schreiben |
|---|---|---|---|---|
| Helligkeit | 0x10 | `number` (0-100) | ✅ | ✅ |
| Kontrast | 0x12 | `number` (0-100) | ✅ | ✅ |
| Input Source | 0x60 | `select` (Thunderbolt, DP1, DP2, HDMI1, HDMI2) | ✅ | ✅ |
| Lautstärke | 0x62 | `number` (0-100) | ✅ | ✅ |
| Mute | 0x8D | `switch` | ✅ | ✅ |
| Power Mode | 0xD6 | `select` (on, standby, off) | ✅ | ✅ |
| Farbtemperatur | 0x0E | `select` (warm, neutral, cool) | ✅ | ✅ |
| Color Preset | 0x14 | `select` (Standard, Movie, Game, etc.) | ✅ | ✅ |
| OSD Sprache | 0xCC | `select` | ✅ | ✅ |
| Firmware Version | 0xC9 | `sensor` | ✅ | ❌ |
| Betriebsstunden | 0xC0 | `sensor` | ✅ | ❌ |
| USB-C Prioritization | - | `select` (charging, data) | ✅ | ✅ |
| KVM Switch | - | `select` (PC1-PC4) | ✅ | ✅ |
| Picture-by-Picture | - | `switch` + `select` | ✅ | ✅ |

**Automatisierungs-Ideen:**
- "Wenn ich den Arbeitsplatz verlasse → Monitor auf Standby"
- "Abends automatisch Helligkeit auf 30%"
- "KVM auf PC2 umschalten wenn Arbeitslaptop angedockt"
- "Input auf HDMI2 für Gaming-PC am Abend"

### 2. Dell Webcam (WB7022) — UVC Extension Units

**Steuerbar via USB Video Class (UVC):**

| Datenpunkt | UVC Control | HA Entity-Typ | Lesen | Schreiben |
|---|---|---|---|---|
| Helligkeit | CT_BRIGHTNESS | `number` | ✅ | ✅ |
| Kontrast | CT_CONTRAST | `number` | ✅ | ✅ |
| Sättigung | CT_SATURATION | `number` | ✅ | ✅ |
| Schärfe | CT_SHARPNESS | `number` | ✅ | ✅ |
| Weißabgleich (auto/manuell) | CT_WHITE_BALANCE | `select` | ✅ | ✅ |
| Weißabgleich Temperatur | CT_WB_TEMPERATURE | `number` (2500-6500K) | ✅ | ✅ |
| Zoom | CT_ZOOM | `number` | ✅ | ✅ |
| Pan/Tilt | CT_PANTILT | `number` | ✅ | ✅ |
| HDR | Extension Unit | `switch` | ✅ | ✅ |
| AI Auto-Framing | Extension Unit | `switch` | ✅ | ✅ |
| Field of View | Extension Unit | `select` (65°/78°/90°) | ✅ | ✅ |
| Anti-Flicker | Extension Unit | `select` (auto/50Hz/60Hz) | ✅ | ✅ |
| Noise Reduction | Extension Unit | `switch` | ✅ | ✅ |
| Presence Detection | Extension Unit | `binary_sensor` + `switch` | ✅ | ✅ |
| Privacy Shutter | Extension Unit | `binary_sensor` | ✅ | ❌ |
| Mikrofon Mute | Extension Unit | `switch` | ✅ | ✅ |
| LED Indikator | Extension Unit | `switch` | ✅ | ✅ |

**Automatisierungs-Ideen:**
- "Presence Detection als Trigger für Raum-Beleuchtung"
- "Webcam AI-Framing automatisch bei Teams/Zoom Meetings an"
- "HDR an wenn Tageslicht, aus bei Kunstlicht"
- "Mikrofon auto-mute wenn Tür offen"

### 3. Dell Keyboard (KB900) — BLE GATT + HID

**Bereits implementiert:**
- Akku-Level (%)
- Verbindungsstatus (connected/disconnected)

**Zusätzlich möglich:**

| Datenpunkt | Quelle | HA Entity-Typ | Lesen | Schreiben |
|---|---|---|---|---|
| Akku-Level | GATT 0x2A19 | `sensor` | ✅ | ❌ |
| Lade-Status | GATT 0x2A1B | `binary_sensor` | ✅ | ❌ |
| Hintergrundbeleuchtung | HID Feature Report | `number` (0-3) | ✅ | ✅ |
| Hintergrundbeleuchtung Auto | HID Feature Report | `switch` | ✅ | ✅ |
| Tastendruck-Aktivität | HID Input Report | `binary_sensor` | ✅ | ❌ |
| Collaboration-Tasten | HID Input Report | `event` (mute/camera/share) | ✅ | ❌ |
| Lock-Taste Status | HID Feature Report | `binary_sensor` | ✅ | ❌ |
| Firmware Version | GATT 0x2A26 | `sensor` | ✅ | ❌ |
| Aktives Gerät (1/2/3) | HID Feature Report | `select` | ✅ | ✅ |

**Automatisierungs-Ideen:**
- "Wenn Collaboration Mute-Taste gedrückt → HA Mute-Automation triggern"
- "Keyboard Hintergrundbeleuchtung aus nach 22 Uhr"
- "Keyboard-Akku unter 10% → Notification an Handy"

### 4. Dell Mouse (MS900) — BLE GATT + HID

**Bereits implementiert:**
- Akku-Level (%)
- Verbindungsstatus (connected/disconnected)

**Zusätzlich möglich:**

| Datenpunkt | Quelle | HA Entity-Typ | Lesen | Schreiben |
|---|---|---|---|---|
| Akku-Level | GATT 0x2A19 | `sensor` | ✅ | ❌ |
| Lade-Status | GATT 0x2A1B | `binary_sensor` | ✅ | ❌ |
| DPI Stufe | HID Feature Report | `select` (800/1200/1600/2400/4000) | ✅ | ✅ |
| Scroll-Modus | HID Feature Report | `select` (smooth/stepped) | ✅ | ✅ |
| Scroll-Geschwindigkeit | HID Feature Report | `number` | ✅ | ✅ |
| Firmware Version | GATT 0x2A26 | `sensor` | ✅ | ❌ |
| Aktives Gerät (1/2/3) | HID Feature Report | `select` | ✅ | ✅ |

### 5. Weitere Geräte (Zukunft)

| Gerät | Schnittstelle | Datenpunkte |
|---|---|---|
| **Dell Dock (WD22TB4, WD19)** | USB-C / Thunderbolt | Firmware, Temperatur, angeschlossene Geräte, Ethernet-Status, Display-Konfiguration |
| **Dell Headset** | BLE GATT | Akku L/R, ANC Mode, Wear Detection, Mikrofon-Mute, EQ Preset |
| **Dell Soundbar** | USB Audio | Lautstärke, Mute, EQ |
| **Dell Touchpen** | BLE GATT | Akku, Druckempfindlichkeit, Tastenbelegung |
| **Dell Speakerphone** | USB Audio + HID | Lautstärke, Mikrofon-Mute, LED-Ring, Akku |

## Technische Umsetzung

### Architektur

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  UVC Camera │     │  DDC/CI      │     │  BLE GATT       │
│  Control    │     │  Monitor     │     │  Peripherals    │
│  (libusb)   │     │  (monitorctl)│     │  (WinRT/bleak)  │
└──────┬──────┘     └──────┬───────┘     └────────┬────────┘
       │                   │                      │
       ▼                   ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│                    Dell HA Agent                         │
│  Collectors: webcam_uvc | ddcci_monitor | bt_peripheral  │
│  + windows_base | windows_dcm                            │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP + MQTT
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Home Assistant                          │
│  sensor | number | select | switch | binary_sensor       │
│  button (Kommandos) | event (Tastendruck)               │
└─────────────────────────────────────────────────────────┘
```

### Phase 1: Monitor-Steuerung (DDC/CI)

**Aufwand: Klein — monitorcontrol kann schon schreiben**

1. Agent: `ddcci_monitor` Collector erweitern mit `set_brightness()`,
   `set_input_source()`, `set_contrast()`
2. Agent: Neuer `/v1/commands` Endpoint für Steuerungsbefehle
3. Integration: `number.py` Entity für Helligkeit/Kontrast
4. Integration: `select.py` Entity für Input Source
5. Integration: `switch.py` Entity für Power/Mute

### Phase 2: Webcam-Steuerung (UVC)

**Aufwand: Mittel — braucht UVC Extension Unit Zugriff**

1. Agent: Neuer Collector `webcam_uvc.py` mit `python-uvc` oder `pyuvc`
2. Standard UVC Controls (Helligkeit, Kontrast, etc.) über
   `v4l2-ctl` (Linux) oder DirectShow (Windows)
3. Dell-spezifische Extension Units für HDR, AI-Framing,
   Presence Detection (reverse-engineered aus DDPM)
4. Integration: Entsprechende HA Entities

### Phase 3: BLE Peripheral-Steuerung

**Aufwand: Mittel — braucht HID Feature Reports**

1. Agent: `bt_peripheral` Collector erweitern um GATT Characteristic Reads
   für Firmware, Charge Status, etc.
2. HID Feature Reports für Hintergrundbeleuchtung, DPI, etc. über
   Windows HID API (`hid` Python Library)
3. Integration: Entities für Beleuchtung, DPI, etc.

### Phase 4: Dock und weitere Geräte

**Aufwand: Groß — Dock-API ist proprietär**

1. Dell Dock Communication über USB Vendor-spezifische Requests
2. Oder: Auslesen der Dock-Daten über DDPM's interne Kommunikation

## Prioritäten

| Prio | Feature | Aufwand | Nutzen |
|------|---------|---------|--------|
| 1 | Monitor Input-Umschaltung | Klein | Hoch — KVM über HA steuern |
| 2 | Monitor Helligkeit als `number` | Klein | Hoch — Automatisierungen |
| 3 | Webcam Presence Detection | Mittel | Hoch — Raumsensor |
| 4 | Webcam HDR/AI-Framing Toggle | Mittel | Mittel — Meeting-Setup |
| 5 | Keyboard Backlight | Mittel | Mittel — Ambiente |
| 6 | Mouse DPI | Mittel | Niedrig — selten geändert |
| 7 | Dock-Telemetrie | Groß | Mittel — Nischennutzen |

## DDPM Reverse-Engineering Strategie

DDPM kommuniziert mit den Geräten über:
1. **DDC/CI** für Monitore (offener Standard, gut dokumentiert)
2. **UVC Extension Units** für Webcams (Dell-proprietär, aber
   per USB-Sniffer analysierbar)
3. **BLE GATT + HID** für Peripherie (teilweise offen, teilweise
   Dell-proprietäre GATT Services)
4. **USB Vendor Requests** für Docks (proprietär, am schwierigsten)

Für UVC Extension Units: `Wireshark` mit USB-Capture auf den
DDPM-Prozess anwenden, während Einstellungen geändert werden.
Die Vendor/Product IDs und Extension Unit GUIDs sind dann sichtbar.

## Nächste Schritte

1. Monitor Input-Umschaltung als `select` Entity implementieren
2. Monitor Helligkeit als steuerbare `number` Entity
3. Webcam Presence Detection als `binary_sensor`
4. Konzept mit Tim besprechen und Prioritäten validieren
