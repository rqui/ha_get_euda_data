"""Tests for the identity-provider terms form parser."""

from __future__ import annotations

import importlib.util
import json
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
    def rendered_page(self, **changes):
        """Synthetic shape of October 2026's page, never live identity tokens."""
        model = {
            "template": "termsAndConditions",
            "clientLegalEntityModel": {"clientId": "example@apps_vw-dilab_com"},
            "hmac": "synthetic-hmac", "relayState": "synthetic-relay",
            "countryOfResidence": "ES",
            "legalDocuments": [{
                "name": "termsOfUse", "language": "es", "version": "4.0",
                "countryCode": "es", "updated": True,
                "skippable": False, "declinable": False,
                "changeSummary": "A brace } and an escaped quote: \"",
                "saveLink": "http://internal.invalid/not-a-browser-post-target",
            }],
        }
        model.update(changes)
        return '<script>window._IDK = {templateModel: ' + json.dumps(model, indent=2) + ''',
            csrf_parameterName: '_csrf', csrf_token: 'synthetic-csrf'};</script>'''

    def test_reads_client_rendered_terms_without_executing_javascript(self):
        action, data = load_terms_module().parse_terms_form(self.rendered_page())
        self.assertEqual(action, "/signin-service/v1/example@apps_vw-dilab_com/terms-and-conditions")
        self.assertEqual(data["_csrf"], "synthetic-csrf")
        self.assertEqual(data["hmac"], "synthetic-hmac")
        self.assertEqual(data["relayState"], "synthetic-relay")
        self.assertEqual(data["countryOfResidence"], "ES")
        self.assertEqual(data["legalDocuments[0].version"], "4.0")
        self.assertEqual(data["legalDocuments[0].updated"], "yes")
        self.assertEqual(data["legalDocuments[0].skippable"], "no")
        self.assertEqual(len(data), 11)
        self.assertNotIn("saveLink", data)

    def test_rejects_missing_rendered_session_fields(self):
        for key in ("hmac", "relayState", "countryOfResidence"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_terms_module().parse_terms_form(self.rendered_page(**{key: ""}))

    def test_rejects_missing_rendered_csrf(self):
        with self.assertRaises(ValueError):
            load_terms_module().parse_terms_form(self.rendered_page().replace("csrf_token:", "other_token:"))

    def test_rejects_other_templates_and_unsafe_client_paths(self):
        for changes in ({"template": "credentials"}, {"clientLegalEntityModel": {"clientId": "//other.invalid"}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                load_terms_module().parse_terms_form(self.rendered_page(**changes))

    def test_rejects_ambiguous_templates(self):
        with self.assertRaises(ValueError):
            load_terms_module().parse_terms_form(self.rendered_page() * 2)

    def test_rejects_missing_legal_document_metadata(self):
        with self.assertRaises(ValueError):
            load_terms_module().parse_terms_form(self.rendered_page(legalDocuments=[{"updated": True}]))

    def test_does_not_supplement_incomplete_legacy_form_from_script(self):
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            load_terms_module().parse_terms_form('<form action="/terms-and-conditions"></form>' + self.rendered_page())

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

        with self.assertRaisesRegex(ValueError, "missing required fields: hmac, relayState"):
            terms.parse_terms_form(
                '<form action="/terms-and-conditions"><input name="_csrf" value="x"></form>'
            )

    def test_ignores_inputs_outside_the_terms_form(self):
        terms = load_terms_module()

        with self.assertRaises(ValueError):
            terms.parse_terms_form(
                '''<form action="/unrelated"><input name="relayState" value="wrong"></form>
                   <form action="/terms-and-conditions"><input name="_csrf" value="csrf"></form>'''
            )


if __name__ == "__main__":
    unittest.main()
