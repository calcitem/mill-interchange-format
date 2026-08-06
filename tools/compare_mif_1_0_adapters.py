#!/usr/bin/env python3
"""Compare independent MIF-INTEROP/1 adapters over deterministic NDJSON."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.jcs import JCSValueError, jcs_bytes as rfc8785_bytes  # noqa: E402

INTEROP = ROOT / "interop"
ARTIFACT = ROOT / "artifacts" / "mif-1.0"
MESSAGE_SCHEMA = INTEROP / "schema" / "adapter-message-v1.schema.json"
CONFIG_SCHEMA = INTEROP / "schema" / "adapter-config-v1.schema.json"
CASES_SCHEMA = INTEROP / "schema" / "adapter-cases-v1.schema.json"


class HarnessError(Exception):
    """A process, source, Schema or protocol failure in the harness itself."""


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HarnessError(f"duplicate JSON member after unescape: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_members,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HarnessError(f"cannot read JSON {path}: {exc}") from exc


def raw_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def jcs_bytes(value: Any) -> bytes:
    try:
        return rfc8785_bytes(value)
    except JCSValueError as exc:
        raise HarnessError(str(exc)) from exc


def safe_repo_path(relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise HarnessError("repository path must be a non-empty string")
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise HarnessError(f"path escapes repository: {relative}") from exc
    if not candidate.is_file():
        raise HarnessError(f"referenced file does not exist: {relative}")
    return candidate


def pointer_parts(pointer: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise HarnessError(f"invalid JSON Pointer: {pointer!r}")
    return [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer[1:].split("/")
    ]


def resolve_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return copy.deepcopy(value)
    cursor = value
    for token in pointer_parts(pointer):
        try:
            cursor = cursor[int(token)] if isinstance(cursor, list) else cursor[token]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise HarnessError(f"source pointer does not exist: {pointer}") from exc
    return copy.deepcopy(cursor)


def apply_patch(value: Any, mutations: list[Mapping[str, Any]]) -> Any:
    result = copy.deepcopy(value)
    for mutation in mutations:
        if set(mutation) not in ({"op", "path"}, {"op", "path", "value"}):
            raise HarnessError(f"invalid patch member set: {sorted(mutation)}")
        operation = mutation["op"]
        parts = pointer_parts(mutation["path"])
        parent = result
        for token in parts[:-1]:
            try:
                parent = parent[int(token)] if isinstance(parent, list) else parent[token]
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise HarnessError(f"patch path does not exist: {mutation['path']}") from exc
        leaf = parts[-1]
        if operation == "remove":
            try:
                if isinstance(parent, list):
                    del parent[int(leaf)]
                else:
                    del parent[leaf]
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise HarnessError(f"remove path does not exist: {mutation['path']}") from exc
        elif operation == "replace":
            if "value" not in mutation:
                raise HarnessError("replace patch requires value")
            replacement = expand_sources(mutation["value"])
            try:
                if isinstance(parent, list):
                    parent[int(leaf)] = replacement
                else:
                    if leaf not in parent:
                        raise KeyError(leaf)
                    parent[leaf] = replacement
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise HarnessError(f"replace path does not exist: {mutation['path']}") from exc
        elif operation == "add":
            if "value" not in mutation:
                raise HarnessError("add patch requires value")
            replacement = expand_sources(mutation["value"])
            if isinstance(parent, list):
                if leaf == "-":
                    parent.append(replacement)
                else:
                    parent.insert(int(leaf), replacement)
            else:
                parent[leaf] = replacement
        else:
            raise HarnessError(f"unsupported patch operation: {operation}")
    return result


def expand_sources(value: Any) -> Any:
    if isinstance(value, list):
        return [expand_sources(item) for item in value]
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    if "$json" in value:
        if not set(value).issubset({"$json", "$pointer", "$patch"}):
            raise HarnessError(
                "$json source permits only $json, $pointer and $patch"
            )
        loaded = read_json(safe_repo_path(value["$json"]))
        loaded = resolve_pointer(loaded, value.get("$pointer", ""))
        mutations = value.get("$patch", [])
        if not isinstance(mutations, list):
            raise HarnessError("$patch must be an array")
        return apply_patch(loaded, mutations)
    return {key: expand_sources(child) for key, child in value.items()}


def build_registry() -> tuple[Registry, dict[Path, Any]]:
    registry = Registry()
    documents: dict[Path, Any] = {}
    schema_paths = [
        *sorted((ARTIFACT / "schema").glob("*.json")),
        MESSAGE_SCHEMA,
        CONFIG_SCHEMA,
        CASES_SCHEMA,
    ]
    for path in schema_paths:
        document = read_json(path)
        Draft202012Validator.check_schema(document)
        registry = registry.with_resource(
            document["$id"], Resource.from_contents(document)
        )
        documents[path.resolve()] = document
    return registry, documents


def validate_document(
    value: Any,
    schema_path: Path,
    registry: Registry,
    documents: Mapping[Path, Any],
) -> None:
    validator = Draft202012Validator(
        documents[schema_path.resolve()],
        registry=registry,
    )
    errors = sorted(
        validator.iter_errors(value),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        first = errors[0]
        pointer = "".join(f"/{token}" for token in first.absolute_path)
        raise HarnessError(
            f"Schema validation failed for {schema_path.name}{pointer}: {first.message}"
        )


def expand_placeholder(value: str) -> str:
    return value.replace("{python}", sys.executable).replace("{repo}", str(ROOT))


def run_adapter(
    adapter: Mapping[str, Any],
    requests: list[dict[str, Any]],
    *,
    timeout: float,
    registry: Registry,
    documents: Mapping[Path, Any],
) -> list[dict[str, Any]]:
    command = [expand_placeholder(item) for item in adapter["command"]]
    working_text = expand_placeholder(adapter.get("workingDirectory", "{repo}"))
    working = Path(working_text).resolve()
    try:
        working.relative_to(ROOT)
    except ValueError as exc:
        raise HarnessError(
            f"adapter {adapter['name']} working directory escapes repository"
        ) from exc
    if not working.is_dir():
        raise HarnessError(
            f"adapter {adapter['name']} working directory does not exist: {working}"
        )
    environment = os.environ.copy()
    for key, value in adapter.get("environment", {}).items():
        environment[key] = expand_placeholder(value)
    wire = b"".join(
        jcs_bytes(request) + b"\n"
        for request in requests
    )
    try:
        completed = subprocess.run(
            command,
            cwd=working,
            env=environment,
            input=wire,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessError(f"adapter {adapter['name']} could not run: {exc}") from exc
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0:
        raise HarnessError(
            f"adapter {adapter['name']} exited {completed.returncode}: {stderr}"
        )
    raw = completed.stdout
    if b"\r" in raw:
        raise HarnessError(f"adapter {adapter['name']} emitted a CR byte")
    if raw and not raw.endswith(b"\n"):
        raise HarnessError(f"adapter {adapter['name']} omitted final LF")
    try:
        output = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HarnessError(f"adapter {adapter['name']} output is not UTF-8") from exc
    lines = output.splitlines()
    if len(lines) != len(requests):
        raise HarnessError(
            f"adapter {adapter['name']} returned {len(lines)} responses for "
            f"{len(requests)} requests"
        )
    responses: list[dict[str, Any]] = []
    for index, (line, request) in enumerate(zip(lines, requests, strict=True)):
        try:
            response = json.loads(
                line,
                object_pairs_hook=reject_duplicate_members,
            )
        except (json.JSONDecodeError, HarnessError) as exc:
            raise HarnessError(
                f"adapter {adapter['name']} response {index + 1} is invalid JSON: {exc}"
            ) from exc
        validate_document(response, MESSAGE_SCHEMA, registry, documents)
        for member in ("requestId", "operation"):
            if response[member] != request[member]:
                raise HarnessError(
                    f"adapter {adapter['name']} response {index + 1} "
                    f"does not echo {member}"
                )
        responses.append(response)
    return responses


def validate_snapshot(
    snapshot: Mapping[str, Any],
    registry: Registry,
    documents: Mapping[Path, Any],
) -> None:
    expected = {
        "boundary",
        "eventSeq",
        "current",
        "repetitionHistory",
        "claims",
        "claimRights",
        "decisionState",
        "decisionDigest",
    }
    if set(snapshot) != expected:
        raise HarnessError(f"trace snapshot member set mismatch: {sorted(snapshot)}")
    if snapshot["boundary"] not in {"origin", "event"}:
        raise HarnessError("trace snapshot boundary is invalid")
    event_seq = snapshot["eventSeq"]
    if snapshot["boundary"] == "origin":
        if event_seq is not None:
            raise HarnessError("origin trace eventSeq must be null")
    elif isinstance(event_seq, bool) or not isinstance(event_seq, int) or event_seq < 1:
        raise HarnessError("event trace eventSeq must be a positive integer")
    if not isinstance(snapshot["current"], str):
        raise HarnessError("trace current must be MFEN text")
    if not isinstance(snapshot["repetitionHistory"], list):
        raise HarnessError("trace repetitionHistory must be an array")
    if not isinstance(snapshot["claims"], list):
        raise HarnessError("trace claims must be an array")
    if snapshot["claimRights"] is not None and not isinstance(
        snapshot["claimRights"], dict
    ):
        raise HarnessError("trace claimRights must be an object or null")
    validate_document(
        snapshot["decisionState"],
        ARTIFACT / "schema" / "decision-state-v1.schema.json",
        registry,
        documents,
    )
    if snapshot["decisionDigest"] != "sha256:" + hashlib.sha256(
        jcs_bytes(snapshot["decisionState"])
    ).hexdigest():
        raise HarnessError("trace decisionDigest mismatch")


def validate_result(
    case: Mapping[str, Any],
    response: Mapping[str, Any],
    registry: Registry,
    documents: Mapping[Path, Any],
) -> None:
    if response["status"] == "error":
        return
    operation = case["operation"]
    result = response["result"]
    if operation == "capabilities":
        if set(result) != {"capabilities"}:
            raise HarnessError("capabilities result member set mismatch")
        validate_document(
            result["capabilities"],
            ARTIFACT / "schema" / "mifcap-1.0.schema.json",
            registry,
            documents,
        )
        if any(
            item["id"] == "MIF-INTEROP/1"
            for item in result["capabilities"]["formats"]
        ):
            raise HarnessError(
                "MIF-INTEROP/1 must not appear in MIF capability formats"
            )
        return
    if operation == "canonicalize":
        if set(result) != {"value"} or not isinstance(result["value"], str):
            raise HarnessError("canonicalize result shape mismatch")
        return
    if operation == "execute":
        if set(result) != {"trace", "final"} or not result["trace"]:
            raise HarnessError("execute result shape mismatch")
        for snapshot in result["trace"]:
            validate_snapshot(snapshot, registry, documents)
        if result["final"] != result["trace"][-1]:
            raise HarnessError("execute final does not equal last trace snapshot")
        return
    if operation == "replay":
        required = {
            "current",
            "trace",
            "repetitionHistory",
            "claims",
            "claimRights",
            "decisionState",
            "decisionDigest",
            "resumptionState",
            "resumptionDigest",
        }
        if set(result) != required or not result["trace"]:
            raise HarnessError("replay result member set mismatch")
        for snapshot in result["trace"]:
            validate_snapshot(snapshot, registry, documents)
        final = result["trace"][-1]
        for member in (
            "current", "repetitionHistory", "claims", "claimRights",
            "decisionState", "decisionDigest",
        ):
            if result[member] != final[member]:
                raise HarnessError(
                    f"replay {member} does not equal the last trace snapshot"
                )
        validate_document(
            result["decisionState"],
            ARTIFACT / "schema" / "decision-state-v1.schema.json",
            registry,
            documents,
        )
        validate_document(
            result["resumptionState"],
            ARTIFACT / "schema" / "resumption-state-v1.schema.json",
            registry,
            documents,
        )
        if result["decisionDigest"] != "sha256:" + hashlib.sha256(
            jcs_bytes(result["decisionState"])
        ).hexdigest():
            raise HarnessError("replay decisionDigest mismatch")
        if result["resumptionDigest"] != "sha256:" + hashlib.sha256(
            jcs_bytes(result["resumptionState"])
        ).hexdigest():
            raise HarnessError("replay resumptionDigest mismatch")
        return
    if operation == "project-logical-turns":
        if set(result) != {"document"}:
            raise HarnessError("logical-turn result member set mismatch")
        validate_document(
            result["document"],
            ARTIFACT / "schema" / "mifturn-1.0.schema.json",
            registry,
            documents,
        )
        return
    if operation == "transform":
        kind = case["payload"]["kind"]
        expected_members = (
            {
                "document",
                "decisionState",
                "decisionDigest",
                "resumptionState",
                "resumptionDigest",
            }
            if kind == "mstate"
            else {"document"}
        )
        if set(result) != expected_members:
            raise HarnessError("transform result member set mismatch")
        schema_names = {
            "mstate": "mstate-1.0.schema.json",
            "mifpos": "mifpos-1.0.schema.json",
            "decision-state": "decision-state-v1.schema.json",
        }
        validate_document(
            result["document"],
            ARTIFACT / "schema" / schema_names[kind],
            registry,
            documents,
        )
        if kind == "mstate":
            for member, schema_name in (
                ("decisionState", "decision-state-v1.schema.json"),
                ("resumptionState", "resumption-state-v1.schema.json"),
            ):
                validate_document(
                    result[member],
                    ARTIFACT / "schema" / schema_name,
                    registry,
                    documents,
                )
            for member, digest_name in (
                ("decisionState", "decisionDigest"),
                ("resumptionState", "resumptionDigest"),
            ):
                expected_digest = "sha256:" + hashlib.sha256(
                    jcs_bytes(result[member])
                ).hexdigest()
                if result[digest_name] != expected_digest:
                    raise HarnessError(f"transform {digest_name} mismatch")
        return
    raise HarnessError(f"unhandled operation result: {operation}")


def normalize_error(response: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = copy.deepcopy(response["diagnostics"])
    diagnostics.pop("annotations", None)
    for error in diagnostics["errors"]:
        error.pop("message", None)
    return {"status": "error", "diagnostics": diagnostics}


def comparison_value(response: Mapping[str, Any]) -> Any:
    if response["status"] == "error":
        return normalize_error(response)
    return {"status": "ok", "result": response["result"]}


def first_difference(left: Any, right: Any, path: str = "") -> tuple[str, Any, Any] | None:
    if type(left) is not type(right):
        return path, left, right
    if isinstance(left, dict):
        if set(left) != set(right):
            return path, sorted(left), sorted(right)
        for key in sorted(left):
            difference = first_difference(left[key], right[key], f"{path}/{key}")
            if difference is not None:
                return difference
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return path, len(left), len(right)
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            difference = first_difference(
                left_item,
                right_item,
                f"{path}/{index}",
            )
            if difference is not None:
                return difference
        return None
    return None if left == right else (path, left, right)


def compare(
    cases: list[Mapping[str, Any]],
    adapters: list[Mapping[str, Any]],
    responses: Mapping[str, list[Mapping[str, Any]]],
    registry: Registry,
    documents: Mapping[Path, Any],
) -> tuple[list[dict[str, Any]], int]:
    reports: list[dict[str, Any]] = []
    failures = 0
    baseline_name = adapters[0]["name"]
    for index, case in enumerate(cases):
        case_responses = {
            adapter["name"]: responses[adapter["name"]][index]
            for adapter in adapters
        }
        case_errors: list[str] = []
        for name, response in case_responses.items():
            try:
                if response["status"] != case["expectedStatus"]:
                    raise HarnessError(
                        f"expected status {case['expectedStatus']}, got {response['status']}"
                    )
                if "expectedCode" in case:
                    actual_code = (
                        response["diagnostics"]["errors"][0]["code"]
                        if response["status"] == "error"
                        else None
                    )
                    if actual_code != case["expectedCode"]:
                        raise HarnessError(
                            f"expected code {case['expectedCode']}, got {actual_code}"
                        )
                validate_result(case, response, registry, documents)
            except HarnessError as exc:
                case_errors.append(f"{name}: {exc}")
        if case["comparison"] == "semantic-equality" and not case_errors:
            baseline = comparison_value(case_responses[baseline_name])
            baseline_bytes = jcs_bytes(baseline)
            for adapter in adapters[1:]:
                name = adapter["name"]
                candidate = comparison_value(case_responses[name])
                if jcs_bytes(candidate) != baseline_bytes:
                    difference = first_difference(baseline, candidate)
                    assert difference is not None
                    pointer, expected, actual = difference
                    case_errors.append(
                        f"{baseline_name} != {name} at {pointer or '/'}: "
                        f"{expected!r} != {actual!r}"
                    )
        status = "passed" if not case_errors else "failed"
        if case_errors:
            failures += 1
        reports.append(
            {
                "id": case["id"],
                "operation": case["operation"],
                "comparison": case["comparison"],
                "status": status,
                "errors": case_errors,
            }
        )
    return reports, failures


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path = path.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise HarnessError("report path must remain inside the repository") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--allow-single", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        registry, documents = build_registry()
        config_path = args.config.resolve()
        cases_path = args.cases.resolve()
        config = read_json(config_path)
        source = read_json(cases_path)
        validate_document(config, CONFIG_SCHEMA, registry, documents)
        validate_document(source, CASES_SCHEMA, registry, documents)
        adapters = config["adapters"]
        if len(adapters) < 2 and not args.allow_single:
            raise HarnessError("at least two adapters are required for comparison")
        names = [adapter["name"] for adapter in adapters]
        if len(names) != len(set(names)):
            raise HarnessError("adapter names are not unique")
        case_ids = [case["id"] for case in source["cases"]]
        if len(case_ids) != len(set(case_ids)):
            raise HarnessError("case IDs are not unique")
        cases: list[dict[str, Any]] = []
        requests: list[dict[str, Any]] = []
        for case in source["cases"]:
            expanded = copy.deepcopy(dict(case))
            expanded["payload"] = expand_sources(case["payload"])
            request = {
                "protocol": "MIF-INTEROP/1",
                "kind": "request",
                "requestId": case["id"],
                "operation": case["operation"],
                "payload": expanded["payload"],
            }
            validate_document(request, MESSAGE_SCHEMA, registry, documents)
            cases.append(expanded)
            requests.append(request)
        responses = {
            adapter["name"]: run_adapter(
                adapter,
                requests,
                timeout=args.timeout,
                registry=registry,
                documents=documents,
            )
            for adapter in adapters
        }
        case_reports, failures = compare(
            cases,
            adapters,
            responses,
            registry,
            documents,
        )
        report = {
            "protocol": "MIF-INTEROP-REPORT/1",
            "configDigest": raw_digest(config_path),
            "casesDigest": raw_digest(cases_path),
            "adapters": names,
            "cases": case_reports,
            "summary": {
                "passed": len(case_reports) - failures,
                "failed": failures,
            },
        }
        if args.report is not None:
            write_report(args.report, report)
        if failures:
            print(
                f"MIF interop comparison FAILED: {failures}/{len(case_reports)} cases"
            )
            for case in case_reports:
                for error in case["errors"]:
                    print(f"- {case['id']}: {error}")
            return 1
        print(
            "MIF interop comparison passed: "
            f"{len(case_reports)} cases across {len(adapters)} adapters "
            "(candidate interoperability evidence only)"
        )
        return 0
    except HarnessError as exc:
        print(f"MIF interop harness FAILED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
