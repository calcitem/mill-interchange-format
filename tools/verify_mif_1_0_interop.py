#!/usr/bin/env python3
"""Verify the non-normative MIF 1.0 interoperability launch package."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
INTEROP = ROOT / "interop"
PLAN = ROOT / "docs" / "zh-CN" / "mif-1.0-three-project-interop-plan.md"
M3_EVIDENCE = INTEROP / "evidence" / "mif-1.0-candidate-4-m3.json"
BASELINE_DIGESTS = {
    ROOT / "mif-1.0.md": (
        "330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995"
    ),
    ROOT / "docs" / "zh-CN" / "mif-1.0.md": (
        "9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1"
    ),
    ROOT / "artifacts" / "mif-1.0" / "index.json": (
        "5acbb714bed77e24eaac72fa5f24d2e54d1e17aaf568a8b60718c840281a6541"
    ),
    ROOT
    / "artifacts"
    / "mif-1.0"
    / "corpus"
    / "executable"
    / "reference-cases.json": (
        "350b7ff02772e820a57431e11c4e2f15a874d0779fb6e7afb01e9b16f6992741"
    ),
    INTEROP / "adapter-protocol-v1.md": (
        "253c1d201ea1db625e0c534da445ca4ecaa0b07597dfc7dbf59fbd6adf89874f"
    ),
    INTEROP / "cases" / "smoke-v1.json": (
        "a6d292f4d19381172fbc19f89d3ee42145a6d5533d6d81fd719394e25342bb53"
    ),
    INTEROP / "cases" / "deterministic-v1.json": (
        "d11317a090300f8a47f77afed647bdbd236dcdb1996c0147a81c874fa39dfd82"
    ),
    M3_EVIDENCE: (
        "a354e810de0c74dd26226bee39b09f05c2677dbd693f95574fccc17d8c0c6671"
    ),
    ROOT / "mif-0.4.md": (
        "f1f1d839318a4d45f3ecea4850fee080c47ffcbc81025bd74e3ea48c815f3093"
    ),
}
TEXT_FILES = [
    ROOT / "README.md",
    ROOT / "reference" / "README.md",
    PLAN,
    INTEROP / "README.md",
    INTEROP / "adapter-protocol-v1.md",
    INTEROP / "adapters.reference-loopback.json",
    INTEROP / "cases" / "smoke-v1.json",
    INTEROP / "cases" / "deterministic-v1.json",
    *sorted((INTEROP / "schema").glob("*.json")),
    *sorted((INTEROP / "evidence").glob("*.json")),
    *sorted((ROOT / "reference").glob("*.py")),
    ROOT / "tools" / "compare_mif_1_0_adapters.py",
    ROOT / "tools" / "mif_1_0_reference_adapter.py",
    Path(__file__).resolve(),
]
PYTHON_FILES = [path for path in TEXT_FILES if path.suffix == ".py"]
MARKDOWN_FILES = [path for path in TEXT_FILES if path.suffix == ".md"]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


class VerificationError(Exception):
    """A collaboration launch artifact violates its fixed contract."""


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON member after unescape: {key}")
        result[key] = value
    return result


def verify_baselines() -> None:
    for path, expected in BASELINE_DIGESTS.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise VerificationError(
                f"baseline digest mismatch for {path.relative_to(ROOT)}: {actual}"
            )


def verify_text() -> None:
    for path in TEXT_FILES:
        raw = path.read_bytes()
        relative = path.relative_to(ROOT)
        if raw.startswith(b"\xef\xbb\xbf"):
            raise VerificationError(f"UTF-8 BOM is forbidden: {relative}")
        if b"\r" in raw:
            raise VerificationError(f"CR byte is forbidden: {relative}")
        if not raw.endswith(b"\n"):
            raise VerificationError(f"final LF is missing: {relative}")
        text = raw.decode("utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                raise VerificationError(
                    f"trailing whitespace: {relative}:{line_number}"
                )


def verify_json_and_schemas() -> None:
    documents: dict[Path, Any] = {}
    for path in sorted(INTEROP.rglob("*.json")):
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_members,
        )
        documents[path.resolve()] = document
        if path.parent.name == "schema":
            Draft202012Validator.check_schema(document)

    cases_schema = documents[
        (INTEROP / "schema" / "adapter-cases-v1.schema.json").resolve()
    ]
    cases_validator = Draft202012Validator(cases_schema)
    expected_counts = {"smoke-v1.json": 17, "deterministic-v1.json": 58}
    for path in sorted((INTEROP / "cases").glob("*.json")):
        document = documents[path.resolve()]
        errors = sorted(
            cases_validator.iter_errors(document),
            key=lambda item: list(item.absolute_path),
        )
        if errors:
            first = errors[0]
            pointer = "".join(f"/{token}" for token in first.absolute_path)
            raise VerificationError(
                f"case Schema failure: {path.relative_to(ROOT)}{pointer}: "
                f"{first.message}"
            )
        ids = [case["id"] for case in document["cases"]]
        if len(ids) != len(set(ids)):
            raise VerificationError(f"duplicate case ID: {path.relative_to(ROOT)}")
        expected_count = expected_counts.get(path.name)
        if expected_count is None:
            raise VerificationError(f"unregistered case source: {path.relative_to(ROOT)}")
        if len(ids) != expected_count:
            raise VerificationError(
                f"fixed case count mismatch for {path.name}: {len(ids)}"
            )

    deterministic = documents[
        (INTEROP / "cases" / "deterministic-v1.json").resolve()
    ]["cases"]
    operation_counts = {
        operation: sum(case["operation"] == operation for case in deterministic)
        for operation in {
            "capabilities",
            "canonicalize",
            "execute",
            "project-legal-actions",
            "project-logical-turns",
            "replay",
            "transform",
        }
    }
    expected_operation_counts = {
        "capabilities": 1,
        "canonicalize": 10,
        "execute": 11,
        "project-legal-actions": 8,
        "project-logical-turns": 2,
        "replay": 5,
        "transform": 21,
    }
    if operation_counts != expected_operation_counts:
        raise VerificationError(
            f"deterministic operation coverage changed: {operation_counts}"
        )
    required_ids = {
        "canonicalize-mpk-digest-missing",
        "canonicalize-mpk-digest-uppercase",
        "execute-placing-cycle-stable-moving",
        "execute-claim-forbidden-during-removal",
        "execute-origin-phase-sync-asymmetric-reserve",
        "project-legal-actions-moving-flying",
        "project-legal-actions-pending-remove",
        "project-legal-actions-unstabilized",
        "project-legal-actions-asymmetric-reserve-moving",
        "project-legal-actions-asymmetric-reserve-unstabilized",
        "replay-offer-r1-portable",
        "project-origin-stabilization",
        "transform-mstate-mirror-anti",
        "transform-decision-mirror-anti",
        "transform-mifpos-portable-jcs-boundaries",
    }
    actual_ids = {case["id"] for case in deterministic}
    missing = required_ids.difference(actual_ids)
    if missing:
        raise VerificationError(
            f"deterministic corpus omits required cases: {sorted(missing)}"
        )


def verify_python() -> None:
    for path in PYTHON_FILES:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def verify_markdown() -> None:
    for path in MARKDOWN_FILES:
        text = path.read_text(encoding="utf-8")
        fences = sum(1 for line in text.splitlines() if line.startswith("```"))
        if fences % 2:
            raise VerificationError(f"unclosed Markdown fence: {path.relative_to(ROOT)}")
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (path.parent / target_path).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError as exc:
                raise VerificationError(
                    f"Markdown link escapes repository: {path.relative_to(ROOT)} -> {target}"
                ) from exc
            if not resolved.exists():
                raise VerificationError(
                    f"broken Markdown link: {path.relative_to(ROOT)} -> {target}"
                )


def verify_required_language() -> None:
    protocol = (INTEROP / "adapter-protocol-v1.md").read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    for token in (
        "MIF-INTEROP/1",
        "capabilities",
        "canonicalize",
        "execute",
        "replay",
        "transform",
        "project-legal-actions",
        "legal-actions-v1",
        "project-logical-turns",
        "semantic-equality",
        "$pointer",
        "$patch",
    ):
        if token not in protocol:
            raise VerificationError(f"adapter protocol omits required token: {token}")
    for token in (
        "Sanmill",
        "NMM_LLM",
        "Byte-level",
        "State-level",
        "Replay-level",
        "M0 Baseline",
        "M5 Release",
        "M3 已完成",
        "M4 Differential",
    ):
        if token not in plan:
            raise VerificationError(f"collaboration plan omits required token: {token}")


def verify_m3_evidence() -> None:
    evidence = json.loads(
        M3_EVIDENCE.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_members,
    )
    expected_members = {
        "artifact",
        "status",
        "suiteConformance",
        "baseline",
        "implementations",
        "threeProjectReport",
        "commitBinding",
        "verification",
        "nextMilestone",
    }
    if set(evidence) != expected_members:
        raise VerificationError("M3 evidence member set mismatch")
    if (
        evidence["artifact"] != "mif-1.0-candidate-4-m3-evidence"
        or evidence["status"]
        != "m3-deterministic-complete-suite-unpublished"
        or evidence["suiteConformance"] is not False
        or evidence["nextMilestone"] != "M4-differential"
    ):
        raise VerificationError("M3 evidence status mismatch")

    baseline = evidence["baseline"]
    if set(baseline) != {"repository", "branch", "commit", "inputs"}:
        raise VerificationError("M3 baseline member set mismatch")
    if (
        baseline["repository"]
        != "https://github.com/calcitem/mill-interchange-format.git"
        or baseline["branch"] != "master"
        or baseline["commit"]
        != "7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978"
    ):
        raise VerificationError("M3 baseline identity mismatch")
    expected_inputs = {
        "mif-1.0.md": (
            "330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995"
        ),
        "docs/zh-CN/mif-1.0.md": (
            "9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1"
        ),
        "artifacts/mif-1.0/index.json": (
            "5acbb714bed77e24eaac72fa5f24d2e54d1e17aaf568a8b60718c840281a6541"
        ),
        "artifacts/mif-1.0/corpus/executable/reference-cases.json": (
            "350b7ff02772e820a57431e11c4e2f15a874d0779fb6e7afb01e9b16f6992741"
        ),
        "interop/adapter-protocol-v1.md": (
            "253c1d201ea1db625e0c534da445ca4ecaa0b07597dfc7dbf59fbd6adf89874f"
        ),
        "interop/cases/smoke-v1.json": (
            "a6d292f4d19381172fbc19f89d3ee42145a6d5533d6d81fd719394e25342bb53"
        ),
        "interop/cases/deterministic-v1.json": (
            "d11317a090300f8a47f77afed647bdbd236dcdb1996c0147a81c874fa39dfd82"
        ),
    }
    if not isinstance(baseline["inputs"], list) or any(
        set(item) != {"path", "sha256"} for item in baseline["inputs"]
    ):
        raise VerificationError("M3 evidence input member set mismatch")
    actual_inputs = {
        item["path"]: item["sha256"] for item in baseline["inputs"]
    }
    if len(actual_inputs) != len(baseline["inputs"]) or actual_inputs != {
        path: f"sha256:{digest}" for path, digest in expected_inputs.items()
    }:
        raise VerificationError("M3 evidence input binding mismatch")
    for relative, digest in expected_inputs.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise VerificationError(f"M3 evidence input bytes changed: {relative}")

    expected_implementations = [
        {
            "project": "MIF",
            "adapter": "mif-reference",
            "repository": "https://github.com/calcitem/mill-interchange-format.git",
            "branch": "master",
            "testedCommit": "7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978",
        },
        {
            "project": "Sanmill",
            "adapter": "sanmill-rust",
            "repository": "https://github.com/calcitem/Sanmill.git",
            "branch": "master",
            "testedCommit": "e6d639d41f079b15ca697268d0c2c21dad5c2bc3",
            "evidenceCommit": "fe780b7d40ce1c101b2f635e45bee780dfd30606",
        },
        {
            "project": "NMM_LLM",
            "adapter": "nmm-llm-python",
            "repository": "https://github.com/benmarkbrandwood-blip/NMM_LLM.git",
            "branch": "dev",
            "testedCommit": "11bebd14e0d538a41a4b43aebfe57ee74c2a2601",
            "documentationCommit": "e2ab05d29885af9a16a9aa5d5f62b1517cf6d91b",
        },
    ]
    if evidence["implementations"] != expected_implementations:
        raise VerificationError("M3 implementation commit binding mismatch")

    report = evidence["threeProjectReport"]
    if report != {
        "repository": "https://github.com/calcitem/Sanmill.git",
        "commit": "e6d639d41f079b15ca697268d0c2c21dad5c2bc3",
        "path": (
            "interop/evidence/"
            "mif-interop-candidate-4-three-project-report-2026-08-06.json"
        ),
        "sha256": (
            "sha256:895c04cd69fc00e50bdcd349b150293e52fcc4150c63321d8c9771015f70aaaf"
        ),
        "protocol": "MIF-INTEROP-REPORT/1",
        "adapters": ["mif-reference", "sanmill-rust", "nmm-llm-python"],
        "casesDigest": (
            "sha256:d11317a090300f8a47f77afed647bdbd236dcdb1996c0147a81c874fa39dfd82"
        ),
        "configDigest": (
            "sha256:4184d56c696b2e5031d95cc18918757af9f91fa5634dded579ecfae2ef3cf70f"
        ),
        "summary": {"passed": 58, "failed": 0},
    }:
        raise VerificationError("M3 report binding mismatch")
    if evidence["commitBinding"] != {
        "repository": "https://github.com/calcitem/Sanmill.git",
        "commit": "fe780b7d40ce1c101b2f635e45bee780dfd30606",
        "path": (
            "interop/evidence/"
            "mif-interop-candidate-4-three-project-evidence-manifest-2026-08-06.json"
        ),
        "sha256": (
            "sha256:aeb119d074a4ff53f819c9aed0d5ac2b5951e83ab9ea74e2d6a5bf91d1d4fd06"
        ),
        "protocol": "SANMILL-MIF-INTEROP-EVIDENCE/1",
    }:
        raise VerificationError("M3 companion evidence binding mismatch")
    if evidence["verification"] != {
        "method": "independent-rerun-and-byte-identity-v1",
        "date": "2026-08-06",
        "reportSha256": report["sha256"],
        "passed": 58,
        "failed": 0,
    }:
        raise VerificationError("M3 independent verification record mismatch")


def verify_loopback() -> None:
    for case_name, count in (("smoke-v1.json", 17), ("deterministic-v1.json", 58)):
        command = [
            sys.executable,
            "-B",
            "tools/compare_mif_1_0_adapters.py",
            "--config",
            "interop/adapters.reference-loopback.json",
            "--cases",
            f"interop/cases/{case_name}",
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stdout + completed.stderr).strip()
            raise VerificationError(
                f"reference loopback failed for {case_name}: {details}"
            )
        expected = f"MIF interop comparison passed: {count} cases across 2 adapters"
        if expected not in completed.stdout:
            raise VerificationError(
                f"reference loopback did not report the fixed {case_name} count"
            )


def main() -> int:
    try:
        verify_baselines()
        verify_text()
        verify_json_and_schemas()
        verify_python()
        verify_markdown()
        verify_required_language()
        verify_m3_evidence()
        verify_loopback()
    except (OSError, UnicodeError, json.JSONDecodeError, VerificationError) as exc:
        print(f"MIF 1.0 interop launch gate FAILED: {exc}")
        return 1
    print(
        "MIF 1.0 interop launch gate passed: fixed baselines, documents, "
        "Schema, 17-case smoke, 58-case deterministic reference loopbacks and "
        "commit-bound three-project M3 evidence "
        "(candidate evidence only; Suite conformance not established)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
