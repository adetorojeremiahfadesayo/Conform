"""JCS-style canonical JSON serialisation (RFC 8785 subset) — deterministic core.

Canonicalisation is what makes fingerprints stable: the same semantic value
must serialise to the same bytes regardless of key order, whitespace, or
process. This implements the subset of RFC 8785 needed for our payloads:
- object keys sorted by UTF-16 code units (ASCII-sufficient here)
- no insignificant whitespace
- numbers: integers bare; non-integral floats via repr (shortest round-trip)
- str / bool / None verbatim JSON escapes
- Decimals serialised via str() (exact)
- datetimes serialised as ISO-8601 UTC

Deliberately NOT a general-purpose serialiser — unsupported types raise, they
never silently degrade.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _esc(s: str) -> str:
    out = ['"']
    for ch in s:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _num(n: int | float) -> str:
    if isinstance(n, bool):  # guard: bool is an int subclass
        raise TypeError("bool is not a number")
    if isinstance(n, int):
        return str(n)
    if not math.isfinite(n):
        raise ValueError("non-finite numbers are not canonicalisable")
    if n == int(n) and abs(n) < 2**53:
        return str(int(n))
    return repr(n)


def canonicalize(value: Any) -> str:
    """Return the canonical JSON string for a supported value."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _num(value)
    if isinstance(value, Decimal):
        return _esc(str(value))
    if isinstance(value, datetime):
        return _esc(value.isoformat())
    if isinstance(value, date):
        return _esc(value.isoformat())
    if isinstance(value, str):
        return _esc(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonicalize(v) for v in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        return "{" + ",".join(f"{_esc(str(k))}:{canonicalize(v)}" for k, v in items) + "}"
    if hasattr(value, "model_dump"):
        return canonicalize(value.model_dump(mode="python"))
    raise TypeError(f"unsupported type for canonicalisation: {type(value).__name__}")
