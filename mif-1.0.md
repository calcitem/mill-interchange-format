# Mill Interchange Format 1.0

## Candidate Wire Contract

Status: frozen wire contract; MIF Suite 1.0 conformance is not yet available

This document is the standalone normative wire contract for MIF 1.0. It
defines the bytes, JSON data models, state transitions, identities and
failure behaviour that later ABNF files, JSON Schemas, registries,
conformance corpora and executable runners shall implement.

Freezing this contract does not assert that those later artifacts or two
independent implementations exist. A producer shall not claim MIF Suite 1.0
conformance until a final `MIFSUITE/1.0` manifest identifies them.

MIF Community Working Draft 0.4 at commit
`9ecc134853628dc29d3037727a566702505fda1f` remains a byte-frozen
historical input. Its English specification raw-file SHA-256 is
`F1F1D839318A4D45F3ECEA4850FEE080C47FFCBC81025BD74E3EA48C815F3093`.

# 1 Scope

MIF defines interoperable representations for Mill-family games:

- MFEN: a compact instantaneous position under an external ruleset context;
- MPK: an intentionally incomplete structural analysis key;
- MIFPOS: a self-identifying instantaneous-position envelope;
- MSTATE: a resumable event history with authoritative checkpoints; and
- MRS: a finite-mechanism ruleset manifest.

It also defines derived resumption and decision identities, diagnostics,
capabilities, conversion reports, transform-invariance declarations,
logical-turn projections and the shape of a future suite manifest.

MIF does not standardize tournament rules, search evaluation, UI behaviour,
database packing, a general rules DSL, network discovery or publisher trust.

# 2 Normative references

The following specifications are required by this contract:

- RFC 5234, Augmented BNF for Syntax Specifications: ABNF;
- RFC 7405, case-sensitive ABNF string literals;
- RFC 8259, The JavaScript Object Notation (JSON) Data Interchange Format;
- RFC 7493, The I-JSON Message Format;
- RFC 8785, JSON Canonicalization Scheme (JCS);
- RFC 6901, JSON Pointer; and
- FIPS PUB 180-4, SHA-256.

# 3 Terms and definitions

## 3.1 player identity and initial player

`w` is White and stable player identity 0. `b` is Black and stable player
identity 1. Neither identity implies move order. The **initial player** is the
value of `turn.initial`.

The unqualified terms *first player* and *second player* are not normative
aliases for White and Black.

## 3.2 authoritative state

State that a consumer shall preserve and shall not replace with a derived
cache or guessed value.

## 3.3 stable primary decision boundary

An ongoing state with no obligation, after every deterministic transition,
at which a primary gameplay event can be selected or a current claim right
can be exercised.

## 3.4 primary and supplementary actions

A primary action is a successful `place` or `move`. A supplementary action
is a `remove` that resolves an obligation.

## 3.5 MIF logical turn and round

A **MIF logical turn** is one player's primary action plus every consequent
mandatory removal through the next stable boundary. A **full move** or
**round** normally contains one logical turn by each player.

## 3.6 profiles

A state profile defines position fields. A semantics profile defines
transitions and terminal priority. A key profile defines MPK projection and
normalization. A transform profile defines coordinate transforms. Each
profile identifier has independent versioning.

# 4 Conformance boundary

## 4.1 Contract status

The following format signatures and profile meanings are frozen by this
contract:

```text
MFEN/1.0
MPK/1.0
MIFPOS/1.0
MSTATE/1.0
MRS/1.0
MIFDIAG/1.0
MIFCAP/1.0
MIFCONV/1.0
MIFINV/1.0
MIFTURN/1.0
MIFSUITE/1.0
```

This contract registers:

- state profile `mill24-state-v1`;
- topology profiles `mill24-orthogonal-v1` and `mill24-diagonal-v1`;
- semantics profile `mif-finite-rules-v3`;
- finite transition subprofiles `after-unobligated-place-v1`,
  `on-enter-moving-v1`, `target-commits-v1` and
  `stable-after-primary-sequence-v1`;
- MRS semantic projection `mrs-semantic-v1`;
- key profiles `structural-d4-v1` and `structural-aut16-v1`;
- repetition projection `repetition-observation-v1`;
- observation profiles `stable-moving-v1` and
  `stable-primary-decision-v1`;
- repetition summary `reset-count-smt-v1`;
- resumption profile `resumption-state-v1`;
- decision profile `decision-state-v1`;
- claim lifecycle `stable-claim-rights-v1`;
- MPK binding profile `inline-semantic-digest-v1`;
- full-state transform profile `mill24-full-state-v1`;
- invariance declaration profile `transform-invariance-v1`; and
- logical-turn projection `logical-turn-v1`.

An implementation shall emit only signatures and profiles it implements. It
shall not interpret an unknown signature as the nearest known version.

## 4.2 Conformance classes

A future suite may claim separately:

- `position`: MFEN and MIFPOS parsing, validation and canonical output;
- `key`: MPK eligibility, projection and canonicalization;
- `ruleset`: MRS validation and both digest domains;
- `replay`: complete MSTATE event replay and checkpoint validation;
- `identity`: repetition, resumption and decision projections and digests;
- `transform`: coordinate conversion and declared equivalence;
- `conversion`: MIFCONV reports and registered mappings; and
- `full`: every class selected by the suite.

No class is testable merely from this prose. A claim requires the later suite
digest and its identified executable corpus.

## 4.3 Fail-closed rule

Unknown unprefixed syntax, semantic event types, semantic extensions,
profiles, obligation causes or standard outcome reasons shall be rejected.
Unknown semantic content shall never be ignored or guessed.

# 5 Common wire conventions

## 5.1 Text and JSON

MFEN and MPK contain US-ASCII only and use exactly one U+0020 SPACE between
fields. They have no leading or trailing whitespace. Transport framing is
outside each record.

Every JSON format in this contract is UTF-8 I-JSON. A BOM shall not be
emitted. Object names shall be unique after JSON escape decoding. Unpaired
surrogates are invalid. Parsers shall detect duplicate names before
conversion to a map.

Canonical JSON output and every JSON digest input use RFC 8785 JCS. Strings
shall not be Unicode-normalized.

## 5.2 Integers

Exact integers are in the inclusive range 0 through 9007199254740991.
Textual integers use unsigned decimal without leading zeroes except `0`.

## 5.3 Identifiers

An identifier is 1 to 63 lowercase ASCII letters, digits, dots or hyphens and
begins with a lowercase letter or digit. `x-` begins a private or
provisional identifier.

A ruleset reference is `<identifier>@<positive-integer>`.

## 5.4 Digests

Every digest in this contract has the lexical form:

```text
sha256:<64 lowercase hexadecimal digits>
```

The hexadecimal payload denotes the 32 SHA-256 bytes. Digest names identify
different domains; equal lexical algorithms do not make their inputs
interchangeable.

## 5.5 JSON annotations and extensions

Where permitted, `annotations` is a non-semantic I-JSON object. An empty
`annotations` object is omitted from canonical output.

`extensions` is an array of objects containing exactly `profile` and
`value`. Profile values are unique and sorted by ascending US-ASCII.
`value` is any I-JSON value defined by that profile. An empty array is
omitted. A consumer that does not implement an extension profile shall reject
the containing semantic object.

Annotations never affect legal actions, replay, outcome, semantic digest,
repetition, decision identity or transform equivalence. Extensions affect
every applicable semantic projection.

## 5.6 Closed objects

Each JSON member table is closed. An object contains exactly its required
members, its listed optional members, and no other members. Private content
uses `annotations` or `extensions`, not unknown top-level names.

# 6 `mill24-state-v1`

## 6.1 Ordered state

The state fields are board, side, phase, action, hands, obligations,
no-progress, primary-ply, outcome and named text extensions.

The board is three eight-character rings in this order:

```text
a7 d7 g7 g4 g1 d1 a1 a4 /
b6 d6 f6 f4 f2 d2 b2 b4 /
c5 d5 e5 e4 e3 d3 c3 c4
```

Board characters are:

| Character | Meaning |
|---|---|
| `W`, `B` | live White or Black piece |
| `w`, `b` | blocked delayed-removal token preserving its former owner |
| `.` | empty available point |

Lower-case tokens occupy a point but cannot move, form mills, be removed,
serve as a destination or count as live material.

## 6.2 Side, phase and action

`side` is `w` or `b` in an ongoing state and `-` in a terminal state.
Phase is `p` (placing regime), `m` (moving regime) or `o` (game over).
Action is `p` (phase-p primary input), `m` (moving input), `r`
(supplementary removal) or `o`.

Phase and action are independent authoritative fields.

## 6.3 Hands, counters and outcome

`hands` contains current White and Black unplaced reserves. It is not
derived from placement history.

