# MIF 1.0 design baseline and release gates

Status: retained design basis; wire decisions implemented

Reference baseline: MIF Community Working Draft 0.4 at `9ecc134853628dc29d3037727a566702505fda1f`

Normative successor: [`mif-1.0.md`](mif-1.0.md), MIF 1.0 Candidate Wire Contract

Conformance status: superseded as normative wire text; MIF Suite 1.0 is not yet
a conformance target

The Candidate Wire Contract implements the decisions recorded here. This file
is retained as review rationale and release-gate history; where it differs from
the wire contract, the wire contract controls.

This document records decisions that a MIF 1.0 candidate and its release
artifacts are required to implement. The key words **shall**, **should** and
**may** constrain that future candidate; they do not change MIF/0.4.

The review verdict is **accepted with refinements**. The five proposed release
blockers are accepted. The additional recommendations are also accepted as
1.0 work, with the release classification in Clause 13. The refinements are:

- retain compact MFEN and add a self-identifying position envelope;
- define semantic digest projection per semantics profile rather than by an
  unsafe generic field-deletion rule;
- keep the 0.4 name `legal-state-v1` valid only in 0.4 and introduce the less
  misleading name in 1.0 through an explicit conversion mapping; and
- distinguish exact resumption identity, decision equivalence and optional
  symmetry normalization.

A second maintainer review adds six pre-wire corrections: player/order
identity, separation of resumption and decision equivalence, direct MPK
semantic binding, transform-invariance declarations, placing-phase liveness
and repetition-observation scope. All six are accepted; the first four have
the highest priority before the 1.0 wire contract is frozen.

## 1 Compatibility boundary

### 1.1 Frozen 0.4 baseline and implementation target

The referenced 0.4 edition remains an independently identifiable working
draft. A 1.0 implementation shall not reinterpret any 0.4 signature, digest
or `legal-state-v1` object as if it had been serialized under 1.0.

The edition at commit `9ecc134853628dc29d3037727a566702505fda1f` is frozen as
a historical working draft and migration-test input. Its specification text
and conformance corpus shall receive no further protocol corrections. New
work may add 1.0 conversion and rejection vectors that consume the frozen 0.4
bytes, but shall not mutate those bytes or silently upgrade ambiguous input.
The frozen English specification raw-file SHA-256 is
`F1F1D839318A4D45F3ECEA4850FEE080C47FFCBC81025BD74E3EA48C815F3093`.

NMM_LLM and Sanmill target MIF Suite 1.0 directly. Implementing or claiming
conformance to 0.4 is not a prerequisite.

### 1.2 Retained architecture

MIF 1.0 shall retain the four-layer architecture:

- MFEN for a compact instantaneous position;
- MPK for an intentionally lossy stable structural analysis key;
- MSTATE for resumable history and audit state; and
- MRS for a finite ruleset manifest.

MIFPOS adds an envelope around MFEN. It does not merge the layers. A complete
1.0 release requires new specifications, schemas, grammar, registries and
conformance vectors; changing the four 0.4 signatures alone is not a release.

### 1.3 Player identity and move order

MIF 1.0 selects the fixed-colour interpretation:

- `w` is White and stable player identity 0;
- `b` is Black and stable player identity 1;
- neither identity implies who acts first; and
- the **initial player** is the value of `turn.initial`.

The normative terms *first player* and *second player* shall not be aliases for
White and Black. They may occur only when quoting an external source whose
meaning is explicitly explained.

The MRS/0.4 board-full tokens encoded fixed-colour effects even though their
names used `first` and `second`. MRS/1.0 therefore replaces them as follows:

| MRS/0.4 token | MRS/1.0 token |
|---|---|
| `first-player-loses` | `white-loses` |
| `first-then-second-remove` | `white-then-black-remove` |
| `second-then-first-remove` | `black-then-white-remove` |

`active-player-removes`, `draw` and `disabled` retain their order-independent
names. A 0.4 converter shall map the three renamed values by their specified
0.4 effects, not by `turn.initial` and not by a locale's use of “first”.

The 1.0 corpus shall contain complete `turn.initial=b` initial-state, replay,
board-full terminal and board-full removal-order vectors. The same resulting
effect under `turn.initial=w` and `turn.initial=b` is required for each
fixed-colour token.

