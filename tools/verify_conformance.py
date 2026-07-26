#!/usr/bin/env python3
"""Verify MIF draft/corpus integrity using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / "conformance"
INDEX = CONF / "index.json"
SPEC = ROOT / "mif-0.4.md"
GUIDE = ROOT / "docs" / "zh-CN" / "mif-0.4-guide.md"


class VerificationError(Exception):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def duplicate_safe_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON member after unescaping: {key!r}")
        result[key] = value
    return result


def safe_int(text: str) -> int:
    value = int(text)
    if abs(value) > 9_007_199_254_740_991:
        fail(f"I-JSON integer out of range: {text}")
    return value


def load_json(path: Path) -> Any:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        fail(f"UTF-8 BOM is not permitted: {path.relative_to(ROOT)}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"invalid UTF-8 in {path.relative_to(ROOT)}: {exc}")
    try:
        return json.loads(
            text,
            object_pairs_hook=duplicate_safe_pairs,
            parse_int=safe_int,
            parse_constant=lambda token: fail(f"non-I-JSON number {token}"),
        )
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def canonical_json(value: Any) -> bytes:
    # The normative fixture/JCS inputs intentionally use the RFC 8785 subset
    # consisting of ASCII member names, strings, integers, booleans and null.
    def inspect(node: Any) -> None:
        if isinstance(node, float):
            fail("floating-point JCS input is outside this corpus verifier's subset")
        if isinstance(node, dict):
            for key, child in node.items():
                if not key.isascii():
                    fail("non-ASCII JCS member name is outside this corpus verifier's subset")
                inspect(child)
        elif isinstance(node, list):
            for child in node:
                inspect(child)

    inspect(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def corpus_files() -> list[Path]:
    return sorted(
        (path for path in CONF.rglob("*") if path.is_file() and path != INDEX),
        key=lambda path: path.relative_to(CONF).as_posix(),
    )


def update_index() -> None:
    current = load_json(INDEX)
    current["format"] = "MIF-CONFORMANCE-INDEX/0.4"
    current["draft"] = "MIF Community Working Draft 0.4"
    current["hashAlgorithm"] = "sha256"
    current["digestDomain"] = "raw-file-bytes"
    current["selfExcluded"] = True
    current["files"] = [
        {
            "path": path.relative_to(CONF).as_posix(),
            "bytes": len(raw := path.read_bytes()),
            "sha256": sha256(raw),
        }
        for path in corpus_files()
    ]
    INDEX.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verify_index() -> None:
    index = load_json(INDEX)
    if index.get("format") != "MIF-CONFORMANCE-INDEX/0.4":
        fail("index format is not 0.4")
    expected = {path.relative_to(CONF).as_posix(): path for path in corpus_files()}
    entries = index.get("files")
    if not isinstance(entries, list):
        fail("index files is not an array")
    seen: set[str] = set()
    for entry in entries:
        name = entry["path"]
        if name in seen:
            fail(f"duplicate index path: {name}")
        seen.add(name)
        path = expected.get(name)
        if path is None:
            fail(f"index contains missing or excluded path: {name}")
        raw = path.read_bytes()
        if entry["bytes"] != len(raw):
            fail(f"index byte length mismatch: {name}")
        if entry["sha256"] != sha256(raw):
            fail(f"index SHA-256 mismatch: {name}")
    if seen != set(expected):
        missing = sorted(set(expected) - seen)
        fail(f"index omits corpus files: {missing}")


def manifests() -> dict[str, tuple[Path, str, Any]]:
    result: dict[str, tuple[Path, str, Any]] = {}
    spec = SPEC.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    for path in sorted((CONF / "manifests").glob("*.json")):
        value = load_json(path)
        identity = f"{value['id']}@{value['version']}"
        if path.stem != identity:
            fail(f"manifest filename/identity mismatch: {path.name} vs {identity}")
        if value.get("format") != "MRS/0.4":
            fail(f"manifest is not MRS/0.4: {path.name}")
        digest = sha256(canonical_json(value))
        if identity in result:
            fail(f"duplicate manifest identity: {identity}")
        if digest not in spec:
            fail(f"manifest digest missing from Annex D: {identity}")
        if digest not in guide:
            fail(f"manifest digest missing from Chinese guide: {identity}")
        result[identity] = (path, digest, value)
    return result


def strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


def verify_ruleset_references(mf: dict[str, tuple[Path, str, Any]]) -> None:
    pattern = re.compile(
        r"(?:MFEN|MPK)/0\.4 [^\"\r\n]*?\b"
        r"(?P<ruleset>[a-z0-9][a-z0-9.-]*@[1-9][0-9]*)\b"
        r"[^\"\r\n]*?\brh=sha256:(?P<digest>[0-9a-f]{64})"
    )
    count = 0
    for path in sorted(CONF.rglob("*.json")):
        value = load_json(path)
        for text in strings(value):
            for match in pattern.finditer(text):
                count += 1
                identity = match.group("ruleset")
                if identity not in mf:
                    fail(f"unresolved fixture {identity} in {path.relative_to(ROOT)}")
                if match.group("digest") != mf[identity][1]:
                    fail(f"ruleset digest mismatch for {identity} in {path.relative_to(ROOT)}")
    if count == 0:
        fail("no MFEN/MPK ruleset references were checked")

    example = load_json(CONF / "examples" / "mstate-pending-board.json")
    ruleset = example["ruleset"]
    identity = f"{ruleset['id']}@{ruleset['version']}"
    if identity not in mf or ruleset["digest"] != f"sha256:{mf[identity][1]}":
        fail("MSTATE envelope ruleset digest mismatch")
    if canonical_json(ruleset["manifest"]) != canonical_json(mf[identity][2]):
        fail("MSTATE embedded manifest mismatch")


def verify_jcs_vectors() -> None:
    path = CONF / "vectors" / "json-jcs.json"
    vectors = load_json(path)
    for vector in vectors["canonicalization"]:
        input_path = (path.parent / vector["inputPath"]).resolve()
        raw = canonical_json(load_json(input_path))
        if len(raw) != vector["expectedUtf8Length"]:
            fail(f"JCS byte length mismatch: {vector['id']}")
        if raw.decode("utf-8") != vector["expectedJcs"]:
            fail(f"JCS output mismatch: {vector['id']}")
        if sha256(raw) != vector["sha256"]:
            fail(f"JCS digest mismatch: {vector['id']}")


def verify_abnf() -> None:
    spec = SPEC.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"# Annex C \(normative\).*?```abnf\n(.*?)\n```", spec, re.S)
    if not match:
        fail("cannot locate Annex C ABNF fence")
    embedded = match.group(1).strip()
    lines = (CONF / "mif-0.4.abnf").read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
    while lines and (not lines[0].strip() or lines[0].startswith(";")):
        lines.pop(0)
    standalone = "\n".join(lines).strip()
    if embedded != standalone:
        fail("Annex C ABNF differs from conformance/mif-0.4.abnf")


def verify_transforms() -> None:
    data = load_json(CONF / "vectors" / "transforms.json")
    lines16 = [
        [0, 1, 2], [2, 3, 4], [4, 5, 6], [6, 7, 0],
        [8, 9, 10], [10, 11, 12], [12, 13, 14], [14, 15, 8],
        [16, 17, 18], [18, 19, 20], [20, 21, 22], [22, 23, 16],
        [1, 9, 17], [3, 11, 19], [5, 13, 21], [7, 15, 23],
    ]
    lines20 = lines16 + [[0, 8, 16], [2, 10, 18], [4, 12, 20], [6, 14, 22]]
    by_id: dict[str, Any] = {}
    for transform in data["transforms"]:
        identity = transform["id"]
        if identity in by_id:
            fail(f"duplicate transform id: {identity}")
        by_id[identity] = transform
        pp = transform["pointPermutation"]
        lp16 = transform["linePermutation16"]
        lp20 = transform["linePermutation20"]
        if sorted(pp) != list(range(24)):
            fail(f"point transform is not bijective: {identity}")
        if sorted(lp16) != list(range(16)) or sorted(lp20) != list(range(20)):
            fail(f"line transform is not bijective: {identity}")
        for lines, permutation in ((lines16, lp16), (lines20, lp20)):
            for source, target in enumerate(permutation):
                mapped = {pp[index] for index in lines[source]}
                if mapped != set(lines[target]):
                    fail(f"transform does not preserve topology: {identity}, line {source}")

    source = data["singlePieceCandidates"]["sourceBoard"]
    generated: list[str] = []
    for transform in data["transforms"]:
        board = ["."] * 24
        for old, token in enumerate(source):
            board[transform["pointPermutation"][old]] = token
        generated.append("".join(board))
    if generated[:8] != data["singlePieceCandidates"]["d4"]:
        fail("D4 single-piece candidates do not match point permutations")
    if min(generated[:8]) != data["singlePieceCandidates"]["d4Selected"]:
        fail("D4 selected board is not canonical minimum")
    if min(generated) != data["singlePieceCandidates"]["aut16Selected"]:
        fail("Aut16 selected board is not canonical minimum")

    for vector in data["lineIdActionTransforms"]:
        transform = by_id[vector["transform"]]
        if transform["linePermutation16"][vector["sourceLineId"]] != vector["normalizedLineId"]:
            fail(f"line action transform mismatch: {vector['id']}")


def verify_mstate_contract() -> None:
    data = load_json(CONF / "vectors" / "mstate.json")
    ids: set[str] = set()
    for vector in data["validReplay"]:
        identity = vector["id"]
        if identity in ids:
            fail(f"duplicate MSTATE vector id: {identity}")
        ids.add(identity)
        if "preOriginClaims" not in vector or not isinstance(vector["preOriginClaims"], list):
            fail(f"missing preOriginClaims seed: {identity}")
        if not isinstance(vector.get("claims"), list):
            fail(f"missing final claims audit: {identity}")
    required = {
        "MSTATE-REPLAY-PREORIGIN-OFFER",
        "MSTATE-ORIGIN-PREORIGIN-OFFER-AUTO-EXPIRE",
        "MSTATE-REPLAY-PHASE-SYNC-M-TO-P",
        "MSTATE-REPLAY-PHASE-SYNC-P-TO-M",
        "MSTATE-ORIGIN-PLACING-STABILIZATION",
        "MSTATE-REPLAY-REMOVAL-DYNAMIC-CAPACITY",
        "MSTATE-ORIGIN-SIMULTANEOUS-MINIMUM",
        "MSTATE-REPLAY-LEAP-MILL-SEMANTICS",
    }
    if not required.issubset(ids):
        fail(f"missing required 0.4 MSTATE vectors: {sorted(required - ids)}")


def verify_mapping_digest() -> None:
    path = CONF / "vectors" / "implementation-mappings.json"
    digest = sha256(path.read_bytes())
    if digest not in SPEC.read_text(encoding="utf-8"):
        fail("Annex E implementation-mappings raw digest mismatch")


def verify_all() -> None:
    for path in sorted(CONF.rglob("*.json")):
        load_json(path)
    mf = manifests()
    verify_index()
    verify_ruleset_references(mf)
    verify_jcs_vectors()
    verify_abnf()
    verify_transforms()
    verify_mstate_contract()
    verify_mapping_digest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-index", action="store_true")
    args = parser.parse_args()
    try:
        if args.update_index:
            update_index()
        verify_all()
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        return 1
    print("MIF 0.4 corpus verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