`no-progress` is the current manifest counter. `primary-ply` counts
successful place and move events. Remove events do not increment it.

Outcome is `-` while ongoing or `w:<reason>`, `b:<reason>` or
`d:<reason>` when terminal.

## 6.4 Obligations

Obligations are `-` or alternative branches separated by `|`. Sequential
obligations inside a branch are separated by `;`.

An obligation is:

```text
actor:cause:zone:target-owner:remaining:targets:after
```

| Field | Values |
|---|---|
| actor | `w`, `b` |
| cause | registered cause in Annex A |
| zone | `b` board or `h` hand |
| target-owner | `w`, `b` |
| remaining | positive integer |
| targets | six lowercase hex digits, `-` for hand, or `~` for deferred later board targets |
| after | `w`, `b`, or `q` to continue the branch |

All branch heads have the same actor; side equals that actor and action is
`r`. A board head has a concrete non-zero target set. A later board record
uses `~` until it becomes head. A hand record uses `-`. `q` requires a
following record; a final record names the next primary player.

Branches sort by cause order and then complete US-ASCII serialization. A
remove target matching multiple heads selects the first canonical branch.

## 6.5 Text extensions

The standard state extensions are:

| Key | Feature | Canonical value |
|---|---|---|
| `lm` | last mill | `W-from,W-to;B-from,B-to` |
| `pc` | placement count | `White-count,Black-count` |
| `ul` | used line IDs | `White-lines,Black-lines` |

Required semantic extensions occur even when zero. Extension keys are unique
and sorted in ascending US-ASCII.

For `lm`, each player value is `from,to`, each coordinate is replaced by `-`
when absent, and White precedes Black. `pc` contains two unsigned integers,
White then Black. Each `ul` value is a four- or five-digit lowercase
hexadecimal bit set over Annex A line IDs; White precedes Black. `ul` records
line IDs, not a union of their points. `pc` increments only after a successful
place and is never decremented by removal.

## 6.6 State consistency

An ongoing state has side `w` or `b`, phase `p` or `m`, outcome `-`.
A terminal state has side `-`, phase/action `o`, obligations `-` and a
terminal outcome.

No obligations means action matches phase. Non-empty obligations mean action
`r` and side equals all branch-head actors.

For each player, live pieces plus delayed tokens plus hand do not exceed the
manifest initial count. Delayed tokens require the delayed placing effect.
Every declared semantic state extension is present.

An independent ongoing stable MFEN shall already be a fixed point of every
deterministic transition evaluable without repetition history. MSTATE origin
is exempt because replay performs origin stabilization.

# 7 MFEN/1.0 and MPK/1.0

## 7.1 MFEN purpose and syntax

MFEN is a compact instantaneous state under caller-supplied ruleset context.
It carries no ruleset identity, digest, history, claim audit or provenance.
It is **context-bound** and shall not be advertised as an independently
shareable semantic object.

```text
MFEN/1.0 <state-profile> <board> <side> <phase> <action>
<hands> <obligations> <no-progress> <primary-ply> <outcome>
[<extension> ...]
```

The display wraps only for readability; a record is one logical line.

Canonical output uses Annex A point order, lowercase hexadecimal, shortest
integers, `-` for no obligation and ongoing outcome, canonical branch order
and sorted extension keys.

Semantic validation requires a resolved `(id, version, semanticDigest)`
context. A context-free parser can perform lexical and state-profile checks
only.

## 7.2 MPK purpose and syntax

MPK is an intentionally incomplete structural key. It omits no-progress,
primary-ply, repetition, claims, offers, outcome and provenance. It shall not
be used as a resumable-state or decision-state key.

```text
MPK/1.0 <state-profile> <ruleset-id@version> <semanticDigest>
<key-profile> <board24> <side> <phase> <hands>
[<key-extension> ...]
```

The semantic digest occurs directly after the ruleset reference. Missing
digest, disagreement with a containing envelope, or a resolved manifest with
another semantic digest is invalid.

An input is eligible only when ongoing, stable, without obligations, with
action `p` or `m`, and when the selected key profile understands every
semantic extension. Unknown adjudication state cannot be silently omitted.

`structural-d4-v1` applies the eight Annex A D4 transforms.
`structural-aut16-v1` applies those eight followed by each composed with
outer/inner ring exchange. Aut16 eligibility additionally requires a valid
MIFINV declaration for the exact semantic digest and transform profile.

For each transform, transform board, `lm`, `ul` and every registered
coordinate or line extension; retain player-bound scalars; serialize the full
candidate; select the lexicographically least US-ASCII bytes. Ties select the
lowest transform ordinal.

# 8 Common ruleset envelope and MIFPOS/1.0

## 8.1 Ruleset envelope

The ruleset envelope has exactly these common members:

| Member | Type | Requirement |
|---|---|---|
| `mode` | string | `portable` or `reference` |
| `id` | identifier | required |
| `version` | positive integer | required |
| `semanticDigest` | digest | required |
| `documentDigest` | digest | portable required; reference optional |
| `manifest` | MRS object | portable required; reference forbidden |

Portable validation verifies manifest ID/version, semantic projection,
semantic digest, full JCS document digest and MRS validity.

Reference resolution uses `(id, version, semanticDigest)`. If
`documentDigest` is present the resolved document also matches it. Resolution
is caller supplied and local; parsing never initiates network access.

## 8.2 MIFPOS closed object

MIFPOS contains exactly:

| Member | Type |
|---|---|
| `format` | `MIFPOS/1.0` |
| `positionFormat` | `MFEN/1.0` |
| `stateProfile` | `mill24-state-v1` |
| `position` | canonical MFEN string |
| `ruleset` | ruleset envelope |
| `annotations` | optional non-semantic object |
| `extensions` | optional semantic extension array |

The embedded profile matches `stateProfile`. Generic export, copy, QR and
share operations default to portable mode. Reference mode requires explicit
caller selection.

MIFPOS contains no event history and does not replace MSTATE, resumption state
or decision state.

# 9 MSTATE/1.0

## 9.1 Top-level object

MSTATE contains exactly:

| Member | Type |
|---|---|
| `format` | `MSTATE/1.0` |
| `positionFormat` | `MFEN/1.0` |
| `stateProfile` | `mill24-state-v1` |
| `ruleset` | ruleset envelope |
| `origin` | canonical MFEN |
| `events` | ordered event array |
| `current` | canonical MFEN replay checkpoint |
| `repetitionHistory` | ordered active window |
| `preOriginClaims` | ordered claim-audit seed |
| `claims` | ordered claim/offer audit |
| `annotations` | optional non-semantic object |
| `extensions` | optional semantic extension array |

Portable is the default for training data, archives, save/export/share APIs
and cross-project exchange. Reference is an explicit storage optimization.

MSTATE contains neither a resumption/decision object nor resumptionDigest or
decisionDigest cache members. Those identities are derived under Clause 12;
a consumer never chooses between an embedded cache and replayed authority.

## 9.2 Events

Every event contains `seq`, `actor`, `type`, optional `annotations` and
optional `extensions`, plus only the members permitted by its type.
Sequences are consecutive integers beginning at 1 and array order equals
sequence order.

Standard events are:

| Type | Actor | Additional members |
|---|---|---|
| `place` | current side | `at`; optional non-default `interventionLine` |
| `move` | current side | `from`, `to`; optional non-default `interventionLine` |
| `remove` | obligation head actor | structured `target` |
| `offer-draw` | current side | none |
| `accept-draw` | non-offerer | `offerEventSeq` |
| `decline-draw` | non-offerer | `offerEventSeq` |
| `withdraw-draw` | offerer | `offerEventSeq` |
| `claim-draw` | current side | `reason`: `no-progress` or `repetition` |
| `resign` | `w` or `b` | none |
| `adjudicate` | `system` | `result`, `reason`, `authority` |

A board remove target is exactly
`{"zone":"board","at":<coordinate>}`. A hand target is exactly
`{"zone":"hand","player":"w|b"}`.

Place and move increment primary-ply once after successful mutation. Every
hand or board removal remains an independent event.

Draw negotiation changes no gameplay state. At most one offer is open.
Accept, decline and withdraw reference the exact open event; pre-origin open
offers use reserved `offerEventSeq=0`.

`system` performs only adjudication. Unknown semantic event extensions
require an implemented extension profile authorized by the MRS.

## 9.3 Repetition history

Each entry contains:

| Member | Requirement |
|---|---|
| `source` | `pre-origin`, `origin` or `event` |
| `eventSeq` | required only for `event` |
| `key` | `repetition-observation-v1` object |

Leading pre-origin entries are chronological and precede origin/event entries.
Origin stabilization adds an origin observation only when the selected
observation profile applies. An event observation references the final event
that closed its primary sequence.