### 1.4 Turn-counting terminology

A **MIF logical turn** is one player's primary `place` or `move` action plus
every consequent mandatory `remove` action through the next stable boundary.
A primary ply counts one successful primary action; supplementary removals do
not add a primary ply.

A **full move** or **round** normally contains one logical turn by each player.
Normative text shall not use unqualified *turn* when a logical turn, primary
ply or full move is intended. This avoids conflict with problem literature in
which one “turn” can mean two plies.

## 2 Ruleset identity and two digest domains

### 2.1 Digest definitions

MRS/1.0 shall define two digest domains:

- `semanticDigest` identifies the normalized gameplay meaning of a valid
  manifest; and
- `documentDigest` identifies the complete canonical manifest document.

Both values use the existing lexical form:

```text
sha256:<64 lowercase hexadecimal digits>
```

`documentDigest` shall be SHA-256 over the RFC 8785 JCS UTF-8 bytes of the
complete MRS object. Neither digest member is inserted into the object being
hashed.

`semanticDigest` shall be SHA-256 over the JCS UTF-8 bytes of a semantic
projection object. That object shall contain a projection-profile identifier
such as `mrs-semantic-v1` to domain-separate it from the full document.

### 2.2 Semantic projection

Each registered semantics profile shall define its complete semantic
projection algorithm. The algorithm shall:

1. list every included member and its canonical order or set treatment;
2. include the semantics-profile identity, topology, active rule mechanisms,
   transition policy, outcome policy, semantic-state declarations and every
   understood semantic extension;
3. exclude ruleset aliases and lifecycle or presentation metadata, including
   `id`, `version`, `title`, `status`, `description` and `annotations`;
4. normalize or omit values that the semantics profile declares inert while
   their enclosing mechanism is disabled;
5. reject an unknown semantic extension instead of omitting it; and
6. produce the same projection for manifests that differ only in excluded
   non-semantic metadata.

A generic implementation shall not obtain the projection by deleting a
hard-coded list of names from an otherwise unknown MRS object. It shall
implement the selected projection profile and fail closed when that profile
or a semantic extension is unknown.

The `mif-finite-rules` profile selected for 1.0 shall publish an explicit
member-by-member projection table and vectors before its identifier is
frozen. This is necessary because some retained fields in MRS/0.4 are inert
when their mechanisms are disabled.

### 2.3 Required use

Gameplay identity in MSTATE, decision-state keys, training environments and
gameplay caches shall be bound to `semanticDigest`. Implementations shall not
invalidate gameplay identity solely because `title`, `status`, `description`
or an annotation changes.

Registry records, release packages, signatures and exact-document integrity
shall be bound to `documentDigest`. A portable envelope shall carry both
digests: one states which gameplay semantics is used and the other verifies
the exact embedded document.

Ruleset `id@version` remains provenance and resolution identity. Two
independently named rulesets may have the same `semanticDigest`; they are
gameplay-equivalent under that semantic projection but are not the same
publication.

Required vectors include:

- a title or status change: unchanged `semanticDigest`, changed
  `documentDigest`;
- an active rule change: both digests change;
- an alias with different `id@version`: unchanged `semanticDigest`, changed
  `documentDigest`;
- a difference only in an inert disabled-mechanism member: unchanged
  `semanticDigest`; and
- an unknown semantic extension: projection failure, not a guessed digest.

## 3 Self-identifying position envelope

### 3.1 Selected design

MIF 1.0 shall keep bare MFEN compact and add a JSON position envelope named
`MIFPOS/1.0`. Adding ruleset identity directly to MFEN is not selected.

The following non-conforming sketch shows the minimum MIFPOS shape. The
ellipses and empty manifest are placeholders:

```json
{
  "format": "MIFPOS/1.0",
  "positionFormat": "MFEN/1.0",
  "stateProfile": "mill24-state-v1",
  "position": "MFEN/1.0 ...",
  "ruleset": {
    "mode": "portable",
    "id": "example-rules",
    "version": 1,
    "semanticDigest": "sha256:...",
    "documentDigest": "sha256:...",
    "manifest": {}
  }
}
```

