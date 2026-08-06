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
BASELINE_DIGESTS = {
    ROOT / "mif-1.0.md": (
        "330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995"
    ),
    ROOT / "docs" / "zh-CN" / "mif-1.0.md": (
        "9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1"
    ),
    ROOT / "artifacts" / "mif-1.0" / "index.json": (
        "176db4d3701af8aa66c1691e87f99fddb71bf484f07ce9d9380e79e8fa62e10b"
    ),
    ROOT
    / "artifacts"
    / "mif-1.0"
    / "corpus"
    / "executable"
    / "reference-cases.json": (
        "e3af2bd5e2d88774a8ce7a4344702c0878ddffba8b77fa0740f3d3104a1258dd"
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
    *sorted((INTEROP / "schema").glob("*.json")),
    ROOT / "reference" / "mif1_adapter.py",
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
    for path in sorted(INTEROP.rglob("*.json")):
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_members,
        )
        if path.parent.name == "schema":
            Draft202012Validator.check_schema(document)


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
    ):
        if token not in plan:
            raise VerificationError(f"collaboration plan omits required token: {token}")


def verify_loopback() -> None:
    command = [
        sys.executable,
        "-B",
        "tools/compare_mif_1_0_adapters.py",
        "--config",
        "interop/adapters.reference-loopback.json",
        "--cases",
        "interop/cases/smoke-v1.json",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        details = (completed.stdout + completed.stderr).strip()
        raise VerificationError(f"reference loopback failed: {details}")
    expected = "MIF interop comparison passed: 16 cases across 2 adapters"
    if expected not in completed.stdout:
        raise VerificationError("reference loopback did not report the fixed case count")


def main() -> int:
    try:
        verify_baselines()
        verify_text()
        verify_json_and_schemas()
        verify_python()
        verify_markdown()
        verify_required_language()
        verify_loopback()
    except (OSError, UnicodeError, json.JSONDecodeError, VerificationError) as exc:
        print(f"MIF 1.0 interop launch gate FAILED: {exc}")
        return 1
    print(
        "MIF 1.0 interop launch gate passed: fixed baselines, documents, "
        "Schema and 16-case reference loopback "
        "(harness evidence only; independent conformance not established)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
