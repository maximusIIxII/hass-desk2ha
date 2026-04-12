# Desk2HA — Vendor Tool Feature Analysis

Research date: 2026-04-08. Basis for the Desk2HA multi-vendor integration scope.

---

## 1. Dell Display and Peripheral Manager (DDPM)

### Monitor Management (DDC/CI)
| Feature | Protocol | R/W |
|---------|----------|-----|
| Brightness | DDC/CI VCP 0x10 | RW |
| Contrast | DDC/CI VCP 0x12 | RW |
| Input Source | DDC/CI VCP 0x60 | RW |
| Power State | DDC/CI VCP 0xD6 | RW |
| Color Preset | DDC/CI VCP 0x14 / proprietary | RW |
| Brightness/Contrast Scheduling | DDC/CI + app logic | RW |
| Easy Arrange (window layout) | Windows API | RW |
| Easy Arrange Memory (restore on reconnect) | Windows API + state | RW |
| USB KVM (share KB/mouse via USB) | USB hub + DDC/CI | RW |
| Network KVM (share over LAN) | Proprietary Dell network | RW |
| Monitor Asset Info (model, serial, FW) | EDID + DDC/CI | R |
| Resolution/Refresh Rate | EDID / Windows API | R |

### Keyboard
| Feature | Protocol | R/W |
|---------|----------|-----|
| Collaboration Keys (Teams/Zoom mute, share, chat) | HID + Dell proprietary | RW |
| Custom Button Actions | HID + Dell proprietary | RW |
| Copilot Key Remap | HID + Dell proprietary | RW |
| Backlight Level + Timeout | HID (USB/BLE) + Dell proprietary | RW |
| Battery Level | HID battery report | R |
| Firmware Version | USB descriptor | R |
| Multi-Device Pairing | BLE / Dell RF | R |

### Mouse
| Feature | Protocol | R/W |
|---------|----------|-----|
| DPI / Tracking Speed | HID + Dell proprietary | RW |
| Button Assignment | HID + Dell proprietary | RW |
| Scroll Behavior | HID + Dell proprietary | RW |
| Battery Level | HID battery report | R |
| Firmware Version | USB descriptor | R |

### Webcam (UVC)
| Feature | Protocol | R/W |
|---------|----------|-----|
| Brightness / Contrast / Saturation / Sharpness | UVC | RW |
| White Balance (auto/manual) | UVC | RW |
| Anti-Flicker (50/60Hz) | UVC | RW |
| FOV / Zoom / Pan | UVC | RW |
| HDR Toggle | UVC / proprietary extension | RW |
| AI Auto Framing | Proprietary Dell firmware | RW |
| Video Presets (profiles) | App-level UVC sets | RW |
| Firmware Version | USB descriptor | R |

### Audio (Headsets, Speakers)
| Feature | Protocol | R/W |
|---------|----------|-----|
| Equalizer (multi-band) | USB HID / proprietary | RW |
| Audio Presets (Collaboration/Multimedia) | USB HID / proprietary | RW |
| AI Mic Noise Cancellation | Proprietary Dell firmware | RW |
| ANC Control (on/off/levels) | USB HID / BLE + proprietary | RW |
| Sidetone | USB HID / proprietary | RW |
| Battery Level | HID / BLE | R |

### Dock (Dell Pro Smart Docks)
| Feature | Protocol | R/W |
|---------|----------|-----|
| Firmware Update (scheduled) | Proprietary Dell cloud/USB | RW |
| Fleet Policy Management | Dell cloud console | RW |
| SSO via Intune | OAuth/SAML | RW |
| Real-Time Telemetry | Proprietary Dell cloud | R |
| Asset Tracking | Proprietary Dell cloud | R |

### Stylus/Pen
| Feature | Protocol | R/W |
|---------|----------|-----|
| Button Programming | BLE + Dell proprietary / MPP | RW |
| Tilt Sensitivity | BLE + proprietary / MPP | RW |
| Tip Pressure Sensitivity | BLE + proprietary / MPP | RW |
| Battery Level | BLE | R |

### IT/Fleet Management
- Dell Device Management Console (cloud, 300+ models)
- CLI for scripted deployment (Windows + macOS)
- Silent MSI/PKG deployment
- Intune integration
- Fleet firmware management + asset inventory

---

## 2. Lenovo Vantage

Three variants: Lenovo Vantage (consumer), Commercial Vantage (enterprise/IT-managed), Vantage for Gaming (Legion). All via Microsoft Store, experience adapts to detected hardware.