The exact closed member set and schemas remain work for the 1.0 candidate.
The following behaviour is already decided:

- `mode` is explicit and is `portable` or `reference`;
- portable mode requires the exact manifest and both verified digests;
- reference mode omits the manifest, requires `semanticDigest` and explicit
  resolver use, and carries `documentDigest` only when the exact published
  document must be pinned;
- unresolved or conflicting ruleset semantics fail closed;
- a consumer shall not perform automatic network retrieval; and
- a generic export, copy, QR or share command emits portable mode unless the
  caller explicitly requests a compact reference.

### 3.2 Bare MFEN boundary

MFEN/1.0 shall describe itself as **context-bound**. A bare MFEN is a complete
instantaneous state under a supplied ruleset context, but it is not a
self-identifying interchange object. Documentation and capability statements
shall not describe bare MFEN as independently shareable or semantically
validatable.

MIFPOS supplies ruleset closure for one instantaneous position. It does not
carry event history, the effective repetition window or draw-offer audit and
therefore is not a replacement for MSTATE, resumption state or decision state.

## 4 Portable and reference MSTATE

MSTATE/1.0 shall use the same explicit ruleset modes as MIFPOS.

In `portable` mode the ruleset envelope shall contain the exact MRS manifest,
`semanticDigest` and `documentDigest`. Validation shall check identity,
semantic projection and full-document integrity before replay.

In `reference` mode the manifest may be absent. Resolution shall use
`(id, version, semanticDigest)`. The envelope may additionally carry
`documentDigest` when it needs to pin one exact published manifest. When that
member is present, the resolver result shall match it; when it is absent,
non-semantic document changes shall not invalidate resolution. Absence or
conflict at the required digest level shall fail. Reference mode is an
explicit storage optimization, not an implicit property inferred from whether
a ruleset is public.

Default export behaviour is:

- training data, archives and cross-project exchange shall use portable mode;
- generic save, export and share APIs shall use portable mode unless the
  caller explicitly asks for reference mode; and
- an application-local compact cache may use reference mode when it controls
  and documents the resolver lifetime.

Compression and package-level deduplication may reduce repeated manifest
bytes, but an individual object advertised as portable shall remain
self-contained.

## 5 State and key identities

### 5.1 Repetition observation

MRS/1.0 shall replace the 0.4 projection token `legal-state-v1` with
`repetition-observation-v1`. The object remains a repetition-rule projection,
not a full decision key. Its specification shall continue to state explicitly
which authoritative fields it excludes.

A `repetition-observation-v1` object shall bind rules semantics with
`semanticDigest`, not `documentDigest` or ruleset publication metadata.
Ruleset `id@version` provenance may be carried by its containing MSTATE but
shall not alter repetition equality.
The observation boundaries and their placing/moving scope are defined in 10.2.

The 0.4 to 1.0 conversion shall map `legal-state-v1` to
`repetition-observation-v1` only after validating the complete 0.4 ruleset and
state and computing its semantic projection. It shall not rewrite stored 0.4
bytes in place.

### 5.2 `resumption-state-v1`

MIF 1.0 shall register `resumption-state-v1` as the exact, coordinate-frame
preserving recovery and audit identity. Its canonical JCS object shall include:

- a resumption-profile identifier;
- the position-format identifier and current canonical authoritative MFEN;
- the MRS `semanticDigest`;
- the complete ordered repetition window as `repetition-observation-v1`
  objects, including observation and source/event provenance required for
  exact replay;
- the currently open draw offer, including the reference value required by a
  legal accept, decline or withdrawal event, or `null`;
- the exact set of draw-claim reasons currently exercisable; and
- a content digest of the canonical origin, pre-origin seeds and replayed event
  prefix, together with its current event-sequence anchor;
- the complete claim/offer audit and wire references needed for exact replay;
- every registered semantic resumption extension required by the selected
  profile.

The embedded authoritative MFEN already carries no-progress, primary-ply,
pending obligations, semantic state and terminal outcome. Those values shall
not be silently dropped or duplicated with independently mutable copies.

