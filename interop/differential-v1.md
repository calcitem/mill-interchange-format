# MIF candidate differential harness v1

Status: non-normative interoperability infrastructure for the MIF 1.0
Candidate Wire Contract. `MIF-INTEROP-DIFFERENTIAL/1` and its reports are not
MIF wire formats or MIF Suite conformance artifacts.

## 1. Inputs and process boundary

The harness consumes:

1. an `MIF-INTEROP-DIFFERENTIAL/1` launch package;
2. an `MIF-INTEROP-CONFIG/1` adapter configuration; and
3. the fixed negative case source named by the launch package.
The launch `resources` array is sorted by repository-relative path and contains
one raw SHA-256 for every harness contract, Schema, mutation source and driver
file required by the run. Paths are unique. The harness verifies every resource
before starting an adapter, so the report's launch digest transitively binds all
of these inputs.

Every adapter continues to implement only `MIF-INTEROP/1`. The differential
layer must not import gameplay code from any adapter and must not use the MIF
reference runner to choose a preferred result. The first configured adapter is
only the comparison baseline after every adapter has returned a valid response.

The launch package and report are validated by
`schema/differential-launch-v1.schema.json` and
`schema/differential-report-v1.schema.json`.

## 2. SplitMix64 profile

`splitmix64-v1` uses an unsigned 64-bit state. Addition, multiplication and
right shift operate on unsigned values; addition and multiplication discard
all bits above bit 63. A seed is exactly 16 lowercase hexadecimal digits and
is decoded directly as the initial state.

For every draw:

```text
state = state + 9e3779b97f4a7c15 (mod 2^64)
z = state
z = (z xor (z >> 30)) * bf58476d1ce4e5b9 (mod 2^64)
z = (z xor (z >> 27)) * 94d049bb133111eb (mod 2^64)
output = z xor (z >> 31)
```

The test vectors in the launch package are mandatory. A harness must reject a
launch package if its implementation does not reproduce all vector outputs.

## 3. Positive trajectory algorithm

Scenarios and seeds execute in launch-file order. Adapter order is config-file
order. Each `(scenario, seed)` run follows this algorithm:

1. Expand repository JSON references using the rules in adapter protocol v1.
2. Send `execute` with the scenario manifest, origin, empty event prefix,
   repetition seed and pre-origin claims. Require `status=ok`, validate the
   complete result and compare its JCS bytes across all adapters.
3. Record coverage at the stabilized origin.
4. At every current boundary, send `project-legal-actions` to all adapters.
   Validate and compare the complete result before selecting an action.
5. If the action array is empty, the current MFEN must be terminal and the run
   stops as `terminal`.
6. At a stable primary boundary, stop as `logical-turn-limit` before selecting
   another primary action when `maxLogicalTurns` has already been reached.
   A pending removal must be completed before this limit may stop a run.
7. Draw exactly one SplitMix64 output, including when there is only one action.
   Select `output mod actionCount` from the canonical `legal-actions-v1` array.
8. Add the next consecutive positive `seq` to the selected event template,
   append it to the event prefix and increment the logical-turn count only for
   `place` or `move`.
9. Reject the run as a harness resource failure before appending an event that
   would exceed `maxEvents`.
10. Send `execute` with the complete event prefix. Validate and compare its
    complete result, including every trace snapshot and decision digest.
11. At every configured completed-primary interval, and once at final stop,
    construct a reference-mode MSTATE from the agreed execute result and send
    `replay`. Validate and compare the complete replay result.
12. At final stop, also send `project-logical-turns` for that MSTATE and compare
    the complete `MIFTURN/1.0` result.

The MSTATE ruleset envelope is derived without gameplay inference. Its ID and
version come from the manifest, its `semanticDigest` comes from the agreed
decision state, and its `documentDigest` is SHA-256 over the manifest's RFC
8785 JCS bytes. `current`, repetition history and claims come from the agreed
execute snapshot. The origin, events, pre-origin claims and exact manifest are
the scenario inputs.

## 4. Equality and first difference

Successful responses compare the RFC 8785 JCS bytes of the complete `result`.
Error responses use the normalization in adapter protocol v1: only diagnostic
`message` and top-level diagnostic `annotations` are excluded. All other
diagnostic members remain significant.

The first non-equal response stops only its current trajectory or mutation.
The report records the stage, request ID, baseline and candidate adapter,
first JSON Pointer, expected and actual values, and the exact event prefix.
Together with the launch package and seed, this is the minimal deterministic
reproduction. Other configured seeds continue so one report can expose more
than one independent failure.

## 5. Coverage

Coverage is observed from agreed boundaries and results, not asserted merely
from a scenario label:

- `placing`, `moving` and `terminal` come from MFEN phase;
- `removal` comes from MFEN action `r`;
- `flying` requires moving phase, an enabled flying mechanism and no more than
  the manifest maximum live pieces for the active player;
- `claim-right` requires a non-null derived claim right;
- `repetition` requires a non-empty active repetition history; and
- `resource-limit` is recorded only when the zero-turn limit probe stops before
  issuing a gameplay event.

Every scenario must observe all entries in its `requiredCoverage`. Missing
coverage fails that run even if adapter outputs otherwise agree.

## 6. Negative mutations and limits

The fixed negative case source exercises illegal gameplay events,
non-canonical text, digest/envelope conflicts and truncated replay history.
Every adapter must return the fixed status and code, and normalized diagnostics
must compare semantically.

The `resource-limit` family is the launch package's zero-turn probe. It proves
that the harness applies the fixed limit without selecting or sending a
gameplay event. Process limits also apply to every run:

- a response must arrive within `perRequestTimeoutMs`;
- one response line must not exceed `maxResponseBytes`; and
- the complete harness run must not exceed `maxTotalRequests` per adapter.

Exceeding a process limit is a harness failure. It is not converted into a MIF
diagnostic and must not be reported as an adapter semantic disagreement.

## 7. Deterministic report

The report contains no time, host path or process ID. It binds the raw launch
and config SHA-256 values, ordered adapter names, capability identities and JCS
digests, every scenario/seed result, selected events, PRNG state, observed
coverage, final state identity and normalized transcript digest. Negative cases
record their expected code and normalized response digest.

The report's `suiteConformance` member is always false. Passing this package is
M4 Candidate interoperability evidence only. A separate commit-bound evidence
manifest must bind the report to the exact MIF, Sanmill and NMM_LLM commits.
