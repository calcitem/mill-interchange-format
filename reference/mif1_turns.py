"""Normative MIFTURN/1.0 projection over executable MSTATE replay."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .mif1 import (
    Session,
    parse_mfen,
    replay_mstate,
    validate_ruleset_envelope,
    validate_schema,
)


def project_logical_turns(
    mstate: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay and project primary/removal causal fragments without causedBySeq."""
    document = copy.deepcopy(dict(mstate))
    validate_schema(document, "mstate-1.0.schema.json")
    completed = replay_mstate(document, manifest=manifest)
    rules = validate_ruleset_envelope(document["ruleset"], manifest)
    origin = parse_mfen(document["origin"], rules)
    leading: list[dict[str, Any]] = []
    for entry in document["repetitionHistory"]:
        if entry["source"] != "pre-origin":
            break
        leading.append(copy.deepcopy(entry))
    session = Session(
        rules,
        origin,
        repetition_seed=leading,
        pre_origin_claims=document["preOriginClaims"],
    )
    fragments: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    if origin.obligations:
        active = {
            "kind": "origin-obligation",
            "removeEventSeqs": [],
            "status": "truncated",
        }
    else:
        session.stabilize_origin()
        if session.state.obligations:
            active = {
                "kind": "origin-stabilization",
                "removeEventSeqs": [],
                "status": "truncated",
            }

    independent_terminal = {
        "accept-draw",
        "claim-draw",
        "resign",
        "adjudicate",
    }
    for event in document["events"]:
        event_type = event["type"]
        if active is None and event_type in {"place", "move"}:
            active = {
                "kind": "logical-turn",
                "primaryEventSeq": event["seq"],
                "removeEventSeqs": [],
                "status": "truncated",
            }
        session.apply_event(event)
        if active is not None and event_type == "remove":
            active["removeEventSeqs"].append(event["seq"])
        if active is not None and not session.state.obligations:
            active["status"] = (
                "truncated" if event_type in independent_terminal else "complete"
            )
            fragments.append(active)
            active = None
    if active is not None:
        fragments.append(active)
    result = {
        "format": "MIFTURN/1.0",
        "profile": "logical-turn-v1",
        "sourceResumptionDigest": completed.resumption_digest,
        "fragments": fragments,
    }
    validate_schema(result, "mifturn-1.0.schema.json")
    return result