`resumptionDigest` is SHA-256 over the JCS UTF-8 bytes of the complete
`resumption-state-v1` object, with no digest member inserted. It uses the
lexical form in 2.1. It is intended for save files, replay checkpoints,
cross-implementation recovery comparison and audit identity. It shall not be
used as the default training-deduplication or PUCT-node key.

If the complete repetition history, replay-prefix identity, offer references
or claim audit cannot be established, a producer shall report insufficient
history and shall not emit `resumption-state-v1`.

### 5.3 `decision-state-v1`

MIF 1.0 shall separately register `decision-state-v1` as the sufficient state
that can change legal actions, subsequent transitions or outcome under the
selected semantics profile. It shall be a profile-defined projection, not an
opaque copy of the complete MFEN or MSTATE.

The projection shall include:

- the decision-profile and MRS `semanticDigest`;
- board, active player, phase/action, hands and pending obligations when they
  can affect a future decision;
- no-progress, terminal outcome and semantic extensions only as required by
  the selected semantics profile;
- the repetition profile's sufficient statistic;
- the semantic open-offer state, expressed as actor and available operations
  without a raw `offerEventSeq`; and
- the exact set of draw-claim reasons currently exercisable.

The projection shall exclude:

- `primary-ply`, unless the selected semantics profile explicitly declares
  that it changes a legal action, transition or outcome;
- event sequence numbers and history provenance used only as wire references;
- closed offer/claim audit records;
- ordered repetition history when the selected repetition profile declares an
  order-independent sufficient statistic; and
- `documentDigest`, titles, status and annotations.

An adapter maps canonical offer operations back to the current wire
`offerEventSeq`; that reference is part of resumption identity, not decision
equivalence.

Each repetition profile shall define its sufficient-statistic profile. For
reset-clears-window semantics, the baseline statistic is a canonical map from
`repetition-observation` digest to occurrence count, with counts capped at the
claim or automatic threshold. Array order and observation provenance are not
part of that statistic. A future sliding-window or order-sensitive rule
requires a separately versioned statistic profile.

The statistic and its digest shall have a specified incremental update
algorithm, no worse than logarithmic in the number of distinct active
observations. A producer shall not re-hash an ever-growing ordered window on
every primary action. A portable diagnostic representation may materialize
the map, while search nodes may retain the registered persistent-map root and
its backing state.

`decisionDigest` is SHA-256 over the canonical `decision-state-v1` projection,
with no digest member inserted. It uses the lexical form in 2.1 and is the
standard exact-coordinate identity for training deduplication, PUCT nodes,
decision caches and cross-implementation decision comparison.

Training constraints that are not game rules, including `max_ply`, rollout
limits and truncation policy, shall be bound by a separate versioned
`experimentDigest`. A training identity therefore binds at least the suite,
ruleset semantic, experiment and decision digests; `primary-ply` shall not be
used as an implicit substitute for experiment configuration.

Identity vectors shall include pairs of otherwise decision-equivalent valid
histories that differ in decision-irrelevant primary-ply/provenance, ordered
repetition history with the same registered sufficient statistic, or raw
`offerEventSeq`. Each pair shall produce identical canonical decision state
and `decisionDigest`, but distinct resumption state and `resumptionDigest`.

Negative vectors shall change each semantic component separately, including
active player, legal-action-affecting obligation, available offer operation,
claim right, repetition threshold status, no-progress status when applicable
and outcome. Each change shall be reflected in canonical decision state and
its expected digest.

The base digest preserves the source coordinate frame. An application that
wants symmetry-equivalent deduplication shall first apply a registered
full-state normalization profile, include that profile identity in the
normalized object and then compute the digest. It shall not silently substitute
MPK normalization.

### 5.4 MPK/1.0 ruleset binding

MPK remains an intentionally incomplete structural key. It shall not be used
as a repetition key, resumable-state key or decision-state key.

An independent MPK/1.0 record shall nevertheless bind its rules semantics
directly. Its wire form shall place the full `semanticDigest` immediately after
`ruleset-id@version` and before `key-profile`:

```text
MPK/1.0 <state-profile> <ruleset-id@version> <semanticDigest>
<key-profile> <board24> <side> <phase> <hands> [<key-extension> ...]
```

