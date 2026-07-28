"""Locale helpers for the Volkswagen identity-provider flow."""

from __future__ import annotations


def _two_letter_code(value: object, fallback: str) -> str:
    """Return a safe two-letter locale component."""
    candidate = str(value or "").replace("_", "-").split("-", 1)[0].lower()
    return candidate if len(candidate) == 2 and candidate.isalpha() else fallback


def identity_locale(country: object, language: object) -> tuple[str, str]:
    """Derive identity country and language from Home Assistant settings."""
    return _two_letter_code(country, "de"), _two_letter_code(language, "en")


def accept_language(country: str, language: str) -> str:
    """Build a browser-like Accept-Language header for identity pages."""
    return f"{language}-{country.upper()},{language};q=0.9,en;q=0.8"


def oidc_state(country: str, language: str, client: str) -> str:
    """Build the locale-qualified OIDC state accepted by the identity portal."""
    return f"{country}__{language}__{client.upper()}"
