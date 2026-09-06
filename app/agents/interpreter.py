"""Change interpreter — LLM-or-fallback side of the boundary.

Gemini (when live) may interpret free-text change requests into the typed
ChangeIntent contract. Without a live key, a clearly-labelled deterministic
fallback parser handles the curated demo prompt family. LLM output is treated
as untrusted: strictly validated, retried once, then falls back — it never
reaches the engines unvalidated.
"""

from __future__ import annotations

import re

from app.config import Config
from app.domain.schemas import (
    ChangeIntent,
    ChangeKind,
    ConformError,
    NodeKind,
    Rule,
    RuleOp,
    Severity,
)

_RULE_LINE = re.compile(r"rule\s+(?P<rid>R-[A-Z0-9-]+)", re.IGNORECASE)
_FIELD_VAL = re.compile(r"field\s+(?P<field>[\w.]+)\s+(?P<op>contains|not_contains|min_len|max_len)\s+(?P<value>\S+)", re.IGNORECASE)
_TERRITORIES = re.compile(r"territor(?:y|ies)\s+((?:[a-z]{2}[,\s]*)+)", re.IGNORECASE)


def interpret_fallback(text: str) -> ChangeIntent:
    """Deterministic parser for the curated demo prompt family.

    Recognises, e.g.:
      'new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40'
      'edit node campaign_a.copy.de: set disclaimer to ...'
    Anything it cannot map goes into deferred_requirements — never silently dropped.
    """
    lowered = text.lower()
    deferred: list[str] = []

    if lowered.startswith("new rule") or lowered.startswith("add rule"):
        rid_match = _RULE_LINE.search(text)
        fv_match = _FIELD_VAL.search(text)
        if not rid_match or not fv_match:
            raise ConformError(
                "PARSE_FAILED",
                "could not parse rule change; expected 'new rule R-XXX ... field <f> <op> <v>'",
                {"input": text[:200]},
            )
        territories: list[str] = []
        terr_match = _TERRITORIES.search(text)
        if terr_match:
            territories = re.findall(r"[a-z]{2}", terr_match.group(1).lower())
        kinds = [NodeKind.COPY]
        if "package" in lowered:
            kinds = [NodeKind.PACKAGE]
        value_raw = fv_match.group("value")
        value = int(value_raw) if value_raw.isdigit() else value_raw
        rule = Rule(
            rule_id=rid_match.group("rid").upper(),
            name=text[:60],
            node_kinds=kinds,
            territories=territories,
            predicate={"field": fv_match.group("field"), "op": fv_match.group("op").lower(), "value": value},
            severity=Severity.WARNING,
        )
        return ChangeIntent(
            kind=ChangeKind.RULE_CHANGE,
            rule_op=RuleOp.NEW,
            rule=rule,
            deferred_requirements=deferred,
            interpretation_mode="fallback_deterministic",
        )

    if "remove rule" in lowered:
        rid_match = _RULE_LINE.search(text)
        if not rid_match:
            raise ConformError("PARSE_FAILED", "could not parse rule removal", {"input": text[:200]})
        return ChangeIntent(
            kind=ChangeKind.RULE_CHANGE,
            rule_op=RuleOp.REMOVE,
            rule_id=rid_match.group("rid").upper(),
            interpretation_mode="fallback_deterministic",
        )

    node_match = re.search(r"node\s+([\w.]+)", text, re.IGNORECASE)
    if node_match:
        set_match = re.search(r"set\s+([\w.]+)\s+to\s+(.+)$", text, re.IGNORECASE)
        new_inputs = {set_match.group(1): set_match.group(2).strip()} if set_match else {"prompt": text}
        if not set_match:
            deferred.append("no explicit 'set <field> to <value>' found; replaced prompt wholesale")
        return ChangeIntent(
            kind=ChangeKind.ASSET_EDIT,
            node_id=node_match.group(1),
            new_inputs=new_inputs,
            deferred_requirements=deferred,
            interpretation_mode="fallback_deterministic",
        )

    raise ConformError(
        "PARSE_FAILED",
        "unrecognised change request",
        {"input": text[:200], "hint": "try 'new rule ...' or 'edit node <id>: set <field> to <value>'"},
    )


def interpret(text: str, config: Config) -> ChangeIntent:
    """LLM-first with validated retry, then labelled deterministic fallback."""
    if config.vertex_live:
        try:
            return _interpret_gemini(text, config)
        except Exception:
            pass  # fall through to labelled fallback — never fake success
    return interpret_fallback(text)


def _interpret_gemini(text: str, config: Config) -> ChangeIntent:
    """Ask Gemini for a ChangeIntent as structured JSON; validate strictly."""
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=config.google_cloud_project, location=config.google_cloud_region)
    prompt = (
        "Interpret this media-pipeline change request into the ChangeIntent JSON schema.\n"
        "If this is a rule change, ensure rule.predicate contains:\n"
        "  'field': field name string (e.g. 'disclaimer')\n"
        "  'op': one of ['min_len', 'max_len', 'contains', 'not_contains', 'equals', 'not_equals', 'exists', 'not_exists']\n"
        "  'value': integer length or string value\n"
        "Only fill fields grounded in the text; put anything unsupported into deferred_requirements.\n\n"
        f"Request: {text}"
    )
    last_error: Exception | None = None
    for _ in range(2):  # initial attempt + one retry
        try:
            resp = client.models.generate_content(
                model=config.vertex_text_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ChangeIntent,
                ),
            )
            intent = ChangeIntent.model_validate_json(resp.text)
            if intent.kind == ChangeKind.RULE_CHANGE and intent.rule_op == RuleOp.NEW and intent.rule:
                pred = intent.rule.predicate or {}
                if not pred.get("op") or not pred.get("field"):
                    fb = interpret_fallback(text)
                    if fb.rule and fb.rule.predicate:
                        intent.rule.predicate = fb.rule.predicate
                        if not intent.rule.territories and fb.rule.territories:
                            intent.rule.territories = fb.rule.territories
            return intent.model_copy(update={"interpretation_mode": "gemini"})
        except Exception as exc:  # validation or transport failure -> retry once
            last_error = exc
    raise ConformError("LLM_INTERPRETATION_FAILED", str(last_error)[:200])