The display wraps only for readability. A containing dataset may repeat the
binding, but its value shall match the MPK record. An MPK/1.0 record that has
only `id@version`, or whose resolved manifest produces another
`semanticDigest`, is invalid. MPK is self-binding but still requires a trusted
manifest or registry when semantic validation or publisher trust is needed.

MPK vectors shall cover a missing `semanticDigest`, an envelope/record
digest mismatch, a resolved-manifest mismatch and two otherwise identical MPK
records with the same `id@version` but different semantic digests. The first
three are rejected; the last pair has different canonical MPK bytes and
cannot collide as a textual database key.

### 5.5 Claim-right lifecycle

MIF 1.0 shall make claim entitlement a deterministic derived state with these
boundaries:

1. a no-progress or repetition claim right is created only after all
   deterministic processing reaches a stable primary decision boundary and a
   claim-mode threshold is satisfied;
2. the right belongs to the active player and records the exact set of
   currently claimable reasons;
3. offer, decline and withdrawal events do not consume the right while the
   same gameplay decision boundary remains; acceptance, resignation,
   adjudication or another terminal transition closes it;
4. the right expires immediately before any successful primary or
   supplementary gameplay action is accepted;
5. no previous right carries into a pending-removal state, and no new right is
   evaluated until the logical turn reaches its next stable boundary; and
6. a valid `claim-draw` consumes the selected right and enters the terminal
   state.

A player who continues with a primary action cannot later claim using the
right from the earlier boundary. A `claim-draw` event while an obligation is
pending is invalid in 1.0. Imported resumption state shall contain or derive
the current rights, and replay shall verify them rather than infer persistence
from a counter alone.

Vectors shall cover creation, persistence across non-gameplay draw
negotiation, expiration on primary action, a primary action that creates a
pending removal, post-removal re-evaluation and terminal consumption.

## 6 Logical-turn projection and atomic-action conversion

MSTATE/1.0 shall standardize a replay-derived logical-turn projection without
hiding remove events inside primary events.

The base algorithm shall:

1. replay the origin and events in sequence;
2. start a logical turn at each successful `place` or `move` event;
3. associate every later `remove` event that resolves an obligation causally
   produced by that primary sequence, including obligations deterministically
   generated at its stable boundary;
4. close the turn after all such obligations and stable-boundary processing
   complete, or mark it truncated if a terminal event intervenes;
5. preserve the original `seq` values and the ordered list of associated
   remove-event sequence values;
6. represent removals of an obligation already present at origin as an origin
   fragment with no invented primary event; and
7. when an obligation-free origin deterministically generates a board-full,
   stalemate or mill-count obligation during origin stabilization, represent
   its removals as an `origin-stabilization` fragment with no invented primary
   event.

Draw negotiation or other permitted non-gameplay events may occur inside the
event sequence range. They remain in MSTATE but are not recast as primary or
remove actions in the logical-turn action list.

A mandatory `causedBySeq` member is not required in the base event format:
valid replay already determines a unique causal primary sequence. A future
profile may add redundant causal indexes only if their verification and
canonical treatment are specified.

The conformance corpus shall include bidirectional NMM_LLM vectors for:

- place without removal;
- move without removal;
- place or move plus one board removal;
- a hand removal when the target representation supports it;
- multiple consequent removals;
- a pending-origin fragment; and
- obligation-free origins whose stabilization generates board-full,
  stalemate and mill-count fragments;
- every lossy or unrepresentable reverse mapping.

An atomic target record may be emitted only when it represents the entire
logical turn without guessing. MSTATE continues to serialize each removal as
an independent event.

## 7 Standard diagnostic envelope

MIF 1.0 shall define one JSON diagnostic envelope for parsing, validation,
replay and conversion failures. At minimum it shall contain a format
identifier and a non-empty ordered `errors` array. Every error contains the
standard `category` and `code`.

The following location and detail members shall be standardized and omitted
only when inapplicable:

- `instancePath`: RFC 6901 JSON Pointer into a JSON input;
- `textOffset`: zero-based UTF-8 byte `start` (inclusive) and `end`
  (exclusive) in the original text input;