## 9.4 Claim audit

Pre-origin claim seeds contain actor, `kind=draw-offer` and offer status.
At most one seed is open.

Audit records contain source, actor, eventSeq when event-sourced, kind
`draw-offer` or `draw-claim`, status, and resolvedEventSeq when a later
event resolves the record. Offer status is `open`, `accepted`, `declined`,
`withdrawn` or `expired`; a valid draw claim is `accepted`.

Event records sort by eventSeq. Claim rights themselves are derived and are
not audit events.

## 9.5 Replay

A replayer validates JSON and the ruleset, parses origin, seeds pre-origin
repetition and claims, performs origin stabilization, applies every event and
deterministic transition, and then compares canonical current, repetition
history and claim audit.

Mismatch codes are `checkpoint-mismatch`,
`repetition-history-mismatch` and `claims-mismatch`. A mismatch is never
repaired in conforming replay.

# 10 MRS/1.0 and digest domains

## 10.1 Closed manifest

MRS is a finite-mechanism manifest, not a general rules language.

Required members are:

| Member | Type |
|---|---|
| `format` | `MRS/1.0` |
| `id` | identifier |
| `version` | positive integer |
| `title` | string |
| `status` | `fixture`, `experimental`, `registered` or `deprecated` |
| `semanticsProfile` | `mif-finite-rules-v3` |
| `topology` | registered topology |
| `pieces` | material object |
| `turn` | initial/boundary object |
| `flying` | flying object |
| `placing` | placing-regime object |
| `mills` | mill object |
| `captures` | capture object |
| `boardFull` | board-full object |
| `stalemate` | stalemate object |
| `draw` | draw object |
| `semanticState` | sorted unique feature array |

Optional members are non-empty `description`, `annotations` and
`extensions`. Unknown members are invalid.

`pieces`, `turn`, `flying`, `mills`, `captures`, `stalemate` and
`semanticState` retain the finite shapes and value meanings defined below.

## 10.2 Material, turn and placing

`topology` is `mill24-orthogonal-v1` or `mill24-diagonal-v1`.

`pieces` contains positive `white`, `black` and `minimumLive`.
`minimumLive` does not exceed either initial count.

`turn` contains `initial` (`w` or `b`) and
`placingEndActivePlayer` (`w`, `b` or `retain`).

`flying` contains Boolean `enabled` and positive `maximumLive`.

When flying is enabled, a phase-m player with no more than `maximumLive` live
pieces may move to any empty point. When it is disabled, `maximumLive` remains
required in the document but is semantically inert and is removed by the
semantic projection in 10.7.

`placing` contains:

- Boolean `movementAllowed`;
- `earlyStop` with `emptyPoints` and
  `boundary=after-unobligated-place-v1`; and
- `noLegalPrimaryAction`, one of `apply-board-full`, `loss` or `draw`.

Zero early-stop points disables early stop.

`apply-board-full` requires `boardFull.action` not `disabled` and every
reachable trigger under the selected extension profiles to satisfy the
full-board predicate.

## 10.3 Mills and captures

`mills` contains:

- `placingEffect`: `remove-opponent-board`,
  `remove-opponent-hand-change`, `remove-opponent-hand-retain`,
  `opponent-remove-own-board`, `mark-opponent-board-until-moving` or
  `remove-by-current-mill-count-at-placing-end`;
- `movingEffect=remove-opponent-board`;
- `removalMultiplicity`: `one-per-primary` or `one-per-new-line`;
- `targetProtection`: `outside-mill-first` or `all-opponent`;
- `lineReuse`: `unlimited` or `once-per-player`;
- `reverseReformation`: `allowed` or `prohibit-immediate`; and
- `delayedClearBoundary=on-enter-moving-v1`.

`captures` contains `resolution=target-commits-v1` and `custodian`,
`intervention`, `leap`. Each mechanism contains Boolean `enabled`,
`lines` Booleans for `squareEdges`, `cross`, `diagonal`, sorted unique
`phases` containing `placing` or `moving`, and
`maximumOwnLivePieces` as positive integer or null.

Disabled capture mechanisms retain those members in MRS wire documents, but
all members except `enabled` are semantically inert. For custodian and
intervention, `maximumOwnLivePieces` applies in phase m only. For leap it
applies in every listed phase. Null means no material limit. The diagonal
line family is empty under `mill24-orthogonal-v1`, even when selected.

## 10.4 Board-full and stalemate

`boardFull.action` is:

- `disabled`;
- `white-loses`;
- `white-then-black-remove`;
- `black-then-white-remove`;
- `active-player-removes`; or
- `draw`.

These are fixed-colour effects and do not depend on `turn.initial`.

`stalemate` contains `action` and
`boardRemovalTargets=adjacent-opponent`. Action is `loss`,
`change-player`, `remove-and-retain`, `remove-and-change`, `draw` or
`both-remove`.

## 10.5 Draw mechanisms

`draw` contains `noProgress`, `repetition`, `offers` and
`claimRights`.

`noProgress` contains non-negative `normalLimit`, `endgameLimit`,
`endgamePredicate` (`none` or `either-player-live-equals-3`), `mode`
(`automatic` or `claim`), sorted unique `countedPrimaryActions`, sorted
unique `resetEvents`, and
`evaluationBoundary=stable-after-primary-sequence-v1`.

`countedPrimaryActions` is a subset of `move`, `place`. Each `resetEvents`
array is a subset of `board-remove`, `hand-remove`, `mill-formation`,
`place`. A physical event reset occurs only after its mutation succeeds.
`mill-formation` occurs when at least one usable new line is detected, even
when its alternative obligation branch is not selected.

`repetition` contains:

- `count`, zero or at least 2;
- `mode`, `automatic` or `claim`;
- `observation`, `stable-moving-v1` or
  `stable-primary-decision-v1`;
- `projection=repetition-observation-v1`;
- `summary=reset-count-smt-v1`; and
- sorted unique `resetEvents`.

Count zero disables observations and the decision repetition summary.

`offers.expiry` is `explicit-only` or
`on-opponent-primary-action`.

`claimRights.profile` is `stable-claim-rights-v1`.

The `draw` object and every nested object are closed. `offers` contains only
`expiry`; `claimRights` contains only `profile`.

## 10.6 Semantic state and consistency

Supported features are `last-mill`→`lm`,
`placement-count`→`pc`, and `used-lines`→`ul`.
`once-per-player` requires used-lines;
`prohibit-immediate` requires last-mill.

Manifest set arrays are sorted unique US-ASCII. Enabled capture mechanisms
select a non-empty applicable line family. Disabled repetition has count zero.
`endgamePredicate=none` requires endgameLimit zero.

The complete MRS set-array classification is:

| Array | Meaning | Canonical requirement |
|---|---|---|
| capture `phases` | set | unique, ascending US-ASCII |
| no-progress `countedPrimaryActions` | set | unique, ascending US-ASCII |
| no-progress/repetition `resetEvents` | set | unique, ascending US-ASCII |
| `semanticState` | set | unique, ascending US-ASCII |
| `extensions` | profile-keyed set | unique profile, ascending profile US-ASCII |

Enabled flying has `maximumLive >= minimumLive`.
`opponent-remove-own-board` is not combined with a capture mechanism enabled
in phase p. Delayed marking requires `on-enter-moving-v1`. An enabled capture
selects at least one non-empty line family. `apply-board-full` satisfies the
reachability condition in 10.2. These are manifest-consistency requirements,
not runtime repair hints.

## 10.7 Semantic projection

`mrs-semantic-v1` is a closed JCS object with required member
`profile=mrs-semantic-v1`. It includes `semanticsProfile`, `topology`,
`pieces`, `turn`, `flying`, `placing`, `mills`, `captures`, `boardFull`,
`stalemate`, `draw` and `semanticState`. It includes `extensions` if and only
if the manifest has a non-empty semantic extension array.

It excludes format, id, version, title, status, description and annotations.

| MRS member | Projection treatment |
|---|---|
| synthetic `profile` | include as `mrs-semantic-v1` |
| `format`, `id`, `version` | exclude |
| `title`, `status`, `description`, `annotations` | exclude |
| `semanticsProfile`, `topology`, `pieces`, `turn` | include exactly |
| `flying` | include, folding disabled form below |
| `placing` | include, folding disabled early stop below |
| `mills` | include exactly |
| `captures` | include, folding each disabled mechanism below |
| `boardFull`, `stalemate` | include exactly |
| `draw` | include, folding disabled counters below |
| `semanticState` | include sorted unique array |
| `extensions` | include sorted array when non-empty; unknown profile rejects |

“Include exactly” means copy the complete closed value after MRS validation;
JCS determines object-member byte order and the array classifications in 10.6
determine set order. No MRS member not listed in this table can enter the
projection.

