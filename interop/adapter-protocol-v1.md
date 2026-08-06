# MIF interoperability adapter protocol v1

Status: non-normative test infrastructure for the MIF 1.0 Candidate Wire
Contract. `MIF-INTEROP/1` is not a MIF format signature and must not appear in
MIF Suite manifests or format capability lists.

## 1. Process model

An adapter is an executable started with the command array in the harness
configuration. The harness writes UTF-8 NDJSON requests to standard input. The
adapter writes exactly one UTF-8 JSON response line for every request, in the
same order, to standard output. Diagnostic logging is permitted only on
standard error.

Input and output:

- use UTF-8 without BOM;
- contain one I-JSON object per LF-terminated line;
- reject duplicate members after JSON unescaping;
- contain no NaN or Infinity values;
- do not depend on current working directory or network resolution; and
- remain deterministic for the same request and implementation version.

EOF requests orderly shutdown. A process crash, extra stdout line, missing
response, malformed JSON or timeout is a harness failure rather than a MIF
diagnostic.

## 2. Message envelopes

A request contains exactly:

```json
{
  "protocol": "MIF-INTEROP/1",
  "kind": "request",
  "requestId": "replay-offer-r1",
  "operation": "replay",
  "payload": {}
}
```

A successful response contains exactly:

```json
{
  "protocol": "MIF-INTEROP/1",
  "kind": "response",
  "requestId": "replay-offer-r1",
  "operation": "replay",
  "status": "ok",
  "result": {}
}
```

A rejected request contains `status=error` and a complete `MIFDIAG/1.0`
object named `diagnostics` instead of `result`. `requestId` and `operation`
must echo the request.

The envelope Schema is `schema/adapter-message-v1.schema.json`.

## 3. Operations

### 3.1 `capabilities`

Payload is `{}`. Result contains exactly `capabilities`, whose value is the
adapter's `MIFCAP/1.0` object. Capability responses are validated but are not
expected to be byte-identical because implementation identities differ.

### 3.2 `canonicalize`

Payload contains:

- `format`: `MFEN/1.0` or `MPK/1.0`;
- `value`: input text; and
- optional `manifest`: exact MRS context when required.

Result contains exactly `value`, the canonical text. An unsupported format or
missing ruleset context returns MIFDIAG rather than echoing the input.

### 3.3 `execute`

Payload contains exact `manifest`, `origin`, ordered `events`,
`repetitionSeed` and `preOriginClaims`. The two seed arrays may be empty but
remain present.

Result contains exactly `trace` and `final`. Trace begins with the stabilized
origin and then contains one snapshot after every successful event. A snapshot
contains exactly:

- `boundary`: `origin` or `event`;
- `eventSeq`: null at origin or the positive event sequence;
- canonical `current` MFEN;
- complete active `repetitionHistory`;
- complete `claims` audit;
- current `claimRights` or null;
- `decisionState`; and
- `decisionDigest`.

`final` equals the last trace entry. Adapters may later add a separately
versioned legal-action projection; v1 deliberately compares state transitions
before standardizing action-list encoding.

### 3.4 `replay`

Payload contains `mstate` and optional `manifest`. Portable MSTATE omits the
caller manifest. Reference MSTATE requires it. No adapter may perform automatic
network resolution.

Result contains exactly:

- canonical `current`;
- `trace` as defined for execute;
- final `repetitionHistory`, `claims` and `claimRights`;
- `decisionState` and `decisionDigest`; and
- `resumptionState` and `resumptionDigest`.

The adapter verifies the supplied checkpoint, repetition window and claim
audit; it does not merely replay events and discard supplied evidence.

### 3.5 `transform`

Payload contains `kind`, `document`, optional `manifest`, `transform`, optional
`repetitionHistory`, `verifyReplay`, `requireEquivalence` and optional
`invariance`.

`kind` is `mstate`, `mifpos` or `decision-state`. Result always contains the
transformed `document`. MSTATE additionally returns the replay-derived
decision and resumption objects and digests.

When `requireEquivalence` is true, the exact MIFINV declaration is mandatory
and must pass the `(semanticDigest, transform-profile)` gate before coordinate
conversion is described as equivalence. A decision object with a non-null
repetition root requires complete `repetitionHistory`; otherwise the adapter
returns `insufficient-transform-history`.

### 3.6 `project-logical-turns`

Payload contains `mstate` and optional `manifest`. Result contains exactly
`document`, a complete `MIFTURN/1.0` object.

## 4. Comparison rules

For `semantic-equality` cases, the harness parses each response and compares
RFC 8785 JCS bytes of the complete `result`. Canonical wire strings inside the
result therefore compare byte for byte.

For error responses, the harness removes only non-normative `message` from
each diagnostic error and top-level `annotations`, then compares JCS bytes.
Category, code, JSON Pointer, UTF-8 offsets, eventSeq, expected/actual and
resource limits remain comparison fields.

For `schema-only` cases, every adapter must return the expected status and a
Schema-valid response, but results need not match.

## 5. Harness source references

Case source files are not sent directly to adapters. Within a case payload, an
object of the following form instructs the harness to load repository JSON:

```json
{
  "$json": "artifacts/mif-1.0/corpus/fixtures/example-morris@1.json"
}
```

It may include `$pointer` to select a value inside the loaded document and
`$patch`, an ordered RFC 6901 mutation array using `add`, `replace` or
`remove`. Pointer selection occurs before patching, and patch values may contain
their own source references. The harness resolves all references before
constructing the protocol request. Resolved paths must remain inside the
repository.

## 6. Adapter configuration

Commands are arrays, never shell strings. The harness expands `{python}` to
its current Python executable and `{repo}` to the absolute repository root.
Relative working directories resolve under the repository and may not escape
it. Adapter names are unique identifiers.

The adapter protocol is intentionally independent of Sanmill and NMM_LLM build
systems. Each project may use a native executable, a test binary or a small
process wrapper around its independently implemented library.