- `eventSeq`: the MSTATE event being validated or replayed;
- `expected` and `actual`: bounded I-JSON diagnostic values; and
- `resourceLimit`: resource name, configured limit and observed value.

The envelope shall define deterministic precedence when one defect can be
reported at multiple validation stages. Implementations may add localized
human text, but interoperable consumers shall not have to parse that text.

## 8 Machine-readable capabilities

MIF 1.0 shall define a capability document with a versioned format identifier.
It shall be able to declare:

- implementation name and version;
- exact suite digests;
- supported read and write formats;
- conformance classes;
- semantics, state, repetition, repetition-summary, resumption, decision, key
  and transform profiles;
- placing-liveness, claim-right and MPK semantic-binding profiles, plus every
  claimed transform-invariance declaration;
- ruleset `id@version`, `semanticDigest` and, when exact publication support is
  claimed, `documentDigest`;
- supported source/target conversion mappings and loss policies;
- configured resource limits; and
- the conformance-corpus digest against which a claim was tested.

Read support, write support, tested conformance and experimental support shall
be distinguishable. A capability document is a machine-readable claim, not
proof of correctness or publisher trust.

## 9 Full-state transformations

The 1.0 transformation specification shall cover MFEN, MIFPOS, MSTATE,
resumption state, decision state and actions, not only MPK. A registered
full-state transform shall transform every coordinate- or line-bearing value,
including:

- boards in origin, current, resumption and decision positions;
- primary-event `at`, `from`, `to` and `interventionLine`;
- board-removal targets;
- obligation target bitsets and any coordinate-bearing branch data;
- `lm`, `ul` and registered semantic extensions;
- repetition-observation boards and semantic values; and
- any normalized action, principal variation or result coordinates associated
  with the state.

Player-specific scalar values, event sequence values, counters, offer
references and non-coordinate audit data retain their meaning. The transformed
MSTATE shall replay to its transformed current checkpoint under the same
ruleset semantics.

Vectors shall cover every registered transform, its inverse, pending
obligations, `lm`, `ul`, repetition history, actions and at least one complete
multi-event logical turn. A transform profile shall state whether it preserves
the source frame or selects a canonical frame and how ties are resolved.

Coordinate conversion and equivalence normalization are different claims. A
transform implementation may convert a record into another coordinate frame,
but shall claim rules-equivalent normalization only when a versioned
invariance declaration exists for the exact pair:

```text
(semanticDigest, transform-profile)
```

The declaration shall identify its version, state profile, permitted transform
IDs, treatment of every semantic extension and its own document digest. It
shall demonstrate that legal actions, transitions, claim rights and outcomes
are preserved in both directions.

Without that declaration, transformed records may be used only as explicit
coordinate-frame conversions. They shall not be used for decision
canonicalization, training deduplication, PUCT merging, tablebase merging or
a claim of equivalent MPK normalization.

The suite and capability document shall pin every invariance declaration they
claim. Vectors shall include an absolute-coordinate semantic extension that
transforms structurally but is rejected for equivalence normalization, plus
positive and inverse cases for each declared transform.

## 10 Finite-rule liveness and repetition scope

### 10.1 No legal primary action during placing

MRS/1.0 shall add a mandatory `placing.noLegalPrimaryAction` finite mechanism.
At any ongoing stable phase-`p` primary decision boundary, after deterministic
processing, the engine shall test whether the active player has any legal
place or permitted move. If none exists, it shall apply exactly one selected
action:

- `apply-board-full`: execute `boardFull.action`; this selection is valid
  only when manifest-consistency analysis proves that every reachable trigger
  also satisfies the full-board predicate and `boardFull.action` is not
  `disabled`;
- `loss`: the active player loses with reason `no-legal-primary-action`; or
- `draw`: the game draws with reason `no-legal-primary-action`.

The state shall not remain ongoing with no legal primary action. This rule also
covers a full board with reserve pieces, delayed blocked points and
`placing.movementAllowed=true` when no movement destination exists.

A 0.4 ruleset that can reach such a state and does not determine one of these
effects requires explicit policy selection during conversion. A converter
shall not guess from `boardFull.action=disabled`.