### Battery Management
| Feature | Devices | API Access |
|---------|---------|------------|
| Conservation Mode (cap at 55-60%) | IdeaPad, Yoga, Legion, ThinkBook | Linux: `/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/conservation_mode`. Windows: Vantage-proprietary ACPI, no standard WMI |
| Rapid Charge | IdeaPad, Yoga, Legion, ThinkBook | Vantage only, no public WMI |
| Battery Charge Threshold (Start/Stop %) | ThinkPad | Linux: `/sys/class/power_supply/BAT0/charge_start_threshold` + `charge_stop_threshold`. Windows: WMI `root\WMI` `Lenovo_BiosSetting` → `ChargeThreshold` |
| Battery Health (cycle count, capacity) | All notebooks | Vantage-proprietary (NOT via WMI) |
| Always On USB | ThinkPad, select IdeaPad | BIOS WMI: `AlwaysOnUSB,Enable/Disable` |

### Thermal/Performance Modes
| Feature | Devices | API Access |
|---------|---------|------------|
| Intelligent Cooling (Quiet/Balanced/Perf) | ThinkPad | BIOS WMI: `AdaptiveThermalManagementAC` + `AdaptiveThermalManagementBattery` → `MaximizePerformance`, `Balanced` |
| Thermal Mode (Quiet/Balanced/Perf/Extreme) | IdeaPad, Yoga, Legion | Linux: `/sys/bus/platform/drivers/ideapad_acpi/.../thermal_mode`. Windows: no standard WMI |
| Fan Speed Display | ThinkPad, Legion | Linux: `/proc/acpi/ibm/fan`. Windows: Vantage-proprietary |
| Custom Fan Curves | Legion | GUI only |

### Display
| Feature | API Access |
|---------|------------|
| Eye Care / Low Blue Light | GUI only (Vantage-proprietary) |
| Color Temperature | GUI only |
| Privacy Guard (ePrivacy) | ThinkPad Privacy Guard models, GUI only |
| Display Over-Drive | Legion, GUI only |

### Audio
| Feature | API Access |
|---------|------------|
| Dolby Atmos/Audio (5 profiles) | Via Dolby Access app, no WMI |
| Smart Noise Cancellation (AI mic) | Vantage-proprietary, no WMI |

### Keyboard/Input
| Feature | API Access |
|---------|------------|
| FN Key Swap (Fn↔Ctrl) | BIOS WMI: `FnCtrlKeySwap,Enable/Disable` |
| Hotkey Mode (Fn Lock) | BIOS WMI: `HotkeyMode,Enable/Disable` |
| Keyboard Backlight Level | BIOS WMI: `KeyboardBacklightLevel` |
| TrackPoint Sensitivity | Windows driver settings, no WMI |

### Security (via BIOS WMI)
| Feature | API Access |
|---------|------------|
| TPM (SecurityChip) | BIOS WMI: `SecurityChip,Enable/Disable` |
| Secure Boot | BIOS WMI: `SecureBoot,Enable/Disable` |
| Thunderbolt Access | BIOS WMI: `ThunderboltAccess,Enable/Disable` |
| AMT Control (vPro) | BIOS WMI: `AMTControl,Enable/Disable` |
| BIOS Password Management | WMI: `Lenovo_setBiosPassword` |
| Virtualization Technology | BIOS WMI: `VirtualizationTechnology,Enable/Disable` |

### Legion-Specific (Gaming)
| Feature | API Access |
|---------|------------|
| Hybrid Mode (Optimus) | BIOS WMI: `HybridGraphics` |
| GPU/CPU Overclock Offset | Vantage-proprietary, no WMI |
| RGB Lighting (per-key) | Vantage-proprietary, no WMI |
| Network Boost (per-app priority) | Vantage-proprietary, no WMI |

### WMI Access — Corrected & Detailed

**Namespace: `root\WMI`** (NOT `root\Lenovo` — that namespace does not exist)

| WMI Class | Purpose | R/W |
|-----------|---------|-----|
| `Lenovo_BiosSetting` | Read all BIOS settings (`CurrentSetting` = `"Name,Value"` pairs) | R |
| `Lenovo_SetBiosSetting` | Modify single setting (`.SetBiosSetting("Name,Value,Password,Encoding")`) | W |
| `Lenovo_SaveBiosSettings` | Commit pending changes (`.SaveBiosSettings("Password,Encoding")`) | W |
| `Lenovo_GetBiosSelections` | Get valid values for a setting (`.GetBiosSelections("Name")`) | R |
| `Lenovo_BiosPasswordSettings` | Query password state (0=none, 2=supervisor, etc.) | R |
| `Lenovo_setBiosPassword` | Set/change BIOS passwords | W |

