"""Helpers for the Volkswagen identity-provider terms form."""

from __future__ import annotations

from html.parser import HTMLParser


REQUIRED_TERMS_FIELDS = frozenset(
    {"_csrf", "relayState", "hmac", "countryOfResidence"}
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
        raise ValueError("Identity terms form is missing required fields")

    return parser.action, {
        field: parser.fields[field] for field in REQUIRED_TERMS_FIELDS
    }
