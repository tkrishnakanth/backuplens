"""Launcher and redaction unit tests."""

from __future__ import annotations

import logging
import socket

from backend.api.logging_setup import RedactingFilter, register_secret


def test_find_free_port_is_usable() -> None:
    from backend.app import find_free_port

    port = find_free_port()
    assert 1024 < port < 65536
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", port))


def test_redacting_filter_replaces_registered_secrets() -> None:
    secret = "another-super-secret"
    register_secret(secret)
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "value=%s", (secret,), None)
    RedactingFilter().filter(record)
    assert secret not in record.getMessage()
    assert "[redacted]" in record.getMessage()
