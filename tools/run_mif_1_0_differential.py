#!/usr/bin/env python3
"""Run deterministic multi-adapter MIF candidate differential trajectories."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any, Mapping



ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compare_mif_1_0_adapters as base  # noqa: E402


INTEROP = ROOT / "interop"
LAUNCH_SCHEMA = INTEROP / "schema" / "differential-launch-v1.schema.json"
REPORT_SCHEMA = INTEROP / "schema" / "differential-report-v1.schema.json"
MASK64 = (1 << 64) - 1
COVERAGE_ORDER = (
    "placing",
    "moving",
    "flying",
    "removal",
    "claim-right",
    "repetition",
    "terminal",
    "resource-limit",
)


class DifferentialError(Exception):
    """The launch package, harness process or deterministic run is invalid."""


class DifferenceError(Exception):
    """Adapters disagree or one adapter violates the expected response contract."""

    def __init__(self, failure: dict[str, Any]) -> None:
        super().__init__(failure["stage"])
        self.failure = failure


class SplitMix64:
    """Unsigned SplitMix64 with an observable state and draw count."""

    def __init__(self, seed: str) -> None:
        self.state = int(seed, 16)
        self.draws = 0

    def next(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        value ^= value >> 31
        self.draws += 1
        return value

    def state_hex(self) -> str:
        return f"{self.state:016x}"


class AdapterSession:
    """A persistent MIF-INTEROP/1 adapter process with bounded responses."""

    def __init__(
        self,
        adapter: Mapping[str, Any],
        *,
        timeout_ms: int,
        max_response_bytes: int,
        max_total_requests: int,
        registry: Any,
        documents: Mapping[Path, Any],
    ) -> None:
        self.name = adapter["name"]
        self.timeout = timeout_ms / 1000.0
        self.max_response_bytes = max_response_bytes
        self.max_total_requests = max_total_requests
        self.requests = 0
        self.registry = registry
        self.documents = documents
        command = [base.expand_placeholder(item) for item in adapter["command"]]
        working_text = base.expand_placeholder(
            adapter.get("workingDirectory", "{repo}")
        )
        working = Path(working_text).resolve()
        try:
            working.relative_to(ROOT)
        except ValueError as exc:
            raise DifferentialError(
                f"adapter {self.name} working directory escapes repository"
            ) from exc
        if not working.is_dir():
            raise DifferentialError(
                f"adapter {self.name} working directory does not exist: {working}"
            )
        environment = os.environ.copy()
        for key, value in adapter.get("environment", {}).items():
            environment[key] = base.expand_placeholder(value)
        self.stderr_file = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(
                command,
                cwd=working,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.stderr_file,
            )
        except OSError as exc:
            self.stderr_file.close()
            raise DifferentialError(
                f"adapter {self.name} could not start: {exc}"
            ) from exc
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.reader = ThreadPoolExecutor(max_workers=1)
        self.closed = False

    def _stderr(self) -> str:
        self.stderr_file.flush()
        self.stderr_file.seek(0)
        return self.stderr_file.read().decode("utf-8", errors="replace").strip()

    def _abort(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    def request(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if self.closed:
            raise DifferentialError(f"adapter {self.name} is already closed")
        if self.requests >= self.max_total_requests:
            raise DifferentialError(
                f"adapter {self.name} exceeded maxTotalRequests="
                f"{self.max_total_requests}"
            )
        base.validate_document(
            request,
            base.MESSAGE_SCHEMA,
            self.registry,
            self.documents,
        )
        wire = base.jcs_bytes(request) + b"\n"
        try:
            self.process.stdin.write(wire)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            self._abort()
            raise DifferentialError(
                f"adapter {self.name} input failed: {exc}; {self._stderr()}"
            ) from exc
        self.requests += 1
        future = self.reader.submit(
            self.process.stdout.readline,
            self.max_response_bytes + 2,
        )
        try:
            raw = future.result(timeout=self.timeout)
        except FutureTimeout as exc:
            self._abort()
            raise DifferentialError(
                f"adapter {self.name} exceeded perRequestTimeoutMs"
            ) from exc
        if not raw:
            self._abort()
            raise DifferentialError(
                f"adapter {self.name} closed stdout: {self._stderr()}"
            )
        if b"\r" in raw:
            self._abort()
            raise DifferentialError(f"adapter {self.name} emitted a CR byte")
        if not raw.endswith(b"\n"):
            self._abort()
            raise DifferentialError(
                f"adapter {self.name} response exceeds maxResponseBytes or omits LF"
            )
        raw_json = raw[:-1]
        if len(raw_json) > self.max_response_bytes:
            self._abort()
            raise DifferentialError(
                f"adapter {self.name} response exceeds maxResponseBytes"
            )
        try:
            response = json.loads(
                raw_json.decode("utf-8"),
                object_pairs_hook=base.reject_duplicate_members,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, base.HarnessError) as exc:
            self._abort()
            raise DifferentialError(
                f"adapter {self.name} emitted invalid JSON: {exc}"
            ) from exc
        base.validate_document(
            response,
            base.MESSAGE_SCHEMA,
            self.registry,
            self.documents,
        )
        for member in ("requestId", "operation"):
            if response[member] != request[member]:
                raise DifferentialError(
                    f"adapter {self.name} did not echo {member}"
                )
        return response

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        error: DifferentialError | None = None
        try:
            if self.process.poll() is None:
                self.process.stdin.close()
                try:
                    self.process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    self._abort()
                    error = DifferentialError(
                        f"adapter {self.name} did not stop after EOF"
                    )
            if self.process.returncode not in (0, None):
                error = DifferentialError(
                    f"adapter {self.name} exited {self.process.returncode}: "
                    f"{self._stderr()}"
                )
            remainder = self.process.stdout.read()
            if remainder:
                error = DifferentialError(
                    f"adapter {self.name} emitted extra stdout after final response"
                )
        finally:
            self.reader.shutdown(wait=True, cancel_futures=True)
            self.stderr_file.close()
        if error is not None:
            raise error


def sha256_jcs(value: Any) -> str:
    return "sha256:" + hashlib.sha256(base.jcs_bytes(value)).hexdigest()


def failure_record(
    *,
    stage: str,
    request_id: str,
    pointer: str,
    expected: Any,
    actual: Any,
    events: list[Mapping[str, Any]],
    baseline: str | None = None,
    candidate: str | None = None,
) -> dict[str, Any]:
    failure: dict[str, Any] = {
        "stage": stage,
        "requestId": request_id,
        "pointer": pointer,
        "expected": copy.deepcopy(expected),
        "actual": copy.deepcopy(actual),
        "eventPrefix": copy.deepcopy(events),
    }
    if baseline is not None:
        failure["baselineAdapter"] = baseline
    if candidate is not None:
        failure["candidateAdapter"] = candidate
    return failure


def request_all(
    sessions: list[AdapterSession],
    *,
    request_id: str,
    operation: str,
    payload: Mapping[str, Any],
    stage: str,
    registry: Any,
    documents: Mapping[Path, Any],
    expected_status: str = "ok",
    expected_code: str | None = None,
    compare_semantics: bool = True,
    events: list[Mapping[str, Any]] | None = None,
    transcript: list[Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    event_prefix = [] if events is None else events
    request = {
        "protocol": "MIF-INTEROP/1",
        "kind": "request",
        "requestId": request_id,
        "operation": operation,
        "payload": copy.deepcopy(dict(payload)),
    }
    case: dict[str, Any] = {
        "id": request_id,
        "operation": operation,
        "comparison": "semantic-equality" if compare_semantics else "schema-only",
        "expectedStatus": expected_status,
        "payload": request["payload"],
    }
    if expected_code is not None:
        case["expectedCode"] = expected_code
    responses: dict[str, dict[str, Any]] = {}
    baseline_name = sessions[0].name
    for session in sessions:
        response = session.request(request)
        responses[session.name] = response
        try:
            if response["status"] != expected_status:
                raise base.HarnessError(
                    f"expected status {expected_status}, got {response['status']}"
                )
            if expected_code is not None:
                actual_code = (
                    response["diagnostics"]["errors"][0]["code"]
                    if response["status"] == "error"
                    else None
                )
                if actual_code != expected_code:
                    raise base.HarnessError(
                        f"expected code {expected_code}, got {actual_code}"
                    )
            base.validate_result(case, response, registry, documents)
        except base.HarnessError as exc:
            raise DifferenceError(
                failure_record(
                    stage=stage,
                    request_id=request_id,
                    pointer="/",
                    expected=f"valid {expected_status} {operation} response",
                    actual=str(exc),
                    events=event_prefix,
                    baseline=baseline_name,
                    candidate=session.name,
                )
            ) from exc
    baseline_value = base.comparison_value(responses[baseline_name])
    if compare_semantics:
        baseline_bytes = base.jcs_bytes(baseline_value)
        for session in sessions[1:]:
            candidate_value = base.comparison_value(responses[session.name])
            if base.jcs_bytes(candidate_value) != baseline_bytes:
                difference = base.first_difference(baseline_value, candidate_value)
                assert difference is not None
                pointer, expected, actual = difference
                raise DifferenceError(
                    failure_record(
                        stage=stage,
                        request_id=request_id,
                        pointer=pointer or "/",
                        expected=expected,
                        actual=actual,
                        events=event_prefix,
                        baseline=baseline_name,
                        candidate=session.name,
                    )
                )
    if transcript is not None:
        transcript.append(
            {
                "operation": operation,
                "payload": copy.deepcopy(dict(payload)),
                "response": baseline_value,
            }
        )
    return responses


def verify_prng(launch: Mapping[str, Any]) -> None:
    constants = launch["prng"]["constants"]
    if constants != {
        "gamma": "9e3779b97f4a7c15",
        "mul1": "bf58476d1ce4e5b9",
        "mul2": "94d049bb133111eb",
    }:
        raise DifferentialError("splitmix64-v1 constants changed")
    for vector in launch["prng"]["vectors"]:
        prng = SplitMix64(vector["seed"])
        actual = [f"{prng.next():016x}" for _ in vector["outputs"]]
        if actual != vector["outputs"]:
            raise DifferentialError(
                f"splitmix64-v1 vector mismatch for seed {vector['seed']}"
            )


def record_coverage(
    coverage: set[str],
    snapshot: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    parts = snapshot["current"].split(" ")
    if len(parts) < 11:
        raise DifferentialError("agreed current MFEN has too few fields")
    board, side, phase, action = parts[2], parts[3], parts[4], parts[5]
    if phase == "p":
        coverage.add("placing")
    elif phase == "m":
        coverage.add("moving")
    elif phase == "o":
        coverage.add("terminal")
    if action == "r":
        coverage.add("removal")
    flying = manifest["flying"]
    if phase == "m" and side in {"w", "b"} and flying["enabled"]:
        piece = "W" if side == "w" else "B"
        if board.count(piece) <= flying["maximumLive"]:
            coverage.add("flying")
    if snapshot["claimRights"] is not None:
        coverage.add("claim-right")
    if snapshot["repetitionHistory"]:
        coverage.add("repetition")


def make_mstate(
    scenario: Mapping[str, Any],
    manifest: Mapping[str, Any],
    events: list[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "format": "MSTATE/1.0",
        "stateProfile": "mill24-state-v1",
        "ruleset": {
            "mode": "reference",
            "id": manifest["id"],
            "version": manifest["version"],
            "semanticDigest": snapshot["decisionState"]["semanticDigest"],
            "documentDigest": sha256_jcs(manifest),
        },
        "positionFormat": "MFEN/1.0",
        "origin": scenario["origin"],
        "current": snapshot["current"],
        "events": copy.deepcopy(events),
        "repetitionHistory": copy.deepcopy(snapshot["repetitionHistory"]),
        "preOriginClaims": copy.deepcopy(scenario["preOriginClaims"]),
        "claims": copy.deepcopy(snapshot["claims"]),
    }


def run_one(
    scenario_source: Mapping[str, Any],
    seed: str,
    sessions: list[AdapterSession],
    *,
    registry: Any,
    documents: Mapping[Path, Any],
) -> dict[str, Any]:
    scenario = base.expand_sources(scenario_source)
    manifest = scenario["manifest"]
    events: list[dict[str, Any]] = []
    transcript: list[Mapping[str, Any]] = []
    coverage: set[str] = set()
    prng = SplitMix64(seed)
    logical_turns = 0
    last_replay_event_count = -1
    stop_reason = "difference"
    failure: dict[str, Any] | None = None
    final_snapshot: Mapping[str, Any] | None = None
    request_serial = 0

    def request_id(suffix: str) -> str:
        nonlocal request_serial
        request_serial += 1
        return f"d-{scenario['id']}-{seed}-{request_serial}-{suffix}"

    def execute_prefix() -> Mapping[str, Any]:
        responses = request_all(
            sessions,
            request_id=request_id("execute"),
            operation="execute",
            payload={
                "manifest": manifest,
                "origin": scenario["origin"],
                "events": events,
                "repetitionSeed": scenario["repetitionSeed"],
                "preOriginClaims": scenario["preOriginClaims"],
            },
            stage="execute",
            registry=registry,
            documents=documents,
            events=events,
            transcript=transcript,
        )
        result = responses[sessions[0].name]["result"]
        snapshot = result["final"]
        record_coverage(coverage, snapshot, manifest)
        return snapshot

    def replay_checkpoint(snapshot: Mapping[str, Any], *, final: bool) -> None:
        nonlocal last_replay_event_count
        if last_replay_event_count == len(events) and not final:
            return
        mstate = make_mstate(scenario, manifest, events, snapshot)
        request_all(
            sessions,
            request_id=request_id("replay"),
            operation="replay",
            payload={"mstate": mstate, "manifest": manifest},
            stage="replay-final" if final else "replay-checkpoint",
            registry=registry,
            documents=documents,
            events=events,
            transcript=transcript,
        )
        last_replay_event_count = len(events)

    try:
        final_snapshot = execute_prefix()
        while True:
            responses = request_all(
                sessions,
                request_id=request_id("legal"),
                operation="project-legal-actions",
                payload={"manifest": manifest, "current": final_snapshot["current"]},
                stage="project-legal-actions",
                registry=registry,
                documents=documents,
                events=events,
                transcript=transcript,
            )
            actions = responses[sessions[0].name]["result"]["document"]["actions"]
            parts = final_snapshot["current"].split(" ")
            if not actions:
                if len(parts) < 6 or parts[4] != "o":
                    raise DifferenceError(
                        failure_record(
                            stage="project-legal-actions",
                            request_id=request_id("empty-nonterminal"),
                            pointer="/result/document/actions",
                            expected="terminal MFEN when actions are empty",
                            actual=final_snapshot["current"],
                            events=events,
                        )
                    )
                stop_reason = "terminal"
                break
            pending_removal = len(parts) >= 6 and parts[5] == "r"
            if not pending_removal and logical_turns >= scenario["maxLogicalTurns"]:
                stop_reason = "logical-turn-limit"
                if scenario["id"] == "resource-limit-probe":
                    coverage.add("resource-limit")
                break
            if len(events) >= scenario["maxEvents"]:
                raise DifferentialError(
                    f"scenario {scenario['id']} seed {seed} exceeded maxEvents"
                )
            action = copy.deepcopy(actions[prng.next() % len(actions)])
            action["seq"] = len(events) + 1
            events.append(action)
            if action["type"] in {"place", "move"}:
                logical_turns += 1
            final_snapshot = execute_prefix()
            now_parts = final_snapshot["current"].split(" ")
            stable_after_turn = len(now_parts) >= 6 and now_parts[5] != "r"
            interval = scenario["replayEveryLogicalTurns"]
            if (
                stable_after_turn
                and logical_turns > 0
                and logical_turns % interval == 0
            ):
                replay_checkpoint(final_snapshot, final=False)

        replay_checkpoint(final_snapshot, final=True)
        final_mstate = make_mstate(scenario, manifest, events, final_snapshot)
        request_all(
            sessions,
            request_id=request_id("turns"),
            operation="project-logical-turns",
            payload={"mstate": final_mstate, "manifest": manifest},
            stage="project-logical-turns",
            registry=registry,
            documents=documents,
            events=events,
            transcript=transcript,
        )
        if stop_reason not in scenario["allowedStops"]:
            failure = failure_record(
                stage="stop-condition",
                request_id=request_id("stop"),
                pointer="/stopReason",
                expected=scenario["allowedStops"],
                actual=stop_reason,
                events=events,
            )
        missing = sorted(set(scenario["requiredCoverage"]) - coverage)
        if missing and failure is None:
            failure = failure_record(
                stage="coverage",
                request_id=request_id("coverage"),
                pointer="/coverage",
                expected=scenario["requiredCoverage"],
                actual=sorted(coverage),
                events=events,
            )
    except DifferenceError as exc:
        failure = exc.failure
        stop_reason = "difference"

    report: dict[str, Any] = {
        "scenario": scenario["id"],
        "seed": seed,
        "status": "passed" if failure is None else "failed",
        "stopReason": stop_reason,
        "logicalTurns": logical_turns,
        "eventCount": len(events),
        "prngDraws": prng.draws,
        "prngState": prng.state_hex(),
        "coverage": [item for item in COVERAGE_ORDER if item in coverage],
        "events": events,
        "eventsDigest": sha256_jcs(events),
        "transcriptDigest": sha256_jcs(transcript),
        "finalCurrent": None if final_snapshot is None else final_snapshot["current"],
        "finalDecisionDigest": (
            None if final_snapshot is None else final_snapshot["decisionDigest"]
        ),
    }
    if failure is not None:
        report["failure"] = failure
    return report


def run_negative_cases(
    launch: Mapping[str, Any],
    runs: list[Mapping[str, Any]],
    sessions: list[AdapterSession],
    *,
    registry: Any,
    documents: Mapping[Path, Any],
) -> list[dict[str, Any]]:
    source_path = base.safe_repo_path(launch["negativeCases"]["path"])
    source = base.read_json(source_path)
    base.validate_document(source, base.CASES_SCHEMA, registry, documents)
    case_ids = [case["id"] for case in source["cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise DifferentialError("negative case IDs are not unique")
    if any("family" not in case for case in source["cases"]):
        raise DifferentialError("every differential negative case needs a family")
    source_families = {case["family"] for case in source["cases"]}
    declared_families = set(launch["negativeCases"]["families"])
    if source_families | {"resource-limit"} != declared_families:
        raise DifferentialError(
            "negative mutation families do not match the launch package"
        )
    reports: list[dict[str, Any]] = []
    for case_source in source["cases"]:
        case = copy.deepcopy(dict(case_source))
        case["payload"] = base.expand_sources(case["payload"])
        failure: dict[str, Any] | None = None
        response_digest: str | None = None
        try:
            responses = request_all(
                sessions,
                request_id=case["id"],
                operation=case["operation"],
                payload=case["payload"],
                stage=f"negative-{case['family']}",
                registry=registry,
                documents=documents,
                expected_status=case["expectedStatus"],
                expected_code=case.get("expectedCode"),
                events=case["payload"].get("events", []),
            )
            response_digest = sha256_jcs(
                base.comparison_value(responses[sessions[0].name])
            )
        except DifferenceError as exc:
            failure = exc.failure
        report: dict[str, Any] = {
            "id": case["id"],
            "family": case["family"],
            "status": "passed" if failure is None else "failed",
            "expectedCode": case.get("expectedCode"),
            "responseDigest": response_digest,
        }
        if failure is not None:
            report["failure"] = failure
        reports.append(report)

    resource_runs = [run for run in runs if run["scenario"] == "resource-limit-probe"]
    resource_ok = (
        len(resource_runs) == 1
        and resource_runs[0]["status"] == "passed"
        and resource_runs[0]["stopReason"] == "logical-turn-limit"
        and resource_runs[0]["eventCount"] == 0
        and "resource-limit" in resource_runs[0]["coverage"]
    )
    resource_report: dict[str, Any] = {
        "id": "mutation-harness-resource-limit",
        "family": "resource-limit",
        "status": "passed" if resource_ok else "failed",
        "expectedCode": None,
        "responseDigest": (
            sha256_jcs(resource_runs[0]) if resource_ok else None
        ),
    }
    if not resource_ok:
        resource_report["failure"] = failure_record(
            stage="negative-resource-limit",
            request_id="mutation-harness-resource-limit",
            pointer="/runs/resource-limit-probe",
            expected="zero events and logical-turn-limit",
            actual=resource_runs,
            events=[],
        )
    reports.append(resource_report)
    return reports


def validate_unique_launch(launch: Mapping[str, Any]) -> None:
    scenario_ids = [scenario["id"] for scenario in launch["scenarios"]]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise DifferentialError("scenario IDs are not unique")
    resource_paths = [resource["path"] for resource in launch["resources"]]
    if resource_paths != sorted(resource_paths) or len(resource_paths) != len(
        set(resource_paths)
    ):
        raise DifferentialError("launch resources must be sorted and path-unique")
    for resource in launch["resources"]:
        actual = base.raw_digest(base.safe_repo_path(resource["path"]))
        if actual != resource["sha256"]:
            raise DifferentialError(
                f"launch resource digest mismatch: {resource['path']}"
            )
    evidence = launch["baseline"]["m3Evidence"]
    if base.raw_digest(base.safe_repo_path(evidence["path"])) != evidence["sha256"]:
        raise DifferentialError("M3 evidence digest mismatch")


def close_sessions(sessions: list[AdapterSession]) -> None:
    errors: list[str] = []
    for session in sessions:
        try:
            session.close()
        except DifferentialError as exc:
            errors.append(str(exc))
    if errors:
        raise DifferentialError("; ".join(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--launch", type=Path, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--report", type=Path)
    output.add_argument("--expect-report", type=Path)
    args = parser.parse_args(argv)
    sessions: list[AdapterSession] = []
    try:
        registry, documents = base.build_registry()
        config_path = args.config.resolve()
        launch_path = args.launch.resolve()
        config = base.read_json(config_path)
        launch = base.read_json(launch_path)
        base.validate_document(config, base.CONFIG_SCHEMA, registry, documents)
        base.validate_document(launch, LAUNCH_SCHEMA, registry, documents)
        if len(config["adapters"]) < 2:
            raise DifferentialError("at least two adapters are required")
        names = [adapter["name"] for adapter in config["adapters"]]
        if len(names) != len(set(names)):
            raise DifferentialError("adapter names are not unique")
        validate_unique_launch(launch)
        verify_prng(launch)
        limits = launch["resourceLimits"]
        sessions = [
            AdapterSession(
                adapter,
                timeout_ms=limits["perRequestTimeoutMs"],
                max_response_bytes=limits["maxResponseBytes"],
                max_total_requests=limits["maxTotalRequests"],
                registry=registry,
                documents=documents,
            )
            for adapter in config["adapters"]
        ]

        capability_responses = request_all(
            sessions,
            request_id="d-capabilities",
            operation="capabilities",
            payload={},
            stage="capabilities",
            registry=registry,
            documents=documents,
            compare_semantics=False,
        )
        implementations = []
        for session in sessions:
            capabilities = capability_responses[session.name]["result"]["capabilities"]
            identity = capabilities["implementation"]
            implementations.append(
                {
                    "adapter": session.name,
                    "name": identity["name"],
                    "version": identity["version"],
                    "capabilitiesDigest": sha256_jcs(capabilities),
                }
            )

        runs = [
            run_one(
                scenario,
                seed,
                sessions,
                registry=registry,
                documents=documents,
            )
            for scenario in launch["scenarios"]
            for seed in scenario["seeds"]
        ]
        negative_reports = run_negative_cases(
            launch,
            runs,
            sessions,
            registry=registry,
            documents=documents,
        )
        close_sessions(sessions)
        sessions = []
        run_failures = sum(run["status"] == "failed" for run in runs)
        negative_failures = sum(
            case["status"] == "failed" for case in negative_reports
        )
        report = {
            "protocol": "MIF-INTEROP-DIFFERENTIAL-REPORT/1",
            "status": "failed" if run_failures or negative_failures else "passed",
            "suiteConformance": False,
            "launchDigest": base.raw_digest(launch_path),
            "configDigest": base.raw_digest(config_path),
            "adapters": names,
            "implementations": implementations,
            "runs": runs,
            "negativeCases": negative_reports,
            "summary": {
                "runsPassed": len(runs) - run_failures,
                "runsFailed": run_failures,
                "negativePassed": len(negative_reports) - negative_failures,
                "negativeFailed": negative_failures,
            },
        }
        base.validate_document(report, REPORT_SCHEMA, registry, documents)
        if args.expect_report is not None:
            expected_report = args.expect_report.resolve()
            actual_bytes = (
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")
            if expected_report.read_bytes() != actual_bytes:
                raise DifferentialError(
                    f"generated report differs from {expected_report}"
                )
        else:
            assert args.report is not None
            base.write_report(args.report, report)
        if run_failures or negative_failures:
            print(
                "MIF differential comparison FAILED: "
                f"{run_failures}/{len(runs)} runs and "
                f"{negative_failures}/{len(negative_reports)} negative cases"
            )
            return 1
        print(
            "MIF differential comparison passed: "
            f"{len(runs)} seeded runs and {len(negative_reports)} negative cases "
            f"across {len(names)} adapters (candidate evidence only)"
        )
        return 0
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        base.HarnessError,
        DifferentialError,
        DifferenceError,
    ) as exc:
        print(f"MIF differential harness FAILED: {exc}")
        return 2
    finally:
        if sessions:
            try:
                close_sessions(sessions)
            except DifferentialError as exc:
                print(f"MIF differential harness FAILED during shutdown: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