Before JCS:

- disabled flying becomes exactly `{"enabled":false}`;
- disabled early stop becomes exactly `{"emptyPoints":0}`;
- each disabled capture becomes exactly `{"enabled":false}`;
- no-progress with both limits zero becomes exactly `{"enabled":false}`;
- disabled repetition becomes exactly `{"count":0}`; and
- all enabled mechanisms retain every semantic member in canonical array
  order.

The projection retains `placing.noLegalPrimaryAction`, `draw.offers` and
`draw.claimRights`; none is disabled by another mechanism. The projection is
constructed from the listed members, not by deleting a blacklist from an
unknown MRS object. Unknown projection or extension profiles fail before a
digest is produced.

`semanticDigest` is SHA-256 over those JCS UTF-8 bytes.
`documentDigest` is SHA-256 over the complete MRS JCS bytes. No digest member
is inserted into either input.

# 11 `mif-finite-rules-v3` transitions

## 11.1 Initial state and primary validation

The normal initial state has an empty board, manifest hands, side
`turn.initial`, phase/action `p`, empty obligations, zero counters, ongoing
outcome and zero required semantic state.

A place requires action `p`, actor hand greater than zero and an empty
target. A move requires action `m`, or action `p` with movementAllowed;
an actor live source; empty destination; and adjacency unless flying or leap
applies. Primary-ply increments after successful mutation.

## 11.2 Trigger and branch order

After a primary action, detect leap, usable new mills, intervention and
custodian in that order. A legal leap branch is exclusive, while mill
formation still updates semantic state and no-progress resets.

New mills contain the destination, consist of actor live pieces and are not
excluded by used-line policy. Mill multiplicity is one per primary or one per
usable new line.

Ordinary `outside-mill-first` targets opponent live pieces outside complete
mills when any exist, otherwise all opponent live pieces.

Custodian brackets an opponent middle piece. Intervention occupies a middle
between two opponent endpoints and selects the explicitly named candidate or
the first line-ID candidate. Leap moves endpoint-to-endpoint across an
opponent middle piece.

Non-empty branches sort leap, intervention, custodian, mill. The first remove
target commits to the first matching branch; alternative branches are
discarded.

## 11.3 Mill effects and obligations

Board-removal counts are capped by current target material. Hand-first
effects create explicit hand obligations and optional later board
obligations. Opponent-remove-own-board changes actor and target owner to the
opponent. Delayed removal changes the selected live token to its lower-case
owner marker. Current-mill-count effect waits for the global placing boundary.

Resolving a remove discards unselected branches, applies the mutation,
decrements remaining, performs configured reset and immediate minimum
material, recomputes targets, promotes the next obligation, or empties the
queue and restarts stable processing.

## 11.4 Phase synchronization

Before the global placing boundary, an actor with hand pieces is phase `p`;
an actor without hand pieces is phase `m`, even if the opponent retains a
hand. MovementAllowed additionally permits movement while action is `p`.

The global boundary occurs when both hands are zero or early stop sets both
to zero. It sets phase `m`, clears every delayed token to empty, selects side
from placingEndActivePlayer and evaluates deferred mill-count obligations.

## 11.5 Board-full, material and stalemate

Board-full is evaluated at every ongoing stable boundary with no empty point.
`white-loses` makes Black win. The two fixed-colour removal actions generate
their named order and then activate White or Black respectively.
`active-player-removes` removes one opponent piece then changes side.

After each removal and at stable boundaries, a player below minimum live plus
hand loses; simultaneous deficiency is a draw.

Phase-m stalemate applies after flying. Loss/draw are terminal.
Change-player restarts once and draws if the second moving player is also
stuck. Removal variants use adjacent opponent targets without mill
protection.

## 11.6 No legal phase-p primary action

At an ongoing stable phase-p boundary, determine whether the active player
has any legal place or permitted move. If none:

- `apply-board-full` applies the configured board-full effect;
- `loss` makes the opponent win with reason
  `no-legal-primary-action`; or
- `draw` draws with that reason.

The state shall not remain ongoing without a legal primary action.

## 11.7 Repetition, no-progress and claims

No-progress updates after a primary sequence and evaluates only when stable.
Automatic mode terminates at the selected limit; claim mode derives a right.

Repetition observes only boundaries selected by its observation profile.
`stable-moving-v1` observes ongoing stable phase/action `m`.
`stable-primary-decision-v1` observes every ongoing stable phase-p or
phase-m primary boundary. Pending obligations are never observed.

An observation occurrence at the threshold terminates in automatic mode or
derives a claim right in claim mode.

A claim right is created only after deterministic processing reaches an
ongoing stable primary boundary. It belongs to side and contains the exact
sorted reasons currently satisfied. Offer, decline and withdrawal do not
consume it while the gameplay boundary is unchanged.

The right expires immediately before any successful place, move or remove.
No right carries into a pending-removal state. Claim-draw while an obligation
is pending is invalid. A valid claim consumes the right and terminates.

## 11.8 Stable-boundary priority

Whenever an obligation empties or a primary action creates none, use this
order and stop or pause at the first terminal result or non-empty obligation:

1. enter the global placing boundary and clear delayed tokens;
2. generate deferred mill-count obligations;
3. evaluate board full;
4. evaluate both players' minimum material;
5. evaluate phase-p no-legal-primary-action;
6. evaluate phase-m stalemate;
7. perform repetition observation and automatic repetition;
8. evaluate automatic no-progress;
9. derive current claim rights; and
10. finalize action from phase.

Origin stabilization uses this same pipeline after history and claim seeds
are installed.

## 11.9 Terminal normalization

Terminal state sets phase/action `o`, side and obligations `-`, preserves
post-event board, hands, counters and semantic state, expires open offers
except accepted agreement, and sets exactly one registered outcome reason.

# 12 State identities

## 12.1 Repetition observation

A `repetition-observation-v1` object contains exactly:

| Member | Type or value |
|---|---|
| `profile` | `repetition-observation-v1` |
| `stateProfile` | `mill24-state-v1` |
| `semanticDigest` | rules semantics digest |
| `board` | canonical MFEN board field |
| `side` | `w` or `b` |
| `phase` | `p` or `m` |
| `action` | matching primary action `p` or `m` |
| `hands` | `[white,black]` |
| `semantic` | closed object described below |

`semantic` maps each MRS-declared semantic-state extension key to its
canonical MFEN string value and contains each registered per-state semantic
extension projection required by the selected ruleset extension profiles.
Unknown required state semantics make observation production fail closed.

It excludes no-progress, primary-ply, outcome, offers, claims, audit,
ruleset id/version and publication metadata.

Its observation digest is SHA-256 over its JCS UTF-8 bytes.

## 12.2 Resumption state

A `resumption-state-v1` object contains exactly:

| Member | Meaning |
|---|---|
| `profile` | `resumption-state-v1` |
| `positionFormat` | `MFEN/1.0` |
| `stateProfile` | state profile |
| `semanticDigest` | rules semantics |
| `current` | complete canonical MFEN |
| `replayPrefixDigest` | digest defined below |
| `lastEventSeq` | zero when no events, otherwise last seq |
| `repetitionHistory` | complete ordered active window with provenance |
| `claims` | complete claim/offer audit |
| `openOffer` | raw source/actor/offerEventSeq object or null |
| `claimRights` | current rights object or null |
| `extensions` | optional non-empty resumption semantic extensions |

The optional `extensions` member follows 5.5 and is omitted when empty. Every
implemented extension profile defines its exact resumption projection.

The replay-prefix object is not embedded. It contains exactly `origin`,
`preOriginRepetition`, `preOriginClaims` and `events` in that member spelling.
`preOriginRepetition` is the leading `source=pre-origin` prefix copied from
MSTATE repetitionHistory; the other values are copied without losing raw wire
references. `replayPrefixDigest` is SHA-256 over this object's JCS bytes.

A non-null openOffer object contains exactly `source`, `actor` and
`offerEventSeq`. Source is `pre-origin` with sequence zero or `event` with a
positive sequence. Actor is the offerer. A non-null claimRights object
contains exactly `actor` and `reasons`; reasons is non-empty, unique and
ordered `no-progress`, then `repetition`.

`resumptionDigest` is SHA-256 over the resumption object JCS bytes. It is
returned beside the object and is not inserted into it.
A producer that cannot establish the complete active repetition window,
replay prefix, claim audit or raw open-offer reference shall not emit this
profile and reports `insufficient-resumption-history`.

## 12.3 Decision state

A `decision-state-v1` object contains exactly:

