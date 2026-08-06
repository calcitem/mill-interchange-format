"""Non-normative NDJSON adapter for exercising the MIF 1.0 reference model."""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .mif1 import (
    MIFError,
    PLAYER_ORDER,
    POINT_INDEX,
    Rules,
    Session,
    jcs_digest,
    parse_mfen,
    replay_mstate,
    require,
    validate_ruleset_envelope,
    validate_schema,
)
from .mif1_key import canonicalize_mpk
from .mif1_transform import (
    transform_decision_state,
    transform_mifpos,
    transform_mstate,
    validate_invariance,
)
from .mif1_turns import project_logical_turns


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "mif-1.0"
MESSAGE_SCHEMA = ROOT / "interop" / "schema" / "adapter-message-v1.schema.json"
CAPABILITY = ARTIFACT / "corpus" / "instances" / "mifcap.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _message_validator() -> Draft202012Validator:
    registry = Registry()
    for path in sorted((ARTIFACT / "schema").glob("*.json")):
        document = _read_json(path)
        registry = registry.with_resource(
            document["$id"], Resource.from_contents(document)
        )
    schema = _read_json(MESSAGE_SCHEMA)
    registry = registry.with_resource(
        schema["$id"], Resource.from_contents(schema)
    )
    return Draft202012Validator(schema, registry=registry)


