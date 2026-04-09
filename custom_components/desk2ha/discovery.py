"""Network host discovery for remote agent installation."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Ports to check for remote management
_SSH_PORT = 22
_WINRM_HTTP_PORT = 5985
_AGENT_PORT = 9693

_CONNECT_TIMEOUT = 1.0  # seconds per host
_MAX_CONCURRENT = 50  # parallel connection attempts


@dataclass
class DiscoveredHost:
    """A host found on the network."""

    ip: str
    hostname: str
    ssh: bool = False
    winrm: bool = False
    agent: bool = False  # Already has a Desk2HA agent

    @property
    def os_hint(self) -> str:
        """Guess OS based on available services."""
        if self.winrm:
            return "windows"
        if self.ssh:
            return "linux"
        return "unknown"

    @property
    def label(self) -> str:
        """Human-readable label for the UI."""
        services = []
        if self.agent:
            services.append("agent running")
        if self.ssh:
            services.append("SSH")
        if self.winrm:
            services.append("WinRM")
        svc = ", ".join(services)
        if self.hostname and self.hostname != self.ip:
            return f"{self.hostname} ({self.ip}) [{svc}]"
        return f"{self.ip} [{svc}]"


async def scan_network(
    subnet: str | None = None,
    timeout: float = _CONNECT_TIMEOUT,
) -> list[DiscoveredHost]:
    """Scan the local network for hosts with SSH, WinRM, or Desk2HA agent.

    Args:
        subnet: CIDR notation (e.g. "192.168.1.0/24"). If None, auto-detect.
        timeout: TCP connect timeout per host in seconds.

    Returns:
        List of discovered hosts, sorted by IP.
    """
    if subnet is None:
        subnet = _detect_subnet()
    if subnet is None:
        logger.warning("Could not detect local subnet")
        return []

    try:
        network = ipaddress.IPv4Network(subnet, strict=False)
    except ValueError:
        logger.warning("Invalid subnet: %s", subnet)
        return []

    # Skip very large networks
    if network.num_addresses > 1024:
        logger.warning("Subnet too large: %s (%d hosts)", subnet, network.num_addresses)
        return []

    hosts = [str(ip) for ip in network.hosts()]
    results: list[DiscoveredHost] = []
    sem = asyncio.Semaphore(_MAX_CONCURRENT)

    async def check_host(ip: str) -> DiscoveredHost | None:
        async with sem:
            ssh, winrm, agent = await asyncio.gather(
                _check_port(ip, _SSH_PORT, timeout),
                _check_port(ip, _WINRM_HTTP_PORT, timeout),
                _check_port(ip, _AGENT_PORT, timeout),
            )
            if not (ssh or winrm or agent):
                return None

            hostname = await _resolve_hostname(ip)
            return DiscoveredHost(
                ip=ip,
                hostname=hostname,
                ssh=ssh,
                winrm=winrm,
                agent=agent,
            )

    tasks = [check_host(ip) for ip in hosts]
    found = await asyncio.gather(*tasks)
    results = [h for h in found if h is not None]
    results.sort(key=lambda h: ipaddress.IPv4Address(h.ip))

    logger.info(
        "Network scan of %s: %d hosts found (%d SSH, %d WinRM, %d agent)",
        subnet,
        len(results),
        sum(1 for h in results if h.ssh),
        sum(1 for h in results if h.winrm),
        sum(1 for h in results if h.agent),
    )
    return results


async def _check_port(ip: str, port: int, timeout: float) -> bool:
    """Check if a TCP port is open on the given IP."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, TimeoutError):
        return False


async def _resolve_hostname(ip: str) -> str:
    """Resolve IP to hostname via reverse DNS."""
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: socket.gethostbyaddr(ip),
        )
        return result[0].split(".")[0]  # Short hostname
    except (socket.herror, socket.gaierror, OSError):
        return ip


def _detect_subnet() -> str | None:
    """Detect the local subnet from the default interface."""
    try:
        import psutil

        for iface, addrs in psutil.net_if_addrs().items():
            iface_lower = iface.lower()
            if any(s in iface_lower for s in ("loopback", "lo", "isatap", "teredo")):
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address != "127.0.0.1" and addr.netmask:
                    net = ipaddress.IPv4Network(f"{addr.address}/{addr.netmask}", strict=False)
                    return str(net)
    except ImportError:
        pass

    # Fallback: connect to external host to find local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return f"{local_ip}/24"
    except OSError:
        return None
