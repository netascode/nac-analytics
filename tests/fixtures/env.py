"""Shared test environment variables for Nexus Dashboard."""

from __future__ import annotations

ND_TEST_ENV: dict[str, str] = {
    "ND_HOST": "nd.test",
    "ND_USER": "admin",
    "ND_PASSWORD": "secret",
    "ND_DOMAIN": "DefaultAuth",
    "ND_FABRIC": "FABRIC-A",
    "ND_VERIFY_SSL": "false",
}
