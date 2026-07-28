"""Tests for the identity-provider terms form parser."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


TERMS_MODULE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "get_euda_data"
    / "get_euda_data"
    / "terms.py"
)


def load_terms_module():
    spec = importlib.util.spec_from_file_location("euda_terms", TERMS_MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TermsFormParserTests(unittest.TestCase):
    def test_extracts_the_terms_post_target_and_required_session_fields(self):
        terms = load_terms_module()

        action, data = terms.parse_terms_form(
            '''<form method="post" action="/signin-service/v1/client/terms-and-conditions">
                 <input type="hidden" name="countryOfResidence" value="ES">
                 <input type="hidden" name="_csrf" value="csrf-value">
                 <input type="hidden" name="relayState" value="relay-value">
                 <input type="hidden" name="hmac" value="hmac-value">
               </form>'''
        )

        self.assertEqual(action, "/signin-service/v1/client/terms-and-conditions")
        self.assertEqual(
            data,
            {
                "countryOfResidence": "ES",
                "_csrf": "csrf-value",
                "relayState": "relay-value",
                "hmac": "hmac-value",
            },
        )

    def test_rejects_a_form_missing_required_identity_data(self):
        terms = load_terms_module()

        with self.assertRaises(ValueError):
            terms.parse_terms_form('<form action="/terms"><input name="_csrf" value="x"></form>')

    def test_ignores_inputs_outside_the_terms_form(self):
        terms = load_terms_module()

        with self.assertRaises(ValueError):
            terms.parse_terms_form(
                '''<form action="/unrelated"><input name="relayState" value="wrong"></form>
                   <form action="/terms-and-conditions"><input name="_csrf" value="csrf"></form>'''
            )


if __name__ == "__main__":
    unittest.main()
