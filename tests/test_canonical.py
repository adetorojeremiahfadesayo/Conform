"""Canonicalisation (JCS subset) invariants."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.canonical import canonicalize


def test_key_order_is_irrelevant():
    assert canonicalize({"b": 1, "a": 2}) == canonicalize({"a": 2, "b": 1})


def test_nested_key_order_is_irrelevant():
    a = {"x": {"b": 1, "a": [3, {"y": 1, "z": 2}]}}
    b = {"x": {"a": [3, {"z": 2, "y": 1}], "b": 1}}
    assert canonicalize(a) == canonicalize(b)


def test_no_insignificant_whitespace():
    assert canonicalize({"a": [1, 2]}) == '{"a":[1,2]}'


def test_scalars():
    assert canonicalize(None) == "null"
    assert canonicalize(True) == "true"
    assert canonicalize(False) == "false"
    assert canonicalize("hello") == '"hello"'
    assert canonicalize('a"b\\c') == '"a\\"b\\\\c"'


def test_numbers():
    assert canonicalize(42) == "42"
    assert canonicalize(3.0) == "3"  # integral floats normalise
    assert canonicalize(Decimal("2.50")) == '"2.50"'


def test_non_finite_rejected():
    with pytest.raises(ValueError):
        canonicalize(float("nan"))
    with pytest.raises(ValueError):
        canonicalize(float("inf"))


def test_unsupported_type_raises():
    with pytest.raises(TypeError):
        canonicalize(object())


def test_control_chars_escaped():
    assert canonicalize("a\tb") == '"a\\tb"'
    assert canonicalize("ab") == '"a\\u0001b"'
