"""Tests for network host discovery."""

from __future__ import annotations

from custom_components.desk2ha.discovery import DiscoveredHost, _detect_subnet


class TestDiscoveredHost:
    def test_label_ssh(self) -> None:
        h = DiscoveredHost(ip="192.168.1.10", hostname="workpc", ssh=True)
        assert "workpc" in h.label
        assert "SSH" in h.label
        assert "192.168.1.10" in h.label

    def test_label_winrm(self) -> None:
        h = DiscoveredHost(ip="192.168.1.20", hostname="winpc", winrm=True)
        assert "WinRM" in h.label

    def test_label_agent_running(self) -> None:
        h = DiscoveredHost(ip="192.168.1.30", hostname="desk", agent=True, ssh=True)
        assert "agent running" in h.label

    def test_os_hint_windows(self) -> None:
        h = DiscoveredHost(ip="10.0.0.1", hostname="win", winrm=True, ssh=True)
        assert h.os_hint == "windows"

    def test_os_hint_linux(self) -> None:
        h = DiscoveredHost(ip="10.0.0.2", hostname="srv", ssh=True)
        assert h.os_hint == "linux"

    def test_os_hint_unknown(self) -> None:
        h = DiscoveredHost(ip="10.0.0.3", hostname="x")
        assert h.os_hint == "unknown"

    def test_label_no_hostname(self) -> None:
        h = DiscoveredHost(ip="192.168.1.5", hostname="192.168.1.5", ssh=True)
        # Should not duplicate IP
        assert h.label.count("192.168.1.5") == 1


class TestDetectSubnet:
    def test_returns_string_or_none(self) -> None:
        result = _detect_subnet()
        assert result is None or isinstance(result, str)

    def test_contains_slash(self) -> None:
        result = _detect_subnet()
        if result:
            assert "/" in result
