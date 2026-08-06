"""Coordinate transforms and MIFINV gating for the MIF 1.0 reference model."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .mif1 import (
    LINES,
    MILL24,
    POINTS,
    POINT_INDEX,
    MIFError,
    Obligation,
    Rules,
    Session,
    State,
    jcs_digest,
    parse_mfen,
    replay_mstate,
    require,
    validate_ruleset_envelope,
    validate_schema,
)


TRANSFORM_IDS = tuple(item["id"] for item in MILL24["transforms"])
LINE_BY_POINTS = {frozenset(points): line_id for line_id, points in LINES.items()}


def transform_point_index(index: int, transform: str) -> int:
    require(
        transform in TRANSFORM_IDS,
        "unsupported-profile",
        f"unknown transform {transform}",
        category="unsupported",
    )
    point = POINTS[index]
    x = ord(point[0]) - ord("d")
    y = int(point[1]) - 4
    operations = {
        "i": (x, y),
        "r90ccw": (-y, x),
        "r180": (-x, -y),
        "r90cw": (y, -x),
        "mirror-v": (-x, y),
        "mirror-h": (x, -y),
        "mirror-main": (y, x),
        "mirror-anti": (-y, -x),
    }
    tx, ty = operations[transform]
    return POINT_INDEX[f"{chr(ord('d') + tx)}{ty + 4}"]


def point_permutation(transform: str) -> tuple[int, ...]:
    return tuple(transform_point_index(index, transform) for index in range(24))


def line_permutation(transform: str) -> dict[int, int]:
    permutation = point_permutation(transform)
    result: dict[int, int] = {}
    for line_id, points in LINES.items():
        transformed = frozenset(permutation[index] for index in points)
        require(
            transformed in LINE_BY_POINTS,
            "unsupported-profile",
            f"transform {transform} does not preserve registered line {line_id}",
            category="unsupported",
        )
        result[line_id] = LINE_BY_POINTS[transformed]
    return result


def _transform_bitset(value: int, mapping: Mapping[int, int]) -> int:
    result = 0
    for source, target in mapping.items():
        if value & (1 << source):
            result |= 1 << target
    return result


def _transform_board_text(board: str, transform: str) -> str:
    source = list(board.replace("/", ""))
    require(len(source) == 24, "x-transform-input", "board is not 24 points")
    target = ["."] * 24
    for source_index, target_index in enumerate(point_permutation(transform)):
        target[target_index] = source[source_index]
    return "/".join("".join(target[start : start + 8]) for start in (0, 8, 16))


def transform_state(state: State, rules: Rules, transform: str) -> State:
    point_map = point_permutation(transform)
    line_map = line_permutation(transform)
    result = state.clone()
    result.board = ["."] * 24
    for source, target in enumerate(point_map):
        result.board[target] = state.board[source]
    for branch in result.obligations:
        for obligation in branch:
            if obligation.targets is not None:
                obligation.targets = {point_map[index] for index in obligation.targets}
            if obligation.scope is not None:
                obligation.scope = {point_map[index] for index in obligation.scope}
    if "lm" in result.semantic:
        for player in ("w", "b"):
            endpoints = result.semantic["lm"][player]
            result.semantic["lm"][player] = tuple(
                None if endpoint is None else point_map[endpoint]
                for endpoint in endpoints
            )
    if "ul" in result.semantic:
        for player in ("w", "b"):
            result.semantic["ul"][player] = _transform_bitset(
                result.semantic["ul"][player], line_map
            )
    result.obligations.sort(
        key=lambda branch: (
            MILL24["causeOrder"].index(branch[0].cause),
            ";".join(
                item.wire(deferred=index > 0 and item.zone == "b")
                for index, item in enumerate(branch)
            ),
        )
    )
    return result


def _transform_semantic_wire(
    semantic: Mapping[str, str],
    rules: Rules,
    transform: str,
) -> dict[str, str]:
    result = copy.deepcopy(dict(semantic))
    point_map = point_permutation(transform)
    line_map = line_permutation(transform)
    if "lm" in result:
        players = result["lm"].split(";")
        converted: list[str] = []
        for player in players:
            endpoints = []
            for endpoint in player.split(","):
                endpoints.append(
                    "-"
                    if endpoint == "-"
                    else POINTS[point_map[POINT_INDEX[endpoint]]]
                )
            converted.append(",".join(endpoints))
        result["lm"] = ";".join(converted)
    if "ul" in result:
        width = 4 if rules.manifest["topology"] == "mill24-orthogonal-v1" else 5
        result["ul"] = ",".join(
            f"{_transform_bitset(int(value, 16), line_map):0{width}x}"
            for value in result["ul"].split(",")
        )
    return result


def transform_observation(
    observation: Mapping[str, Any],
    rules: Rules,
    transform: str,
) -> dict[str, Any]:
    result = copy.deepcopy(dict(observation))
    result["board"] = _transform_board_text(result["board"], transform)
    result["semantic"] = _transform_semantic_wire(
        result["semantic"], rules, transform
    )
    return result


def transform_event(event: Mapping[str, Any], transform: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(event))
    point_map = point_permutation(transform)
    line_map = line_permutation(transform)
    for member in ("at", "from", "to"):
        if member in result:
            result[member] = POINTS[point_map[POINT_INDEX[result[member]]]]
    target = result.get("target")
    if isinstance(target, dict) and target.get("zone") == "board":
        target["at"] = POINTS[point_map[POINT_INDEX[target["at"]]]]
    if "interventionLine" in result:
        result["interventionLine"] = line_map[result["interventionLine"]]
    return result


def transform_mifpos(
    document: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any] | None,
    transform: str,
) -> dict[str, Any]:
    source = copy.deepcopy(dict(document))
    validate_schema(source, "mifpos-1.0.schema.json")
    rules = validate_ruleset_envelope(source["ruleset"], manifest)
    require(not source.get("extensions"), "unsupported-profile", "MIFPOS semantic extensions are unsupported", category="unsupported")
    state = parse_mfen(source["position"], rules)
    source["position"] = transform_state(state, rules, transform).serialize(rules)
    return source


def transform_mstate(
    document: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any] | None,
    transform: str,
    verify_replay: bool = True,
) -> dict[str, Any]:
    source = copy.deepcopy(dict(document))
    validate_schema(source, "mstate-1.0.schema.json")
    rules = validate_ruleset_envelope(source["ruleset"], manifest)
    require(not source.get("extensions"), "unsupported-profile", "MSTATE semantic extensions are unsupported", category="unsupported")
    source["origin"] = transform_state(
        parse_mfen(source["origin"], rules), rules, transform
    ).serialize(rules)
    source["current"] = transform_state(
        parse_mfen(source["current"], rules), rules, transform
    ).serialize(rules)
    source["events"] = [transform_event(event, transform) for event in source["events"]]
    source["repetitionHistory"] = [
        {
            **{key: copy.deepcopy(value) for key, value in entry.items() if key != "key"},
            "key": transform_observation(entry["key"], rules, transform),
        }
        for entry in source["repetitionHistory"]
    ]
    if verify_replay:
        replay_mstate(source, manifest=manifest)
    return source


def transform_decision_state(
    document: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    transform: str,
    repetition_history: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Transform a decision identity when its repetition root is materialized."""
    source = copy.deepcopy(dict(document))
    validate_schema(source, "decision-state-v1.schema.json")
    rules = Rules(manifest)
    require(
        source["semanticDigest"] == rules.semantic_digest,
        "semantic-digest-mismatch",
        "decision state and manifest semantic digests differ",
        category="integrity",
    )
    require(
        not source.get("extensions"),
        "unsupported-profile",
        "decision semantic extensions are unsupported",
        category="unsupported",
    )
    if source["repetitionSummary"] is not None:
        require(
            repetition_history is not None,
            "insufficient-transform-history",
            "decision repetition root requires its materialized active history",
            category="ineligible",
        )
    history = [] if repetition_history is None else [
        copy.deepcopy(dict(entry)) for entry in repetition_history
    ]
    semantic_fields = [
        f"{key}={value}" for key, value in sorted(source["semantic"].items())
    ]
    no_progress = 0 if source["noProgress"] is None else source["noProgress"]
    mfen = " ".join(
        [
            "MFEN/1.0",
            "mill24-state-v1",
            source["board"],
            source["side"],
            source["phase"],
            source["action"],
            f"{source['hands'][0]},{source['hands'][1]}",
            source["obligations"],
            str(no_progress),
            "0",
            source["outcome"],
            *semantic_fields,
        ]
    )
    state = parse_mfen(mfen, rules)
    materialized_summary = Session(
        rules, state, repetition_seed=history
    ).repetition_summary()
    require(
        materialized_summary == source["repetitionSummary"],
        "insufficient-transform-history",
        "materialized repetition history does not reconstruct the decision root",
        category="ineligible",
    )
    transformed_state = transform_state(state, rules, transform)
    transformed_history = [
        {
            **{key: copy.deepcopy(value) for key, value in entry.items() if key != "key"},
            "key": transform_observation(entry["key"], rules, transform),
        }
        for entry in history
    ]
    source["board"] = transformed_state.board_text()
    source["obligations"] = transformed_state.obligations_text()
    source["semantic"] = {
        key: transformed_state.semantic_wire_value(key, rules)
        for key in rules.required_state_keys
    }
    source["repetitionSummary"] = Session(
        rules, transformed_state, repetition_seed=transformed_history
    ).repetition_summary()
    validate_schema(source, "decision-state-v1.schema.json")
    return source


def validate_invariance(
    declaration: Mapping[str, Any] | None,
    rules: Rules,
    transform: str,
) -> None:
    require(
        declaration is not None,
        "transform-invariance-undeclared",
        "coordinate conversion has no exact invariance declaration",
        category="ineligible",
    )
    document = copy.deepcopy(dict(declaration))
    validate_schema(document, "mifinv-1.0.schema.json")
    expected_document = copy.deepcopy(document)
    supplied_digest = expected_document.pop("documentDigest")
    require(
        supplied_digest == jcs_digest(expected_document),
        "document-digest-mismatch",
        "MIFINV document digest mismatch",
        category="integrity",
    )
    require(
        document["semanticDigest"] == rules.semantic_digest
        and document["stateProfile"] == "mill24-state-v1"
        and document["transformProfile"] == "mill24-full-state-v1"
        and transform in document["transforms"],
        "transform-invariance-undeclared",
        "MIFINV does not cover the exact semantic/transform pair",
        category="ineligible",
    )
    require(
        not document["extensionTreatments"],
        "unsupported-profile",
        "reference runner implements no extension transform treatment",
        category="unsupported",
    )
