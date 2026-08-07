#!/usr/bin/env python3
"""Verify the immutable inputs for independent MIF Suite 1.0 adapter pinning."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - incomplete local tooling
    raise SystemExit("jsonschema is required to verify adapter finalization") from exc


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.jcs import jcs_bytes, jcs_digest  # noqa: E402


LAUNCH_PATH = ROOT / "release" / "mif-1.0-adapter-finalization.json"
SCHEMA_PATH = ROOT / "release" / "mif-1.0-adapter-finalization.schema.json"
SUITE_PATH = ROOT / "mif-suite-1.0.json"
CURRENT_MANIFEST_PATH = ROOT / "release" / "mif-1.0-release-manifest.json"

BASELINE_COMMIT = "3ee7e57c7d4c7208be91f62914f344a587fb0f70"
WIRE_COMMIT = "7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978"
SUITE_JCS_DIGEST = "sha256:81a5feabc281bfc4f830addabc2c6846d1f191bbbcf04e548f04b35dd358ae6f"
SUITE_RAW_DIGEST = "sha256:088ca33234289b06d9276aa4c430758222aa85d61621dee7bef4bfc6dcc069a4"
REQUIRED_CLASSES = ["identity", "key", "position", "replay", "ruleset", "transform"]
REQUIRED_FIELDS = [
    "adapter",
    "artifactIndexRawSha256",
    "capabilityRawSha256",
    "deterministicReportRawSha256",
    "differentialReportRawSha256",
    "evidenceCommit",
    "implementationCommit",
    "mifCommit",
    "rulesetSemanticDigests",
    "suiteJcsSha256",
    "suiteRawSha256",
    "testedClasses",
]


class FinalizationVerificationError(RuntimeError):
    """A suite adapter-finalization invariant is not satisfied."""


def fail(message: str) -> None:
    raise FinalizationVerificationError(message)


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json_bytes(raw: bytes, label: str) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        fail(f"UTF-8 BOM is forbidden: {label}")
    if b"\r" in raw:
        fail(f"CR bytes are forbidden: {label}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                fail(f"duplicate JSON member {key!r}: {label}")
            result[key] = value
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid UTF-8 JSON {label}: {exc}")


def load_json(path: Path) -> Any:
    return load_json_bytes(path.read_bytes(), str(path.relative_to(ROOT)))


def validate_schema(instance: Any, schema: Any) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        first = errors[0]
        pointer = "/" + "/".join(str(part) for part in first.absolute_path)
        fail(f"launch schema failure at {pointer}: {first.message}")


def resolve_local_path(value: str) -> Path:
    if "\\" in value or value.startswith("/"):
        fail(f"path is not repository-relative: {value}")
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        fail(f"path escapes repository: {value}")
    return candidate


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
    )


def verify_git_baseline() -> None:
    git("cat-file", "-e", f"{BASELINE_COMMIT}^{{commit}}")
    ancestor = git("merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD", check=False)
    if ancestor.returncode != 0:
        fail("suite candidate commit is not an ancestor of HEAD")


def verify_bound_file(record: dict[str, Any]) -> None:
    path = resolve_local_path(record["path"])
    if not path.is_file():
        fail(f"bound file is missing: {record['path']}")
    actual = raw_sha256(path)
    if actual != record["rawSha256"]:
        fail(
            f"bound file digest mismatch for {record['path']}: "
            f"expected {record['rawSha256']}, got {actual}"
        )


def verify_baseline(launch: dict[str, Any], suite: dict[str, Any]) -> None:
    baseline = launch["baseline"]
    if baseline["suiteCandidateCommit"] != BASELINE_COMMIT:
        fail("unexpected suite candidate commit")
    if baseline["wireCommit"] != WIRE_COMMIT:
        fail("unexpected wire commit")
    if baseline["ci"] != {
        "workflow": "MIF verification",
        "runId": 31139940388,
        "url": "https://github.com/calcitem/mill-interchange-format/actions/runs/31139940388",
        "conclusion": "success",
    }:
        fail("suite candidate CI identity is not the frozen successful run")

    for name in (
        "suite",
        "artifactIndex",
        "deterministicCorpus",
        "differentialLaunch",
        "license",
    ):
        verify_bound_file(baseline[name])

    if baseline["suite"]["rawSha256"] != SUITE_RAW_DIGEST:
        fail("unexpected suite raw-file digest")
    if baseline["suite"]["jcsSha256"] != SUITE_JCS_DIGEST:
        fail("unexpected suite JCS digest")
    if jcs_digest(suite) != SUITE_JCS_DIGEST:
        fail("current suite JCS digest differs from the launch pin")

    manifest_record = baseline["releaseManifest"]
    manifest_blob = git("show", f"{BASELINE_COMMIT}:{manifest_record['path']}").stdout
    if sha256_bytes(manifest_blob) != manifest_record["rawSha256"]:
        fail("baseline release manifest blob digest mismatch")
    baseline_manifest = load_json_bytes(
        manifest_blob, f"{BASELINE_COMMIT}:{manifest_record['path']}"
    )
    if baseline_manifest.get("status") != manifest_record["status"]:
        fail("baseline release manifest status mismatch")

    deterministic = load_json(resolve_local_path(baseline["deterministicCorpus"]["path"]))
    if len(deterministic.get("cases", [])) != baseline["deterministicCorpus"]["cases"]:
        fail("deterministic case count does not match the launch")

    differential = load_json(resolve_local_path(baseline["differentialLaunch"]["path"]))
    seeded_runs = sum(len(item["seeds"]) for item in differential["scenarios"])
    if seeded_runs != baseline["differentialLaunch"]["seededRuns"]:
        fail("differential seeded-run count does not match the launch")
    families = differential["negativeCases"]["families"]
    if len(families) != baseline["differentialLaunch"]["mutationFamilies"]:
        fail("mutation-family count does not match the launch")


def verify_projects(projects: list[dict[str, Any]]) -> None:
    if [item["id"] for item in projects] != ["nmm-llm", "sanmill"]:
        fail("projects must be the sorted NMM_LLM and Sanmill pair")
    expected = {
        "nmm-llm": {
            "adapter": "nmm-llm-python",
            "repository": "https://github.com/benmarkbrandwood-blip/NMM_LLM.git",
            "branch": "dev",
            "implementationCommit": "6c1538082fc551203d827782d137a5799c810535",
            "independentEvidenceCommit": "382eddd1c5a3364c0056e152b524f517d126a113",
            "requiredOutcome": "suite-bound-evidence-pushed",
        },
        "sanmill": {
            "adapter": "sanmill-rust",
            "repository": "https://github.com/calcitem/Sanmill.git",
            "branch": "master",
            "implementationCommit": "ae9a1d8a16261478631a3a7583cbf35c7b6e0df5",
            "independentEvidenceCommit": "9431b95f151502f415f096c7d96ca944e5d578de",
            "threeProjectEvidenceCommit": "2a53a89893daae528af64503cc87e34bf07e66e3",
            "requiredOutcome": "suite-bound-evidence-pushed",
        },
    }
    for project in projects:
        identifier = project["id"]
        actual = {key: value for key, value in project.items() if key != "id"}
        if actual != expected[identifier]:
            fail(f"unexpected last-verified project baseline: {identifier}")


def verify_policy(launch: dict[str, Any], suite: dict[str, Any]) -> None:
    if launch["requiredClasses"] != REQUIRED_CLASSES:
        fail("required conformance classes are not the frozen tested-domain set")
    if "full" in launch["requiredClasses"] or "conversion" in launch["requiredClasses"]:
        fail("launch must not claim full or require direct implementers to claim conversion")
    if launch["rulesets"] != suite["rulesets"]:
        fail("launch ruleset semantic digests differ from the suite")

    evidence = launch["requiredEvidence"]
    if evidence["requiredFields"] != REQUIRED_FIELDS:
        fail("suite adapter evidence fields are not the frozen sorted set")
    if evidence["suiteConformance"] is not True:
        fail("final adapter evidence must be suite-bound")
    if evidence["unexplainedDifferences"] != 0:
        fail("final adapter evidence must require zero unexplained differences")

    gate = launch["trainingGate"]
    if gate["currentDecision"] != "not-yet-authorized":
        fail("formal training must remain gated before the signed suite tag")

    current_manifest = load_json(CURRENT_MANIFEST_PATH)
    if current_manifest["status"] != "awaiting-adapter-suite-pin":
        fail("finalization launch is stale after release status changed")
    if current_manifest["release"]["license"] != "Apache-2.0":
        fail("release manifest does not bind the repository Apache-2.0 policy")


def verify_finalization() -> str:
    for path in (LAUNCH_PATH, SCHEMA_PATH, SUITE_PATH, CURRENT_MANIFEST_PATH):
        if not path.is_file():
            fail(f"required file is missing: {path.relative_to(ROOT)}")
    launch = load_json(LAUNCH_PATH)
    schema = load_json(SCHEMA_PATH)
    suite = load_json(SUITE_PATH)
    validate_schema(launch, schema)
    verify_git_baseline()
    verify_baseline(launch, suite)
    verify_projects(launch["projects"])
    verify_policy(launch, suite)
    jcs_bytes(launch)
    return raw_sha256(LAUNCH_PATH)


def main() -> int:
    try:
        digest = verify_finalization()
    except (
        FinalizationVerificationError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"MIF Suite 1.0 adapter finalization verification FAILED: {exc}")
        return 1
    print(f"MIF Suite 1.0 adapter finalization verified: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
