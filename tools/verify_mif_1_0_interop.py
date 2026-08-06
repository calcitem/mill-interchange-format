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
M4_LAUNCH = INTEROP / "differential-candidate-4-v1.json"
M4_BASELINE = (
    INTEROP / "evidence" / "mif-1.0-candidate-4-m4-reference-baseline.json"
)
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
    M4_LAUNCH: (
        "560ef369fde248bd96d3468a4336442db1d970ede04f488821509e69925fd48e"
    ),
    INTEROP / "differential-v1.md": (
        "57056faf5fc347dc97876ada350784feb84acff2324ef00175c915c6d019a133"
    ),
    INTEROP / "cases" / "differential-negative-v1.json": (
        "b4072a2fd786104c5344619a818d59b657904e92c419175e795cc03fcd0697ff"
    ),
    INTEROP / "schema" / "adapter-cases-v1.schema.json": (
        "74877776612215ffa9c894ba659b7ce0e41b60fb4cb65e5b4f40a187b537ef7d"
    ),
    INTEROP / "schema" / "differential-launch-v1.schema.json": (
        "4452be5b48e085ad7887985fd5066f899bb96b00bef225e2b8c8b41a740a1f60"
    ),
    INTEROP / "schema" / "differential-report-v1.schema.json": (
        "d69646ac0a3746d4ac72d3bb1958e28019813da48dc71ea80e45a1d6d253c29e"
    ),
    ROOT / "tools" / "run_mif_1_0_differential.py": (
        "bcd23bf5666f3ba07e78e653fa4777a190719877341aa4e6adb159178fc6c505"
    ),
    M4_BASELINE: (
        "29d198dbcf8221fa0235af6a72db9d6a82646b45fc653c584071821a9a4bb61b"
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
    INTEROP / "cases" / "differential-negative-v1.json",
    M4_LAUNCH,
    INTEROP / "differential-v1.md",
    *sorted((INTEROP / "schema").glob("*.json")),
    *sorted((INTEROP / "evidence").glob("*.json")),
    *sorted((ROOT / "reference").glob("*.py")),
    ROOT / "tools" / "compare_mif_1_0_adapters.py",
    ROOT / "tools" / "mif_1_0_reference_adapter.py",
    ROOT / "tools" / "run_mif_1_0_differential.py",
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
    expected_counts = {
        "smoke-v1.json": 17,
        "deterministic-v1.json": 58,
        "differential-negative-v1.json": 4,
    }
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


def verify_m4_launch() -> None:
    launch = json.loads(
        M4_LAUNCH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_members,
    )
    baseline = json.loads(
        M4_BASELINE.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_members,
    )
    for document, schema_name, label in (
        (launch, "differential-launch-v1.schema.json", "M4 launch"),
        (baseline, "differential-report-v1.schema.json", "M4 baseline"),
    ):
        schema = json.loads(
            (INTEROP / "schema" / schema_name).read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_members,
        )
        errors = sorted(
            Draft202012Validator(schema).iter_errors(document),
            key=lambda item: list(item.absolute_path),
        )
        if errors:
            first = errors[0]
            pointer = "".join(f"/{token}" for token in first.absolute_path)
            raise VerificationError(
                f"{label} Schema failure at {pointer or '/'}: {first.message}"
            )

    if launch["baseline"] != {
        "mifCommit": "7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978",
        "m3ClosureCommit": "736801412e11dee9d2bfb65082757e0609a5ade3",
        "m3Evidence": {
            "path": "interop/evidence/mif-1.0-candidate-4-m3.json",
            "sha256": (
                "sha256:"
                "a354e810de0c74dd26226bee39b09f05c2677dbd693f95574fccc17d8c0c6671"
            ),
        },
    }:
        raise VerificationError("M4 launch baseline binding mismatch")
    if launch["suiteConformance"] is not False or launch["status"] != "candidate-only":
        raise VerificationError("M4 launch overclaims conformance")
    expected_seeds = {
        "placing-standard": ["0000000000000000", "0000000000000001"],
        "moving-standard": ["0123456789abcdef", "deadbeefcafef00d"],
        "flying-three-pieces": ["0000000000000002", "0000000000000003"],
        "pending-removal": ["1111111111111111"],
        "claim-right-at-origin": ["2222222222222222"],
        "terminal-full-board": ["3333333333333333"],
        "resource-limit-probe": ["4444444444444444"],
    }
    actual_seeds = {
        scenario["id"]: scenario["seeds"] for scenario in launch["scenarios"]
    }
    if actual_seeds != expected_seeds:
        raise VerificationError("M4 scenario or seed matrix mismatch")
    if launch["negativeCases"] != {
        "path": "interop/cases/differential-negative-v1.json",
        "families": [
            "illegal-event",
            "noncanonical-text",
            "digest-envelope-conflict",
            "truncated-history",
            "resource-limit",
        ],
    }:
        raise VerificationError("M4 negative mutation family mismatch")

    if (
        baseline["status"] != "passed"
        or baseline["suiteConformance"] is not False
        or baseline["launchDigest"]
        != "sha256:560ef369fde248bd96d3468a4336442db1d970ede04f488821509e69925fd48e"
        or baseline["configDigest"]
        != "sha256:2af95a7eacb11b854286df1312928d3e20c06055a488ddc54637d4db306e34a4"
        or baseline["adapters"] != ["reference-a", "reference-b"]
        or baseline["summary"]
        != {
            "runsPassed": 10,
            "runsFailed": 0,
            "negativePassed": 5,
            "negativeFailed": 0,
        }
    ):
        raise VerificationError("M4 reference baseline summary mismatch")
    expected_implementations = [
        {
            "adapter": name,
            "name": "mif-python-reference-runner",
            "version": "candidate-4",
            "capabilitiesDigest": (
                "sha256:"
                "f2a9890b9d3b4bca6f2197a8ba48e0075db88e2d25007536431d883d4ca76f8a"
            ),
        }
        for name in ("reference-a", "reference-b")
    ]
    if baseline["implementations"] != expected_implementations:
        raise VerificationError("M4 reference capability binding mismatch")

    scenarios = {scenario["id"]: scenario for scenario in launch["scenarios"]}
    expected_pairs = {
        (scenario, seed)
        for scenario, seeds in expected_seeds.items()
        for seed in seeds
    }
    actual_pairs = {(run["scenario"], run["seed"]) for run in baseline["runs"]}
    if len(baseline["runs"]) != 10 or actual_pairs != expected_pairs:
        raise VerificationError("M4 reference run identity mismatch")
    for run in baseline["runs"]:
        if run["status"] != "passed" or "failure" in run:
            raise VerificationError("M4 reference run is not clean")
        scenario = scenarios[run["scenario"]]
        if not set(scenario["requiredCoverage"]).issubset(run["coverage"]):
            raise VerificationError(
                f"M4 reference coverage missing for {run['scenario']}"
            )
        if run["logicalTurns"] > scenario["maxLogicalTurns"]:
            raise VerificationError("M4 reference logical-turn limit exceeded")
        if run["eventCount"] > scenario["maxEvents"]:
            raise VerificationError("M4 reference event limit exceeded")
    resource_runs = [
        run for run in baseline["runs"] if run["scenario"] == "resource-limit-probe"
    ]
    if (
        len(resource_runs) != 1
        or resource_runs[0]["stopReason"] != "logical-turn-limit"
        or resource_runs[0]["eventCount"] != 0
        or "resource-limit" not in resource_runs[0]["coverage"]
    ):
        raise VerificationError("M4 resource-limit probe mismatch")

    expected_negative = {
        "mutation-illegal-remove-without-obligation": (
            "illegal-event",
            "remove-without-obligation",
        ),
        "mutation-noncanonical-mpk-digest-uppercase": (
            "noncanonical-text",
            "non-canonical-digest",
        ),
        "mutation-envelope-semantic-digest-mismatch": (
            "digest-envelope-conflict",
            "semantic-digest-mismatch",
        ),
        "mutation-repetition-history-truncated": (
            "truncated-history",
            "repetition-history-mismatch",
        ),
        "mutation-harness-resource-limit": ("resource-limit", None),
    }
    actual_negative = {
        item["id"]: (item["family"], item["expectedCode"])
        for item in baseline["negativeCases"]
        if item["status"] == "passed" and "failure" not in item
    }
    if len(baseline["negativeCases"]) != 5 or actual_negative != expected_negative:
        raise VerificationError("M4 reference negative results mismatch")

    command = [
        sys.executable,
        "-B",
        str(ROOT / "tools" / "run_mif_1_0_differential.py"),
        "--config",
        str(INTEROP / "adapters.reference-loopback.json"),
        "--launch",
        str(M4_LAUNCH),
        "--expect-report",
        str(M4_BASELINE),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
        check=False,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise VerificationError(f"M4 reference baseline is not reproducible: {detail}")
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
        verify_m4_launch()
        verify_loopback()
    except (OSError, UnicodeError, json.JSONDecodeError, VerificationError) as exc:
        print(f"MIF 1.0 interop launch gate FAILED: {exc}")
        return 1
    print(
        "MIF 1.0 interop launch gate passed: fixed baselines, documents, "
        "Schema, 17-case smoke, 58-case deterministic reference loopbacks and "
        "commit-bound three-project M3 evidence plus the reproducible 10-run/"
        "5-mutation M4 reference launch baseline "
        "(candidate evidence only; Suite conformance not established)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
