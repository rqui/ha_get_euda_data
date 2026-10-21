"""Helpers for the Volkswagen identity-provider terms form."""

from __future__ import annotations

from html.parser import HTMLParser
import ast
import json
import re


REQUIRED_TERMS_FIELDS = frozenset(
    {"_csrf", "relayState", "hmac"}
)


class _TermsFormParser(HTMLParser):
    """Extract the form action and hidden form values without extra deps."""

    def __init__(self) -> None:
        super().__init__()
        self.action: str | None = None
        self.fields: dict[str, str] = {}
        self._in_terms_form = False
        self.scripts: list[str] = []
        self._script: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script" and not attributes.get("src"):
            self._script = []
        if tag == "form" and self.action is None:
            action = attributes.get("action")
            if action is not None and "terms-and-conditions" in action:
                self.action = action
                self._in_terms_form = True
        if tag == "input" and self._in_terms_form:
            name = attributes.get("name")
            value = attributes.get("value")
            if name is not None and value is not None:
                self.fields[name] = value

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None
        if tag == "form" and self._in_terms_form:
            self._in_terms_form = False

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)


def _script_string(script: str, key: str) -> str:
    """Read a string literal, never execute the identity provider's JavaScript."""
    match = re.search(
        rf"\b{re.escape(key)}\s*:\s*(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')",
        script,
    )
    if match is None:
        raise ValueError(f"Identity template missing {key}")
    # literal_eval accepts both quoting styles used by the provider. It cannot
    # evaluate calls/identifiers; only the matched quoted literal reaches it.
    value = ast.literal_eval(match[1])
    if not isinstance(value, str) or not value:
        raise ValueError(f"Identity template has empty {key}")
    return value


def _rendered_terms_form(scripts: list[str]) -> tuple[str, dict[str, str]]:
    """Reconstruct the POST emitted by VW's client-rendered terms page.

    Since October 2026 the HTML can contain no form at all. The public
    signIn.bundle.js renders it from _IDK.templateModel. Decode its JSON only;
    never follow legalDocuments.saveLink (an internal service URL), execute JS,
    or retain the session's CSRF/hmac/relayState in logs or disk fixtures.
    """
    candidates = [s for s in scripts if re.search(r"\bwindow\._IDK\s*=", s)]
    if len(candidates) != 1:
        raise ValueError("Identity terms template not found or ambiguous")
    script = candidates[0]
    match = re.search(r"\btemplateModel\s*:\s*", script)
    if match is None:
        raise ValueError("Identity terms template model missing")
    model, _ = json.JSONDecoder().raw_decode(script[match.end():].lstrip())
    if not isinstance(model, dict) or model.get("template") != "termsAndConditions":
        raise ValueError("Unexpected identity template")
    client = model.get("clientLegalEntityModel", {}).get("clientId", "")
    if not isinstance(client, str) or not re.fullmatch(r"[A-Za-z0-9_.@-]+", client):
        raise ValueError("Invalid identity terms client")
    if _script_string(script, "csrf_parameterName") != "_csrf":
        raise ValueError("Unexpected identity CSRF parameter")
    data = {"_csrf": _script_string(script, "csrf_token")}
    for key in ("hmac", "relayState", "countryOfResidence"):
        value = model.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Identity terms template missing {key}")
        data[key] = value
    documents = model.get("legalDocuments")
    if not isinstance(documents, list) or not documents or len(documents) > 20:
        raise ValueError("Identity legal documents missing or invalid")
    # These are exactly the hidden inputs rendered by the official bundle.
    # This helper constructs data only; the connection retains origin checks
    # and owns the explicit acceptance POST, as for the legacy HTML form.
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValueError("Invalid identity legal document")
        for key in ("name", "language", "version", "countryCode"):
            value = document.get(key)
            if not isinstance(value, str) or not value:
                raise ValueError(f"Identity legal document missing {key}")
            data[f"legalDocuments[{index}].{key}"] = value
        for key in ("updated", "skippable", "declinable"):
            value = document.get(key)
            if not isinstance(value, bool):
                raise ValueError(f"Identity legal document missing {key}")
            data[f"legalDocuments[{index}].{key}"] = "yes" if value else "no"
    return f"/signin-service/v1/{client}/terms-and-conditions", data