100+ BIOS settings accessible including: VirtualizationTechnology, SecureBoot, SecurityChip, ThunderboltAccess, AMTControl, OnByAcAttach, WirelessAutoDisconnection, FnCtrlKeySwap, HotkeyMode, KeyboardBacklightLevel, AlwaysOnUSB, HybridGraphics, ChargeThreshold, AdaptiveThermalManagement*, WakeOnLAN, BootOrder, and more.

**Key difference vs Dell:** Dell DCM exposes rich real-time sensor telemetry via WMI (temps, fan speeds, power). Lenovo keeps runtime telemetry locked in Vantage-proprietary APIs — only BIOS-level configuration is exposed via standard WMI. On Linux, `thinkpad_acpi` and `ideapad_acpi` kernel drivers expose significantly more runtime data via sysfs.

**Linux Kernel Interfaces (ThinkPad):**
- `/sys/class/power_supply/BAT0/charge_start_threshold` + `charge_stop_threshold`
- `/proc/acpi/ibm/fan` — fan control + RPM
- `/proc/acpi/ibm/thermal` — temperatures
- `/sys/class/firmware-attributes/thinklmi/` — BIOS settings via `think_lmi` module

---

## 3. HP Tools Ecosystem

### HP Command Center (Thermal)
| Feature | Devices | API Access |
|---------|---------|------------|
| Balanced Profile | Consumer (Spectre, Envy, OMEN) | **GUI only — no WMI/CLI** |
| Performance/Turbo Profile | Consumer | GUI only |
| Cool/Quiet Profile | Consumer | GUI only |
| CoolSense (motion-adaptive) | Older consumer | GUI only |

### HP Battery Health Manager (BHM)
| Feature | Devices | API Access |
|---------|---------|------------|
| Adaptive Charging ("Let HP manage") | Business (EliteBook, ProBook, ZBook) | **WMI + CMSL** |
| Max Health (cap at ~80%) | Business | WMI + CMSL |
| Max Duration (charge to 100%) | Business | WMI + CMSL |

### HP BIOS — WMI Namespace `root\HP\InstrumentedBIOS`
| WMI Class | Purpose | R/W |
|-----------|---------|-----|
| HP_BIOSEnumeration | Dropdown-style BIOS settings | R |
| HP_BIOSString | Text BIOS settings | R |
| HP_BIOSInteger | Numeric BIOS settings | R |
| HP_BIOSOrderedList | Boot order | R |
| HP_BIOSSettingInterface | **SetBIOSSetting() method** | **W** |

Controllable via WMI: Wake-on-LAN, Secure Boot, TPM, Battery Health Manager, Boot Order, Virtualization, Sure Start policy, LAN/Wireless Switching

### HP Client Management Script Library (HPCMSL)
PowerShell module (`Install-Module HPCMSL`) with cmdlets:
- **BIOS**: `Get-HPBIOSSetting`, `Set-HPBIOSSettingValue`, `Get-HPBIOSSettingsList`
- **Device**: `Get-HPDeviceSerialNumber`, `Get-HPDeviceModel`, `Get-HPDeviceUptime`, `Get-HPWarrantyInfo`
- **Display**: `Get-HPDisplay`, `Set-HPDisplay` (color profile), `Update-HPDisplayFirmware`
- **Sure View**: `Get-HPSureViewState`, `Set-HPSureViewState` (privacy screen)
- **Docks**: `Get-HPDockInfo`, `Update-HPDockFirmware`
- **Security**: Sure Admin, Sure Start, Sure Recover, Secure Platform Management
- **SoftPaq**: Driver/firmware repository management

### HP Accessory Center (Peripherals)
| Feature | Devices | API Access |
|---------|---------|------------|
| Button/Key Customization | HP mice, keyboards | GUI only |
| DPI/Sensitivity | HP mice | GUI only |
| Battery Monitoring | HP wireless peripherals | GUI only |
| Backlight Control | HP keyboards | GUI only |

---

## 4. Logitech Ecosystem

### HID++ Protocol (Key Finding)
Logitech's proprietary HID extension — **partially documented** and **self-describing**:
- Feature `0x0000` (IRoot) + `0x0001` (IFeatureSet) allow dynamic capability discovery
- Works over: Unifying 2.4GHz, Bolt BLE, Lightspeed, USB wired, Bluetooth
- **Third-party battery reading confirmed**: works without Options+ installed

