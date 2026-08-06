#!/usr/bin/env python3
"""Read-only integrity checks for the frozen bilingual MIF 1.0 wire contract.

This checker validates documentation structure and deterministic inline
examples. It deliberately does not execute MIF transition or replay
conformance.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EN_PATH = ROOT / "mif-1.0.md"
ZH_PATH = ROOT / "docs" / "zh-CN" / "mif-1.0.md"
README_PATH = ROOT / "README.md"
FROZEN_04_PATH = ROOT / "mif-0.4.md"

EXPECTED_RAW_SHA256 = {
    EN_PATH: "330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995",
    ZH_PATH: "9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1",
}
EXPECTED_04_SHA256 = (
    "f1f1d839318a4d45f3ecea4850fee080c47ffcbc81025bd74e3ea48c815f3093"
)

FORMAT_SIGNATURES = {
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

REGISTERED_VERSIONED_TOKENS = {
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
HISTORICAL_VERSIONED_TOKENS = {"legal-state-v1"}

EXPECTED_HEADING_IDS = [
    "title",
    "status",
    "1",
    "2",
    "3",
    "3.1",
    "3.2",
    "3.3",
    "3.4",
    "3.5",
    "3.6",
    "4",
    "4.1",
    "4.2",
    "4.3",
    "5",
    "5.1",
    "5.2",
    "5.3",
    "5.4",
    "5.5",
    "5.6",
    "6",
    "6.1",
    "6.2",
    "6.3",
    "6.4",
    "6.5",
    "6.6",
    "7",
    "7.1",
    "7.2",
    "8",
    "8.1",
    "8.2",
    "9",
    "9.1",
    "9.2",
    "9.3",
    "9.4",
    "9.5",
    "10",
    "10.1",
    "10.2",
    "10.3",
    "10.4",
    "10.5",
    "10.6",
    "10.7",
    "11",
    "11.1",
    "11.2",
    "11.3",
    "11.4",
    "11.5",
    "11.6",
    "11.7",
    "11.8",
    "11.9",
    "12",
    "12.1",
    "12.2",
    "12.3",
    "12.4",
    "12.5",
    "13",
    "13.1",
    "13.2",
    "13.3",
    "13.4",
    "13.5",
    "13.6",
    "14",
    "14.1",
    "14.2",
    "14.3",
    "15",
    "15.1",
    "15.2",
    "15.3",
    "16",
    "16.1",
    "16.2",
    "16.3",
    "16.4",
    "A",
    "A.1",
    "A.2",
    "A.3",
    "A.4",
    "B",
    "C",
    "C.1",
    "C.2",
    "C.3",
    "C.4",
    "C.5",
    "C.6",
    "C.7",
    "C.8",
    "C.9",
]

EXPECTED_EXAMPLE_DIGESTS = {
    "semantic": "224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393",
    "document1": "62479b6f40efb8ab478bab3d2b725647213604fcd3cc9cd4c1f69357535ae257",
    "document2": "60b8f91214e2273a0f7eb411794ce3b133c61653b2199763ab555d90f042e6e4",
    "observation": "6adc3718c5b16999b2a75b444728656e9901b003b8ff641813d73b2cdcba1e4e",
    "empty_root": "e9fbf966ccdff764594a5e199e6aea0cc36034b46c8057cc3df88a088c20101a",
    "one_root": "3a08cdfcc2a0be8a7fd9277649ff0a2e2b30cb20b98d808f825594c9a31aa885",
    "decision": "f25cfb5dae617feba90fc1cbd48fb5d526727c8a3fad65910400a72a03657d19",
    "resumption1": "1abb022db99a0959d00c90ca5ba6a946b99d183c8a811e01f242ef081bf5d5b3",
    "resumption2": "2f2188fe6beb34042bcf201644f262d25552a5a6263d2ba0de024aa917a83657",
}


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jcs_bytes(value: object) -> bytes:
    # Inline vectors use only JCS-safe integers and strings; this is the exact
    # RFC 8785 serialization for that restricted value set.
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def jcs_sha256(value: object) -> str:
    return hashlib.sha256(jcs_bytes(value)).hexdigest()


def fenced_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    language: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("```"):
            if language is None:
                language = line[3:]
                body = []
            else:
                blocks.append((language, "\n".join(body)))
                language = None
                body = []
        elif language is not None:
            body.append(line)
    if language is not None:
        raise ValueError("unclosed Markdown fence")
    return blocks


def markdown_tables(text: str) -> list[list[str]]:
    lines = text.splitlines()
    result: list[list[str]] = []
    index = 0
    while index < len(lines):
        is_header = (
            lines[index].startswith("|")
            and index + 1 < len(lines)
            and re.match(r"^\|\s*:?-{3}", lines[index + 1]) is not None
        )
        if not is_header:
            index += 1
            continue
        table: list[str] = []
        while index < len(lines) and lines[index].startswith("|"):
            table.append(lines[index])
            index += 1
        result.append(table)
    return result


def heading_ids(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        if line == "# Mill Interchange Format 1.0":
            result.append("title")
            continue
        if line.startswith("## Candidate Wire Contract") or line.startswith(
            "## 候选 Wire Contract"
        ):
            result.append("status")
            continue
        match = re.match(
            r"^#{1,4}\s+(?:([0-9]+(?:\.[0-9]+)*)|Annex\s+([A-C])|([A-C]\.[0-9]+))",
            line,
        )
        if match:
            result.append(next(group for group in match.groups() if group))
    return result


def semantic_projection(manifest: dict[str, object]) -> dict[str, object]:
    projection = {
        "profile": "mrs-semantic-v1",
        "semanticsProfile": manifest["semanticsProfile"],
        "topology": manifest["topology"],
        "pieces": copy.deepcopy(manifest["pieces"]),
        "turn": copy.deepcopy(manifest["turn"]),
        "flying": copy.deepcopy(manifest["flying"]),
        "placing": copy.deepcopy(manifest["placing"]),
        "mills": copy.deepcopy(manifest["mills"]),
        "captures": copy.deepcopy(manifest["captures"]),
        "boardFull": copy.deepcopy(manifest["boardFull"]),
        "stalemate": copy.deepcopy(manifest["stalemate"]),
        "draw": copy.deepcopy(manifest["draw"]),
        "semanticState": copy.deepcopy(manifest["semanticState"]),
    }
    flying = projection["flying"]
    if isinstance(flying, dict) and not flying["enabled"]:
        projection["flying"] = {"enabled": False}
    placing = projection["placing"]
    assert isinstance(placing, dict)
    early_stop = placing["earlyStop"]
    assert isinstance(early_stop, dict)
    if early_stop["emptyPoints"] == 0:
        placing["earlyStop"] = {"emptyPoints": 0}
    captures = projection["captures"]
    assert isinstance(captures, dict)
    for name in ("custodian", "intervention", "leap"):
        mechanism = captures[name]
        assert isinstance(mechanism, dict)
        if not mechanism["enabled"]:
            captures[name] = {"enabled": False}
    draw = projection["draw"]
    assert isinstance(draw, dict)
    no_progress = draw["noProgress"]
    assert isinstance(no_progress, dict)
    if no_progress["normalLimit"] == 0 and no_progress["endgameLimit"] == 0:
        draw["noProgress"] = {"enabled": False}
    repetition = draw["repetition"]
    assert isinstance(repetition, dict)
    if repetition["count"] == 0:
        draw["repetition"] = {"count": 0}
    if "extensions" in manifest:
        projection["extensions"] = copy.deepcopy(manifest["extensions"])
    return projection


def sparse_merkle_roots(observation: dict[str, object], count: int) -> tuple[str, str]:
    observation_digest = hashlib.sha256(jcs_bytes(observation)).digest()
    empty = [hashlib.sha256(b"\x00").digest()]
    for _ in range(256):
        empty.append(hashlib.sha256(b"\x02" + empty[-1] + empty[-1]).digest())
    node = hashlib.sha256(
        b"\x01" + observation_digest + struct.pack(">Q", count)
    ).digest()
    bits = "".join(f"{byte:08b}" for byte in observation_digest)
    for level, bit in enumerate(reversed(bits)):
        children = node + empty[level] if bit == "0" else empty[level] + node
        node = hashlib.sha256(b"\x02" + children).digest()
    return empty[256].hex(), node.hex()


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    required_paths = [EN_PATH, ZH_PATH, README_PATH, FROZEN_04_PATH]
    for path in required_paths:
        check(path.is_file(), f"missing required file: {path.relative_to(ROOT)}", errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    texts: dict[Path, str] = {}
    for path in (EN_PATH, ZH_PATH):
        raw = path.read_bytes()
        label = path.relative_to(ROOT).as_posix()
        check(not raw.startswith(b"\xef\xbb\xbf"), f"BOM in {label}", errors)
        check(b"\r" not in raw, f"non-LF newline in {label}", errors)
        check(raw.endswith(b"\n"), f"missing final LF in {label}", errors)
        check(
            re.search(rb"[ \t]+\n", raw) is None,
            f"trailing whitespace in {label}",
            errors,
        )
        try:
            texts[path] = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"invalid UTF-8 in {label}: {exc}")

    if EN_PATH not in texts or ZH_PATH not in texts:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    en = texts[EN_PATH]
    zh = texts[ZH_PATH]
    for path, text in texts.items():
        label = path.relative_to(ROOT).as_posix()
        check(
            re.search(r"\b(?:TBD|TODO|placeholder)\b", text, re.IGNORECASE) is None,
            f"unfinished marker in {label}",
            errors,
        )

    check(heading_ids(en) == EXPECTED_HEADING_IDS, "English heading layout drift", errors)
    check(heading_ids(zh) == EXPECTED_HEADING_IDS, "Chinese heading layout drift", errors)

    en_tables = markdown_tables(en)
    zh_tables = markdown_tables(zh)
    check(len(en_tables) == 22, "English table count is not 22", errors)
    check(len(zh_tables) == 22, "Chinese table count is not 22", errors)
    if len(en_tables) == len(zh_tables):
        for index, (en_table, zh_table) in enumerate(zip(en_tables, zh_tables), 1):
            check(
                len(en_table) == len(zh_table),
                f"table {index} row-count mismatch",
                errors,
            )
            en_tokens = re.findall(r"`([^`]+)`", "\n".join(en_table))
            zh_tokens = re.findall(r"`([^`]+)`", "\n".join(zh_table))
            check(en_tokens == zh_tokens, f"table {index} wire-token mismatch", errors)

    try:
        en_blocks = fenced_blocks(en)
        zh_blocks = fenced_blocks(zh)
        check(en_blocks == zh_blocks, "bilingual fenced wire blocks differ", errors)
    except ValueError as exc:
        errors.append(str(exc))
        en_blocks = []
        zh_blocks = []

    version_pattern = re.compile(
        r"(?<![A-Za-z0-9.-])([a-z][a-z0-9.-]*-v[0-9]+)(?![A-Za-z0-9.-])"
    )
    expected_versioned = REGISTERED_VERSIONED_TOKENS | HISTORICAL_VERSIONED_TOKENS
    for label, text, start, end in (
        ("English", en, "This contract registers:", "An implementation shall emit"),
        ("Chinese", zh, "本合同注册：", "实现只能输出"),
    ):
        used = set(version_pattern.findall(text))
        check(used == expected_versioned, f"{label} versioned-token set drift", errors)
        if start in text and end in text:
            registry = text.split(start, 1)[1].split(end, 1)[0]
            missing = sorted(token for token in REGISTERED_VERSIONED_TOKENS if token not in registry)
            check(not missing, f"{label} unregistered profiles: {missing}", errors)
        else:
            errors.append(f"{label} profile registry boundary missing")

    for signature in FORMAT_SIGNATURES:
        check(signature in en, f"English missing signature {signature}", errors)
        check(signature in zh, f"Chinese missing signature {signature}", errors)

    abnf_blocks = [body for language, body in en_blocks if language == "abnf"]
    check(len(abnf_blocks) == 1, "expected exactly one inline ABNF block", errors)
    if len(abnf_blocks) == 1:
        abnf = abnf_blocks[0]
        rules = set(re.findall(r"^([a-z][a-z0-9-]*)\s*=", abnf, re.MULTILINE))
        required_rules = {
            "mfen",
            "mpk",
            "digest",
            "board",
            "obligations",
            "outcome",
            "extension",
            "lm-value",
            "pc-value",
            "ul-value",
        }
        check(required_rules <= rules, "inline ABNF rule set incomplete", errors)
        check('%s"MFEN/1.0"' in abnf, "MFEN/1.0 ABNF literal missing", errors)
        check('%s"MPK/1.0"' in abnf, "MPK/1.0 ABNF literal missing", errors)
        check(
            re.search(
                r"mpk\s*=.*?state-profile SP ruleset SP digest\s+SP key-profile",
                abnf,
                re.DOTALL,
            )
            is not None,
            "MPK semanticDigest ABNF position drift",
            errors,
        )

    json_objects: list[dict[str, object]] = []
    for language, body in en_blocks:
        if language != "json":
            continue
        try:
            value = json.loads(body)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid inline JSON example: {exc}")
            continue
        if isinstance(value, dict):
            json_objects.append(value)

    manifests = [obj for obj in json_objects if obj.get("format") == "MRS/1.0"]
    projections = [obj for obj in json_objects if obj.get("profile") == "mrs-semantic-v1"]
    decisions = [obj for obj in json_objects if obj.get("profile") == "decision-state-v1"]
    resumptions = [obj for obj in json_objects if obj.get("profile") == "resumption-state-v1"]
    check(len(manifests) == 1, "expected one complete MRS digest fixture", errors)
    check(len(projections) == 1, "expected one semantic projection fixture", errors)
    check(len(decisions) == 1, "expected one decision-state fixture", errors)
    check(len(resumptions) == 2, "expected two resumption-state fixtures", errors)

    if len(manifests) == 1 and len(projections) == 1:
        manifest = manifests[0]
        projection = projections[0]
        check(
            semantic_projection(manifest) == projection,
            "inline semantic projection does not match mrs-semantic-v1",
            errors,
        )
        check(
            jcs_sha256(projection) == EXPECTED_EXAMPLE_DIGESTS["semantic"],
            "semanticDigest worked example mismatch",
            errors,
        )
        check(
            jcs_sha256(manifest) == EXPECTED_EXAMPLE_DIGESTS["document1"],
            "documentDigest D1 worked example mismatch",
            errors,
        )
        retitled = copy.deepcopy(manifest)
        retitled["title"] = "Example Morris (retitled)"
        check(
            jcs_sha256(retitled) == EXPECTED_EXAMPLE_DIGESTS["document2"],
            "documentDigest D2 worked example mismatch",
            errors,
        )

    if len(decisions) == 1 and len(resumptions) == 2:
        decision = decisions[0]
        resumptions.sort(key=lambda value: int(value["lastEventSeq"]))
        observation = resumptions[0]["repetitionHistory"][0]["key"]  # type: ignore[index]
        assert isinstance(observation, dict)
        check(
            jcs_sha256(observation) == EXPECTED_EXAMPLE_DIGESTS["observation"],
            "observationDigest worked example mismatch",
            errors,
        )
        empty_root, one_root = sparse_merkle_roots(observation, 1)
        check(empty_root == EXPECTED_EXAMPLE_DIGESTS["empty_root"], "empty SMT root mismatch", errors)
        check(one_root == EXPECTED_EXAMPLE_DIGESTS["one_root"], "one-count SMT root mismatch", errors)
        check(jcs_sha256(decision) == EXPECTED_EXAMPLE_DIGESTS["decision"], "decisionDigest mismatch", errors)
        check(
            jcs_sha256(resumptions[0]) == EXPECTED_EXAMPLE_DIGESTS["resumption1"],
            "resumptionDigest R1 mismatch",
            errors,
        )
        check(
            jcs_sha256(resumptions[1]) == EXPECTED_EXAMPLE_DIGESTS["resumption2"],
            "resumptionDigest R2 mismatch",
            errors,
        )

    for name, digest in EXPECTED_EXAMPLE_DIGESTS.items():
        lexical = f"sha256:{digest}"
        check(lexical in en, f"English missing worked digest {name}", errors)
        check(lexical in zh, f"Chinese missing worked digest {name}", errors)

    readme = README_PATH.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
            continue
        local_target = target.split("#", 1)[0]
        resolved = (ROOT / local_target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"README link escapes repository: {target}")
            continue
        check(resolved.exists(), f"broken README link: {target}", errors)

    for path, expected in EXPECTED_RAW_SHA256.items():
        label = path.relative_to(ROOT).as_posix()
        actual = raw_sha256(path)
        check(actual == expected, f"raw-file SHA-256 drift: {label}", errors)
        check(f"{label} sha256:{expected}" in readme, f"README hash missing: {label}", errors)

    check(
        raw_sha256(FROZEN_04_PATH) == EXPECTED_04_SHA256,
        "frozen mif-0.4.md SHA-256 drift",
        errors,
    )
    check(
        "MIF Suite 1.0 conformance is not yet available" in en,
        "English candidate status missing",
        errors,
    )
    check(
        "MIF Suite 1.0 conformance 尚不可用" in zh,
        "Chinese candidate status missing",
        errors,
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "MIF 1.0 wire contract integrity passed "
        "(documentation only; executable conformance not performed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
