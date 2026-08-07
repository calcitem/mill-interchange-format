#!/usr/bin/env python3
"""Verify final Suite-bound adapter and three-process evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError as exc:  # pragma: no cover - incomplete local tooling
    raise SystemExit("jsonschema is required to verify final evidence") from exc


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.jcs import jcs_digest  # noqa: E402


SUITE_PATH = ROOT / "mif-suite-1.0.json"
MANIFEST_PATH = ROOT / "release" / "mif-1.0-release-manifest.json"
ADAPTER_SCHEMA_PATH = ROOT / "release" / "mif-1.0-adapter-evidence.schema.json"
FINAL_SCHEMA_PATH = ROOT / "release" / "mif-1.0-final-evidence.schema.json"
FINAL_PATH = (
    ROOT / "release" / "evidence" / "mif-suite-1.0-final-evidence-2026-08-07.json"
)
MIF_SCHEMA_PATH = ROOT / "artifacts" / "mif-1.0" / "schema" / "mif-1.0.schema.json"
DIFFERENTIAL_SCHEMA_PATH = (
    ROOT / "interop" / "schema" / "differential-report-v1.schema.json"
)

SUITE_DIGEST = "sha256:81a5feabc281bfc4f830addabc2c6846d1f191bbbcf04e548f04b35dd358ae6f"
SUITE_RAW_DIGEST = (
    "sha256:088ca33234289b06d9276aa4c430758222aa85d61621dee7bef4bfc6dcc069a4"
)
SUITE_COMMIT = "3ee7e57c7d4c7208be91f62914f344a587fb0f70"
WIRE_COMMIT = "7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978"
ARTIFACT_INDEX_DIGEST = (
    "sha256:5acbb714bed77e24eaac72fa5f24d2e54d1e17aaf568a8b60718c840281a6541"
)
LAUNCH_DIGEST = (
    "sha256:560ef369fde248bd96d3468a4336442db1d970ede04f488821509e69925fd48e"
)
FINALIZATION_DIGEST = (
    "sha256:3ab079c44158979eb78221a64abe5347e9e3697b33972673659a0ea80053536d"
)
CONFIG_DIGEST = (
    "sha256:133cc572ba786ebd544e9fe5fc89c67248432952a1a2fce451a3e1ec6bfda0f2"
)
CLASSES = ["identity", "key", "position", "replay", "ruleset", "transform"]
ADAPTERS = ["mif-reference", "nmm-llm-python", "sanmill-rust"]

EXPECTED_PRODUCTS = {
    "nmm-llm": {
        "adapter": "nmm-llm-python",
        "repository": "https://github.com/benmarkbrandwood-blip/NMM_LLM.git",
        "branch": "dev",
        "implementationCommit": "a7e7dbd5461cc2d8d8c0a09317d6091598202214",
        "evidenceArtifactCommit": "ae7911e37fa2bf45ea6074850453bbad2479438e",
        "evidencePublicationCommit": "b599e0d45a660a020b45860e60c9409b503c454d",
    },
    "sanmill": {
        "adapter": "sanmill-rust",
        "repository": "https://github.com/calcitem/Sanmill.git",
        "branch": "master",
        "implementationCommit": "7e86de7e8156a7d7f46a6a6179a8878051699505",
        "evidenceArtifactCommit": "9d36d04b4d2a8cd5c660e9582426bedeb888b591",
        "evidencePublicationCommit": "57f41c1d0dae90e6f614c6aa9b2c177e9df4ffc0",
    },
}


class EvidenceVerificationError(RuntimeError):
    """Final release evidence violates a frozen invariant."""


def fail(message: str) -> None:
    raise EvidenceVerificationError(message)


def raw_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    raw = path.read_bytes()
    relative = path.relative_to(ROOT)
    if raw.startswith(b"\xef\xbb\xbf"):
        fail(f"UTF-8 BOM is forbidden: {relative}")
    if b"\r" in raw:
        fail(f"CR bytes are forbidden: {relative}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                fail(f"duplicate JSON member {key!r}: {relative}")
            result[key] = value
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid UTF-8 JSON {relative}: {exc}")


def validate_schema(instance: Any, schema: Any, label: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        fail(f"{label} schema is invalid: {exc.message}")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        first = errors[0]
        pointer = "/" + "/".join(str(part) for part in first.absolute_path)
        fail(f"{label} schema failure at {pointer}: {first.message}")


def resolve(value: str) -> Path:
    if "\\" in value or value.startswith("/"):
        fail(f"path is not repository-relative: {value}")
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        fail(f"path escapes repository: {value}")
    if not path.is_file():
        fail(f"evidence file is missing: {value}")
    return path


def verify_file(record: dict[str, Any]) -> Path:
    path = resolve(record["path"])
    actual = raw_sha256(path)
    if actual != record["rawSha256"]:
        fail(f"raw digest mismatch for {record['path']}: {actual}")
    return path


def binding_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bindings = manifest["bindings"]
    identifiers = [item["id"] for item in bindings]
    if identifiers != sorted(identifiers) or len(identifiers) != len(set(identifiers)):
        fail("release bindings are not sorted and unique")
    return {item["id"]: item for item in bindings}


def require_binding(
    bindings: dict[str, dict[str, Any]], identifier: str, digest: str
) -> None:
    if identifier not in bindings or bindings[identifier]["role"] != "evidence":
        fail(f"required evidence binding is missing: {identifier}")
    if bindings[identifier]["sha256"] != digest:
        fail(f"release binding digest mismatch: {identifier}")


def verify_adapter(
    record: dict[str, Any],
    suite: dict[str, Any],
    manifest: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
    adapter_schema: dict[str, Any],
    mif_schema: dict[str, Any],
    differential_schema: dict[str, Any],
) -> None:
    evidence_path = verify_file(record["evidence"])
    capability_path = verify_file(record["capability"])
    deterministic_path = verify_file(record["deterministicReport"])
    differential_path = verify_file(record["differentialReport"])
    evidence = load_json(evidence_path)
    capability = load_json(capability_path)
    deterministic = load_json(deterministic_path)
    differential = load_json(differential_path)

    validate_schema(evidence, adapter_schema, f"{record['id']} adapter evidence")
    validate_schema(capability, mif_schema, f"{record['id']} MIFCAP")
    validate_schema(
        differential, differential_schema, f"{record['id']} differential report"
    )

    expected_product = EXPECTED_PRODUCTS.get(record["id"])
    if expected_product is None:
        fail(f"unexpected product evidence: {record['id']}")
    for key, expected in expected_product.items():
        if record[key] != expected:
            fail(f"product identity mismatch: {record['id']} {key}")

    if evidence["adapter"] != record["adapter"]:
        fail(f"adapter identity mismatch: {record['id']}")
    if evidence["mifCommit"] != SUITE_COMMIT:
        fail(f"MIF baseline mismatch: {record['id']}")
    if evidence["implementationCommit"] != record["implementationCommit"]:
        fail(f"implementation commit mismatch: {record['id']}")
    if evidence["evidenceCommit"] != record["evidenceArtifactCommit"]:
        fail(f"evidence artifact commit mismatch: {record['id']}")
    if evidence["suiteJcsSha256"] != SUITE_DIGEST:
        fail(f"suite JCS digest mismatch: {record['id']}")
    if evidence["suiteRawSha256"] != SUITE_RAW_DIGEST:
        fail(f"suite raw digest mismatch: {record['id']}")
    if evidence["artifactIndexRawSha256"] != ARTIFACT_INDEX_DIGEST:
        fail(f"artifact index digest mismatch: {record['id']}")
    if evidence["testedClasses"] != CLASSES:
        fail(f"tested class mismatch: {record['id']}")
    if evidence["rulesetSemanticDigests"] != suite["rulesets"]:
        fail(f"tested ruleset mismatch: {record['id']}")
    if evidence["verification"]["finalizationLaunchRawSha256"] != FINALIZATION_DIGEST:
        fail(f"finalization launch mismatch: {record['id']}")
    if evidence["verification"]["rawArtifactsByteIdenticalAcrossRuns"] is not True:
        fail(f"artifact repeatability was not established: {record['id']}")

    expected_digests = {
        "capabilityRawSha256": record["capability"]["rawSha256"],
        "deterministicReportRawSha256": record["deterministicReport"]["rawSha256"],
        "differentialReportRawSha256": record["differentialReport"]["rawSha256"],
    }
    for key, expected in expected_digests.items():
        if evidence[key] != expected:
            fail(f"nested evidence digest mismatch: {record['id']} {key}")

    artifact_digests = {
        "capability": record["capability"]["rawSha256"],
        "deterministicReport": record["deterministicReport"]["rawSha256"],
        "differentialReport": record["differentialReport"]["rawSha256"],
    }
    for identifier, expected in artifact_digests.items():
        if evidence["artifacts"][identifier]["rawSha256"] != expected:
            fail(f"artifact digest mismatch: {record['id']} {identifier}")

    if capability["suites"] != [SUITE_DIGEST]:
        fail(f"MIFCAP suite pin mismatch: {record['id']}")
    levels = {item["id"]: item["level"] for item in capability["classes"]}
    if any(levels.get(identifier) != "tested" for identifier in CLASSES):
        fail(f"MIFCAP tested class mismatch: {record['id']}")
    if levels.get("conversion") != "none" or capability["conversions"] != []:
        fail(f"MIFCAP conversion overclaim: {record['id']}")

    expected_pair = ["mif-reference", record["adapter"]]
    if deterministic.get("protocol") != "MIF-INTEROP-REPORT/1":
        fail(f"deterministic protocol mismatch: {record['id']}")
    if deterministic.get("adapters") != expected_pair:
        fail(f"deterministic adapter mismatch: {record['id']}")
    if deterministic.get("summary") != {"failed": 0, "passed": 58}:
        fail(f"deterministic result is not 58/58: {record['id']}")
    deterministic_record = evidence["artifacts"]["deterministicReport"]
    if deterministic_record["summary"] != {"failed": 0, "passed": 58}:
        fail(f"nested deterministic result is not 58/58: {record['id']}")
    if deterministic.get("configDigest") != deterministic_record["configDigest"]:
        fail(f"deterministic config mismatch: {record['id']}")

    if differential["adapters"] != expected_pair:
        fail(f"differential adapter mismatch: {record['id']}")
    if differential["launchDigest"] != LAUNCH_DIGEST:
        fail(f"differential launch mismatch: {record['id']}")
    if differential["summary"] != {
        "negativeFailed": 0,
        "negativePassed": 5,
        "runsFailed": 0,
        "runsPassed": 10,
    }:
        fail(f"differential result is not 10/10 and 5/5: {record['id']}")

    differential_record = evidence["artifacts"]["differentialReport"]
    if differential.get("configDigest") != differential_record["configDigest"]:
        fail(f"differential config mismatch: {record['id']}")
    if differential_record["summary"] != {
        "mutationFamiliesFailed": 0,
        "mutationFamiliesPassed": 5,
        "runsFailed": 0,
        "runsPassed": 10,
    }:
        fail(f"nested differential result is not 10/10 and 5/5: {record['id']}")

    prefix = f"{record['adapter']}-suite-1.0"
    resources = {
        f"{prefix}-evidence": record["evidence"]["rawSha256"],
        f"{prefix}-capability": record["capability"]["rawSha256"],
        f"{prefix}-deterministic-report": record["deterministicReport"]["rawSha256"],
        f"{prefix}-differential-report": record["differentialReport"]["rawSha256"],
    }
    for identifier, digest in resources.items():
        require_binding(bindings, identifier, digest)

    implementations = {item["adapter"]: item for item in manifest["implementations"]}
    implementation = implementations.get(record["adapter"])
    if implementation is None:
        fail(f"release implementation is missing: {record['adapter']}")
    if implementation["implementationCommit"] != record["implementationCommit"]:
        fail(f"release implementation commit mismatch: {record['id']}")
    if implementation.get("suiteEvidenceBinding") != "mif-1.0-final-evidence":
        fail(f"release implementation lacks final evidence binding: {record['id']}")


def verify_final_evidence() -> str:
    paths = (
        SUITE_PATH,
        MANIFEST_PATH,
        ADAPTER_SCHEMA_PATH,
        FINAL_SCHEMA_PATH,
        FINAL_PATH,
        MIF_SCHEMA_PATH,
        DIFFERENTIAL_SCHEMA_PATH,
    )
    for path in paths:
        if not path.is_file():
            fail(f"required file is missing: {path.relative_to(ROOT)}")

    suite = load_json(SUITE_PATH)
    manifest = load_json(MANIFEST_PATH)
    final = load_json(FINAL_PATH)
    adapter_schema = load_json(ADAPTER_SCHEMA_PATH)
    final_schema = load_json(FINAL_SCHEMA_PATH)
    mif_schema = load_json(MIF_SCHEMA_PATH)
    differential_schema = load_json(DIFFERENTIAL_SCHEMA_PATH)
    validate_schema(final, final_schema, "final evidence")

    if manifest["status"] != "ready-for-tag":
        fail("release manifest is not ready-for-tag")
    if jcs_digest(suite) != SUITE_DIGEST or raw_sha256(SUITE_PATH) != SUITE_RAW_DIGEST:
        fail("suite identity differs from the adapter pin")
    if final["suiteDigest"] != SUITE_DIGEST:
        fail("aggregate suite digest mismatch")
    if final["suite"] != {
        "id": "mif-suite-1.0",
        "candidateCommit": SUITE_COMMIT,
        "wireCommit": WIRE_COMMIT,
        "jcsSha256": SUITE_DIGEST,
        "rawSha256": SUITE_RAW_DIGEST,
    }:
        fail("final evidence suite identity mismatch")
    if final["testedDomain"]["classes"] != CLASSES:
        fail("final evidence tested classes mismatch")
    if final["testedDomain"]["rulesetSemanticDigests"] != suite["rulesets"]:
        fail("final evidence tested rulesets mismatch")

    bindings = binding_map(manifest)
    require_binding(bindings, "mif-1.0-final-evidence", raw_sha256(FINAL_PATH))
    product_ids = [record["id"] for record in final["adapters"]]
    if product_ids != list(EXPECTED_PRODUCTS):
        fail("final evidence does not contain the two fixed product adapters")

    for record in final["adapters"]:
        verify_adapter(
            record,
            suite,
            manifest,
            bindings,
            adapter_schema,
            mif_schema,
            differential_schema,
        )

    three = final["threeAdapter"]
    if three["configDigest"] != CONFIG_DIGEST or three["adapters"] != ADAPTERS:
        fail("final three-adapter configuration mismatch")
    deterministic_id = "mif-1.0-final-three-adapter-deterministic-report"
    differential_id = "mif-1.0-final-three-adapter-differential-report"
    require_binding(bindings, deterministic_id, three["deterministic"]["rawSha256"])
    require_binding(bindings, differential_id, three["differential"]["rawSha256"])
    deterministic = load_json(verify_file(three["deterministic"]))
    differential = load_json(verify_file(three["differential"]))
    if deterministic.get("protocol") != "MIF-INTEROP-REPORT/1":
        fail("final deterministic protocol mismatch")
    if deterministic.get("adapters") != ADAPTERS:
        fail("final deterministic adapter mismatch")
    if deterministic.get("configDigest") != CONFIG_DIGEST:
        fail("final deterministic config mismatch")
    if deterministic.get("summary") != {"failed": 0, "passed": 58}:
        fail("final deterministic report is not 58/58")
    validate_schema(differential, differential_schema, "final differential report")
    if differential["adapters"] != ADAPTERS:
        fail("final differential adapter mismatch")
    if differential["configDigest"] != CONFIG_DIGEST:
        fail("final differential config mismatch")
    if differential["launchDigest"] != LAUNCH_DIGEST:
        fail("final differential launch mismatch")
    if differential["summary"] != {
        "negativeFailed": 0,
        "negativePassed": 5,
        "runsFailed": 0,
        "runsPassed": 10,
    }:
        fail("final differential report is not 10/10 and 5/5")
    if three["repetitionsByteIdentical"] is not True:
        fail("final report repeatability is not established")
    return raw_sha256(FINAL_PATH)


def main() -> int:
    try:
        digest = verify_final_evidence()
    except (EvidenceVerificationError, OSError) as exc:
        print(f"MIF Suite 1.0 final evidence verification FAILED: {exc}")
        return 1
    print(f"MIF Suite 1.0 final evidence verified: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