| HID++ Feature ID | Name | Description |
|------------------|------|-------------|
| 0x1000 | BatteryUnifiedLevelStatus | Battery % + charging |
| 0x1001 | BatteryVoltage | Raw voltage (more granular) |
| 0x1004 | UnifiedBattery | Newer battery reporting |
| 0x2201 | AdjustableDPI | Mouse DPI get/set |
| 0x1b04 | ReprogramControlsV4 | Button remapping |
| 0x1981-83 | Backlight | Keyboard backlight |
| 0x8060 | ReportRate | USB polling rate |
| 0x8070 | ColorLEDEffects | RGB LED |
| 0x2205 | PointerSpeed | Acceleration |
| 0x0003 | DeviceFwVersion | Firmware info |
| 0x0005 | DeviceName | Device name/type |

### Logitech Options+ Features
| Feature | Protocol | Devices |
|---------|----------|---------|
| Battery Monitoring | HID++ 0x1000/0x1001 | All wireless MX |
| DPI/Sensitivity | HID++ 0x2201 | MX mice |
| Button Remap (per-app) | HID++ 0x1b04 | Mice + keyboards |
| SmartShift Scroll | HID++ SmartShift | MX Master, MX Anywhere |
| Gesture Support | Software + HID++ diversion | MX mice |
| Keyboard Backlight | HID++ 0x1981-83 | MX Keys |
| Flow (cross-computer) | LAN UDP 59870 / TCP 59866 | Multi-host devices |
| Smart Actions (macros) | Software automation | All |
| Webcam Controls | UVC | Brio, MX Brio |
| Litra Lights | USB HID / BLE | Litra Glow/Beam |

### Logitech G HUB Features
| Feature | Protocol | Devices |
|---------|----------|---------|
| LIGHTSYNC RGB (per-key) | USB HID proprietary | G keyboards, mice |
| DPI Profiles (5 levels) | HID++ 0x2201 | G mice |
| G SHIFT (secondary layer) | Software | G mice, keyboards |
| Lua Scripting | Software | G mice, keyboards |
| DTS Headphone:X 7.1 | Software | G headsets |
| Blue VO!CE (mic enhance) | Software | G Pro X headsets |
| Battery Monitoring | HID++ 0x1000/0x1001 | Wireless G devices |

### Solaar (Open-Source Linux)
Full HID++ access: battery, DPI, backlight, scroll, FN swap, report rate, LED, host switching.
Rules engine for custom automation. No Flow, no gestures, no webcam (those are software-level in Options+).

### Third-Party Battery Access (no Logitech software needed)
- **Linux**: kernel driver `hid-logitech-hidpp` + UPower/sysfs
- **Windows**: LGSTrayBattery (native HID++ or G HUB WebSocket)
- **macOS**: batteryconsole CLI
- **Python**: direct HID++ scripting

---

## 5. Audio Peripheral Tools

### Jabra Direct
| Feature | Protocol | API |
|---------|----------|-----|
| Battery % | USB HID / BLE | **Jabra JS SDK** (`@gnaudio/jabra-js`) |
| Active Call Detection / Busylight | USB HID + softphone | JS SDK (call control) |
| Sidetone | USB HID / proprietary | No public API |
| EQ Presets | USB HID / proprietary | No public API |
| ANC Levels (Off/Low/Med/High) | USB HID / proprietary | No public API |
| HearThrough | USB HID / proprietary | No public API |
| Mic Noise Cancellation | Firmware | No public API |
| Firmware Updates | USB / BLE | No public API |

**Jabra JS SDK**: WebHID transport (Chromium 89+) for call control. Full transport (native host + Chrome extension) for telemetry + settings. NPM: `@gnaudio/jabra-js`

### Corsair iCUE (Headsets)
| Feature | Protocol | API |
|---------|----------|-----|
| Battery % (0-100) | USB HID | **iCUE SDK** (`CDPI_BatteryLevel`) |
| Sidetone | USB HID | No public API |
| Custom EQ | USB HID / proprietary | No public API |
| 7.1 Virtual Surround | Software | No public API |
| RGB | USB HID | iCUE SDK |

### SteelSeries GG / Sonar
| Feature | Protocol | API |
|---------|----------|-----|
| Battery Status | USB HID | No official API |
| Sidetone | Software | **Sonar REST API** (community) |
| 10-Band Parametric EQ | Software | Sonar REST API |
| ClearCast AI Noise Cancel (3 levels) | Software | Sonar REST API |
| Sonar Spatial Audio | Software | Sonar REST API |
| Volume/Mute per channel | Software | Sonar REST API |

Community Sonar API: `steelseries-sonar-py` (PyPI), `OpenSteelSeries.Sonar.Sdk` (NuGet)