def validate_message(message: Mapping[str, Any]) -> None:
    errors = sorted(
        _message_validator().iter_errors(message),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        first = errors[0]
        pointer = "".join(f"/{token}" for token in first.absolute_path)
        raise MIFError(
            "x-interop-message-invalid",
            first.message,
            category="syntax",
            instance_path=pointer,
        )


def _payload_members(
    payload: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
) -> None:
    missing = required.difference(payload)
    extra = set(payload).difference(required | optional)
    require(
        not missing,
        "x-interop-payload-invalid",
        f"missing payload members: {sorted(missing)}",
        category="syntax",
    )
    require(
        not extra,
        "x-interop-payload-invalid",
        f"unknown payload members: {sorted(extra)}",
        category="syntax",
    )


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    require(
        isinstance(value, Mapping),
        "x-interop-payload-invalid",
        f"{name} must be an object",
        category="syntax",
    )
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    require(
        isinstance(value, list),
        "x-interop-payload-invalid",
        f"{name} must be an array",
        category="syntax",
    )
    return value


def _require_string(value: Any, name: str) -> str:
    require(
        isinstance(value, str),
        "x-interop-payload-invalid",
        f"{name} must be a string",
        category="syntax",
    )
    return value


def _require_boolean(value: Any, name: str) -> bool:
    require(
        isinstance(value, bool),
        "x-interop-payload-invalid",
        f"{name} must be a boolean",
        category="syntax",
    )
    return value


def _snapshot(
    session: Session,
    rules: Rules,
    *,
    boundary: str,
    event_seq: int | None,
) -> dict[str, Any]:
    decision = session.decision_state()
    validate_schema(decision, "decision-state-v1.schema.json")
    return {
        "boundary": boundary,
        "eventSeq": event_seq,
        "current": session.state.serialize(rules),
        "repetitionHistory": copy.deepcopy(session.repetition_history),
        "claims": copy.deepcopy(session.claims),
        "claimRights": copy.deepcopy(session.claim_rights),
        "decisionState": decision,
        "decisionDigest": jcs_digest(decision),
    }


def _execute(
    manifest: Mapping[str, Any],
    origin: str,
    events: list[Mapping[str, Any]],
    repetition_seed: list[Mapping[str, Any]],
    pre_origin_claims: list[Mapping[str, Any]],
) -> tuple[Rules, Session, list[dict[str, Any]]]:
    rules = Rules(manifest)
    state = parse_mfen(origin, rules)
    session = Session(
        rules,
        state,
        repetition_seed=repetition_seed,
        pre_origin_claims=pre_origin_claims,
    )
    session.stabilize_origin()
    trace = [_snapshot(session, rules, boundary="origin", event_seq=None)]
    for event in events:
        session.apply_event(event)
        trace.append(
            _snapshot(
                session,
                rules,
                boundary="event",
                event_seq=event["seq"],
            )
        )
    return rules, session, trace


def _leading_pre_origin_history(
    history: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in history:
        if entry["source"] != "pre-origin":
            break
        result.append(copy.deepcopy(dict(entry)))
    return result


def _capabilities(payload: Mapping[str, Any]) -> dict[str, Any]:
    _payload_members(payload, required=set())
    capabilities = _read_json(CAPABILITY)
    validate_schema(capabilities, "mifcap-1.0.schema.json")
    return {"capabilities": capabilities}


def _canonicalize(payload: Mapping[str, Any]) -> dict[str, Any]:
    _payload_members(
        payload,
        required={"format", "value"},
        optional={"manifest"},
    )
    format_name = _require_string(payload["format"], "format")
    value = _require_string(payload["value"], "value")
    require(
        format_name in {"MFEN/1.0", "MPK/1.0"},
        "unsupported-profile",
        f"reference adapter cannot canonicalize {format_name}",
        category="unsupported",
    )
    manifest = payload.get("manifest")
    if manifest is None:
        raise MIFError(
            "manifest-missing",
            "MFEN canonicalization requires an exact manifest",
            category="integrity",
        )
    manifest = _require_mapping(manifest, "manifest")
    if format_name == "MPK/1.0":
        return {"value": canonicalize_mpk(value, manifest)}
    rules = Rules(manifest)
    state = parse_mfen(value, rules)
    return {"value": state.serialize(rules)}


def _execute_operation(payload: Mapping[str, Any]) -> dict[str, Any]:
    _payload_members(
        payload,
        required={
            "manifest",
            "origin",
            "events",
            "repetitionSeed",
            "preOriginClaims",
        },
    )
    manifest = _require_mapping(payload["manifest"], "manifest")
    origin = _require_string(payload["origin"], "origin")
    events = _require_list(payload["events"], "events")
    repetition_seed = _require_list(payload["repetitionSeed"], "repetitionSeed")
    pre_origin_claims = _require_list(payload["preOriginClaims"], "preOriginClaims")
    for index, event in enumerate(events):
        _require_mapping(event, f"events/{index}")
    for index, entry in enumerate(repetition_seed):
        _require_mapping(entry, f"repetitionSeed/{index}")
    for index, claim in enumerate(pre_origin_claims):
        _require_mapping(claim, f"preOriginClaims/{index}")
    _, _, trace = _execute(
        manifest,
        origin,
        events,
        repetition_seed,
        pre_origin_claims,
    )
    return {"trace": trace, "final": copy.deepcopy(trace[-1])}


def _replay(payload: Mapping[str, Any]) -> dict[str, Any]:
    _payload_members(payload, required={"mstate"}, optional={"manifest"})
    mstate = _require_mapping(payload["mstate"], "mstate")
    manifest = payload.get("manifest")
    if manifest is not None:
        manifest = _require_mapping(manifest, "manifest")
    validate_schema(mstate, "mstate-1.0.schema.json")
    rules = validate_ruleset_envelope(mstate["ruleset"], manifest)
    _, _, trace = _execute(
        rules.manifest,
        mstate["origin"],
        mstate["events"],
        _leading_pre_origin_history(mstate["repetitionHistory"]),
        mstate["preOriginClaims"],
    )
    replay = replay_mstate(mstate, manifest=manifest)
    return {
        "current": replay.state.serialize(rules),
        "trace": trace,
        "repetitionHistory": replay.repetition_history,
        "claims": replay.claims,
        "claimRights": replay.claim_rights,
        "decisionState": replay.decision_state,
        "decisionDigest": replay.decision_digest,
        "resumptionState": replay.resumption_state,
        "resumptionDigest": replay.resumption_digest,
    }


def _transform(payload: Mapping[str, Any]) -> dict[str, Any]:
    _payload_members(
        payload,
        required={
            "kind",
            "document",
            "transform",
            "verifyReplay",
            "requireEquivalence",
        },
        optional={"manifest", "repetitionHistory", "invariance"},
    )
    kind = _require_string(payload["kind"], "kind")
    manifest = payload.get("manifest")
    if manifest is not None:
        manifest = _require_mapping(manifest, "manifest")
    transform = _require_string(payload["transform"], "transform")
    document = _require_mapping(payload["document"], "document")
    verify_replay = _require_boolean(payload["verifyReplay"], "verifyReplay")
    require_equivalence = _require_boolean(
        payload["requireEquivalence"], "requireEquivalence"
    )
    repetition_history = payload.get("repetitionHistory")
    if repetition_history is not None:
        repetition_history = _require_list(
            repetition_history, "repetitionHistory"
        )
    invariance = payload.get("invariance")
    if invariance is not None:
        invariance = _require_mapping(invariance, "invariance")
    if kind in {"mstate", "mifpos"}:
        validate_schema(document, f"{kind}-1.0.schema.json")
        rules = validate_ruleset_envelope(document["ruleset"], manifest)
    elif kind == "decision-state":
        require(
            manifest is not None,
            "manifest-missing",
            "decision transform requires an exact manifest",
            category="integrity",
        )
        validate_schema(document, "decision-state-v1.schema.json")
        rules = Rules(manifest)
    else:
        raise MIFError(
            "unsupported-profile",
            f"unsupported transform input kind {kind}",
            category="unsupported",
        )
    if require_equivalence:
        validate_invariance(invariance, rules, transform)
    if kind == "mstate":
        transformed = transform_mstate(
            document,
            manifest=manifest,
            transform=transform,
            verify_replay=verify_replay,
        )
        replay = replay_mstate(transformed, manifest=manifest)
        return {
            "document": transformed,
            "decisionState": replay.decision_state,
            "decisionDigest": replay.decision_digest,
            "resumptionState": replay.resumption_state,
            "resumptionDigest": replay.resumption_digest,
        }
    if kind == "mifpos":
        transformed = transform_mifpos(
            document,
            manifest=manifest,
            transform=transform,
        )
        return {"document": transformed}
    transformed = transform_decision_state(
        document,
        manifest=manifest,
        transform=transform,
        repetition_history=repetition_history,
    )
    return {"document": transformed}


def _project_logical_turns(payload: Mapping[str, Any]) -> dict[str, Any]:
    _payload_members(payload, required={"mstate"}, optional={"manifest"})
    mstate = _require_mapping(payload["mstate"], "mstate")
    manifest = payload.get("manifest")
    if manifest is not None:
        manifest = _require_mapping(manifest, "manifest")
    document = project_logical_turns(
        mstate,
        manifest=manifest,
    )
    return {"document": document}


def _project_legal_actions(payload: Mapping[str, Any]) -> dict[str, Any]:
    _payload_members(payload, required={"manifest", "current"})
    manifest = _require_mapping(payload["manifest"], "manifest")
    current = _require_string(payload["current"], "current")
    rules = Rules(manifest)
    state = parse_mfen(current, rules)
    canonical = state.serialize(rules)
    session = Session(rules, state)
    session.stabilize_origin()
    require(
        session.state.serialize(rules) == canonical,
        "unstabilized-boundary",
        "legal action projection requires a stable, pending-obligation, or terminal state",
        category="inconsistent",
    )
    actions = session.legal_actions()

    def action_key(action: Mapping[str, Any]) -> tuple[int, int, int]:
        action_type = action["type"]
        if action_type == "place":
            return 0, POINT_INDEX[action["at"]], 0
        if action_type == "move":
            return 1, POINT_INDEX[action["from"]], POINT_INDEX[action["to"]]
        target = action["target"]
        if target["zone"] == "board":
            return 2, 0, POINT_INDEX[target["at"]]
        return 2, 1, PLAYER_ORDER[target["player"]]

    actions.sort(key=action_key)
    document = {
        "profile": "legal-actions-v1",
        "stateProfile": "mill24-state-v1",
        "semanticDigest": rules.semantic_digest,
        "current": canonical,
        "actions": actions,
    }
    return {"document": document}


OPERATIONS = {
    "capabilities": _capabilities,
    "canonicalize": _canonicalize,
    "execute": _execute_operation,
    "replay": _replay,
    "transform": _transform,
    "project-legal-actions": _project_legal_actions,
    "project-logical-turns": _project_logical_turns,
}


def handle_request(request: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(request))
    validate_message(document)
    request_id = document["requestId"]
    operation = document["operation"]
    try:
        result = OPERATIONS[operation](document["payload"])
        response: dict[str, Any] = {
            "protocol": "MIF-INTEROP/1",
            "kind": "response",
            "requestId": request_id,
            "operation": operation,
            "status": "ok",
            "result": result,
        }
    except MIFError as exc:
        response = {
            "protocol": "MIF-INTEROP/1",
            "kind": "response",
            "requestId": request_id,
            "operation": operation,
            "status": "error",
            "diagnostics": exc.diagnostic(),
        }
    validate_message(response)
    return response