| Member | Meaning |
|---|---|
| `profile` | `decision-state-v1` |
| `stateProfile` | state profile |
| `semanticDigest` | rules semantics |
| `board` | canonical MFEN board field |
| `side` | current side |
| `phase`, `action` | current values |
| `hands` | `[white,black]` |
| `obligations` | canonical MFEN obligation field |
| `noProgress` | normalized integer or null |
| `outcome` | canonical MFEN outcome field |
| `semantic` | declared semantic state |
| `repetitionSummary` | summary object or null |
| `openOffer` | semantic operations or null |
| `claimRights` | current rights or null |
| `extensions` | optional non-empty decision semantic extensions |

It excludes primary-ply, event sequence values, history provenance, closed
audit, documentDigest, title, status, annotations and experiment limits.

When both no-progress limits are zero, noProgress is null. Otherwise it is:

```text
L = max({normalLimit if non-zero} union {endgameLimit if non-zero})
noProgress = min(current no-progress, L)
```

The maximum is taken over a non-empty set. It deliberately includes an
enabled endgame limit when its predicate is not currently true: material may
later enter or leave that predicate, so the capped value preserves every
future transition while merging all values at or above the largest threshold.

`semantic` has the same base shape as in 12.1 and additionally contains any
registered decision-relevant state projection. The optional `extensions`
member follows 5.5; an extension profile defines its decision projection and
may omit resumption-only data.

A non-null openOffer contains exactly `offerer` and `available`.
`available` contains exactly three `{actor,action}` objects: offerer may
`withdraw`; the other player may `accept` or `decline`. Entries sort first by
actor identity (`w`, `b`), then by action order `accept`, `decline`,
`withdraw`. It excludes raw offerEventSeq; an adapter maps a selected operation
back to the current resumption reference.

A non-null claimRights object has the exact shape defined in 12.2. Terminal
states have null openOffer, null claimRights and retain their normalized
outcome. A change to any listed member changes decision identity even if an
implementation's current move generator does not inspect it.

## 12.4 Sparse Merkle repetition summary

`reset-count-smt-v1` is a fixed 256-level sparse binary Merkle tree.
Observation-digest bits choose left=0 or right=1 from most-significant bit to
least-significant bit.

Let SHA-256 inputs below be raw octets:

- empty leaf: `SHA256(0x00)`;
- populated leaf:
  `SHA256(0x01 || observationDigest32 || uint64be(cappedCount))`;
- branch: `SHA256(0x02 || left32 || right32)`.

Define `E[0]=SHA256(0x00)` and
`E[h+1]=SHA256(0x02 || E[h] || E[h])` for h from 0 through 255. `E[256]`
is the canonical empty root. A populated observation leaf replaces `E[0]` at
the 256-bit path, and its ancestors are recomputed bottom-up with the sibling
hash at each depth.

A map entry exists only for a positive occurrence count. Count is capped at
the manifest repetition threshold before uint64 big-endian encoding. An
observation appends by incrementing its prior count; a configured repetition
reset discards every entry and selects `E[256]`. Two unequal canonical
observations producing the same observation digest are an integrity failure,
not one merged entry.

The decision member is exactly
`{"profile":"reset-count-smt-v1","root":<digest>}`. When repetition is
disabled it is null. A materialized map may occur only in excluded diagnostic
annotations. `root` uses the lexical digest form in 5.4 and contains the raw
32-byte tree root as its hexadecimal payload.

`decisionDigest` is SHA-256 over decision-state JCS bytes and is returned
beside the object. Updating one repetition key changes 256 fixed branches and
does not re-hash an ordered history.

## 12.5 Experiment identity

Training limits such as max ply, rollout limits and truncation policy are
encoded in an application-defined versioned I-JSON experiment object.
`experimentDigest` is its JCS SHA-256. Training identity binds suite,
semantic, experiment and decision digests.

# 13 Auxiliary JSON wire formats

## 13.1 MIFDIAG/1.0

The envelope is a closed object:

| Member | Requirement |
|---|---|
| `format` | required `MIFDIAG/1.0` |
| `errors` | required non-empty ordered error array |
| `annotations` | optional non-semantic object |

Each error is closed, contains required string `category` and identifier
`code`, and may contain:

- `instancePath`, RFC 6901 JSON Pointer;
- `textOffset`, a closed object with non-negative integer `start` inclusive
  and `end` exclusive UTF-8 byte offsets, with start no greater than end;
- non-negative integer `eventSeq`;
- bounded I-JSON `expected` and `actual`;
- `resourceLimit`, a closed object with string `name`, non-negative integer
  `limit` and non-negative integer `actual`; and
- non-normative `message`.

Errors order by the validation phases in 16.1. Within one phase they order by
`instancePath`, then text start, eventSeq and code; an absent location sorts
after a present one. A consumer uses category/code and never parses message.

Categories are `syntax`, `canonical`, `unsupported`, `integrity`,
`inconsistent`, `ineligible`, `replay`, `conversion`, `resource` and
`unreachable`.

## 13.2 MIFCAP/1.0

MIFCAP is closed and contains:

| Member | Shape |
|---|---|
| `format` | required `MIFCAP/1.0` |
| `implementation` | required `{name,version}` non-empty strings |
| `suites` | required sorted unique digest array |
| `classes` | required sorted `{id,level}` array |
| `formats` | required sorted `{id,read,write}` array |
| `profiles` | required closed profile-array object below |
| `rulesets` | required sorted ruleset support array |
| `invarianceDeclarations` | required sorted invariance support array |
| `conversions` | required sorted conversion support array |
| `resourceLimits` | required sorted `{name,limit}` array |
| `testedCorpora` | required sorted corpus evidence array |
| `annotations` | optional non-semantic object |

Support level is `none`, `experimental`, `implemented` or `tested`.
Read and write use independent support levels. A class entry uses the same
levels. Profiles contains exactly sorted unique arrays named `semantics`,
`semanticProjection`, `state`, `key`, `repetitionProjection`, `observation`, `repetitionSummary`,
`resumption`, `decision`, `claimLifecycle`, `mpkBinding`, `transform`,
`logicalTurn` and `placingLiveness`.

A ruleset record contains exactly `id`, `version`, `semanticDigest`, optional
`documentDigest`, and `level`. An invariance record contains exactly
`semanticDigest`, `transformProfile`, `documentDigest` and `level`. A
conversion record contains exactly `sourceFormat`, `targetFormat` and a
non-empty `statuses` array in the status order of 13.3. A tested-corpus record
contains exactly `digest` and a sorted unique `classes` array.

Arrays sort by their natural first identity: id; profile string; ruleset
`(id,version,semanticDigest)`; invariance `(semanticDigest,transformProfile)`;
conversion `(sourceFormat,targetFormat)`; resource name; or corpus digest.
Empty arrays remain present because their absence would make capability scope
ambiguous. A capability is a claim, not proof.

## 13.3 MIFCONV/1.0

MIFCONV is closed and contains required `format=MIFCONV/1.0`,
`sourceFormat`, `targetFormat`, `status` and `omitted`; it permits optional
`output`, `diagnostics` and `annotations`. Source and target format are exact
format signatures. Output is the target wire value. Diagnostics is a complete
MIFDIAG/1.0 object.

`omitted` is an ordered array of closed `{instancePath,reason}` objects.
`instancePath` is a JSON Pointer into a JSON source or the empty string for a
whole non-JSON source; reason is an identifier. Entries sort by
instancePath, then reason.

Status is exactly `lossless`, `lossy-history`,
`lossy-semantic-state`, `requires-ruleset-resolution` or
`unrepresentable-under-profile`.

`lossless` requires output and an empty omitted array. Both lossy statuses
require output, explicit caller acceptance and a non-empty omitted array.
The two requires/unrepresentable statuses forbid output. A failed conversion
has diagnostics; a successful conversion may have warnings there.

## 13.4 MIFINV/1.0

MIFINV is closed and contains:

| Member | Requirement |
|---|---|
| `format` | `MIFINV/1.0` |
| `profile` | `transform-invariance-v1` |
| `semanticDigest` | exact MRS semantic digest |
| `stateProfile` | exact state profile |
| `transformProfile` | exact transform profile |
| `transforms` | non-empty unique transform IDs in Annex A ordinal order |
| `extensionTreatments` | sorted closed records described below |
| `documentDigest` | declaration document digest |
| `annotations` | optional non-semantic object |

Each extension-treatment record contains exactly `profile` and
`treatmentProfile`, both identifiers, and sorts by profile. The treatment
profile completely defines forward and inverse transforms; an unknown
treatment fails closed. The document digest is SHA-256 over JCS after removing
only the documentDigest member, so annotations are included. A declaration
proves only its exact `(semanticDigest, transformProfile)` pair and listed
transform IDs.

## 13.5 MIFTURN/1.0

MIFTURN is closed and contains required `format=MIFTURN/1.0`,
`profile=logical-turn-v1`, `sourceResumptionDigest`, ordered `fragments`, and
optional annotations. Fragments are closed.