Vectors shall cover full board plus reserve in phase `p` for all three actions,
the invalid `apply-board-full`/`disabled` combination, an invalid reachable
non-full `apply-board-full` trigger, delayed blocked points and both
`turn.initial` values.

### 10.2 Repetition observation scope

MRS/1.0 shall support at least two explicit observation profiles:

- `stable-moving-v1` observes only ongoing stable phase-`m`, action-`m`
  boundaries; selecting it explicitly means repetition is moving-phase only;
- `stable-primary-decision-v1` observes every ongoing stable primary decision
  boundary in phase `p` or `m`, after deterministic processing and with no
  pending obligation.

A manifest with `placing.movementAllowed=true` and repetition enabled shall
either select `stable-primary-decision-v1` or intentionally select and expose
the moving-only scope. Capability and user-facing rule descriptions shall not
advertise only “threefold repetition” without the selected observation scope.

Vectors shall cover a placing-regime movement cycle, ordinary moving cycles,
placement reset events, pending removals that are not observed, origin
stabilization and both automatic and claim modes.

## 11 MIF Suite 1.0 manifest

The 1.0 release shall publish a canonical `mif-suite-1.0.json`. It shall bind
one tested combination rather than require consumers to guess compatible
component versions.

The suite manifest shall contain at least:

- its own format and suite identifier;
- the exact MFEN, MPK, MSTATE, MIFPOS and MRS versions;
- the exact diagnostic and capability format or schema identifiers;
- selected semantics, state, repetition, repetition-summary, resumption,
  decision, key and transform profiles;
- the placing-liveness policy, claim-right profile, MPK semantic-binding
  profile and every transform-invariance declaration;
- the normative specification commit and raw-file SHA-256;
- registry, conformance-corpus, JSON Schema and ABNF raw-file SHA-256 values;
- conversion-vector and 0.4-to-1.0 migration-vector SHA-256 values;
- corpus-integrity checker and executable reference-runner identifiers and
  raw-file SHA-256 values;
- media-type and recommended-extension assignments;
- the compatibility policy; and
- the signature-manifest identifier or location.

The suite digest shall be SHA-256 over the JCS UTF-8 bytes of the suite object
with no digest member inserted. Release tooling shall publish the resulting
value alongside the file and sign a release manifest that binds it.

Training runs, databases and cross-project tests should record the suite
digest plus every ruleset `semanticDigest` they use. A claim of “MIF 1.0”
without either an exact suite digest or an explicitly listed component set is
incomplete.

No final suite file shall be published with placeholders. Its hashes are
computed only after all referenced 1.0 artifacts are frozen and verified.

## 12 Version lifecycle, annotations and extensions

MRS/1.0 and other JSON envelopes shall reserve separate `annotations` and
`extensions` containers.

For MRS:

- `annotations` is non-semantic, is included in `documentDigest`, is excluded
  from `semanticDigest` and may be ignored or round-tripped as specified by
  MRS; and
- `extensions` is semantic, is included in `semanticDigest`, requires an
  explicitly identified profile and causes fail-closed rejection when that
  profile is unsupported.

For another envelope, `annotations` is excluded from gameplay and decision
projections and is included in a full-document digest when that format defines
one. Its `extensions` is included in every applicable semantic or decision
projection and likewise requires an explicitly identified profile.

An implementation shall not place gameplay behaviour in `annotations` or use
an unknown `extensions` member as ignorable metadata.

The 1.x lifecycle policy shall classify changes as follows:

| Change | Required action |
|---|---|
| Add a ruleset or registry annotation using existing closed formats and profiles | registry update; no existing digest changes |
| Add optional syntax or capability without reinterpreting existing bytes | a new minor format signature or independently identified profile, plus schemas, vectors and a new suite release |
| Change a ruleset's legal actions, transitions, terminal behaviour or semantic extensions | new ruleset version and `semanticDigest` |
| Change publication metadata only | new `documentDigest`; ruleset version and `semanticDigest` unchanged |
| Change the meaning, canonical form, digest projection, required members or default behaviour of an existing signature/profile | 2.0; a separately named 1.x signature/profile is allowed only when existing bytes retain their identity and meaning |
| Remove or rename an existing token, weaken fail-closed handling, or change default meaning of omitted data | 2.0 |