def parse_terms_form(html: str) -> tuple[str, dict[str, str]]:
    """Return the identity terms form action and mandatory POST data."""
    parser = _TermsFormParser()
    parser.feed(html)
    parser.close()

    # Keep legacy forms authoritative: never fill a broken HTML form with
    # session values from an unrelated script. Fall back only if no form exists.
    if parser.action is None:
        return _rendered_terms_form(parser.scripts)
    missing = REQUIRED_TERMS_FIELDS.difference(parser.fields)
    if parser.action is None or missing:
        missing_names = ", ".join(sorted(missing))
        available_names = ", ".join(sorted(parser.fields))
        raise ValueError(
            "Identity terms form missing required fields: "
            f"{missing_names}; available fields: {available_names}"
        )

    return parser.action, parser.fields


# Values that unambiguously mean "no"/"decline" for a marketing-consent choice.
_DECLINE_VALUES = frozenset({"false", "no", "0", "decline", "declined", "reject", "rejected", "disagree"})
# Values that unambiguously mean "yes"/"accept" - used only to confirm a field is a
# genuine binary consent choice before we trust its "decline" option.
_ACCEPT_VALUES = frozenset({"true", "yes", "1", "accept", "accepted", "agree", "agreed"})


class _MarketingConsentFormParser(HTMLParser):
    """Extract the marketing-consent form action, hidden fields, and the set of
    values offered for each named input/button, without extra dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self.action: str | None = None
        self.hidden_fields: dict[str, str] = {}
        self.choices: dict[str, list[str]] = {}
        self._in_consent_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form" and self.action is None:
            action = attributes.get("action")
            if action is not None and "consent/marketing" in action:
                self.action = action
                self._in_consent_form = True
        if not self._in_consent_form:
            return
        if tag == "input":
            name = attributes.get("name")
            value = attributes.get("value")
            input_type = (attributes.get("type") or "text").lower()
            if name is None or value is None:
                return
            if input_type in ("hidden", "text"):
                self.hidden_fields[name] = value
            elif input_type in ("radio", "checkbox", "submit"):
                self.choices.setdefault(name, []).append(value)
        elif tag == "button":
            name = attributes.get("name")
            value = attributes.get("value")
            if name is not None and value is not None:
                self.choices.setdefault(name, []).append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._in_consent_form:
            self._in_consent_form = False


def parse_marketing_consent_form(html: str) -> tuple[str, dict[str, str]]:
    """Return the marketing-consent form action and POST data that declines it.

    Only auto-declines when a field offers a clearly-labelled binary
    accept/decline choice (one recognised "yes" value and one recognised "no"
    value). Anything ambiguous raises ValueError so the caller can fall back
    to asking a human to answer the question in the browser instead of
    guessing and risking an accidental opt-in to marketing.
    """
    parser = _MarketingConsentFormParser()
    parser.feed(html)
    parser.close()

    if parser.action is None:
        raise ValueError("Marketing consent form not found on page")

    decline_field = None
    decline_value = None
    for name, values in parser.choices.items():
        normalised = {v.strip().lower(): v for v in values}
        has_decline = _DECLINE_VALUES.intersection(normalised)
        has_accept = _ACCEPT_VALUES.intersection(normalised)
        if has_decline and has_accept:
            decline_field = name
            decline_value = normalised[next(iter(has_decline))]
            break

    if decline_field is None:
        available = ", ".join(sorted(parser.choices)) or "none"
        raise ValueError(
            "Could not find an unambiguous decline option in the marketing "
            f"consent form; candidate fields: {available}"
        )

    form_data = dict(parser.hidden_fields)
    form_data[decline_field] = decline_value
    return parser.action, form_data
