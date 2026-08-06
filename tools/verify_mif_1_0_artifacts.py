#!/usr/bin/env python3
"""Read-only integrity checks for MIF 1.0 candidate machine artifacts.

This checker validates Schema instances, registries, textual signatures,
deterministic identity vectors and the raw-file index. It deliberately does
not execute the gameplay transition state machine or complete MSTATE replay.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError as exc:  # pragma: no cover - exercised only on incomplete tooling
    raise SystemExit(
        "jsonschema and referencing are required to verify MIF 1.0 artifacts"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "mif-1.0"
SCHEMA_DIR = ARTIFACT / "schema"
CORPUS_DIR = ARTIFACT / "corpus"
VECTOR_DIR = CORPUS_DIR / "vectors"

EXPECTED_CONTRACT_HASHES = {
    "mif-1.0.md": "330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995",
    "docs/zh-CN/mif-1.0.md": "9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1",
}
EXPECTED_04_HASH = "f1f1d839318a4d45f3ecea4850fee080c47ffcbc81025bd74e3ea48c815f3093"

EXPECTED_FORMATS = {
    "MFEN/1.0",
    "MPK/1.0",
    "MIFPOS/1.0",
    "MSTATE/1.0",
    "MRS/1.0",
    "MIFDIAG/1.0",
    "MIFCAP/1.0",
    "MIFCONV/1.0",
    "MIFINV/1.0",
    "MIFTURN/1.0",
    "MIFSUITE/1.0",
}

EXPECTED_PROFILES = {
    "after-unobligated-place-v1",
    "decision-state-v1",
    "inline-semantic-digest-v1",
    "logical-turn-v1",
    "mif-finite-rules-v3",
    "mill24-diagonal-v1",
    "mill24-full-state-v1",
    "mill24-orthogonal-v1",
    "mill24-state-v1",
    "mrs-semantic-v1",
    "on-enter-moving-v1",
    "repetition-observation-v1",
    "reset-count-smt-v1",
    "resumption-state-v1",
    "stable-after-primary-sequence-v1",
    "stable-claim-rights-v1",
    "stable-moving-v1",
    "stable-primary-decision-v1",
    "structural-aut16-v1",
    "structural-d4-v1",
    "target-commits-v1",
    "transform-invariance-v1",
}

EXPECTED_DIAGNOSTIC_CODES = {
    "automatic-terminal-ongoing",
    "checkpoint-mismatch",
    "claim-during-obligation",
    "claim-right-unavailable",
    "claims-mismatch",
    "document-digest-mismatch",
    "duplicate-extension",
    "duplicate-member-after-unescape",
    "extension-order",
    "insufficient-resumption-history",
    "insufficient-transform-history",
    "integer-out-of-range",
    "manifest-conflict",
    "manifest-missing",
    "mpk-semantic-digest-missing",
    "no-legal-primary-action-policy-invalid",
    "obligation-target-mismatch",
    "remove-without-obligation",
    "repetition-history-mismatch",
    "repetition-observation-digest-collision",
    "required-semantic-state-missing",
    "semantic-digest-mismatch",
    "side-obligation-actor-mismatch",
    "transform-invariance-undeclared",
    "unsupported-profile",
    "unstabilized-boundary",
}

EXPECTED_POINTS = [
    "a7", "d7", "g7", "g4", "g1", "d1", "a1", "a4",
    "b6", "d6", "f6", "f4", "f2", "d2", "b2", "b4",
    "c5", "d5", "e5", "e4", "e3", "d3", "c3", "c4",
]

EXPECTED_TRANSFORMS = [
    "i",
    "r90ccw",
    "r180",
    "r90cw",
    "mirror-v",
    "mirror-h",
    "mirror-main",
    "mirror-anti",
]

EXPECTED_BOUNDARY_ORDER = [
    "placing-boundary-or-delayed-clear",
    "mill-count",
    "board-full",
    "minimum-material",
    "phase-p-no-legal-primary-action",
    "phase-m-stalemate",
    "repetition",
    "automatic-no-progress",
    "claim-right-derivation",
    "action-finalization",
]

IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
BOARD_RE = re.compile(r"^[WBwb.]{8}/[WBwb.]{8}/[WBwb.]{8}$")
MPK_BOARD_RE = re.compile(r"^[WBwb.]{24}$")
HANDS_RE = re.compile(r"^(0|[1-9][0-9]*),(0|[1-9][0-9]*)$")
UINT_RE = re.compile(r"^(0|[1-9][0-9]*)$")


class Verification:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_members,
    )


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jcs_bytes(value: Any) -> bytes:
    """Serialize the I-JSON subset used by these vectors as RFC 8785 JCS."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def jcs_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(jcs_bytes(value)).hexdigest()


