"""Install page server for agent distribution.

Serves a self-contained HTML page and platform-specific install scripts
at ``/desk2ha/install/{token}``.  The token is single-use and time-limited
so the page can be accessed without HA authentication.
"""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass, field
from string import Template
from typing import Any

from aiohttp import web
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PORT, DOMAIN

logger = logging.getLogger(__name__)

_TOKEN_TTL = 3600  # 1 hour
_MAX_PENDING = 20  # max simultaneous pending tokens
_PAIRING_CODE_LEN = 6


@dataclass
class _PendingInstall:
    """A pending install token with its metadata."""

    agent_token: str
    created: float
    ha_url: str
    pairing_code: str = ""
    expired: bool = False


@dataclass
class _PhoneHomeData:
    """Data received from an agent phone-home POST."""

    device_key: str
    agent_url: str
    agent_token: str
    hardware: dict[str, Any] = field(default_factory=dict)


class InstallServer:
    """Manages install tokens and serves install pages/scripts."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._pending: dict[str, _PendingInstall] = {}
        self._phone_home_queue: list[_PhoneHomeData] = []

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def create_token(self, ha_url: str) -> tuple[str, str, str]:
        """Create a new install token.  Returns (token, agent_token, pairing_code)."""
        self._purge_expired()
        if len(self._pending) >= _MAX_PENDING:
            # Remove oldest
            oldest = min(self._pending, key=lambda k: self._pending[k].created)
            del self._pending[oldest]

        token = secrets.token_urlsafe(32)
        agent_token = secrets.token_urlsafe(32)
        pairing_code = self._generate_pairing_code()
        self._pending[token] = _PendingInstall(
            agent_token=agent_token,
            created=time.time(),
            ha_url=ha_url,
            pairing_code=pairing_code,
        )
        return token, agent_token, pairing_code

    def validate_pairing_code(self, code: str) -> _PendingInstall | None:
        """Find a pending install by pairing code."""
        self._purge_expired()
        code_upper = code.strip().upper()
        for pending in self._pending.values():
            if pending.pairing_code == code_upper:
                return pending
        return None

    def find_token_by_code(self, code: str) -> str | None:
        """Find the token key for a pairing code."""
        self._purge_expired()
        code_upper = code.strip().upper()
        for token, pending in self._pending.items():
            if pending.pairing_code == code_upper:
                return token
        return None

    def _generate_pairing_code(self) -> str:
        """Generate a unique 6-char alphanumeric pairing code (no ambiguous chars)."""
        import random
        import string

        # Avoid ambiguous chars: 0/O, 1/I/L
        alphabet = string.ascii_uppercase.replace("O", "").replace("I", "").replace("L", "")
        alphabet += string.digits.replace("0", "").replace("1", "")
        existing = {p.pairing_code for p in self._pending.values()}
        for _ in range(100):
            code = "".join(random.choices(alphabet, k=_PAIRING_CODE_LEN))  # noqa: S311
            if code not in existing:
                return code
        return secrets.token_hex(3).upper()[:_PAIRING_CODE_LEN]

    def validate_token(self, token: str) -> _PendingInstall | None:
        """Return the pending install if the token is valid and not expired."""
        self._purge_expired()
        return self._pending.get(token)

    def invalidate_token(self, token: str) -> None:
        """Mark a token as used."""
        self._pending.pop(token, None)

    def pop_phone_home(self) -> _PhoneHomeData | None:
        """Pop the oldest phone-home registration."""
        return self._phone_home_queue.pop(0) if self._phone_home_queue else None

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._pending.items() if now - v.created > _TOKEN_TTL]
        for k in expired:
            del self._pending[k]

    # ------------------------------------------------------------------
    # HTTP handlers (registered on HA's aiohttp app)
    # ------------------------------------------------------------------

    def register_routes(self, app: web.Application) -> None:
        """Register all install-related routes on the HA web app."""
        app.router.add_get(f"/{DOMAIN}/install/{{token}}", self._handle_install_page)
        app.router.add_get(f"/{DOMAIN}/install/{{token}}/script.sh", self._handle_script_sh)
        app.router.add_get(f"/{DOMAIN}/install/{{token}}/script.ps1", self._handle_script_ps1)
        app.router.add_post(f"/{DOMAIN}/install/phone-home", self._handle_phone_home)
        app.router.add_post(f"/{DOMAIN}/install/pair", self._handle_pair)
        logger.info("Registered install server routes under /%s/install/", DOMAIN)

    async def _handle_install_page(self, request: web.Request) -> web.Response:
        """Serve the install HTML page."""
        token = request.match_info["token"]
        pending = self.validate_token(token)
        if pending is None:
            return web.Response(
                text="<h1>Link expired or invalid</h1>"
                "<p>Please generate a new install link from Home Assistant.</p>",
                content_type="text/html",
                status=404,
            )

        base_url = pending.ha_url.rstrip("/")
        html = _INSTALL_HTML.safe_substitute(
            token=token,
            base_url=base_url,
        )
        return web.Response(text=html, content_type="text/html")

    async def _handle_script_sh(self, request: web.Request) -> web.Response:
        """Serve the Unix (macOS/Linux) install script."""
        token = request.match_info["token"]
        pending = self.validate_token(token)
        if pending is None:
            return web.Response(text="# Token expired", status=404)

        base_url = pending.ha_url.rstrip("/")
        script = _INSTALL_SH.safe_substitute(
            agent_token=pending.agent_token,
            ha_url=base_url,
            phone_home_token=token,
            agent_port=DEFAULT_PORT,
        )
        return web.Response(
            text=script,
            content_type="text/plain",
            headers={"Content-Disposition": "inline; filename=install-desk2ha.sh"},
        )

    async def _handle_script_ps1(self, request: web.Request) -> web.Response:
        """Serve the Windows PowerShell install script."""
        token = request.match_info["token"]
        pending = self.validate_token(token)
        if pending is None:
            return web.Response(text="# Token expired", status=404)

        base_url = pending.ha_url.rstrip("/")
        script = _INSTALL_PS1.safe_substitute(
            agent_token=pending.agent_token,
            ha_url=base_url,
            phone_home_token=token,
            agent_port=DEFAULT_PORT,
        )
        return web.Response(
            text=script,
            content_type="text/plain",
            headers={"Content-Disposition": "inline; filename=install-desk2ha.ps1"},
        )

    async def _handle_pair(self, request: web.Request) -> web.Response:
        """Handle pairing code from setup wizard.

        The agent's setup wizard POSTs a pairing code.  We validate it,
        return the agent_token + phone_home_token, and trigger config flow.
        """
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)

        code = data.get("pairing_code", "").strip()
        agent_url = data.get("agent_url", "")
        hardware = data.get("hardware", {})

        pending = self.validate_pairing_code(code)
        if pending is None:
            return web.json_response({"error": "Invalid pairing code"}, status=403)

        token_key = self.find_token_by_code(code)

        # Trigger config flow with phone_home data
        device_key = hardware.get("hostname", "unknown")
        self._hass.async_create_task(
            self._hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "phone_home"},
                data={
                    "agent_url": agent_url,
                    "agent_token": pending.agent_token,
                    "device_key": device_key,
                    "hardware": hardware,
                },
            )
        )

        logger.info(
            "Pairing successful: %s (%s)",
            device_key,
            agent_url,
        )

        # Return credentials so the agent can write its config
        return web.json_response(
            {
                "status": "ok",
                "agent_token": pending.agent_token,
                "phone_home_token": token_key or "",
            }
        )

    async def _handle_phone_home(self, request: web.Request) -> web.Response:
        """Handle agent phone-home POST."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)

        phone_home_token = data.get("phone_home_token", "")
        pending = self.validate_token(phone_home_token)
        if pending is None:
            return web.json_response({"error": "invalid token"}, status=403)

        phone_home = _PhoneHomeData(
            device_key=data.get("device_key", "unknown"),
            agent_url=data.get("agent_url", ""),
            agent_token=pending.agent_token,
            hardware=data.get("hardware", {}),
        )
        self._phone_home_queue.append(phone_home)
        self.invalidate_token(phone_home_token)

        # Trigger config flow
        self._hass.async_create_task(
            self._hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "phone_home"},
                data={
                    "agent_url": phone_home.agent_url,
                    "agent_token": phone_home.agent_token,
                    "device_key": phone_home.device_key,
                    "hardware": phone_home.hardware,
                },
            )
        )

        logger.info(
            "Phone-home received from %s (%s)",
            phone_home.device_key,
            phone_home.agent_url,
        )
        return web.json_response({"status": "ok"})


