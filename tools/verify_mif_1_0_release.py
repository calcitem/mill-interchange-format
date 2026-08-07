#!/usr/bin/env python3
"""Verify the MIF Suite 1.0 release package without changing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - incomplete local tooling
    raise SystemExit("jsonschema is required to verify the MIF 1.0 release") from exc


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.jcs import jcs_bytes, jcs_digest  # noqa: E402


SUITE_PATH = ROOT / "mif-suite-1.0.json"
DIGEST_PATH = ROOT / "mif-suite-1.0.sha256"
MANIFEST_PATH = ROOT / "release" / "mif-1.0-release-manifest.json"
MANIFEST_SCHEMA_PATH = (
    ROOT / "release" / "mif-1.0-release-manifest.schema.json"
)
MIF_SCHEMA_PATH = ROOT / "artifacts" / "mif-1.0" / "schema" / "mif-1.0.schema.json"
CANONICAL_REPOSITORY = "https://github.com/calcitem/mill-interchange-format.git"
WIRE_COMMIT = "7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978"
TAG = "mif-suite-1.0"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ReleaseVerificationError(RuntimeError):
    """The release package violates a frozen release invariant."""


def fail(message: str) -> None:
    raise ReleaseVerificationError(message)


def raw_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        fail(f"UTF-8 BOM is forbidden: {path.relative_to(ROOT)}")
    if b"\r" in raw:
        fail(f"CR bytes are forbidden: {path.relative_to(ROOT)}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                fail(f"duplicate JSON member {key!r}: {path.relative_to(ROOT)}")
            result[key] = value
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid UTF-8 JSON {path.relative_to(ROOT)}: {exc}")


def validate_schema(instance: Any, schema: Any, label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        first = errors[0]
        pointer = "/" + "/".join(str(part) for part in first.absolute_path)
        fail(f"{label} schema failure at {pointer}: {first.message}")


def require_sorted_unique(values: list[Any], key: Any, label: str) -> None:
    keys = [key(value) for value in values]
    if keys != sorted(keys):
        fail(f"{label} is not sorted")
    if len(keys) != len(set(keys)):
        fail(f"{label} contains duplicates")


def collect_suite_records(suite: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    groups = [("specifications", suite["specifications"])]
    groups.extend((name, values) for name, values in suite["artifacts"].items())
    for group, values in groups:
        require_sorted_unique(values, lambda item: item["id"], f"suite {group}")
        for record in values:
            identifier = record["id"]
            if identifier in records:
                fail(f"suite artifact id appears in multiple groups: {identifier}")
            records[identifier] = record
    return records


def verify_media_assignments(suite: dict[str, Any]) -> None:
    formats = {
        "MFEN/1.0": ("text/plain; charset=us-ascii", ".mfen"),
        "MPK/1.0": ("text/plain; charset=us-ascii", ".mpk"),
        "MIFPOS/1.0": ("application/json", ".mifpos.json"),
        "MSTATE/1.0": ("application/json", ".mstate.json"),
        "MRS/1.0": ("application/json", ".mrs.json"),
        "MIFDIAG/1.0": ("application/json", ".mifdiag.json"),
        "MIFCAP/1.0": ("application/json", ".mifcap.json"),
        "MIFCONV/1.0": ("application/json", ".mifconv.json"),
        "MIFINV/1.0": ("application/json", ".mifinv.json"),
        "MIFTURN/1.0": ("application/json", ".mifturn.json"),
        "MIFSUITE/1.0": ("application/json", ".mifsuite.json"),
    }
    expected_media = [
        {"format": fmt, "value": values[0]} for fmt, values in sorted(formats.items())
    ]
    expected_extensions = [
        {"format": fmt, "value": values[1]} for fmt, values in sorted(formats.items())
    ]
    if suite["mediaTypes"] != expected_media:
        fail("suite mediaTypes do not match the release policy")
    if suite["fileExtensions"] != expected_extensions:
        fail("suite fileExtensions do not match the release policy")


def resolve_local_path(value: str) -> Path:
    if "\\" in value or value.startswith("/"):
        fail(f"binding path is not repository-relative: {value}")
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        fail(f"binding path escapes repository: {value}")
    return candidate


def verify_bindings(
    suite: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    bindings = manifest["bindings"]
    require_sorted_unique(bindings, lambda item: item["id"], "release bindings")
    binding_map = {item["id"]: item for item in bindings}
    suite_records = collect_suite_records(suite)

    missing = sorted(set(suite_records) - set(binding_map))
    if missing:
        fail(f"suite records lack release bindings: {missing}")

    for identifier, record in suite_records.items():
        binding = binding_map[identifier]
        if binding["sha256"] != record["sha256"]:
            fail(f"suite/binding digest mismatch: {identifier}")
        if "commit" in record and binding.get("commit") != record["commit"]:
            fail(f"suite/binding commit mismatch: {identifier}")

    for identifier, binding in binding_map.items():
        if binding["repository"] != CANONICAL_REPOSITORY:
            fail(f"non-canonical binding repository: {identifier}")
        path = resolve_local_path(binding["path"])
        if not path.is_file():
            fail(f"bound file is missing: {binding['path']}")
        actual = raw_sha256(path)
        if actual != binding["sha256"]:
            fail(
                f"bound file digest mismatch for {identifier}: "
                f"expected {binding['sha256']}, got {actual}"
            )
    return binding_map


def verify_implementations(
    suite: dict[str, Any],
    manifest: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
) -> None:
    implementations = manifest["implementations"]
    require_sorted_unique(
        implementations, lambda item: item["id"], "release implementations"
    )
    projects = {item["project"] for item in implementations}
    if projects != {"NMM_LLM", "Sanmill"}:
        fail("release must bind exactly the independent Sanmill and NMM_LLM projects")

    adapter_ids = {record["id"] for record in suite["artifacts"]["adapters"]}
    for implementation in implementations:
        artifact_id = implementation["artifactBinding"]
        if artifact_id not in adapter_ids:
            fail(f"implementation does not reference a suite adapter: {artifact_id}")
        if bindings[artifact_id]["role"] != "adapter":
            fail(f"adapter binding has wrong role: {artifact_id}")

        evidence_id = implementation.get("suiteEvidenceBinding")
        if manifest["status"] == "awaiting-adapter-suite-pin":
            if evidence_id is not None:
                fail("awaiting manifest must not claim suite-bound adapter evidence")
            continue
        if evidence_id not in bindings or bindings[evidence_id]["role"] != "evidence":
            fail(f"ready implementation lacks bound suite evidence: {implementation['id']}")
        evidence = load_json(resolve_local_path(bindings[evidence_id]["path"]))
        if evidence.get("suiteDigest") != manifest["suite"]["sha256"]:
            fail(f"suite evidence digest mismatch: {implementation['id']}")
        if evidence.get("suiteConformance") is not True:
            fail(f"suite evidence does not claim conformance: {implementation['id']}")
        if evidence.get("unexplainedDifferences") != 0:
            fail(f"suite evidence has unresolved differences: {implementation['id']}")


def verify_release(require_ready: bool, require_tag: bool) -> str:
    for path in (
        SUITE_PATH,
        DIGEST_PATH,
        MANIFEST_PATH,
        MANIFEST_SCHEMA_PATH,
        MIF_SCHEMA_PATH,
    ):
        if not path.is_file():
            fail(f"required release file is missing: {path.relative_to(ROOT)}")

    suite = load_json(SUITE_PATH)
    manifest = load_json(MANIFEST_PATH)
    validate_schema(suite, load_json(MIF_SCHEMA_PATH), "MIFSUITE/1.0")
    validate_schema(manifest, load_json(MANIFEST_SCHEMA_PATH), "release manifest")

    if suite["id"] != "mif-suite-1.0":
        fail("unexpected suite id")
    if suite["compatibilityPolicy"] != "mif-1x-strict-v1":
        fail("unexpected compatibility policy")
    if suite["releaseManifest"] != "release/mif-1.0-release-manifest.json":
        fail("suite releaseManifest location mismatch")
    if suite["specifications"][0].get("commit") != WIRE_COMMIT:
        fail("wire specification commit mismatch")
    verify_media_assignments(suite)
    require_sorted_unique(suite["profiles"]["key"], lambda item: item, "suite key profiles")
    require_sorted_unique(
        suite["profiles"]["observation"],
        lambda item: item,
        "suite observation profiles",
    )
    require_sorted_unique(suite["rulesets"], lambda item: item, "suite rulesets")
    require_sorted_unique(
        suite["invarianceDeclarations"],
        lambda item: item,
        "suite invariance declarations",
    )

    digest = jcs_digest(suite)
    digest_text = DIGEST_PATH.read_text(encoding="ascii")
    if digest_text != digest + "\n":
        fail("mif-suite-1.0.sha256 does not contain the exact JCS digest")
    if not DIGEST_RE.fullmatch(digest):
        fail("suite digest has invalid lexical form")
    if manifest["suite"] != {"path": "mif-suite-1.0.json", "sha256": digest}:
        fail("release manifest suite binding mismatch")
    release = manifest["release"]
    if release["repository"] != CANONICAL_REPOSITORY or release["wireCommit"] != WIRE_COMMIT:
        fail("release source identity mismatch")

    bindings = verify_bindings(suite, manifest)
    verify_implementations(suite, manifest, bindings)

    subjects = manifest["signing"]["subjects"]
    if subjects != ["mif-suite-1.0.json", "release/mif-1.0-release-manifest.json"]:
        fail("signature subjects are not the frozen sorted pair")
    if require_ready and manifest["status"] != "ready-for-tag":
        fail("release manifest is not ready-for-tag")

    if require_tag:
        result = subprocess.run(
            ["git", "tag", "--points-at", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        if TAG not in result.stdout.splitlines():
            fail(f"HEAD is not tagged {TAG}")

    # Serialize once more so malformed I-JSON cannot hide behind Schema success.
    jcs_bytes(manifest)
    return digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="require final suite-bound evidence and ready-for-tag status",
    )
    parser.add_argument(
        "--require-tag",
        action="store_true",
        help=f"require HEAD to carry the immutable {TAG} tag",
    )
    args = parser.parse_args()
    try:
        digest = verify_release(args.require_ready, args.require_tag)
    except (ReleaseVerificationError, OSError, subprocess.CalledProcessError) as exc:
        print(f"MIF Suite 1.0 release verification FAILED: {exc}")
        return 1
    print(f"MIF Suite 1.0 release candidate verified: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
