"""Helpers for the Volkswagen identity-provider terms form."""

from __future__ import annotations

from html.parser import HTMLParser


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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
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
        if tag == "form" and self._in_terms_form:
            self._in_terms_form = False


def parse_terms_form(html: str) -> tuple[str, dict[str, str]]:
    """Return the identity terms form action and mandatory POST data."""
    parser = _TermsFormParser()
    parser.feed(html)
    parser.close()

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
