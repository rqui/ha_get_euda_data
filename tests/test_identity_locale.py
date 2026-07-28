"""Tests for the identity-provider locale derived from Home Assistant."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


IDENTITY_LOCALE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "get_euda_data"
    / "get_euda_data"
    / "identity_locale.py"
)


def load_identity_locale_module():
    spec = importlib.util.spec_from_file_location("identity_locale", IDENTITY_LOCALE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class IdentityLocaleTests(unittest.TestCase):
    def test_spanish_configuration_matches_the_working_cupra_state(self):
        locale = load_identity_locale_module()

        country, language = locale.identity_locale("ES", "es")

        self.assertEqual((country, language), ("es", "es"))
        self.assertEqual(locale.oidc_state(country, language, "cupra"), "es__es__CUPRA")
        self.assertEqual(
            locale.accept_language(country, language), "es-ES,es;q=0.9,en;q=0.8"
        )

    def test_missing_configuration_keeps_the_previous_default_locale(self):
        locale = load_identity_locale_module()

        self.assertEqual(locale.identity_locale(None, None), ("de", "en"))


if __name__ == "__main__":
    unittest.main()
