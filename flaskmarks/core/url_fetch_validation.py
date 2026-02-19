"""
URL validation helpers for safe outbound fetching.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class URLTargetValidationError(ValueError):
    """Raised when a URL is not allowed for outbound fetching."""


def _ip_rejection_reason(ip: IPAddress) -> str | None:
    """Return a reason when IP is not publicly routable."""
    if ip.is_loopback:
        return "loopback"
    if ip.is_link_local:
        return "link-local"
    if ip.is_private:
        return "private"
    if ip.is_multicast:
        return "multicast"
    if ip.is_unspecified:
        return "unspecified"
    if ip.is_reserved:
        return "reserved"
    if not ip.is_global:
        return "non-public"
    return None


def ensure_public_http_url(url: str) -> None:
    """
    Validate that URL uses http/https and resolves only to public addresses.

    Args:
        url: Candidate URL.

    Raises:
        URLTargetValidationError: If URL is malformed, uses disallowed scheme,
            cannot be resolved, or resolves to any non-public address.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:  # pragma: no cover - extremely defensive
        raise URLTargetValidationError("URL parsing failed.") from exc

    if parsed.scheme not in {"http", "https"}:
        raise URLTargetValidationError(
            "Only http and https URL schemes are allowed."
        )

    if not parsed.netloc:
        raise URLTargetValidationError("URL must include a hostname.")

    hostname = parsed.hostname
    if not hostname:
        raise URLTargetValidationError("URL must include a valid hostname.")

    try:
        addrinfos = socket.getaddrinfo(hostname, parsed.port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise URLTargetValidationError(
            "URL hostname could not be resolved."
        ) from exc

    if not addrinfos:
        raise URLTargetValidationError("URL hostname did not resolve to any address.")

    blocked_targets: list[str] = []
    for addrinfo in addrinfos:
        ip_text = addrinfo[4][0]
        ip_obj = ipaddress.ip_address(ip_text)
        reason = _ip_rejection_reason(ip_obj)
        if reason:
            blocked_targets.append(f"{ip_text} ({reason})")

    if blocked_targets:
        blocked = ", ".join(sorted(set(blocked_targets)))
        raise URLTargetValidationError(
            f"URL resolves to a blocked non-public target: {blocked}."
        )
