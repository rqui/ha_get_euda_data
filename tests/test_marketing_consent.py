"""Tests for the identity-provider marketing-consent form parser."""

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


class MarketingConsentFormParserTests(unittest.TestCase):
    def test_declines_a_radio_choice_with_clear_yes_no_values(self):
        terms = load_terms_module()

        action, data = terms.parse_marketing_consent_form(
            '''<form method="post" action="/signin-service/v1/client/consent/marketing">
                 <input type="hidden" name="_csrf" value="csrf-value">
                 <input type="hidden" name="relayState" value="relay-value">
                 <input type="radio" name="marketingConsent" value="true">
                 <input type="radio" name="marketingConsent" value="false">
               </form>'''
        )

        self.assertEqual(action, "/signin-service/v1/client/consent/marketing")
        self.assertEqual(
            data,
            {
                "_csrf": "csrf-value",
                "relayState": "relay-value",
                "marketingConsent": "false",
            },
        )

    def test_declines_via_a_named_submit_button_pair(self):
        terms = load_terms_module()

        action, data = terms.parse_marketing_consent_form(
            '''<form action="/consent/marketing">
                 <input type="hidden" name="hmac" value="hmac-value">
                 <button name="decision" value="accept">Accept</button>
                 <button name="decision" value="decline">Decline</button>
               </form>'''
        )

        self.assertEqual(data["decision"], "decline")
        self.assertEqual(data["hmac"], "hmac-value")

    def test_refuses_to_guess_when_no_clear_decline_option_exists(self):
        terms = load_terms_module()

        with self.assertRaisesRegex(ValueError, "unambiguous decline option"):
            terms.parse_marketing_consent_form(
                '''<form action="/consent/marketing">
                     <input type="hidden" name="_csrf" value="csrf-value">
                     <input type="checkbox" name="newsletter" value="subscribe">
                   </form>'''
            )

    def test_refuses_to_guess_when_form_is_missing(self):
        terms = load_terms_module()

        with self.assertRaisesRegex(ValueError, "not found"):
            terms.parse_marketing_consent_form(
                '<form action="/unrelated"><input name="x" value="y"></form>'
            )


if __name__ == "__main__":
    unittest.main()
