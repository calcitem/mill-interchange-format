"""Structural MPK/1.0 parsing and canonicalization for the reference adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .mif1 import DIGEST_RE, UINT_MAX, UINT_RE, MIFError, Rules, require
from .mif1_transform import TRANSFORM_IDS, point_permutation


def _parse_uint(value: str, name: str) -> int:
    require(
        bool(UINT_RE.fullmatch(value)),
        "x-mpk-syntax",
        f"invalid unsigned integer for {name}",
        category="syntax",
    )
    result = int(value)
    require(
        result <= UINT_MAX,
        "integer-out-of-range",
        f"integer exceeds I-JSON range for {name}",
        category="syntax",
    )
    return result


def _transform_board(board: str, transform: str) -> str:
    target = ["."] * 24
    for source_index, target_index in enumerate(point_permutation(transform)):
        target[target_index] = board[source_index]
    return "".join(target)


def canonicalize_mpk(value: Any, manifest: Mapping[str, Any] | None) -> str:
    """Validate and canonicalize structural-d4-v1 under an exact MRS context."""

    if manifest is None:
        raise MIFError(
            "manifest-missing",
            "MPK binding requires an exact manifest",
            category="integrity",
        )
    rules = Rules(manifest)
    require(
        isinstance(value, str) and value.isascii(),
        "x-mpk-syntax",
        "MPK must be US-ASCII text",
        category="syntax",
    )
    fields = value.split(" ")
    require(
        all(fields),
        "x-mpk-syntax",
        "MPK fields require exactly one SPACE separator",
        category="syntax",
    )
    if len(fields) == 8 and fields[3] in {
        "structural-d4-v1",
        "structural-aut16-v1",
    }:
        raise MIFError(
            "mpk-semantic-digest-missing",
            "MPK semantic digest is missing",
            category="integrity",
        )
    require(
        len(fields) == 9,
        "x-mpk-syntax",
        "MPK/1.0 requires exactly nine fields for structural-d4-v1",
        category="syntax",
    )
    require(
        fields[0] == "MPK/1.0" and fields[1] == "mill24-state-v1",
        "unsupported-profile",
        "unsupported MPK signature or state profile",
        category="unsupported",
    )

    expected_reference = f"{rules.manifest['id']}@{rules.manifest['version']}"
    require(
        fields[2] == expected_reference,
        "manifest-conflict",
        "MPK ruleset reference differs from the resolved manifest",
        category="integrity",
    )
    if not DIGEST_RE.fullmatch(fields[3]):
        raise MIFError(
            "non-canonical-digest",
            "MPK semantic digest is not canonical lowercase SHA-256 text",
            category="canonical",
        )
    require(
        fields[3] == rules.semantic_digest,
        "semantic-digest-mismatch",
        "MPK semantic digest differs from the resolved manifest",
        category="integrity",
    )
    require(
        fields[4] == "structural-d4-v1",
        "unsupported-profile",
        "reference adapter implements only structural-d4-v1",
        category="unsupported",
    )

    board = fields[5]
    require(
        len(board) == 24 and all(piece in "WBwb." for piece in board),
        "x-mpk-syntax",
        "MPK board must contain exactly 24 registered piece characters",
        category="syntax",
    )
    require(
        fields[6] in {"w", "b"} and fields[7] in {"p", "m"},
        "x-mpk-syntax",
        "MPK side and phase must be active",
        category="syntax",
    )
    hands = fields[8].split(",")
    require(
        len(hands) == 2,
        "x-mpk-syntax",
        "MPK hands require white,black",
        category="syntax",
    )
    canonical_hands = (
        f"{_parse_uint(hands[0], 'white hand')},"
        f"{_parse_uint(hands[1], 'black hand')}"
    )

    prefix = " ".join(
        (
            "MPK/1.0",
            "mill24-state-v1",
            expected_reference,
            rules.semantic_digest,
            "structural-d4-v1",
        )
    )
    candidates = [
        " ".join(
            (
                prefix,
                _transform_board(board, transform),
                fields[6],
                fields[7],
                canonical_hands,
            )
        )
        for transform in TRANSFORM_IDS
    ]
    return min(candidates, key=lambda candidate: candidate.encode("ascii"))