def artifact_path(base: Path, relative: str) -> Path:
    result = (base / relative).resolve()
    try:
        result.relative_to(ARTIFACT.resolve())
    except ValueError as exc:
        raise ValueError(f"artifact path escapes root: {relative}") from exc
    return result


def pointer_parts(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"invalid JSON Pointer: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def mutate(value: Any, operation: dict[str, Any]) -> Any:
    result = copy.deepcopy(value)
    parts = pointer_parts(operation["path"])
    if not parts:
        if operation["op"] == "remove":
            raise ValueError("cannot remove document root")
        return copy.deepcopy(operation["value"])
    parent = result
    for token in parts[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    leaf = parts[-1]
    if operation["op"] == "remove":
        if isinstance(parent, list):
            del parent[int(leaf)]
        else:
            del parent[leaf]
    elif operation["op"] in {"add", "replace"}:
        replacement = copy.deepcopy(operation["value"])
        if isinstance(parent, list):
            if operation["op"] == "add" and leaf == "-":
                parent.append(replacement)
            elif operation["op"] == "add":
                parent.insert(int(leaf), replacement)
            else:
                parent[int(leaf)] = replacement
        else:
            parent[leaf] = replacement
    else:
        raise ValueError(f"unsupported mutation operation: {operation['op']}")
    return result


def semantic_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    projection = {
        "profile": "mrs-semantic-v1",
        "semanticsProfile": copy.deepcopy(manifest["semanticsProfile"]),
        "topology": copy.deepcopy(manifest["topology"]),
        "pieces": copy.deepcopy(manifest["pieces"]),
        "turn": copy.deepcopy(manifest["turn"]),
        "flying": copy.deepcopy(manifest["flying"]),
        "placing": copy.deepcopy(manifest["placing"]),
        "mills": copy.deepcopy(manifest["mills"]),
        "captures": copy.deepcopy(manifest["captures"]),
        "boardFull": copy.deepcopy(manifest["boardFull"]),
        "stalemate": copy.deepcopy(manifest["stalemate"]),
        "draw": copy.deepcopy(manifest["draw"]),
        "semanticState": sorted(set(manifest["semanticState"])),
    }

    if not projection["flying"]["enabled"]:
        projection["flying"] = {"enabled": False}
    if projection["placing"]["earlyStop"]["emptyPoints"] == 0:
        projection["placing"]["earlyStop"] = {"emptyPoints": 0}
    for mechanism in ("leap", "intervention", "custodian"):
        if not projection["captures"][mechanism]["enabled"]:
            projection["captures"][mechanism] = {"enabled": False}
    no_progress = projection["draw"]["noProgress"]
    if no_progress["normalLimit"] == 0 and no_progress["endgameLimit"] == 0:
        projection["draw"]["noProgress"] = {"enabled": False}
    if projection["draw"]["repetition"]["count"] == 0:
        projection["draw"]["repetition"] = {"count": 0}
    extensions = manifest.get("extensions", [])
    if extensions:
        projection["extensions"] = sorted(
            copy.deepcopy(extensions), key=lambda entry: entry["profile"]
        )
    return projection


def sparse_merkle_roots(observation_digest: str, count: int, threshold: int) -> tuple[str, str]:
    digest_bytes = bytes.fromhex(observation_digest.removeprefix("sha256:"))
    empty: list[bytes] = [hashlib.sha256(b"\x00").digest()]
    for _ in range(256):
        empty.append(hashlib.sha256(b"\x02" + empty[-1] + empty[-1]).digest())

    capped = min(count, threshold)
    node = hashlib.sha256(
        b"\x01" + digest_bytes + struct.pack(">Q", capped)
    ).digest()
    path = int.from_bytes(digest_bytes, "big")
    for height in range(256):
        bit = (path >> height) & 1
        sibling = empty[height]
        if bit == 0:
            node = hashlib.sha256(b"\x02" + node + sibling).digest()
        else:
            node = hashlib.sha256(b"\x02" + sibling + node).digest()
    return "sha256:" + empty[256].hex(), "sha256:" + node.hex()


def replay_prefix(mstate: dict[str, Any]) -> dict[str, Any]:
    prefix: list[dict[str, Any]] = []
    for entry in mstate["repetitionHistory"]:
        if entry["source"] != "pre-origin":
            break
        prefix.append(copy.deepcopy(entry))
    return {
        "origin": copy.deepcopy(mstate["origin"]),
        "preOriginRepetition": prefix,
        "preOriginClaims": copy.deepcopy(mstate["preOriginClaims"]),
        "events": copy.deepcopy(mstate["events"]),
    }


def valid_outcome(value: str) -> bool:
    if value == "-":
        return True
    if ":" not in value:
        return False
    result, reason = value.split(":", 1)
    return result in {"w", "b", "d"} and bool(IDENTIFIER_RE.fullmatch(reason))


def valid_mfen(value: str) -> bool:
    parts = value.split(" ")
    if len(parts) < 11 or parts[0] != "MFEN/1.0":
        return False
    if not IDENTIFIER_RE.fullmatch(parts[1]) or not BOARD_RE.fullmatch(parts[2]):
        return False
    if parts[3] not in {"w", "b", "-"}:
        return False
    if parts[4] not in {"p", "m", "o"} or parts[5] not in {"p", "m", "r", "o"}:
        return False
    if not HANDS_RE.fullmatch(parts[6]):
        return False
    if parts[7] != "-":
        return False  # Current vectors intentionally use the empty obligation form.
    if not UINT_RE.fullmatch(parts[8]) or not UINT_RE.fullmatch(parts[9]):
        return False
    if not valid_outcome(parts[10]):
        return False
    return all("=" in extension and extension.split("=", 1)[0] for extension in parts[11:])


def parse_mpk(value: str) -> dict[str, str] | None:
    parts = value.split(" ")
    if len(parts) < 9 or parts[0] != "MPK/1.0":
        return None
    ruleset = parts[2].rsplit("@", 1)
    if len(ruleset) != 2 or not IDENTIFIER_RE.fullmatch(ruleset[0]):
        return None
    if not re.fullmatch(r"[1-9][0-9]*", ruleset[1]):
        return None
    if not IDENTIFIER_RE.fullmatch(parts[1]) or not DIGEST_RE.fullmatch(parts[3]):
        return None
    if not IDENTIFIER_RE.fullmatch(parts[4]) or not MPK_BOARD_RE.fullmatch(parts[5]):
        return None
    if parts[6] not in {"w", "b"} or parts[7] not in {"p", "m"}:
        return None
    if not HANDS_RE.fullmatch(parts[8]):
        return None
    if not all("=" in extension and extension.split("=", 1)[0] for extension in parts[9:]):
        return None
    return {
        "stateProfile": parts[1],
        "rulesetId": ruleset[0],
        "rulesetVersion": ruleset[1],
        "semanticDigest": parts[3],
        "keyProfile": parts[4],
    }


def transform_coordinate(point: str, transform: str) -> str:
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
    return f"{chr(ord('d') + tx)}{ty + 4}"


def check_contract_and_abnf(check: Verification) -> None:
    for relative, expected in EXPECTED_CONTRACT_HASHES.items():
        path = ROOT / relative
        check.require(path.is_file(), f"missing frozen contract: {relative}")
        if path.is_file():
            check.require(raw_sha256(path) == expected, f"frozen contract hash changed: {relative}")
    check.require(
        raw_sha256(ROOT / "mif-0.4.md") == EXPECTED_04_HASH,
        "frozen mif-0.4.md hash changed",
    )

    contract = (ROOT / "mif-1.0.md").read_text(encoding="utf-8")
    match = re.search(
        r"# Annex B \(normative\): inline ABNF\s+```abnf\n(.*?)\n```",
        contract,
        flags=re.DOTALL,
    )
    check.require(match is not None, "cannot locate inline Annex B ABNF")
    if match is not None:
        standalone = (ARTIFACT / "abnf" / "mif-1.0.abnf").read_text(encoding="utf-8")
        check.require(standalone == match.group(1) + "\n", "standalone ABNF differs from Annex B")
    check.require(
        not (ARTIFACT / "mif-suite-1.0.json").exists(),
        "candidate artifact directory must not publish mif-suite-1.0.json",
    )


def schema_registry(check: Verification) -> tuple[Registry, dict[Path, Any]]:
    registry = Registry()
    documents: dict[Path, Any] = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        try:
            document = read_json(path)
            Draft202012Validator.check_schema(document)
            registry = registry.with_resource(document["$id"], Resource.from_contents(document))
            documents[path.resolve()] = document
        except Exception as exc:  # noqa: BLE001 - report all artifact faults together
            check.errors.append(f"invalid Schema {path.relative_to(ROOT)}: {exc}")
    expected_names = {
        "decision-state-v1.schema.json",
        "mif-1.0.schema.json",
        "mifcap-1.0.schema.json",
        "mifconv-1.0.schema.json",
        "mifdiag-1.0.schema.json",
        "mifinv-1.0.schema.json",
        "mifpos-1.0.schema.json",
        "mifsuite-1.0.schema.json",
        "mifturn-1.0.schema.json",
        "mrs-1.0.schema.json",
        "mstate-1.0.schema.json",
        "repetition-observation-v1.schema.json",
        "resumption-state-v1.schema.json",
    }
    check.require(
        {path.name for path in documents} == expected_names,
        "Schema entry-point file set mismatch",
    )

    def references(value: Any) -> list[str]:
        found: list[str] = []
        if isinstance(value, dict):
            if isinstance(value.get("$ref"), str):
                found.append(value["$ref"])
            for child in value.values():
                found.extend(references(child))
        elif isinstance(value, list):
            for child in value:
                found.extend(references(child))
        return found

    by_id = {document["$id"]: document for document in documents.values()}
    for source_path, source in documents.items():
        for reference in references(source):
            resource, separator, fragment = reference.partition("#")
            target: Any | None
            if resource.startswith(("http://", "https://")):
                target = by_id.get(resource)
            else:
                target_path = source_path if resource == "" else (source_path.parent / resource).resolve()
                target = documents.get(target_path)
            check.require(
                target is not None,
                f"unresolved Schema resource {reference} in {source_path.name}",
            )
            if target is None or not separator or fragment == "":
                continue
            try:
                cursor = target
                for token in pointer_parts(fragment):
                    cursor = cursor[int(token)] if isinstance(cursor, list) else cursor[token]
            except (KeyError, IndexError, ValueError, TypeError):
                check.errors.append(
                    f"unresolved Schema fragment {reference} in {source_path.name}"
                )
    return registry, documents


def check_schema_vectors(check: Verification) -> None:
    registry, documents = schema_registry(check)
    cases_path = VECTOR_DIR / "schema-cases.json"
    cases = read_json(cases_path)
    origin_case = next(
        (case for case in cases["positive"] if case["id"] == "logical-turn-origin-stabilization"),
        None,
    )
    check.require(origin_case is not None, "missing executable origin-stabilization Schema case")
    if origin_case is not None:
        check.require(
            origin_case.get("referenceRunnerVerified") is True
            and "executableSource" in origin_case
            and "scope" not in origin_case
            and "sourceBinding" not in origin_case,
            "origin-stabilization case must be bound to the executable reference vector",
        )
    for case in cases["positive"]:
        instance_path = artifact_path(cases_path.parent, case["instance"])
        schema_path = artifact_path(cases_path.parent, case["schema"])
        try:
            validator = Draft202012Validator(documents[schema_path], registry=registry)
            errors = list(validator.iter_errors(read_json(instance_path)))
            check.require(not errors, f"positive Schema case {case['id']} failed: {errors[0].message if errors else ''}")
        except Exception as exc:  # noqa: BLE001
            check.errors.append(f"positive Schema case {case['id']} could not run: {exc}")
    for case in cases["negative"]:
        base_path = artifact_path(cases_path.parent, case["base"])
        schema_path = artifact_path(cases_path.parent, case["schema"])
        try:
            instance = mutate(read_json(base_path), case["mutation"])
            validator = Draft202012Validator(documents[schema_path], registry=registry)
            errors = list(validator.iter_errors(instance))
            check.require(bool(errors), f"negative Schema case {case['id']} unexpectedly passed")
        except Exception as exc:  # noqa: BLE001
            check.errors.append(f"negative Schema case {case['id']} could not run: {exc}")


def check_executable_vectors(check: Verification) -> None:
    path = CORPUS_DIR / "executable" / "reference-cases.json"
    check.require(path.is_file(), "missing executable reference corpus")
    if not path.is_file():
        return
    vector = read_json(path)
    check.require(vector.get("artifact") == "mif-1.0-executable-corpus", "executable corpus identity mismatch")
    capability_path = artifact_path(path.parent, vector.get("capability", ""))
    check.require(capability_path.is_file(), "executable corpus capability binding is missing")
    if capability_path.is_file():
        capability = read_json(capability_path)
        check.require(
            capability.get("implementation")
            == {"name": "mif-python-reference-runner", "version": "candidate-1"},
            "reference runner capability identity mismatch",
        )
        check.require(capability.get("suites") == [], "candidate runner must not claim a suite")
        check.require(
            capability.get("testedCorpora")
            == [
                {
                    "classes": ["identity", "position", "replay", "ruleset", "transform"],
                    "digest": "sha256:" + raw_sha256(path),
                }
            ],
            "reference runner capability is not bound to the executable corpus",
        )
        class_levels = {item["id"]: item["level"] for item in capability["classes"]}
        check.require(
            class_levels.get("conversion") == "none"
            and class_levels.get("key") == "none",
            "reference runner capability overclaims conversion or MPK support",
        )
        check.require(
            capability.get("invarianceDeclarations") == []
            and capability.get("resourceLimits") == [],
            "reference runner capability claims undeclared invariance or unenforced limits",
        )
        fixtures = {
            "example-morris": CORPUS_DIR / "fixtures" / "example-morris@1.json",
            "x-origin-stabilization": CORPUS_DIR / "fixtures" / "x-origin-stabilization@1.json",
        }
        for entry in capability["rulesets"]:
            fixture_path = fixtures.get(entry["id"])
            check.require(fixture_path is not None, f"unknown tested ruleset capability: {entry['id']}")
            if fixture_path is not None:
                fixture = read_json(fixture_path)
                check.require(entry["documentDigest"] == jcs_digest(fixture), f"capability document digest mismatch: {entry['id']}")
                check.require(entry["semanticDigest"] == jcs_digest(semantic_projection(fixture)), f"capability semantic digest mismatch: {entry['id']}")
    required_groups = {
        "replayCases",
        "portableReplayCases",
        "stateCases",
        "claimLifecycleCases",
        "manifestErrorCases",
        "decisionTransformCases",
        "transformCases",
        "turnCases",
        "historicalMigrationAudit",
    }
    check.require(required_groups.issubset(vector), "executable corpus group set is incomplete")

    reference_fields = {
        "replayCases": ("manifest", "document"),
        "portableReplayCases": ("document", "envelopeDocument"),
        "stateCases": ("manifest",),
        "claimLifecycleCases": ("manifest",),
        "manifestErrorCases": ("manifest",),
        "decisionTransformCases": ("manifest", "document"),
        "transformCases": ("manifest", "document"),
        "turnCases": ("manifest", "document", "expected"),
    }
    ids: set[str] = set()
    for group, fields in reference_fields.items():
        for case in vector[group]:
            case_id = case["id"]
            check.require(case_id not in ids, f"duplicate executable case ID: {case_id}")
            ids.add(case_id)
            for field in fields:
                linked = artifact_path(path.parent, case[field])
                check.require(linked.is_file(), f"missing executable case resource: {case_id}.{field}")

    decision_transforms = {
        case["id"]: case for case in vector["decisionTransformCases"]
    }
    check.require(
        set(decision_transforms)
        == {
            "decision-root-without-materialized-history",
            "decision-with-materialized-history",
        },
        "decision transform executable case set mismatch",
    )
    materialized = decision_transforms.get("decision-with-materialized-history")
    if materialized is not None:
        materialization_path = artifact_path(path.parent, materialized["materialization"])
        check.require(materialization_path.is_file(), "decision transform materialization is missing")
        check.require(materialized.get("transforms") == "all-d4", "materialized decision transform must cover D4")
    missing = decision_transforms.get("decision-root-without-materialized-history")
    if missing is not None:
        check.require(missing.get("expectedCode") == "insufficient-transform-history", "decision root rejection code mismatch")

    portable_cases = vector["portableReplayCases"]
    check.require(len(portable_cases) == 1, "portable replay case set mismatch")
    if portable_cases:
        portable = portable_cases[0]
        envelope_document = read_json(
            artifact_path(path.parent, portable["envelopeDocument"])
        )
        envelope = envelope_document.get("ruleset", {})
        check.require(
            portable.get("id") == "offer-history-r1-portable"
            and envelope.get("mode") == "portable"
            and "manifest" in envelope,
            "portable replay case is not self-contained",
        )

    replay = {case["id"]: case for case in vector["replayCases"]}
    turns = {case["id"]: case for case in vector["turnCases"]}
    origin_replay = replay.get("origin-stabilization-removals")
    origin_turn = turns.get("origin-stabilization-removal-sequence")
    check.require(origin_replay is not None and origin_turn is not None, "origin stabilization executable binding is incomplete")
    if origin_replay is not None and origin_turn is not None:
        expected_turn = read_json(artifact_path(path.parent, origin_turn["expected"]))
        check.require(
            origin_replay["document"] == origin_turn["document"]
            and origin_replay["manifest"] == origin_turn["manifest"],
            "origin stabilization replay and turn projection use different sources",
        )
        check.require(
            expected_turn["sourceResumptionDigest"] == origin_replay["expectedResumptionDigest"]
            and expected_turn["sourceResumptionDigest"] != "sha256:" + "0" * 64,
            "origin stabilization turn projection is not bound to its resumption identity",
        )

    audit = vector["historicalMigrationAudit"]
    matches = audit["expectedMatches"]
    rejections = audit["sourceRejections"]
    rejected_ids = {item["id"] for item in rejections}
    check.require(len(matches) == 19 and len(set(matches)) == 19, "historical replay match set mismatch")
    check.require(
        rejected_ids == {"MSTATE-REPLAY-REMOVAL-CAP", "MSTATE-REPLAY-PHASE-SYNC-P-TO-M"},
        "historical contradictory checkpoint rejection set mismatch",
    )
    check.require(not set(matches).intersection(rejected_ids), "historical audit both accepts and rejects a case")


def check_registries(check: Verification) -> None:
    contract = (ROOT / "mif-1.0.md").read_text(encoding="utf-8")
    formats = read_json(ARTIFACT / "registry" / "formats.json")["entries"]
    check.require({entry["id"] for entry in formats} == EXPECTED_FORMATS, "format registry set mismatch")
    for entry in formats:
        check.require(entry["conformanceTarget"] is False, f"format {entry['id']} incorrectly claims conformance")
        link = entry.get("schema") or entry.get("grammar")
        if link:
            linked_path = link.split("#", 1)[0]
            check.require(
                artifact_path(ARTIFACT / "registry", linked_path).is_file(),
                f"format registry link is missing: {link}",
            )

    profiles = read_json(ARTIFACT / "registry" / "profiles.json")["entries"]
    profile_ids = {entry["id"] for entry in profiles}
    check.require(profile_ids == EXPECTED_PROFILES, "profile registry set mismatch")
    for profile in profile_ids:
        check.require(profile in contract, f"registered profile absent from contract: {profile}")

    diagnostics = read_json(ARTIFACT / "registry" / "diagnostics.json")
    codes = set(diagnostics["codes"])
    check.require(codes == EXPECTED_DIAGNOSTIC_CODES, "diagnostic code registry set mismatch")
    for code in codes:
        check.require(code in contract, f"registered diagnostic code absent from contract: {code}")

    tokens = read_json(ARTIFACT / "registry" / "tokens.json")["sets"]
    check.require(
        tokens["boardFullActions"] == [
            "disabled",
            "white-loses",
            "white-then-black-remove",
            "black-then-white-remove",
            "active-player-removes",
            "draw",
        ],
        "board-full token order mismatch",
    )
    old_tokens = {"first-player-loses", "first-then-second-remove", "second-then-first-remove"}
    check.require(not old_tokens.intersection(tokens["boardFullActions"]), "0.4 board-full token leaked into 1.0")

    mill24 = read_json(ARTIFACT / "registry" / "mill24.json")
    check.require(mill24["pointOrder"] == EXPECTED_POINTS, "mill24 point order mismatch")
    check.require(len(set(mill24["pointOrder"])) == 24, "mill24 point order is not unique")
    line_ids = mill24["lineIds"]
    check.require([line["id"] for line in line_ids] == list(range(20)), "mill24 line ID order mismatch")
    check.require(
        all(len(line["points"]) == 3 and set(line["points"]).issubset(EXPECTED_POINTS) for line in line_ids),
        "mill24 line registry contains an invalid line",
    )
    transforms = mill24["transforms"]
    check.require([item["id"] for item in transforms] == EXPECTED_TRANSFORMS, "transform order mismatch")
    check.require([item["ordinal"] for item in transforms] == list(range(8)), "transform ordinal mismatch")


def check_digest_vectors(check: Verification) -> None:
    vector_path = VECTOR_DIR / "digest-identities.json"
    vector = read_json(vector_path)
    fixture = read_json(artifact_path(vector_path.parent, vector["fixture"]))
    projection = semantic_projection(fixture)
    check.require(projection == vector["semanticProjection"], "semantic projection vector mismatch")
    check.require(jcs_digest(projection) == vector["semanticDigest"], "semanticDigest mismatch")

    for variant in vector["documentVariants"]:
        document = fixture if "mutation" not in variant else mutate(fixture, variant["mutation"])
        check.require(jcs_digest(document) == variant["documentDigest"], f"documentDigest mismatch for {variant['id']}")
        check.require(jcs_digest(semantic_projection(document)) == variant["semanticDigest"], f"semanticDigest mismatch for {variant['id']}")

    observation_path = artifact_path(vector_path.parent, vector["observation"]["instance"])
    observation = read_json(observation_path)
    observation_digest = jcs_digest(observation)
    check.require(observation_digest == vector["observation"]["digest"], "observation digest mismatch")
    summary = vector["repetitionSummary"]
    empty_root, one_root = sparse_merkle_roots(observation_digest, 1, summary["threshold"])
    check.require(empty_root == summary["emptyRoot"], "sparse Merkle empty root mismatch")
    check.require(one_root == summary["oneOccurrenceRoot"], "sparse Merkle one-occurrence root mismatch")

    decision = read_json(artifact_path(vector_path.parent, vector["decision"]["instance"]))
    check.require(jcs_digest(decision) == vector["decision"]["digest"], "decisionDigest mismatch")
    check.require(
        decision["repetitionSummary"]["root"] == summary["oneOccurrenceRoot"],
        "decision repetition root is not the vector root",
    )
    check.require("primaryPly" not in decision and "eventSeq" not in decision, "decision object contains audit identity")

    resumption_digests: list[str] = []
    for entry in vector["resumptions"]:
        resumption = read_json(artifact_path(vector_path.parent, entry["instance"]))
        mstate = read_json(artifact_path(vector_path.parent, entry["mstate"]))
        actual = jcs_digest(resumption)
        resumption_digests.append(actual)
        check.require(actual == entry["digest"], f"resumptionDigest mismatch for {entry['id']}")
        check.require(
            jcs_digest(replay_prefix(mstate)) == resumption["replayPrefixDigest"],
            f"replay-prefix digest mismatch for {entry['id']}",
        )
        check.require(resumption["current"] == mstate["current"], f"current state mismatch for {entry['id']}")
        check.require(resumption["claims"] == mstate["claims"], f"claim audit mismatch for {entry['id']}")
        check.require(resumption["lastEventSeq"] == mstate["events"][-1]["seq"], f"lastEventSeq mismatch for {entry['id']}")
    check.require(len(set(resumption_digests)) == 2, "R1 and R2 must have different resumption digests")
    check.require(vector["relationship"] == {"differentResumptionDigest": True, "sameDecisionDigest": True}, "identity relationship vector mismatch")


def check_text_vectors(check: Verification) -> None:
    path = VECTOR_DIR / "text-formats.json"
    vector = read_json(path)
    for case in vector["syntaxValid"]:
        valid = valid_mfen(case["value"]) if case["value"].startswith("MFEN/") else parse_mpk(case["value"]) is not None
        check.require(valid, f"syntax-valid text case failed: {case['id']}")
    for case in vector["syntaxInvalid"]:
        valid = valid_mfen(case["value"]) if case["value"].startswith("MFEN/") else parse_mpk(case["value"]) is not None
        check.require(not valid, f"syntax-invalid text case passed: {case['id']}")

    digest_vector = read_json(VECTOR_DIR / "digest-identities.json")
    for case in vector["semanticReject"]:
        if case["value"].startswith("MPK/"):
            parsed = parse_mpk(case["value"])
            check.require(parsed is not None, f"semantic MPK case is not syntactically valid: {case['id']}")
            if parsed is not None:
                check.require(parsed["semanticDigest"] != digest_vector["semanticDigest"], f"semantic mismatch case does not mismatch: {case['id']}")
        else:
            check.require(valid_mfen(case["value"]), f"context-bound MFEN case is not syntactically valid: {case['id']}")


def check_policy_vectors(check: Verification) -> None:
    state = read_json(VECTOR_DIR / "state-boundaries.json")
    check.require(state["stableBoundaryOrder"] == EXPECTED_BOUNDARY_ORDER, "stable-boundary order vector mismatch")
    required_state_ids = {
        "initial-player-black",
        "white-loses-is-fixed-identity-with-initial-black",
        "placing-full-board-loss",
        "placing-full-board-draw",
        "placing-apply-board-full-while-disabled",
        "placing-movement-cycle",
        "claim-right-lifecycle",
        "origin-stabilization-obligation",
    }
    cases = {case["id"]: case for case in state["cases"]}
    check.require(set(cases) == required_state_ids, "state-boundary case set mismatch")
    check.require(all(case.get("runnerRequired") is True for case in cases.values()), "state-machine case lacks runnerRequired")
    identity_case = cases["white-loses-is-fixed-identity-with-initial-black"]
    check.require(
        identity_case.get("initialPlayer") == "b"
        and identity_case.get("policy") == "white-loses"
        and identity_case.get("winner") == "b",
        "white-loses vector does not distinguish fixed identity from initial player",
    )
    cycle_case = cases["placing-movement-cycle"]
    check.require(
        cycle_case.get("initial", "").split(" ")[4:6] == ["p", "p"]
        and cycle_case.get("expectedObservations")
        == {"stable-moving-v1": 0, "stable-primary-decision-v1": 4},
        "placing movement cycle has an invalid stable phase/action or scope count",
    )
    check.require(
        cases["placing-apply-board-full-while-disabled"].get("expectedCode")
        == "no-legal-primary-action-policy-invalid",
        "placing liveness manifest error code mismatch",
    )
    origin_fragment = cases["origin-stabilization-obligation"]["expectedFragment"]
    check.require("primaryEventSeq" not in origin_fragment and "causedBySeq" not in origin_fragment, "origin stabilization invented a primary reference")

    transforms = read_json(VECTOR_DIR / "transforms.json")
    check.require(transforms["runnerRequired"] is True, "full-state transform vectors must require runner")
    for item in transforms["coordinateVectors"]:
        check.require(
            transform_coordinate(item["input"], item["transform"]) == item["expected"],
            f"coordinate transform vector mismatch: {item['transform']}",
        )
    gate_codes = {item["expectedCode"] for item in transforms["equivalenceGates"]}
    check.require(
        gate_codes == {"transform-invariance-undeclared", "insufficient-transform-history"},
        "transform gate vector mismatch",
    )
    check.require(not list((CORPUS_DIR / "instances").glob("mifinv*.json")), "corpus must not claim unproven invariance")

    migration = read_json(VECTOR_DIR / "migration-0.4-to-1.0.json")
    mapping = {(item["source"], item["target"]) for item in migration["mappings"]}
    required_mapping = {
        ("first-player-loses", "white-loses"),
        ("first-then-second-remove", "white-then-black-remove"),
        ("second-then-first-remove", "black-then-white-remove"),
        ("legal-state-v1", "repetition-observation-v1"),
        ("mpk-without-resolvable-manifest", "requires-ruleset-resolution"),
    }
    check.require(required_mapping.issubset(mapping), "migration mapping set is incomplete")
    rejection_ids = {item["id"] for item in migration["rejections"]}
    check.require(
        rejection_ids == {
            "pending-removal-claim",
            "unknown-semantic-extension",
            "ownerless-delayed-material",
            "missing-used-line-history",
            "missing-mpk-ruleset-semantics",
            "unproven-transform-equivalence",
            "placing-liveness-policy-not-selected",
        },
        "migration rejection set mismatch",
    )
    check.require(migration["runnerRequired"] is True, "migration execution cases must require runner")


def check_file_quality_and_index(check: Verification) -> None:
    index_path = ARTIFACT / "index.json"
    check.require(index_path.is_file(), "missing artifact index.json")
    if not index_path.is_file():
        return
    index = read_json(index_path)
    expected_contracts = {
        path: "sha256:" + digest for path, digest in EXPECTED_CONTRACT_HASHES.items()
    }
    check.require(index["contractHashes"] == expected_contracts, "index contract hash binding mismatch")
    check.require(index["contractStatus"] == "candidate-wire-frozen-suite-unpublished", "index status mismatch")

    delivered = sorted(
        (
            path.relative_to(ARTIFACT).as_posix()
            for path in ARTIFACT.rglob("*")
            if path.is_file() and path != index_path
        ),
        key=str.casefold,
    )
    indexed = [entry["path"] for entry in index["files"]]
    check.require(indexed == delivered, "artifact index path set/order mismatch")
    index_map = {entry["path"]: entry["sha256"] for entry in index["files"]}
    for relative in delivered:
        path = ARTIFACT / relative
        check.require(index_map.get(relative) == "sha256:" + raw_sha256(path), f"artifact hash mismatch: {relative}")
        raw = path.read_bytes()
        check.require(not raw.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM is forbidden: {relative}")
        check.require(raw.endswith(b"\n"), f"missing final LF: {relative}")
        check.require(b"\r" not in raw, f"non-LF line ending: {relative}")
        text = raw.decode("utf-8")
        check.require(
            all(line == line.rstrip(" \t") for line in text.splitlines()),
            f"trailing whitespace: {relative}",
        )


def main() -> int:
    check = Verification()
    try:
        check_contract_and_abnf(check)
        check_schema_vectors(check)
        check_executable_vectors(check)
        check_registries(check)
        check_digest_vectors(check)
        check_text_vectors(check)
        check_policy_vectors(check)
        check_file_quality_and_index(check)
    except Exception as exc:  # noqa: BLE001 - preserve a concise integrity result
        check.errors.append(f"checker aborted: {exc}")

    if check.errors:
        print("MIF 1.0 candidate artifact integrity FAILED:")
        for error in check.errors:
            print(f"- {error}")
        return 1
    print(
        "MIF 1.0 candidate artifact integrity passed "
        "(schema/corpus integrity only; gameplay execution not performed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
