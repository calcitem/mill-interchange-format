"""RFC 8785 JSON Canonicalization Scheme helpers for MIF 1.0.

The standard library's ``json.dumps(sort_keys=True)`` is not JCS: Python
orders object names by Unicode scalar value, while RFC 8785 requires UTF-16
code-unit order, and Python's default binary64 spelling differs at the
ECMAScript fixed/exponent boundaries.  Keep the implementation dependency-free
so the reference model, artifact checkers, and interoperability harness all
exercise exactly the same canonicalization code.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


MAX_EXACT_INTEGER = 9007199254740991


class JCSValueError(ValueError):
    """A value is outside the MIF 1.0 UTF-8 I-JSON data model."""


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _reject_surrogates(value: str, path: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise JCSValueError(f"unpaired surrogate at {path or '/'}")


def validate_ijson(value: Any, *, path: str = "") -> None:
    """Validate the MIF 1.0 UTF-8 I-JSON value space recursively."""

    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        _reject_surrogates(value, path)
        return
    if isinstance(value, int):
        if not 0 <= value <= MAX_EXACT_INTEGER:
            raise JCSValueError(
                f"integer outside MIF exact range at {path or '/'}"
            )
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise JCSValueError(f"non-finite number at {path or '/'}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_ijson(item, path=f"{path}/{index}")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise JCSValueError(f"non-string member name at {path or '/'}")
            member_path = f"{path}/{_pointer_token(key)}"
            _reject_surrogates(key, member_path)
            validate_ijson(item, path=member_path)
        return
    raise JCSValueError(
        f"unsupported JSON value at {path or '/'}: {type(value).__name__}"
    )


def _utf16_sort_key(value: str) -> bytes:
    return value.encode("utf-16-be")


def _serialize_number(value: float) -> str:
    """Return the RFC 8785/ECMAScript spelling of one finite binary64."""

    if value == 0:
        return "0"

    negative = value < 0
    text = repr(abs(value)).lower()
    if "e" in text:
        coefficient, exponent_text = text.split("e", 1)
        exponent = int(exponent_text)
        digits = coefficient.replace(".", "")
        decimal_position = coefficient.find(".")
        if decimal_position < 0:
            decimal_position = len(coefficient)
        adjusted = decimal_position + exponent

        if 1e-6 <= abs(value) < 1e21:
            if adjusted <= 0:
                text = "0." + ("0" * -adjusted) + digits
            elif adjusted >= len(digits):
                text = digits + ("0" * (adjusted - len(digits)))
            else:
                text = digits[:adjusted] + "." + digits[adjusted:]
        else:
            coefficient = coefficient.rstrip("0").rstrip(".")
            sign = "+" if exponent >= 0 else "-"
            text = f"{coefficient}e{sign}{abs(exponent)}"
    elif text.endswith(".0"):
        text = text[:-2]

    return f"-{text}" if negative else text


def _jcs_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _serialize_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(_jcs_text(item) for item in value) + "]"
    if isinstance(value, Mapping):
        members = []
        for key in sorted(value, key=_utf16_sort_key):
            encoded_key = json.dumps(key, ensure_ascii=False, separators=(",", ":"))
            members.append(f"{encoded_key}:{_jcs_text(value[key])}")
        return "{" + ",".join(members) + "}"
    raise AssertionError(f"unvalidated JSON value: {type(value).__name__}")


def jcs_bytes(value: Any) -> bytes:
    """Serialize a MIF I-JSON value using RFC 8785 JCS."""

    validate_ijson(value)
    return _jcs_text(value).encode("utf-8")


def jcs_digest(value: Any) -> str:
    """Return a prefixed SHA-256 digest of the RFC 8785 representation."""

    return "sha256:" + hashlib.sha256(jcs_bytes(value)).hexdigest()