Fragment kind is `logical-turn`, `origin-obligation` or
`origin-stabilization`. Every fragment contains `kind`, ordered unique
`removeEventSeqs` and `status` (`complete` or `truncated`). A logical-turn
fragment additionally requires positive `primaryEventSeq`; origin kinds
forbid it. Sequence arrays preserve replay order.

Origin-stabilization is used when an obligation-free origin deterministically
creates board-full, stalemate or mill-count obligations. No primary event is
invented. MSTATE does not add `causedBySeq`.

## 13.6 MIFSUITE/1.0 shape

The future suite object is closed and contains exactly:

| Member | Shape |
|---|---|
| `format` | `MIFSUITE/1.0` |
| `id` | identifier |
| `components` | closed component object below |
| `profiles` | closed profile selection object below |
| `specifications` | non-empty sorted artifact records |
| `artifacts` | closed artifact-category object below |
| `rulesets` | sorted unique semantic-digest array |
| `invarianceDeclarations` | sorted unique MIFINV document-digest array |
| `compatibilityPolicy` | identifier |
| `mediaTypes` | sorted closed `{format,value}` records |
| `fileExtensions` | sorted closed `{format,value}` records |
| `releaseManifest` | non-empty string identifier or location |

Components contains exactly `mfen`, `mpk`, `mifpos`, `mstate`, `mrs`,
`diagnostics`, `capabilities`, `conversion`, `invariance` and `logicalTurn`,
each holding its exact format signature. Profiles contains exactly
`semantics`, `semanticProjection`, `state`, `key`,
`repetitionProjection`, `observation`, `repetitionSummary`, `resumption`,
`decision`, `claimLifecycle`, `mpkBinding`, `transform` and `logicalTurn`;
each value is a non-empty sorted unique identifier array except singular
semantics, semanticProjection, state, repetitionProjection,
repetitionSummary, resumption, decision, claimLifecycle, mpkBinding,
transform and logicalTurn, which are identifier strings.

Every specification or artifact record contains exactly `id`, `sha256` and
optional `commit`; specification records require commit. `sha256` uses the
digest lexical form and hashes raw file bytes. Specifications sort by id.
Artifacts contains exactly arrays named
`registries`, `corpora`, `schemas`, `abnf`, `conversions`, `runners` and
`adapters`; every array is non-empty, and adapters contains at least two
independently implemented entries. Each sorts by artifact id. Media-type and
extension records sort by
format then value.

The suite digest is SHA-256 over suite JCS bytes and is published externally,
not inserted. This contract does not publish an actual suite object.

# 14 Full-state transforms and logical turns

## 14.1 Coordinate conversion

`mill24-full-state-v1` transforms every coordinate- or line-bearing value in
MFEN, MIFPOS, MSTATE, events, obligations, repetition observations,
resumption and decision state, logical turns, actions, principal variations,
`lm`, `ul` and semantic extensions.

Player-bound scalars, counters, event seq and offer references retain meaning.
Transformed MSTATE replays to transformed current under the same semantic
digest.

A non-null decision repetition root cannot be coordinate-transformed from the
root alone. The transformer shall receive the corresponding observation/count
map, obtained from the source MSTATE, resumption history or an integrity-checked
backing store; it transforms every observation, merges equal transformed
digests, caps counts and rebuilds the root. Without that material it reports
`insufficient-transform-history` and emits no transformed decision state.

## 14.2 Equivalence gate

Coordinate conversion is permitted when every value has a registered
transform. Decision normalization, training/PUCT/tablebase merging and claims
of equivalent MPK normalization additionally require a valid MIFINV for the
exact semantic digest and transform profile.

Absent a declaration, geometry alone does not establish rules equivalence.

## 14.3 Logical-turn projection

Replay origin and events in order. A place/move starts a logical turn.
Associate every later remove that resolves obligations causally generated by
that primary sequence, including stable-boundary obligations. Close after all
such obligations and deterministic processing. A terminal result caused by
that primary sequence is a complete logical turn. Mark `truncated` only when
the source ends with unresolved consequent obligations or an independent
terminal event interrupts the sequence.

An obligation already present at origin creates an origin-obligation fragment.
An obligation generated while stabilizing an obligation-free origin creates
an origin-stabilization fragment. Draw negotiation remains in MSTATE and is
not converted into primary/removal actions.

# 15 Normative 0.4-to-1.0 conversion

## 15.1 General

Conversion validates the complete 0.4 source and ruleset before emitting 1.0.
Source bytes are never reinterpreted in place. Repair and policy selection are
explicit MIFCONV results.

## 15.2 Required mappings

| 0.4 construct | 1.0 behaviour |
|---|---|
| `first-player-loses` | `white-loses` |
| `first-then-second-remove` | `white-then-black-remove` |
| `second-then-first-remove` | `black-then-white-remove` |
| `legal-state-v1` | resolved `repetition-observation-v1` |
| full-manifest digest | source document identity only; recompute both target digests |
| MSTATE with manifest | portable envelope |
| MSTATE without manifest | reference envelope, or resolve before portable export |
| MPK without resolvable manifest | `requires-ruleset-resolution` |

A 0.4 manifest whose reachable placing state can have no legal primary action
requires an explicit 1.0 liveness policy. Without one it is
`unrepresentable-under-profile`. Selecting loss/draw/board-full where 0.4
would remain stuck is `lossy-semantic-state`.

`stable-moving-v1` retains its moving-only meaning. Changing to
`stable-primary-decision-v1` changes repetition semantics and requires an
explicit target ruleset version.

## 15.3 Mandatory rejection

Do not silently upgrade:

- a claim-draw performed while a 0.4 removal obligation was pending;
- an unknown semantic extension;
- ownerless delayed material;
- missing per-player used-line history;
- missing ruleset semantics needed for MPK or identity; or
- transform equivalence without MIFINV.

# 16 Parsing, errors, security and lifecycle

## 16.1 Validation order

Validate byte/resource limits, grammar/I-JSON, duplicate names, signature and
canonical form, profile support, ruleset/digests, structural consistency,
semantic consistency, replay/checkpoints and optional reachability.

Later validation never reinterprets an earlier invalid token.

## 16.2 Standard error codes

Required codes include:

`duplicate-member-after-unescape`, `duplicate-extension`,
`extension-order`, `integer-out-of-range`, `unsupported-profile`,
`manifest-missing`,
`manifest-conflict`, `semantic-digest-mismatch`,
`document-digest-mismatch`, `mpk-semantic-digest-missing`,
`transform-invariance-undeclared`,
`required-semantic-state-missing`, `remove-without-obligation`,
`side-obligation-actor-mismatch`, `obligation-target-mismatch`,
`claim-right-unavailable`, `claim-during-obligation`,
`insufficient-resumption-history`, `insufficient-transform-history`,
`repetition-observation-digest-collision`,
`no-legal-primary-action-policy-invalid`, `checkpoint-mismatch`,
`repetition-history-mismatch`, `claims-mismatch`,
`automatic-terminal-ongoing` and `unstabilized-boundary`.

## 16.3 Security and limits

Parsing never executes code, loads libraries, opens input-named paths,
contacts a network, installs plugins or establishes publisher trust.

Implementations publish limits through MIFCAP. Exceeding a limit produces a
resource diagnostic, never truncated semantic state.

Recommended general limits are 4 KiB MFEN/MPK, 1 MiB MRS/MIFPOS, 8 MiB
MSTATE, JSON depth 64, 100000 events, 100000 repetition entries and 256 text
extensions.

## 16.4 1.x lifecycle

Metadata-only MRS changes produce a new documentDigest without changing
semanticDigest. Gameplay changes require a new ruleset version and semantic
digest. Additive syntax uses a separately identified 1.x signature/profile
only when existing bytes retain meaning.

Changing existing canonical form, digest projection, required members,
default meaning, fail-closed behaviour or token meaning requires 2.0.

No media type, official extension, license grant or signature mechanism is
assigned by this wire contract. The final suite binds those release choices.

# Annex A (normative): topology and registries

## A.1 Point order

| Index | Coordinate | Index | Coordinate | Index | Coordinate |
|---:|---|---:|---|---:|---|
| 0 | a7 | 8 | b6 | 16 | c5 |
| 1 | d7 | 9 | d6 | 17 | d5 |
| 2 | g7 | 10 | f6 | 18 | e5 |
| 3 | g4 | 11 | f4 | 19 | e4 |
| 4 | g1 | 12 | f2 | 20 | e3 |
| 5 | d1 | 13 | d2 | 21 | d3 |
| 6 | a1 | 14 | b2 | 22 | c3 |
| 7 | a4 | 15 | b4 | 23 | c4 |