# ------------------------------------------------------------------
# Embedded templates (no external files needed)
# ------------------------------------------------------------------

_INSTALL_HTML = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Install Desk2HA Agent</title>
<style>
  :root { --blue: #03A9F4; --dark: #1a1a2e; --card: #16213e; --text: #e0e0e0; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--dark); color: var(--text); min-height: 100vh;
         display: flex; justify-content: center; align-items: center; padding: 2rem; }
  .container { max-width: 640px; width: 100%; }
  h1 { color: var(--blue); font-size: 1.8rem; margin-bottom: 0.5rem; }
  .subtitle { color: #888; margin-bottom: 2rem; }
  .card { background: var(--card); border-radius: 12px; padding: 1.5rem;
          margin-bottom: 1rem; border: 1px solid #2a2a4a; }
  .card h2 { color: var(--blue); font-size: 1.1rem; margin-bottom: 0.8rem; }
  .card p { margin-bottom: 0.8rem; line-height: 1.5; color: #bbb; font-size: 0.95rem; }
  .cmd { background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
         padding: 1rem; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85rem;
         color: #58a6ff; word-break: break-all; cursor: pointer; position: relative;
         transition: border-color 0.2s; }
  .cmd:hover { border-color: var(--blue); }
  .cmd::after { content: 'click to copy'; position: absolute; right: 8px; top: 8px;
                font-size: 0.7rem; color: #666; }
  .cmd.copied::after { content: 'copied!'; color: var(--blue); }
  .tabs { display: flex; gap: 0; margin-bottom: 0; }
  .tab { padding: 0.6rem 1.2rem; cursor: pointer; border: 1px solid #2a2a4a;
         border-bottom: none; border-radius: 8px 8px 0 0; background: transparent;
         color: #888; font-size: 0.9rem; transition: all 0.2s; }
  .tab.active { background: var(--card); color: var(--blue); border-color: #2a2a4a; }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  .card.tabbed { border-top-left-radius: 0; }
  .steps { counter-reset: step; list-style: none; padding: 0; }
  .steps li { counter-increment: step; padding: 0.4rem 0 0.4rem 2rem; position: relative;
              color: #bbb; font-size: 0.95rem; }
  .steps li::before { content: counter(step); position: absolute; left: 0;
                      background: var(--blue); color: #fff; width: 1.4rem; height: 1.4rem;
                      border-radius: 50%; text-align: center; line-height: 1.4rem;
                      font-size: 0.75rem; font-weight: bold; }
  .note { font-size: 0.85rem; color: #666; margin-top: 1rem; }
</style>
</head>
<body>
<div class="container">
  <h1>&#128421; Desk2HA Agent</h1>
  <p class="subtitle">Install the agent on this machine to connect it to Home Assistant.</p>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('macos')">macOS</div>
    <div class="tab" onclick="switchTab('linux')">Linux</div>
    <div class="tab" onclick="switchTab('windows')">Windows</div>
  </div>

  <div id="tab-macos" class="tab-content active">
    <div class="card tabbed">
      <h2>macOS Installation</h2>
      <ol class="steps">
        <li>Open <strong>Terminal</strong> (Cmd+Space, type "Terminal")</li>
        <li>Paste the command below and press Enter</li>
        <li>The agent will install and connect automatically</li>
      </ol>
      <div class="cmd" onclick="copyCmd(this)"
>curl -fsSL ${base_url}/desk2ha/install/${token}/script.sh | bash</div>
      <p class="note">Requires Python 3.11+. The script will check and guide you if needed.</p>
    </div>
  </div>

  <div id="tab-linux" class="tab-content">
    <div class="card tabbed">
      <h2>Linux Installation</h2>
      <ol class="steps">
        <li>Open a terminal</li>
        <li>Paste the command below and press Enter</li>
        <li>The agent will install and connect automatically</li>
      </ol>
      <div class="cmd" onclick="copyCmd(this)"
>curl -fsSL ${base_url}/desk2ha/install/${token}/script.sh | bash</div>
      <p class="note">Requires Python 3.11+ and pip. Works on Debian, Ubuntu, Fedora, Arch.</p>
    </div>
  </div>

  <div id="tab-windows" class="tab-content">
    <div class="card tabbed">
      <h2>Windows Installation</h2>
      <ol class="steps">
        <li>Open <strong>PowerShell</strong> (right-click Start &rarr; Terminal)</li>
        <li>Paste the command below and press Enter</li>
        <li>The agent will install and connect automatically</li>
      </ol>
      <div class="cmd" onclick="copyCmd(this)"
>irm ${base_url}/desk2ha/install/${token}/script.ps1 | iex</div>
      <p class="note">Requires Python 3.11+. The script will check and guide you if needed.</p>
    </div>
  </div>

  <div class="card">
    <h2>What happens next?</h2>
    <ol class="steps">
      <li>The script installs the Desk2HA agent via pip</li>
      <li>A configuration file is created with your HA connection details</li>
      <li>The agent starts as a background service</li>
      <li>Home Assistant automatically discovers the new agent</li>
    </ol>
    <p class="note">This link is single-use and expires in 1 hour.</p>
  </div>
</div>

<script>
function switchTab(os) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + os).classList.add('active');
}
function copyCmd(el) {
  navigator.clipboard.writeText(el.textContent.trim());
  el.classList.add('copied');
  setTimeout(() => el.classList.remove('copied'), 2000);
}
// Auto-detect OS
const ua = navigator.userAgent;
if (ua.includes('Win')) switchTab('windows');
else if (ua.includes('Linux') && !ua.includes('Mac')) switchTab('linux');
</script>
</body>
</html>
""")

_INSTALL_SH = Template("""\
#!/bin/bash
# Desk2HA Agent Installer — macOS / Linux
# Generated by Home Assistant. Single-use, do not share.
set -euo pipefail

AGENT_TOKEN="${agent_token}"
HA_URL="${ha_url}"
PHONE_HOME_TOKEN="${phone_home_token}"
AGENT_PORT="${agent_port}"

BLUE='\\033[0;34m'
GREEN='\\033[0;32m'
RED='\\033[0;31m'
NC='\\033[0m'

info()  { echo -e "$${BLUE}[desk2ha]$${NC} $$1"; }
ok()    { echo -e "$${GREEN}[desk2ha]$${NC} $$1"; }
err()   { echo -e "$${RED}[desk2ha]$${NC} $$1" >&2; }

# --- 1. Check Python ---
info "Checking Python..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$$cmd" >/dev/null 2>&1; then
        ver=$$($$cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$$(echo "$$ver" | cut -d. -f1)
        minor=$$(echo "$$ver" | cut -d. -f2)
        if [ "$$major" -ge 3 ] && [ "$$minor" -ge 11 ]; then
            PYTHON="$$cmd"
            break
        fi
    fi
done

if [ -z "$$PYTHON" ]; then
    err "Python 3.11+ not found."
    if [[ "$$OSTYPE" == "darwin"* ]]; then
        err "Install via: brew install python@3.12"
    else
        err "Install via: sudo apt install python3 python3-pip  (Debian/Ubuntu)"
        err "         or: sudo dnf install python3 python3-pip  (Fedora)"
    fi
    exit 1
fi
ok "Found $$PYTHON ($$($$PYTHON --version))"

# --- 2. Install desk2ha-agent ---
info "Installing desk2ha-agent..."
$$PYTHON -m pip install --user --upgrade desk2ha-agent 2>/dev/null || \\
    $$PYTHON -m pip install --upgrade desk2ha-agent

ok "desk2ha-agent installed"

# --- 3. Generate device key ---
HOSTNAME=$$(hostname -s 2>/dev/null || hostname)
SHORT_UUID=$$($$PYTHON -c "import uuid; print(str(uuid.uuid4())[:8])")
DEVICE_KEY="$${HOSTNAME}-$${SHORT_UUID}"

# --- 4. Write config ---
if [[ "$$OSTYPE" == "darwin"* ]]; then
    CONFIG_DIR="$$HOME/.config/desk2ha"
else
    CONFIG_DIR="/etc/desk2ha"
    if [ ! -w "$$CONFIG_DIR" ] 2>/dev/null; then
        sudo mkdir -p "$$CONFIG_DIR"
        sudo chown "$$USER" "$$CONFIG_DIR"
    fi
fi
mkdir -p "$$CONFIG_DIR"

cat > "$$CONFIG_DIR/config.toml" << TOML
# Desk2HA Agent — auto-generated by HA install
[agent]
device_name = "auto"

[http]
enabled = true
bind = "0.0.0.0"
port = $$AGENT_PORT
auth_token = "$$AGENT_TOKEN"

[provisioning]
phone_home_url = "$$HA_URL/desk2ha/install/phone-home"
phone_home_token = "$$PHONE_HOME_TOKEN"

[logging]
level = "INFO"
TOML

ok "Config written to $$CONFIG_DIR/config.toml"

# --- 5. Set up service ---
info "Setting up background service..."
AGENT_BIN=$$($$PYTHON -c "import shutil; print(shutil.which('desk2ha-agent') or '')")
if [ -z "$$AGENT_BIN" ]; then
    # Try user bin paths
    for p in "$$HOME/.local/bin/desk2ha-agent" "$$HOME/Library/Python/3.12/bin/desk2ha-agent" "$$HOME/Library/Python/3.11/bin/desk2ha-agent"; do
        if [ -x "$$p" ]; then AGENT_BIN="$$p"; break; fi
    done
fi
if [ -z "$$AGENT_BIN" ]; then
    err "desk2ha-agent binary not found in PATH. You may need to add ~/.local/bin to PATH."
    err "Starting manually for now..."
    $$PYTHON -m desk2ha_agent -c "$$CONFIG_DIR/config.toml" &
    ok "Agent started (PID $$!). Set up autostart manually."
    exit 0
fi

if [[ "$$OSTYPE" == "darwin"* ]]; then
    # macOS: launchd plist
    PLIST="$$HOME/Library/LaunchAgents/com.desk2ha.agent.plist"
    mkdir -p "$$HOME/Library/LaunchAgents"
    cat > "$$PLIST" << PXML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.desk2ha.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$$AGENT_BIN</string>
        <string>-c</string>
        <string>$$CONFIG_DIR/config.toml</string>
        <string>--service</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$$CONFIG_DIR/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$$CONFIG_DIR/logs/stderr.log</string>
</dict>
</plist>
PXML
    mkdir -p "$$CONFIG_DIR/logs"
    launchctl unload "$$PLIST" 2>/dev/null || true
    launchctl load "$$PLIST"
    ok "launchd service started (com.desk2ha.agent)"
else
    # Linux: systemd user service
    SERVICE_DIR="$$HOME/.config/systemd/user"
    mkdir -p "$$SERVICE_DIR"
    cat > "$$SERVICE_DIR/desk2ha-agent.service" << UNIT
[Unit]
Description=Desk2HA Agent
After=network-online.target

[Service]
ExecStart=$$AGENT_BIN -c $$CONFIG_DIR/config.toml --service
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
UNIT
    systemctl --user daemon-reload
    systemctl --user enable --now desk2ha-agent.service
    ok "systemd user service started (desk2ha-agent)"
fi

ok "Done! The agent will connect to Home Assistant automatically."
""")

_INSTALL_PS1 = Template("""\
# Desk2HA Agent Installer — Windows PowerShell
# Generated by Home Assistant. Single-use, do not share.
$$ErrorActionPreference = 'Stop'

$$AgentToken     = '${agent_token}'
$$HaUrl          = '${ha_url}'
$$PhoneHomeToken = '${phone_home_token}'
$$AgentPort      = ${agent_port}

function Write-Info  { Write-Host "[desk2ha] $$args" -ForegroundColor Blue }
function Write-Ok    { Write-Host "[desk2ha] $$args" -ForegroundColor Green }
function Write-Err   { Write-Host "[desk2ha] $$args" -ForegroundColor Red }

# --- 1. Check Python ---
Write-Info "Checking Python..."
$$python = $null
foreach ($$cmd in @('python', 'python3', 'py -3')) {
    try {
        $$ver = & ($$cmd.Split(' ')[0]) @($$cmd.Split(' ') | Select-Object -Skip 1) -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$$null
        $$parts = $$ver.Split('.')
        if ([int]$$parts[0] -ge 3 -and [int]$$parts[1] -ge 11) {
            $$python = $$cmd
            break
        }
    } catch {}
}

if (-not $$python) {
    Write-Err "Python 3.11+ not found."
    Write-Err "Download from: https://www.python.org/downloads/"
    Write-Err "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}
Write-Ok "Found $$python"

# --- 2. Install desk2ha-agent ---
Write-Info "Installing desk2ha-agent..."
& ($$python.Split(' ')[0]) @($$python.Split(' ') | Select-Object -Skip 1) -m pip install --user --upgrade desk2ha-agent
Write-Ok "desk2ha-agent installed"

# --- 3. Generate device key ---
$$hostname = [System.Net.Dns]::GetHostName()
$$shortUuid = [guid]::NewGuid().ToString().Substring(0, 8)
$$deviceKey = "$$hostname-$$shortUuid"

# --- 4. Write config ---
$$configDir = "$$env:ProgramData\\desk2ha"
New-Item -ItemType Directory -Path $$configDir -Force | Out-Null

$$config = @"
# Desk2HA Agent - auto-generated by HA install
[agent]
device_name = "auto"

[http]
enabled = true
bind = "0.0.0.0"
port = $$AgentPort
auth_token = "$$AgentToken"

[provisioning]
phone_home_url = "$$HaUrl/desk2ha/install/phone-home"
phone_home_token = "$$PhoneHomeToken"

[logging]
level = "INFO"
"@
$$config | Out-File -FilePath "$$configDir\\config.toml" -Encoding UTF8
Write-Ok "Config written to $$configDir\\config.toml"

# --- 5. Set up scheduled task ---
Write-Info "Setting up background service..."
$$agentBin = & ($$python.Split(' ')[0]) @($$python.Split(' ') | Select-Object -Skip 1) -c "import shutil; print(shutil.which('desk2ha-agent') or '')" 2>$$null
if (-not $$agentBin) {
    # Try common locations
    $$paths = @(
        "$$env:APPDATA\\Python\\Scripts\\desk2ha-agent.exe",
        "$$env:LOCALAPPDATA\\Programs\\Python\\Python312\\Scripts\\desk2ha-agent.exe",
        "$$env:LOCALAPPDATA\\Programs\\Python\\Python311\\Scripts\\desk2ha-agent.exe"
    )
    foreach ($$p in $$paths) { if (Test-Path $$p) { $$agentBin = $$p; break } }
}

if (-not $$agentBin) {
    Write-Err "desk2ha-agent.exe not found in PATH. Add Python Scripts to PATH."
    exit 1
}

# Create Windows Scheduled Task (runs at logon, restarts on failure)
$$action = New-ScheduledTaskAction -Execute $$agentBin -Argument "-c `"$$configDir\\config.toml`" --service"
$$trigger = New-ScheduledTaskTrigger -AtLogon -User $$env:USERNAME
$$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Unregister-ScheduledTask -TaskName "Desk2HA Agent" -Confirm:$$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName "Desk2HA Agent" -Action $$action -Trigger $$trigger -Settings $$settings -RunLevel Highest -Description "Desk2HA desktop telemetry agent"
Start-ScheduledTask -TaskName "Desk2HA Agent"
Write-Ok "Windows Scheduled Task created and started"

Write-Ok "Done! The agent will connect to Home Assistant automatically."
""")
