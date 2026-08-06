#!/usr/bin/env python3
"""Execute the candidate MIF 1.0 Python reference runner and its corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.mif1 import (  # noqa: E402
    MIFError,
    Rules,
    Session,
    parse_mfen,
    replay_mstate,
    semantic_projection,
    validate_schema,
)
from reference.jcs import JCSValueError, jcs_bytes, jcs_digest  # noqa: E402
from reference.mif1_transform import (  # noqa: E402
    TRANSFORM_IDS,
    point_permutation,
    transform_decision_state,
    transform_mstate,
    validate_invariance,
)
from reference.mif1_turns import project_logical_turns  # noqa: E402


ARTIFACT = ROOT / "artifacts" / "mif-1.0"
EXECUTABLE_VECTOR = ARTIFACT / "corpus" / "executable" / "reference-cases.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_capability_binding(
    vector: Mapping[str, Any], vector_path: Path
) -> None:
    capability = read_json(resolve(vector_path.parent, vector["capability"]))
    validate_schema(capability, "mifcap-1.0.schema.json")
    assert capability["implementation"] == {
        "name": "mif-python-reference-runner",
        "version": "candidate-2",
    }
    assert capability["suites"] == []
    corpus_digest = "sha256:" + hashlib.sha256(vector_path.read_bytes()).hexdigest()
    assert capability["testedCorpora"] == [
        {
            "classes": ["identity", "position", "replay", "ruleset", "transform"],
            "digest": corpus_digest,
        }
    ]


def resolve(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise AssertionError(f"vector path escapes repository: {relative}") from exc
    return path


def pointer_parts(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise AssertionError(f"invalid vector JSON Pointer: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def mutate(value: Any, mutations: list[Mapping[str, Any]]) -> Any:
    result = copy.deepcopy(value)
    for mutation in mutations:
        parts = pointer_parts(mutation["path"])
        parent = result
        for token in parts[:-1]:
            parent = parent[int(token)] if isinstance(parent, list) else parent[token]
        leaf = parts[-1]
        if mutation["op"] == "remove":
            if isinstance(parent, list):
                del parent[int(leaf)]
            else:
                del parent[leaf]
        elif mutation["op"] in {"add", "replace"}:
            replacement = copy.deepcopy(mutation["value"])
            if isinstance(parent, list):
                parent[int(leaf)] = replacement
            else:
                parent[leaf] = replacement
        else:
            raise AssertionError(f"unsupported vector mutation: {mutation['op']}")
    return result


def load_manifest(case: Mapping[str, Any], vector_path: Path) -> dict[str, Any]:
    manifest = read_json(resolve(vector_path.parent, case["manifest"]))
    return mutate(manifest, case.get("mutations", []))


def run_jcs_cases(vector: Mapping[str, Any], vector_path: Path) -> int:
    source_path = resolve(vector_path.parent, vector["jcsCases"])
    source = read_json(source_path)
    assert source["artifact"] == "mif-1.0-jcs-rfc8785-vectors"

    for case in source["numberSerialization"]:
        raw = bytes.fromhex(case["ieee754"])
        assert len(raw) == 8, case["ieee754"]
        value = struct.unpack(">d", raw)[0]
        assert jcs_bytes(value).decode("ascii") == case["expected"], case["ieee754"]

    ordering = source["utf16Ordering"]
    ordering_bytes = jcs_bytes(ordering["value"])
    assert ordering_bytes.hex() == ordering["expectedHex"]
    assert jcs_digest(ordering["value"]) == ordering["expectedSha256"]

    identity = source["mifAnnotationIdentity"]
    manifest = read_json(resolve(source_path.parent, identity["manifest"]))
    annotated = copy.deepcopy(manifest)
    annotated["annotations"] = copy.deepcopy(identity["annotations"])
    assert jcs_digest(annotated) == identity["expectedDocumentDigest"]
    assert (
        jcs_digest(semantic_projection(annotated))
        == identity["expectedSemanticDigest"]
    )

    for case in source["rejections"]:
        if "ieee754" in case:
            value = struct.unpack(">d", bytes.fromhex(case["ieee754"]))[0]
        elif "codePoint" in case:
            value = {"value": chr(case["codePoint"])}
        else:
            value = int(case["integerText"])
        try:
            jcs_bytes(value)
        except JCSValueError:
            pass
        else:
            raise AssertionError(f"JCS rejection unexpectedly passed: {case['id']}")

    return len(source["numberSerialization"]) + len(source["rejections"]) + 2


def run_replay_cases(vector: Mapping[str, Any], vector_path: Path) -> int:
    count = 0
    for case in vector["replayCases"]:
        manifest = load_manifest(case, vector_path)
        document = read_json(resolve(vector_path.parent, case["document"]))
        result = replay_mstate(document, manifest=manifest)
        assert result.decision_digest == case["expectedDecisionDigest"], case["id"]
        assert result.resumption_digest == case["expectedResumptionDigest"], case["id"]
        count += 1
    return count


def run_portable_replay_cases(vector: Mapping[str, Any], vector_path: Path) -> int:
    count = 0
    for case in vector["portableReplayCases"]:
        document = read_json(resolve(vector_path.parent, case["document"]))
        envelope_document = read_json(
            resolve(vector_path.parent, case["envelopeDocument"])
        )
        document["ruleset"] = copy.deepcopy(envelope_document["ruleset"])
        assert document["ruleset"]["mode"] == "portable", case["id"]
        assert "manifest" in document["ruleset"], case["id"]
        result = replay_mstate(document)
        assert result.decision_digest == case["expectedDecisionDigest"], case["id"]
        assert result.resumption_digest == case["expectedResumptionDigest"], case["id"]
        count += 1
    return count


def run_state_cases(vector: Mapping[str, Any], vector_path: Path) -> int:
    count = 0
    for case in vector["stateCases"]:
        manifest = load_manifest(case, vector_path)
        rules = Rules(manifest)
        state = (
            rules.normal_initial_state()
            if case.get("normalInitial")
            else parse_mfen(case["origin"], rules)
        )
        session = Session(rules, state)
        session.stabilize_origin()
        for event in case.get("events", []):
            session.apply_event(event)
        actual = session.state.serialize(rules)
        assert actual == case["expectedCurrent"], (
            f"{case['id']} checkpoint mismatch\nexpected {case['expectedCurrent']}\nactual   {actual}"
        )
        if "expectedHistoryEntries" in case:
            assert len(session.repetition_history) == case["expectedHistoryEntries"], case["id"]
        if "expectedEventObservations" in case:
            event_count = sum(
                entry["source"] == "event" for entry in session.repetition_history
            )
            assert event_count == case["expectedEventObservations"], case["id"]
        count += 1
    return count


def run_claim_cases(vector: Mapping[str, Any], vector_path: Path) -> int:
    count = 0
    for case in vector["claimLifecycleCases"]:
        manifest = load_manifest(case, vector_path)
        rules = Rules(manifest)
        origin = parse_mfen(case["origin"], rules)
        preview = Session(rules, origin)
        observation = preview.repetition_observation()
        seed = [
            {"source": "pre-origin", "key": copy.deepcopy(observation)}
            for _ in range(case["repeatOriginObservation"])
        ]
        session = Session(rules, origin, repetition_seed=seed)
        session.stabilize_origin()
        expected_code = case.get("expectedCode")
        try:
            for event in case["events"]:
                session.apply_event(event)
        except MIFError as exc:
            validate_schema(exc.diagnostic(), "mifdiag-1.0.schema.json")
            if expected_code is None or exc.code != expected_code:
                raise
        else:
            assert expected_code is None, f"{case['id']} expected {expected_code}"
            assert session.claim_rights == case["expectedClaimRights"], case["id"]
            if "expectedCurrent" in case:
                assert session.state.serialize(rules) == case["expectedCurrent"], case["id"]
        count += 1
    return count


def run_manifest_errors(vector: Mapping[str, Any], vector_path: Path) -> int:
    count = 0
    for case in vector["manifestErrorCases"]:
        manifest = load_manifest(case, vector_path)
        try:
            Rules(manifest)
        except MIFError as exc:
            validate_schema(exc.diagnostic(), "mifdiag-1.0.schema.json")
            assert exc.code == case["expectedCode"], case["id"]
        else:
            raise AssertionError(f"{case['id']} unexpectedly accepted")
        count += 1
    return count


def run_decision_transform_cases(
    vector: Mapping[str, Any], vector_path: Path
) -> int:
    count = 0
    for case in vector["decisionTransformCases"]:
        manifest = load_manifest(case, vector_path)
        document = read_json(resolve(vector_path.parent, case["document"]))
        expected_code = case.get("expectedCode")
        if expected_code is not None:
            try:
                transform_decision_state(
                    document,
                    manifest=manifest,
                    transform=case["transform"],
                )
            except MIFError as exc:
                validate_schema(exc.diagnostic(), "mifdiag-1.0.schema.json")
                assert exc.code == expected_code, case["id"]
            else:
                raise AssertionError(f"{case['id']} unexpectedly accepted")
        else:
            materialization = read_json(
                resolve(vector_path.parent, case["materialization"])
            )
            transforms = (
                TRANSFORM_IDS
                if case["transforms"] == "all-d4"
                else (case["transforms"],)
            )
            for transform in transforms:
                actual = transform_decision_state(
                    document,
                    manifest=manifest,
                    transform=transform,
                    repetition_history=materialization["repetitionHistory"],
                )
                transformed_mstate = transform_mstate(
                    materialization,
                    manifest=manifest,
                    transform=transform,
                )
                expected = replay_mstate(
                    transformed_mstate, manifest=manifest
                ).decision_state
                assert actual == expected, f"{case['id']}:{transform}"
        count += 1
    return count


def run_transform_cases(vector: Mapping[str, Any], vector_path: Path) -> int:
    count = 0
    for case in vector["transformCases"]:
        manifest = load_manifest(case, vector_path)
        rules = Rules(manifest)
        document = read_json(resolve(vector_path.parent, case["document"]))
        for transform in TRANSFORM_IDS:
            transformed = transform_mstate(
                document,
                manifest=manifest,
                transform=transform,
                verify_replay=True,
            )
            assert transformed["ruleset"] == document["ruleset"], case["id"]
        source_point = case["expectedPoint"]["input"]
        source_index = __import__("reference.mif1", fromlist=["POINT_INDEX"]).POINT_INDEX[source_point]
        target_index = point_permutation(case["transform"])[source_index]
        target_point = __import__("reference.mif1", fromlist=["POINTS"]).POINTS[target_index]
        assert target_point == case["expectedPoint"]["output"], case["id"]
        try:
            validate_invariance(None, rules, case["transform"])
        except MIFError as exc:
            validate_schema(exc.diagnostic(), "mifdiag-1.0.schema.json")
            assert exc.code == case["expectedGateCode"], case["id"]
        else:
            raise AssertionError(f"{case['id']} equivalence gate unexpectedly passed")
        count += 1
    return count


def run_turn_cases(vector: Mapping[str, Any], vector_path: Path) -> int:
    count = 0
    for case in vector["turnCases"]:
        manifest = load_manifest(case, vector_path)
        document = read_json(resolve(vector_path.parent, case["document"]))
        expected = read_json(resolve(vector_path.parent, case["expected"]))
        actual = project_logical_turns(document, manifest=manifest)
        assert actual == expected, case["id"]
        count += 1
    return count


BOARD_FULL_04_TO_10 = {
    "first-player-loses": "white-loses",
    "first-then-second-remove": "white-then-black-remove",
    "second-then-first-remove": "black-then-white-remove",
}


def convert_manifest_04_for_audit(source: Mapping[str, Any]) -> dict[str, Any]:
    manifest = copy.deepcopy(dict(source))
    manifest["format"] = "MRS/1.0"
    manifest["semanticsProfile"] = "mif-finite-rules-v3"
    old_action = manifest["boardFull"]["action"]
    manifest["placing"]["noLegalPrimaryAction"] = (
        "loss" if old_action == "disabled" else "apply-board-full"
    )
    manifest["boardFull"]["action"] = BOARD_FULL_04_TO_10.get(
        old_action, old_action
    )
    repetition = manifest["draw"]["repetition"]
    repetition["projection"] = "repetition-observation-v1"
    repetition["summary"] = "reset-count-smt-v1"
    manifest["draw"]["claimRights"] = {
        "profile": "stable-claim-rights-v1"
    }
    return manifest


def convert_mfen_04(value: str) -> str:
    return value.replace("MFEN/0.4", "MFEN/1.0", 1)


def convert_observation_04(
    key: Mapping[str, Any], rules: Rules
) -> dict[str, Any]:
    return {
        "profile": "repetition-observation-v1",
        "stateProfile": key["stateProfile"],
        "semanticDigest": rules.semantic_digest,
        "board": key["board"],
        "side": key["side"],
        "phase": key["phase"],
        "action": key["action"],
        "hands": copy.deepcopy(key["hands"]),
        "semantic": copy.deepcopy(key["semantic"]),
    }


def execute_historical_case(case: Mapping[str, Any]) -> str:
    vector_dir = ROOT / "conformance" / "vectors"
    source_manifest = read_json(resolve(vector_dir, case["manifest"]))
    rules = Rules(convert_manifest_04_for_audit(source_manifest))
    seed: list[dict[str, Any]] = []
    for entry in case.get("repetitionHistory", []):
        if entry["source"] != "pre-origin":
            break
        seed.append(
            {
                "source": "pre-origin",
                "key": convert_observation_04(entry["key"], rules),
            }
        )
    session = Session(
        rules,
        parse_mfen(convert_mfen_04(case["origin"]), rules),
        repetition_seed=seed,
        pre_origin_claims=case.get("preOriginClaims", []),
    )
    session.stabilize_origin()
    for event in case["events"]:
        session.apply_event(event)
    return session.state.serialize(rules)


def run_historical_audit(vector: Mapping[str, Any]) -> tuple[int, int]:
    source = read_json(ROOT / "conformance" / "vectors" / "mstate.json")
    cases = {case["id"]: case for case in source["validReplay"]}
    audit = vector["historicalMigrationAudit"]
    for case_id in audit["expectedMatches"]:
        actual = execute_historical_case(cases[case_id])
        expected = convert_mfen_04(cases[case_id]["current"])
        assert actual == expected, case_id
    for rejection in audit["sourceRejections"]:
        case = cases[rejection["id"]]
        actual = execute_historical_case(case)
        source_checkpoint = convert_mfen_04(case["current"])
        assert actual == rejection["correctedCurrent"], rejection["id"]
        assert actual != source_checkpoint, rejection["id"]
    return len(audit["expectedMatches"]), len(audit["sourceRejections"])


def run_corpus() -> None:
    vector = read_json(EXECUTABLE_VECTOR)
    validate_capability_binding(vector, EXECUTABLE_VECTOR)
    native = 0
    native += run_jcs_cases(vector, EXECUTABLE_VECTOR)
    native += run_replay_cases(vector, EXECUTABLE_VECTOR)
    native += run_portable_replay_cases(vector, EXECUTABLE_VECTOR)
    native += run_state_cases(vector, EXECUTABLE_VECTOR)
    native += run_claim_cases(vector, EXECUTABLE_VECTOR)
    native += run_manifest_errors(vector, EXECUTABLE_VECTOR)
    native += run_decision_transform_cases(vector, EXECUTABLE_VECTOR)
    native += run_transform_cases(vector, EXECUTABLE_VECTOR)
    native += run_turn_cases(vector, EXECUTABLE_VECTOR)
    historical, rejected = run_historical_audit(vector)
    print(
        "MIF 1.0 reference runner passed: "
        f"{native} native executable cases, {historical} migrated historical "
        f"replays, {rejected} contradictory 0.4 checkpoints rejected "
        "(single implementation; cross-implementation conformance not established)"
    )


def replay_command(mstate_path: Path, manifest_path: Path | None) -> None:
    document = read_json(mstate_path)
    manifest = None if manifest_path is None else read_json(manifest_path)
    result = replay_mstate(document, manifest=manifest)
    output = {
        "current": result.state.serialize(
            Rules(document["ruleset"]["manifest"] if document["ruleset"]["mode"] == "portable" else manifest)
        ),
        "repetitionHistory": result.repetition_history,
        "claims": result.claims,
        "claimRights": result.claim_rights,
        "resumptionState": result.resumption_state,
        "resumptionDigest": result.resumption_digest,
        "decisionState": result.decision_state,
        "decisionDigest": result.decision_digest,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("corpus", help="run the executable candidate corpus")
    replay_parser = subparsers.add_parser("replay", help="replay one MSTATE/1.0 document")
    replay_parser.add_argument("mstate", type=Path)
    replay_parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in {None, "corpus"}:
            run_corpus()
        else:
            replay_command(args.mstate, args.manifest)
    except MIFError as exc:
        print(json.dumps(exc.diagnostic(), ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