### Razer Synapse (Headsets)
| Feature | Protocol | API |
|---------|----------|-----|
| Battery % | USB HID | No public API (Chroma SDK = RGB only) |
| 10-Band EQ | Software | No public API |
| ANC (4 levels) | USB HID | No public API |
| THX Spatial Audio | Software | No public API |
| Mic Noise Suppression | AI / Software | No public API |

### HeadsetControl (Open-Source, GPL v3)
| Feature | Supported Brands | API |
|---------|-----------------|-----|
| Battery % | Logitech, SteelSeries, Corsair, HyperX | **C library + CLI + JSON output** |
| Sidetone (0-128) | Logitech, SteelSeries, Corsair | CLI |
| LED on/off | Logitech, SteelSeries, Corsair | CLI |
| Auto-off timer | Logitech, SteelSeries | CLI |
| EQ Presets | Select devices | CLI |
| **NOT supported**: Jabra | | |

---

## Protocol Summary — What Is Generic vs. Vendor-Specific

### Generic Protocols (multi-vendor)
| Protocol | Scope | Controllable | Notes |
|----------|-------|:---:|-------|
| DDC/CI (MCCS) | Monitor brightness, contrast, input, power, color | RW | VESA standard, works with all DDC/CI monitors |
| UVC (USB Video Class) | Webcam image controls | RW | USB standard, works with all UVC webcams |
| USB HID Battery (0x85) | Peripheral battery | R | Standard exists but NOT consistently used by vendors |
| BLE Battery Service (0x180F) | BLE peripheral battery | R | Standard GATT service |
| EDID | Monitor identification | R | Universal |
| WMI Win32_* | Generic system info | R | Windows standard |

### Vendor-Specific Protocols (require per-vendor implementation)
| Vendor | Protocol | Scope | Documented? |
|--------|----------|-------|:-----------:|
| Dell | Dell Secure Link HID | KB900/MS900 backlight, DPI | Reverse-engineered |
| Dell | DCM WMI `root/DCIM/SYSMAN` | 70+ system management classes | Documented |
| Logitech | HID++ 2.0 | Battery, DPI, buttons, backlight, scroll | **Partially documented** |
| HP | WMI `root/HP/InstrumentedBIOS` | BIOS settings, battery manager | Documented |
| HP | HPCMSL PowerShell | Displays, docks, BIOS, security | Documented |
| Lenovo | WMI `root/WMI` (`Lenovo_BiosSetting` family) | 100+ BIOS settings, battery threshold, thermal mode | Well documented (enterprise SCCM/Intune) |
| Lenovo | Linux sysfs (`thinkpad_acpi`, `ideapad_acpi`) | Fan, thermal, battery threshold, conservation | Documented (kernel) |
| Corsair | iCUE SDK | Battery + RGB | Documented SDK |
| SteelSeries | Sonar REST API | Audio EQ, volume, spatial | Community reverse-engineered |
| Jabra | JS SDK (WebHID) | Call control only | Documented SDK |
| Razer | Chroma SDK | RGB only | Documented SDK |

---

## Key Insight: Integration Feasibility Matrix

| Feature Category | Feasibility for Multi-Vendor | Approach |
|------------------|:---:|---------|
| Monitor DDC/CI (brightness, input, power) | **Easy** | monitorcontrol library, standard VCP codes |
| Webcam UVC controls | **Easy** | Standard UVC, already implemented |
| System telemetry (CPU, RAM, disk, battery) | **Easy** | WMI Win32_* + psutil (cross-platform) |
| Peripheral battery (Logitech) | **Medium** | HID++ protocol, documented, Solaar reference |
| Peripheral battery (generic BLE) | **Medium** | BLE GATT 0x180F |
| Peripheral battery (gaming headsets) | **Medium** | HeadsetControl library (Logitech, SS, Corsair) |
| Dell-specific telemetry | **Medium** | DCM WMI, already implemented |
| HP BIOS settings | **Medium** | WMI `root/HP/InstrumentedBIOS`, HPCMSL |
| Lenovo BIOS/battery/thermal | **Medium** | WMI `root/WMI` `Lenovo_BiosSetting` (config), sysfs on Linux (runtime) |
| Keyboard/mouse button remap | **Hard** | Per-vendor proprietary protocols |
| Audio EQ/ANC | **Hard** | Per-vendor proprietary, few APIs |
| RGB lighting | **Medium** | OpenRGB SDK covers most vendors |
| Fleet management | **Not feasible** | Each vendor has proprietary cloud |