Adding a registry value alone shall not extend a closed grammar or reinterpret
an existing profile.

## 13 Release gates and disposition

### 13.1 Highest-priority blockers before wire freeze

The first work shall close these four items:

1. fixed White/Black identity, initial-player terminology, renamed board-full
   tokens and complete `turn.initial=b` vectors;
2. separate `resumption-state-v1`/`resumptionDigest` from the profile-defined
   sufficient `decision-state-v1`/`decisionDigest`, including incremental
   repetition summaries and separate `experimentDigest`;
3. direct `semanticDigest` binding in every MPK/1.0 record; and
4. versioned invariance declarations for every claimed
   `(semanticDigest, transform-profile)` equivalence.

### 13.2 Other blockers before wire freeze

The wire contract shall not freeze until it also defines:

1. `placing.noLegalPrimaryAction` and its full-board/reserve vectors;
2. `stable-primary-decision-v1` and explicit moving-only repetition scope;
3. the complete claim-right creation, persistence and expiration lifecycle;
4. origin-stabilization logical-turn fragments; and
5. normative 0.4-to-1.0 conversion and rejection behaviour for each ambiguous
   0.4 construct above.

### 13.3 Remaining release artifacts and evidence

The following remain release blockers after the wire contract is frozen:

1. the `semanticDigest`/`documentDigest` split and complete projection vectors;
2. MIFPOS with portable and reference conformance vectors;
3. schemas and vectors for `repetition-observation-v1`,
   `resumption-state-v1`, `resumptionDigest`, `decision-state-v1`,
   `decisionDigest` and `experimentDigest`;
4. portable-by-default MSTATE and resolver-failure vectors;
5. the final `mif-suite-1.0.json` and signed release manifest;
6. standardized logical-turn and NMM_LLM bidirectional conversion vectors;
7. the diagnostic and capability schemas;
8. the 1.x/2.0 lifecycle and extension policy;
9. JSON Schemas, ABNF, recommended file extensions and documented media-type
   assignments;
10. a formal repository license and registry governance policy;
11. full-state transform vectors for every transform claimed by the suite;
12. normative 0.4-to-1.0 conversion and failure vectors;
13. the independent implementation, cross-language replay, fuzzing and
    governance conditions already listed in MIF/0.4 Annex F.9;
14. a corpus-integrity command whose name and success text say only
    `corpus integrity passed`, without claiming rule execution; and
15. an executable reference runner that parses and executes every applicable
    1.0 rule, transition, transform and MSTATE replay vector and reports
    execution conformance separately from corpus integrity.

The repository owners must still select the license, registry governance
authority, final media-type names and release-signature mechanism. This
document deliberately does not invent legal authorization or governance
consent for those choices.

### 13.4 Required implementation order

The project shall proceed in this order:

1. close the design blockers in 13.1 and 13.2;
2. freeze the complete MIF 1.0 wire contract;
3. generate the 1.0 ABNF, JSON Schemas, registries and conformance corpus;
4. build the executable reference runner;
5. have Sanmill and NMM_LLM implement independent 1.0 adapters directly;
6. compare canonical bytes, semantic state and replay results over the same
   corpus; and
7. publish `mif-suite-1.0.json` only after those implementations agree.

The corpus-integrity checker is evidence about delivered files, not a
substitute for steps 4 through 6.

### 13.5 Retained non-changes

The following review recommendations are accepted as constraints:

- do not collapse MFEN, MPK, MSTATE and MRS into one universal format;
- keep removal as an independent MSTATE event;
- keep MRS a finite-mechanism manifest rather than a general rule DSL; and
- keep lossy conversion explicit, ordered and fail-closed, with no guessed
  compatibility.

Until every blocking artifact exists and the suite digest is published, the
repository shall describe 1.0 as a Candidate Wire Contract with no published
suite conformance target and shall not claim MIF Suite 1.0 conformance.

No Sanmill or NMM_LLM implementation of MIF/0.4 is required. The only ongoing
use of 0.4 is as a byte-frozen historical reference and source format for
explicit 0.4-to-1.0 conversion or rejection vectors.