Ring neighbours wrap. Orthogonal cross-ring edges are
`d7-d6 d6-d5 g4-f4 f4-e4 d1-d2 d2-d3 a4-b4 b4-c4`.
The diagonal topology additionally has
`a7-b6 b6-c5 g7-f6 f6-e5 g1-f2 f2-e3 a1-b2 b2-c3`.

## A.2 Line IDs

| ID | Triple | ID | Triple |
|---:|---|---:|---|
| 0 | a7,d7,g7 | 10 | e3,d3,c3 |
| 1 | g7,g4,g1 | 11 | c3,c4,c5 |
| 2 | g1,d1,a1 | 12 | d7,d6,d5 |
| 3 | a1,a4,a7 | 13 | g4,f4,e4 |
| 4 | b6,d6,f6 | 14 | d1,d2,d3 |
| 5 | f6,f4,f2 | 15 | a4,b4,c4 |
| 6 | f2,d2,b2 | 16 | a7,b6,c5 |
| 7 | b2,b4,b6 | 17 | g7,f6,e5 |
| 8 | c5,d5,e5 | 18 | g1,f2,e3 |
| 9 | e5,e4,e3 | 19 | a1,b2,c3 |

Orthogonal uses 0–15; diagonal uses 0–19.

## A.3 Transform order

| Ordinal | ID | Mapping |
|---:|---|---|
| 0 | i | (x,y)→(x,y) |
| 1 | r90ccw | (x,y)→(-y,x) |
| 2 | r180 | (x,y)→(-x,-y) |
| 3 | r90cw | (x,y)→(y,-x) |
| 4 | mirror-v | (x,y)→(-x,y) |
| 5 | mirror-h | (x,y)→(x,-y) |
| 6 | mirror-main | (x,y)→(y,x) |
| 7 | mirror-anti | (x,y)→(-y,-x) |

Files a..g map to -3..3 and ranks 1..7 map to -3..3.

Outer/inner exchange pairs are
`a7-c5 d7-d5 g7-e5 g4-e4 g1-e3 d1-d3 a1-c3 a4-c4`; middle points are fixed.

## A.4 Cause and outcome registries

Cause order is leap, intervention, custodian, mill, mill-count, stalemate,
board-full.

Standard outcome reasons are:

- `fewer-than-minimum`: win or draw;
- `no-legal-move`: win or draw;
- `no-legal-primary-action`: win or draw;
- `board-full`: win or draw;
- `no-progress`, `repetition`, `agreement`: draw;
- `resignation`: win; and
- `adjudication`: win or draw.

# Annex B (normative): inline ABNF

```abnf
mfen = %s"MFEN/1.0" SP state-profile SP board SP side
       SP phase SP action SP hands SP obligations SP no-progress
       SP primary-ply SP outcome *(SP extension)

mpk = %s"MPK/1.0" SP state-profile SP ruleset SP digest
      SP key-profile SP mpk-board SP player SP active-phase SP hands
      *(SP key-extension)

state-profile = identifier
key-profile = identifier
ruleset = identifier %s"@" positive-integer
digest = %s"sha256:" 64lc-hex

identifier = id-start *62id-character
id-start = lc-alpha / DIGIT
id-character = lc-alpha / DIGIT / %s"." / %s"-"
private-identifier = %s"x-" id-start *60id-character

board = ring %s"/" ring %s"/" ring
ring = 8piece
mpk-board = 24piece
piece = %s"W" / %s"B" / %s"." / %s"w" / %s"b"

side = player / %s"-"
player = %s"w" / %s"b"
phase = active-phase / %s"o"
active-phase = %s"p" / %s"m"
action = %s"p" / %s"m" / %s"r" / %s"o"

hands = uint %s"," uint
no-progress = uint
primary-ply = uint

obligations = %s"-" / obligation-branches
obligation-branches = obligation-branch *(%s"|" obligation-branch)
obligation-branch = obligation *(%s";" obligation)
obligation = player %s":" cause %s":" target-zone %s":" player
             %s":" positive-integer %s":" target-spec %s":" after

cause = %s"leap" / %s"intervention" / %s"custodian" /
        %s"mill" / %s"mill-count" / %s"stalemate" /
        %s"board-full"
target-zone = %s"b" / %s"h"
target-spec = hex24 / %s"-" / %s"~"
after = player / %s"q"

outcome = %s"-" / result %s":" reason
result = %s"w" / %s"b" / %s"d"
reason = standard-reason / private-identifier
standard-reason = %s"fewer-than-minimum" / %s"no-legal-move" /
                  %s"no-legal-primary-action" / %s"board-full" /
                  %s"no-progress" / %s"repetition" /
                  %s"agreement" / %s"resignation" /
                  %s"adjudication"

extension = extension-key %s"=" *value-character
key-extension = extension
extension-key = standard-extension-key / private-identifier
standard-extension-key = %s"lm" / %s"pc" / %s"ul"
value-character = %x21-3C / %x3E-7E

; Registered extension-value subgrammars. Semantic validation binds each
; standard key to its corresponding grammar.
lm-value = coord-or-dash %s"," coord-or-dash %s";"
           coord-or-dash %s"," coord-or-dash
pc-value = uint %s"," uint
ul-value = line-bitset %s"," line-bitset
line-bitset = 4lc-hex / 5lc-hex

hex24 = 6lc-hex
coord-or-dash = coord / %s"-"
coord = %s"a7" / %s"d7" / %s"g7" / %s"g4" /
        %s"g1" / %s"d1" / %s"a1" / %s"a4" /
        %s"b6" / %s"d6" / %s"f6" / %s"f4" /
        %s"f2" / %s"d2" / %s"b2" / %s"b4" /
        %s"c5" / %s"d5" / %s"e5" / %s"e4" /
        %s"e3" / %s"d3" / %s"c3" / %s"c4"

uint = %s"0" / positive-integer
positive-integer = nonzero-digit *DIGIT
nonzero-digit = %x31-39
lc-hex = DIGIT / %x61-66
lc-alpha = %x61-7A
```

# Annex C (normative): freeze examples

## C.1 Initial player

For the C.2 manifest, whose `turn.initial` is `b`, the canonical empty origin
is:

```text
MFEN/1.0 mill24-state-v1 ......../......../........ b p p 9,9 - 0 0 -
```

Changing only `turn.initial` to `w` changes the side field to `w`; it does not
rename player identity. Under `white-loses`, either origin eventually resolves
a full-board terminal result as `b:board-full`.

## C.2 Digest domains

This is the complete JCS form of fixture document D1:

```json
{"boardFull":{"action":"disabled"},"captures":{"custodian":{"enabled":false,"lines":{"cross":false,"diagonal":false,"squareEdges":false},"maximumOwnLivePieces":null,"phases":["moving"]},"intervention":{"enabled":false,"lines":{"cross":false,"diagonal":false,"squareEdges":false},"maximumOwnLivePieces":null,"phases":["moving"]},"leap":{"enabled":false,"lines":{"cross":false,"diagonal":false,"squareEdges":false},"maximumOwnLivePieces":null,"phases":["moving"]},"resolution":"target-commits-v1"},"draw":{"claimRights":{"profile":"stable-claim-rights-v1"},"noProgress":{"countedPrimaryActions":["move"],"endgameLimit":0,"endgamePredicate":"none","evaluationBoundary":"stable-after-primary-sequence-v1","mode":"automatic","normalLimit":0,"resetEvents":["board-remove"]},"offers":{"expiry":"explicit-only"},"repetition":{"count":3,"mode":"claim","observation":"stable-primary-decision-v1","projection":"repetition-observation-v1","resetEvents":["board-remove"],"summary":"reset-count-smt-v1"}},"flying":{"enabled":true,"maximumLive":3},"format":"MRS/1.0","id":"example-morris","mills":{"delayedClearBoundary":"on-enter-moving-v1","lineReuse":"unlimited","movingEffect":"remove-opponent-board","placingEffect":"remove-opponent-board","removalMultiplicity":"one-per-primary","reverseReformation":"allowed","targetProtection":"outside-mill-first"},"pieces":{"black":9,"minimumLive":3,"white":9},"placing":{"earlyStop":{"boundary":"after-unobligated-place-v1","emptyPoints":0},"movementAllowed":false,"noLegalPrimaryAction":"loss"},"semanticState":[],"semanticsProfile":"mif-finite-rules-v3","stalemate":{"action":"loss","boardRemovalTargets":"adjacent-opponent"},"status":"fixture","title":"Example Morris","topology":"mill24-orthogonal-v1","turn":{"initial":"b","placingEndActivePlayer":"retain"},"version":1}
```

Its complete `mrs-semantic-v1` JCS projection is:

```json
{"boardFull":{"action":"disabled"},"captures":{"custodian":{"enabled":false},"intervention":{"enabled":false},"leap":{"enabled":false},"resolution":"target-commits-v1"},"draw":{"claimRights":{"profile":"stable-claim-rights-v1"},"noProgress":{"enabled":false},"offers":{"expiry":"explicit-only"},"repetition":{"count":3,"mode":"claim","observation":"stable-primary-decision-v1","projection":"repetition-observation-v1","resetEvents":["board-remove"],"summary":"reset-count-smt-v1"}},"flying":{"enabled":true,"maximumLive":3},"mills":{"delayedClearBoundary":"on-enter-moving-v1","lineReuse":"unlimited","movingEffect":"remove-opponent-board","placingEffect":"remove-opponent-board","removalMultiplicity":"one-per-primary","reverseReformation":"allowed","targetProtection":"outside-mill-first"},"pieces":{"black":9,"minimumLive":3,"white":9},"placing":{"earlyStop":{"emptyPoints":0},"movementAllowed":false,"noLegalPrimaryAction":"loss"},"profile":"mrs-semantic-v1","semanticState":[],"semanticsProfile":"mif-finite-rules-v3","stalemate":{"action":"loss","boardRemovalTargets":"adjacent-opponent"},"topology":"mill24-orthogonal-v1","turn":{"initial":"b","placingEndActivePlayer":"retain"}}
```

Expected digests are:

```text
semanticDigest = sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393
documentDigest(D1) = sha256:62479b6f40efb8ab478bab3d2b725647213604fcd3cc9cd4c1f69357535ae257
```

D2 is D1 with the single exact replacement `"title":"Example Morris"` by
`"title":"Example Morris (retitled)"`. D2 has the same semanticDigest and:

```text
documentDigest(D2) = sha256:60b8f91214e2273a0f7eb411794ce3b133c61653b2199763ab555d90f042e6e4
```

Changing `placing.noLegalPrimaryAction` changes both digests. Adding an unknown
semantic extension yields an unsupported-profile error and no digest.

## C.3 Decision versus resumption

For the C.2 semantics and C.1 origin, the origin observation digest, canonical
empty tree root and one-occurrence tree root are:

```text
observationDigest = sha256:6adc3718c5b16999b2a75b444728656e9901b003b8ff641813d73b2cdcba1e4e
emptyRoot = sha256:e9fbf966ccdff764594a5e199e6aea0cc36034b46c8057cc3df88a088c20101a
oneOccurrenceRoot = sha256:3a08cdfcc2a0be8a7fd9277649ff0a2e2b30cb20b98d808f825594c9a31aa885
```

After Black opens a draw offer, the decision object JCS is:

```json
{"action":"p","board":"......../......../........","claimRights":null,"hands":[9,9],"noProgress":null,"obligations":"-","openOffer":{"available":[{"action":"accept","actor":"w"},{"action":"decline","actor":"w"},{"action":"withdraw","actor":"b"}],"offerer":"b"},"outcome":"-","phase":"p","profile":"decision-state-v1","repetitionSummary":{"profile":"reset-count-smt-v1","root":"sha256:3a08cdfcc2a0be8a7fd9277649ff0a2e2b30cb20b98d808f825594c9a31aa885"},"semantic":{},"semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","side":"b","stateProfile":"mill24-state-v1"}
```

Its decisionDigest is
`sha256:f25cfb5dae617feba90fc1cbd48fb5d526727c8a3fad65910400a72a03657d19`.

History R1 has one `offer-draw` event at sequence 1. History R2 has
`offer-draw(1)`, `withdraw-draw(2, offerEventSeq=1)` and `offer-draw(3)`.
Both have the same gameplay position, active repetition count and semantic
offer operations. Their resumption-object JCS values are:

```json
{"claimRights":null,"claims":[{"actor":"b","eventSeq":1,"kind":"draw-offer","source":"event","status":"open"}],"current":"MFEN/1.0 mill24-state-v1 ......../......../........ b p p 9,9 - 0 0 -","lastEventSeq":1,"openOffer":{"actor":"b","offerEventSeq":1,"source":"event"},"positionFormat":"MFEN/1.0","profile":"resumption-state-v1","repetitionHistory":[{"key":{"action":"p","board":"......../......../........","hands":[9,9],"phase":"p","profile":"repetition-observation-v1","semantic":{},"semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","side":"b","stateProfile":"mill24-state-v1"},"source":"origin"}],"replayPrefixDigest":"sha256:0c3c604aa2b0f9e3407ddaca90e411755f5689066e68faf9f0e709a58857c151","semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","stateProfile":"mill24-state-v1"}
```

```json
{"claimRights":null,"claims":[{"actor":"b","eventSeq":1,"kind":"draw-offer","resolvedEventSeq":2,"source":"event","status":"withdrawn"},{"actor":"b","eventSeq":3,"kind":"draw-offer","source":"event","status":"open"}],"current":"MFEN/1.0 mill24-state-v1 ......../......../........ b p p 9,9 - 0 0 -","lastEventSeq":3,"openOffer":{"actor":"b","offerEventSeq":3,"source":"event"},"positionFormat":"MFEN/1.0","profile":"resumption-state-v1","repetitionHistory":[{"key":{"action":"p","board":"......../......../........","hands":[9,9],"phase":"p","profile":"repetition-observation-v1","semantic":{},"semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","side":"b","stateProfile":"mill24-state-v1"},"source":"origin"}],"replayPrefixDigest":"sha256:d8a8d2e595c1d37ed7f69bd9dee19039d52a346fbf7a1a28076ccf00b14e791a","semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","stateProfile":"mill24-state-v1"}
```

Their resumption digests are respectively
`sha256:1abb022db99a0959d00c90ca5ba6a946b99d183c8a811e01f242ef081bf5d5b3`
and
`sha256:2f2188fe6beb34042bcf201644f262d25552a5a6263d2ba0de024aa917a83657`.
Thus their decisionDigest is equal while resumptionDigest is not.

Changing side, a legal removal target, claim rights, repetition root,
relevant no-progress or outcome changes decision state.

## C.4 MPK binding

The valid structural key for the C.1 position begins:

```text
MPK/1.0 mill24-state-v1 example-morris@1 sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393 structural-d4-v1 ........................ b p 9,9
```

Removing the digest is `mpk-semantic-digest-missing`. Replacing it with
`sha256:0000000000000000000000000000000000000000000000000000000000000000`
while resolving D1 is `semantic-digest-mismatch`. The altered record is not
the same textual key even before semantic resolution.

## C.5 Transform gate

Under Annex A `r90ccw`, `a7` maps to `a1`. A registered semantic extension
whose value names absolute reward point `a7` can therefore be coordinate
converted to `a1`. Without a MIFINV declaration for the exact C.2
semanticDigest and transform profile, the two states are not eligible for
decision, training, PUCT, tablebase or Aut16 equivalence merging.

## C.6 Placing liveness

With initial material 13 each, boardFull disabled and active White, this
stable input has no legal phase-p primary action:

```text
MFEN/1.0 mill24-state-v1 WBWBWBWB/BWBWBWBW/WBWBWBWB w p p 1,1 - 0 0 -
```

Policy loss produces:

```text
MFEN/1.0 mill24-state-v1 WBWBWBWB/BWBWBWBW/WBWBWBWB - o o 1,1 - 0 0 b:no-legal-primary-action
```

Policy draw instead produces `d:no-legal-primary-action`.
`apply-board-full` with boardFull disabled is a manifest error. No policy
emits the ongoing input unchanged.

## C.7 Repetition scope

With movementAllowed true, start from board
`W......./B......./........`, side/action `w p`, and non-zero hands. The legal
cycle `w:a7-a4`, `b:b6-b4`, `w:a4-a7`, `b:b4-b6` returns to the same phase-p
decision observation. `stable-primary-decision-v1` counts those stable
boundaries; `stable-moving-v1` counts none because phase remains p.
Capability output names the selected scope.

## C.8 Claim lifecycle

At a stable boundary with `{actor:"b",reasons:["repetition"]}`, event sequence
`offer-draw(1,b)`, `decline-draw(2,w,offerEventSeq=1)` leaves that right
unchanged. A subsequent successful place or move expires it immediately before
mutation. If the action creates a removal obligation, claimRights is null
through every remove; the next stable boundary derives a new object from the
then-current counters and repetition root. A claim event during that
obligation is `claim-during-obligation`.

## C.9 Origin stabilization

When an obligation-free origin deterministically creates an obligation whose
remove events are 1 and 2, its exact fragment is:

```json
{"kind":"origin-stabilization","removeEventSeqs":[1,2],"status":"complete"}
```

It has no primaryEventSeq. An origin that already carried the obligation uses
`origin-obligation`; neither case invents a primary event or `causedBySeq`.
