# MIF Community Working Draft 0.4

## Mill games — Interchange formats for positions, analysis keys and resumable game states

**26 July 2026**

### Community Working Draft

This document is an independent community working draft. It is not an ISO,
IEC, CEN, WMD or tournament-federation publication; it has not been approved,
endorsed or certified by any such organization; and it shall not be cited as
an International Standard.

The `0.x` format signatures in this draft are experimental. They may change
incompatibly after implementation and working-group review.

## Foreword

This working draft was prepared to support discussion between implementers of
Mill games, database authors, research projects, tournament-tool developers
and rules historians.

The verbal forms used in this document follow standards-writing convention:
`shall` indicates a requirement; `should` indicates a recommendation; `may`
indicates permission; and `can` indicates possibility or capability.

Annexes A to D are normative. Annexes E and F are informative.

## Introduction

Existing software commonly calls several different representations “FEN”:
a user-copyable position, an engine snapshot, a transposition key and a saved
game. Those objects do not have the same equivalence relation.

This draft therefore separates:

- **MFEN**, an exact instantaneous state under a caller-supplied ruleset
  context, including an unresolved removal;
- **MPK**, a profile-declared, symmetry-normalized structural analysis key;
- **MSTATE**, a resumable JSON game state with events, repetition observations
  and draw-claim history; and
- **MRS**, a canonical JSON ruleset manifest selecting finite mechanisms whose
  transitions are defined in this document.

This separation is intentional. An MPK is not a lossless save file. An MFEN
does not invent missing history. An MSTATE does not hide a supplementary
removal inside a primary action.

MFEN deliberately keeps ruleset identity outside its compact position line.
Semantic use of an MFEN therefore requires a caller to supply the complete,
versioned ruleset identity and resolve its manifest; informal names or single
letter labels are not ruleset identities.

The public point order is also separated from an engine's internal node
numbering. A conforming engine may retain any packed board or bitboard layout
and perform a 24-entry permutation only at an interchange boundary.

# 1 Scope

This document specifies:

a) a public coordinate, point, line and transformation model for 24-point Mill
boards;

b) MFEN/0.4, a canonical textual representation of an instantaneous state
under a caller-supplied ruleset context;

c) MPK/0.4, a canonical textual key for structural analysis under an explicit
key profile;

d) MSTATE/0.4, an I-JSON representation of an origin, an event sequence, a
current checkpoint, repetition observations and claims;

e) MRS/0.4, a canonical ruleset manifest that selects the finite rule
mechanisms defined in this edition; and

f) parsing, validation, canonicalization, error and conformance requirements.

This edition covers games played on the 24 points in Annex A with either:

- the standard Nine Men's Morris topology, which has the 16 orthogonal mill
  lines; or
- the diagonal variant topology, which adds four diagonal mill lines for a
  total of 20.

The quick diagram in A.2 makes the distinction visible; the registered
topology identifiers remain authoritative.

This document does not:

- declare that a named community or federation uses a particular ruleset;
- standardize tournament administration, clocks, ratings or pairing;
- require an engine to use the public point order internally;
- standardize an in-memory or binary database layout;
- make MPK sufficient for a dataset whose equivalence depends on state omitted
  by the selected key profile; or
- permit arbitrary rules to be described by combining unregistered Boolean
  switches.

# 2 Normative references

The following documents are normatively referenced. For dated references,
only the edition cited applies.

- [RFC 5234, *Augmented BNF for Syntax Specifications: ABNF*](https://www.rfc-editor.org/rfc/rfc5234.html).
- [RFC 7405, *Case-Sensitive String Support in ABNF*](https://www.rfc-editor.org/rfc/rfc7405.html).
- [RFC 8259, *The JavaScript Object Notation (JSON) Data Interchange Format*](https://www.rfc-editor.org/rfc/rfc8259.html).
- [RFC 7493, *The I-JSON Message Format*](https://www.rfc-editor.org/rfc/rfc7493.html).
- [RFC 8785, *JSON Canonicalization Scheme (JCS)*](https://www.rfc-editor.org/rfc/rfc8785.html).
- [FIPS PUB 180-4, *Secure Hash Standard (SHS)*, August 2015](https://csrc.nist.gov/pubs/fips/180-4/upd1/final).

# 3 Terms and definitions

For the purposes of this document, the following terms and definitions apply.

## 3.1 active player

player required to perform the next gameplay action

## 3.2 authoritative state

value that is serialized because future legal behaviour or exact resumption
can depend on it

## 3.3 canonical form

single permitted serialization of a given conforming data model

## 3.4 choice branch

one complete obligation sequence among alternatives in which selection of the
first target commits to that sequence and discards the other sequences

## 3.5 delayed-removal token

owner-preserving board marker for a removed piece whose visible token remains
blocked until a rules-defined clearing boundary

## 3.6 derived value

value that can be recomputed uniquely from authoritative state and the
identified ruleset

## 3.7 extension field

named field outside the fixed MFEN or MPK core

## 3.8 key profile

versioned definition of the MPK projection, transformation set and canonical
comparison

## 3.9 live piece

piece that occupies a point for movement, mill, capture and material rules

## 3.10 logical turn

primary action together with zero, one or more consequent supplementary
removals that shall be resolved before the next primary action

Note 1 to entry: A logical turn can cross serialized states. If its primary
action creates an obligation, that obligation is authoritative pending state
until every selected removal has been resolved and the deterministic
stable-boundary processing in 11.20 has completed.

## 3.11 obligation

authoritative requirement for a named actor to remove one or more targets
from a stated zone for a stated cause

Note 1 to entry: In ordinary Nine Men's Morris, forming a mill creates a
compulsory capture/removal obligation. An obligation is the pending
requirement; a removal is the state-changing action that resolves it.

## 3.12 primary action

placement or movement that increments `primary-ply`

## 3.13 ruleset

versioned gameplay semantics identified by an MRS manifest

## 3.14 stable position

ongoing position with no unresolved obligation

## 3.15 state profile

versioned definition of a position data model and its textual encodings

## 3.16 supplementary action

removal performed to resolve a capture/removal obligation and not counted as
a primary action

Note 1 to entry: This document uses *capture* for the rule mechanism or
entitlement and *removal* for the operation that changes board or hand state.
It does not replace either term globally.

# 4 Conformance

## 4.1 Conformance classes

An implementation may claim one or more of the following classes:

- MFEN producer;
- MFEN consumer;
- MPK producer;
- MPK consumer;
- MSTATE producer;
- MSTATE replayer;
- MRS producer;
- MRS resolver;
- MIF converter; and
- transformation-profile implementation.

A conformance claim shall list every supported format signature, state
profile, semantics profile, topology and key profile.

A `MIF converter` claim shall additionally list each supported source mapping,
target format and conversion status under 12.4.

## 4.2 Producers

A conforming producer shall:

a) emit the canonical form specified by this document;

b) emit every authoritative field required by the state and ruleset;

c) not substitute a derived estimate for missing authoritative state;

d) not emit an identifier whose semantics it does not implement; and

e) satisfy all applicable normative corpus vectors in Annex D.

## 4.3 Consumers and replayers

A conforming consumer or replayer shall:

a) validate syntax before semantic processing;

b) resolve and verify the state profile, the caller-supplied or enclosing
ruleset manifest and, when applicable, key profile;

c) reject inconsistent authoritative fields rather than silently repairing
them;

d) distinguish structural validity from reachability from a normal initial
position;

e) preserve understood private, non-semantic extensions as required by
Clause 13; and

f) satisfy all applicable normative corpus vectors.

## 4.4 Structural validity and reachability

An MFEN can be structurally valid but unreachable from a named initial
position. A consumer may provide a reachability check, but it shall report
`unreachable` separately from syntax, profile resolution and state
consistency.

## 4.5 Round trip

For every supported valid input, parsing followed by canonical serialization
shall produce the expected canonical output without loss of authoritative
state.

For MSTATE, replay of `origin` plus `events` shall produce `current`,
`repetitionHistory` and `claims` exactly as specified in Clause 9.

# 5 Common conventions and profile model

## 5.1 Character repertoire and case

MFEN and MPK shall contain US-ASCII only. Tokens are case-sensitive.

MSTATE and MRS shall be UTF-8 I-JSON. A byte order mark shall not be emitted.

## 5.2 Whitespace

MFEN and MPK shall use exactly one U+0020 SPACE between fields. Whitespace
shall not occur within a field. Leading and trailing whitespace is not part
of a record and shall not be emitted.

Transport framing, including a final CRLF, is outside the record syntax.

## 5.3 Integers

Textual integers shall use unsigned decimal notation without a leading zero,
except that zero shall be `0`.

Every exact integer in MFEN, MPK, MSTATE and MRS shall be in the inclusive
range:

```text
0 .. 9007199254740991
```

A producer shall not encode an integer outside that range as a JSON number.
An edition that requires a larger exact value shall define a decimal-string
member.

## 5.4 Players

`w` identifies White, the first player. `b` identifies Black, the second
player. Colour names do not imply a physical token colour.

## 5.5 Coordinates and bit sets

Coordinates and the public point order shall be as specified in Annex A.

A 24-point bit set shall be six lowercase hexadecimal digits. Bit `i` shall
refer to public point index `i`; bit 0 is the least-significant bit of the
numeric hexadecimal value. Leading zeroes shall be present.

A line bit set shall use the line IDs in Table A.2. It shall be four lowercase
hexadecimal digits for a 16-line topology and five for a 20-line topology.
Unused high bits shall be zero.

## 5.6 Identifiers

An identifier shall satisfy Annex C and shall be no longer than 63 ASCII
characters.

A ruleset reference shall have the form:

```text
<identifier>@<positive-integer>
```

Identifiers beginning `x-` are private or provisional. This draft's
conformance fixtures deliberately use `x-`; they do not reserve future public
names such as `nmm@1`.

## 5.7 Digests

A manifest digest shall be:

```text
sha256:<64 lowercase hexadecimal digits>
```

The digest input shall be the RFC 8785 JCS UTF-8 octets of the manifest object
itself. A containing `digest` member shall not be inserted into that manifest
object.

Manifest digests are envelope or transport metadata. MPK identifies a ruleset
by `id@version`; MFEN receives ruleset identity and manifest from its caller
or containing envelope. Neither text record repeats a manifest digest.

## 5.8 Authoritative and derived state

The following values are authoritative when applicable:

- board characters, including delayed-token ownership;
- active player, phase and action;
- direct hand counts;
- obligation branches, ordered records, remaining counts and target sets;
- no-progress count;
- primary-ply;
- outcome;
- every semantic extension declared by the ruleset;
- repetition observations and claim records in MSTATE; and
- the identified ruleset manifest.

Live on-board counts, empty-point count, current complete mill lines and
ordinary mobility are derived.

Historical placement count is **not** generally derived. In particular:

```text
placed != initial pieces - current hand
```

when a hand piece can be removed. Historical placement count is outside the
core state. If declared by `semanticState`, it shall be carried in `pc` and
updated only by successful placement events.

## 5.9 Independent identifiers

The following identifiers have independent versioning:

- ruleset: gameplay transitions;
- state profile: position fields and encoding;
- key profile: MPK projection and normalization; and
- format signature: outer wire grammar.

A change from D4 to a 16-transform MPK profile shall not require a ruleset
version change. A serialization-profile change shall not silently change game
rules.

# 6 `mill24-state-v1` state profile

## 6.1 General

`mill24-state-v1` is the state profile specified by this edition. It applies
to the 24 public points in Annex A.

The profile boundary includes the serialized board characters and their
behaviour below. Implementations may use different internal representations,
but shall preserve these distinctions at interchange boundaries.

Its ordered fields are:

1. board;
2. side;
3. phase;
4. action;
5. hands;
6. obligations;
7. no-progress;
8. primary-ply;
9. outcome; and
10. zero or more named semantic or private extensions.

## 6.2 Board

The board shall be three eight-character rings in this order:

```text
a7 d7 g7 g4 g1 d1 a1 a4 /
b6 d6 f6 f4 f2 d2 b2 b4 /
c5 d5 e5 e4 e3 d3 c3 c4
```

Spaces in that display are explanatory.

The characters shall have the meanings in Table 1.

**Table 1 — Board characters**

| Character | Meaning |
|---|---|
| `W` | live White piece |
| `B` | live Black piece |
| `.` | empty and available point |
| `w` | blocked delayed-removal token originally owned by White |
| `b` | blocked delayed-removal token originally owned by Black |

Table 1a summarizes the behaviour that shall be preserved by the profile.

**Table 1a — Derived board-character behaviour**

| Character | Occupies point | Available as destination | Can move | Forms mills | Removal target | Counts as live material |
|---|---:|---:|---:|---:|---:|---:|
| `W`, `B` | yes | no | yes, subject to rules | yes | yes, subject to rules and mill-capture protection | yes |
| `w`, `b` | yes | no | no | no | no | no |
| `.` | no | yes | no | no | no | no |

A lower-case token shall preserve the removed token's owner and shall clear
only at the boundary selected by the ruleset.

An ownerless legacy marker such as `X` has no direct representation. A
converter shall obtain its owner from authoritative data or report
`unrepresentable-under-profile` without emitting an apparently valid target.

## 6.3 Side, phase and action

`side` shall identify the actor required to perform the next gameplay action.
It shall be `-` only in a terminal state.

The phase values shall be:

| Value | Meaning |
|---|---|
| `p` | placing regime for the current rules transition |
| `m` | moving regime for the current rules transition |
| `o` | game over |

There is no `ready` phase. A normal initial position is phase `p` with
`primary-ply` zero.

The action values shall be:

| Value | Meaning |
|---|---|
| `p` | primary input in phase `p`; the ruleset can permit a placement, a movement or both |
| `m` | movement primary input in phase `m` |
| `r` | supplementary removal input |
| `o` | no gameplay input |

Phase and action are direct, separate state. Neither shall be omitted merely
because a common ruleset could derive it.

Examples of non-trivial valid combinations include:

- phase `p`, action `r`, active hand zero: the final placement created an
  unresolved removal;
- phase `m` while the opponent still has hand pieces: asymmetric hand
  depletion can make the active player move before the global placing
  boundary; and
- phase `p` in a ruleset that permits movement while placing.

The ordinary logical-turn flow is:

```text
primary action
    |
    +-- no obligation ----------------------+
    |                                      |
    +-- obligation pending -> removal --+   |
                             -> removal -+   |
                                         v   v
                          deterministic stable-boundary processing
                                         |
                                  next primary action
```

The pending states in that diagram have action `r`. A ruleset can produce
zero, one or multiple supplementary removals. The next primary action is not
available until the selected branch is exhausted and the stable-boundary
pipeline has run.

## 6.4 Hands, counters and outcome

`hands` shall contain the current White and Black **unplaced reserve** counts
(traditionally called pieces “in hand”). They are direct state and shall not
be reconstructed from placement history.

`no-progress` shall contain the current ruleset counter. A pending removal can
therefore preserve the counter value reached immediately after its causing
primary action; the later removal can reset it.

`primary-ply` shall count successful place and move events before the current
state. A remove event shall not increment it. The primary action that created
an unresolved obligation is already included.

`outcome` shall be `-` while the game is ongoing. A terminal outcome shall be
`w:<reason>`, `b:<reason>` or `d:<reason>`.

## 6.5 Obligations

The obligation field shall be `-` or one or more alternative obligation
branches. Vertical bar (`|`) separates branches. Semicolon (`;`) separates
successive obligations within one branch.

An obligation record is:

```text
actor:cause:zone:target-owner:remaining:targets:after
```

The components shall have the meanings in Table 2.

**Table 2 — Obligation components**

| Component | Values | Meaning |
|---|---|---|
| `actor` | `w`, `b` | player who shall perform the removal |
| `cause` | Annex B cause | mechanism that created the context |
| `zone` | `b`, `h` | board or hand |
| `target-owner` | `w`, `b` | owner of the removable token |
| `remaining` | positive integer | removals remaining in that record |
| `targets` | six-hex bit set, `-` or `~` | authoritative board-head targets, hand marker, or deferred non-head board targets |
| `after` | `w`, `b`, `q` | next primary player, or continue with the next obligation in the selected branch |

Order inside a branch is semantic. Branches are sorted by their first
obligation's canonical cause order from Table B.1 and then by their complete
US-ASCII serialization.

The first obligation in every branch shall have the same actor. `side` shall
equal that actor and `action` shall be `r`.

For a board obligation at the head of a branch:

- `zone` shall be `b`;
- `targets` shall be non-zero;
- every target bit shall currently contain a live piece owned by
  `target-owner`; and
- `remaining` shall not exceed the number of distinct removals the mechanism
  can still require.

For a later board obligation in the same branch, `targets` shall be `~`.
Its target set does not yet exist because preceding removals can change that
set. The `~` marker is an explicit deterministic deferral, not permission to
guess missing imported state. When the record becomes the branch head, 11.11
shall replace `~` with a concrete non-zero bit set before another event can
be accepted. A branch head shall never contain `~`.

For a hand obligation:

- `zone` shall be `h`;
- `targets` shall be `-`; and
- the target owner's hand shall be at least `remaining`.

An obligation whose `after` is `q` shall have another obligation after it in
the same branch. An obligation whose `after` is `w` or `b` shall be the last
obligation in its branch.

When the selected target belongs to more than one branch head, the first
branch in canonical order wins. The other branches are discarded. This rule
makes the imported state and the first removal deterministic.

## 6.6 Semantic extensions

The standard semantic extensions are listed in Table 3.

**Table 3 — Semantic extensions**

| Key | Semantic feature | Value |
|---|---|---|
| `lm` | `last-mill` | White `from,to`; Black `from,to`, using `-` for none |
| `pc` | `placement-count` | White and Black historical successful placements |
| `ul` | `used-lines` | per-player mill-line bit sets |

If `semanticState` declares a feature, its mapped extension shall occur even
when its value is zero or `-`.

`ul` records line IDs, not the union of points belonging to used lines. A
point union cannot distinguish all histories and shall not be used to
implement once-per-line semantics.

`pc` increments only on a successful `place` event. Removing a piece from a
hand or board does not decrement it.

## 6.7 State consistency

A conforming consumer shall enforce the following:

a) ongoing states have side `w` or `b`, phase `p` or `m`, outcome `-`;

b) terminal states have side `-`, phase `o`, action `o`, obligations `-` and a
non-empty outcome;

c) obligations `-` implies action `p` in phase `p` or action `m` in phase `m`;

d) non-empty obligations imply action `r`, and side equals every branch-head
actor;

e) the sum of a player's live pieces, delayed tokens and hand shall not exceed
that player's initial token count;

f) delayed tokens are permitted only by a ruleset selecting
`mark-opponent-board-until-moving`;

g) every semantic extension required by the manifest is present;

h) a standard semantic extension not declared by the manifest shall not
affect gameplay or legal-state equality;

i) duplicate extension keys are invalid;

j) extension keys are in ascending US-ASCII order;

k) values in authoritative fields are not changed to agree with derived
caches;

l) the caller-supplied ruleset context and locally resolved manifest agree on
ID and version, and any expected digest supplied by an envelope or caller
agrees with that manifest;

m) when an MFEN is consumed as an independent position, phase at an ongoing
stable boundary shall be synchronized with the active player under 11.12; and

n) when an MFEN is consumed as an independent position (not as an MSTATE
`origin` or `current` field), an ongoing stable-boundary MFEN shall be a fixed
point of every deterministic Clause 11 transition that can be evaluated from
that MFEN and its supplied ruleset context alone, excluding repetition.

Repetition is excluded from item (n) because an independent MFEN carries no
repetition history. If deterministic processing would make the state
terminal, reject it as `automatic-terminal-ongoing`. If deterministic
processing would instead clear tokens, create an obligation, change side or
otherwise leave a different ongoing state, reject it as
`unstabilized-boundary`.

An MSTATE `origin` may be ongoing before such processing. The replayer shall
apply 11.20 after seeding history and before events, and `current` shall then
carry the resulting terminal, pending or claimable state; see 9.12.

# 7 MFEN/0.4 — Instantaneous position

## 7.1 Purpose

MFEN/0.4 shall represent the exact instantaneous state defined by
`mill24-state-v1`. Its rules semantics come from a caller-supplied context. It
can represent stable positions and copyable mid-obligation positions.

MFEN does not include ruleset identity or version, a manifest digest, event
history, repetition observations, draw-offer history or provenance. Those
belong in the caller context or MSTATE. A context-free MFEN can be parsed
structurally but cannot be validated semantically.

Copying or storing an MFEN for later semantic use therefore requires its
complete `ruleset-id@version` context to be copied or stored alongside it.
Labels such as `g`, `r`, “German”, “Russian” or “English” are not substitutes
for a registered, versioned identity.

## 7.2 Syntax

The normative ABNF is in Annex C and in the machine-readable
`conformance/mif-0.4.abnf` file.

The field order is:

```text
MFEN/0.4 <state-profile> <board> <side> <phase> <action>
<hands> <obligations> <no-progress> <primary-ply> <outcome>
[<extension> ...]
```

The display wraps only for readability. An MFEN record is one logical line.

## 7.3 Canonical serialization

A producer shall:

- use the exact signature `MFEN/0.4`;
- use the Annex A board order;
- use lowercase hexadecimal;
- use the shortest permitted unsigned decimal integer;
- serialize a missing obligation and ongoing outcome as `-`;
- serialize each branch in semantic order and alternative branches in
  canonical order; and
- sort extension fields by key.

There shall be no duplicate extension key.

An empty private extension value is syntactically valid:

```text
x-note=
```

Whether such a value is meaningful is defined by its private specification.

## 7.4 Examples

The examples use caller-supplied provisional fixture manifests from the
conformance corpus. The contexts for 7.4.1 through 7.4.6 are, respectively,
`x-mif-fixture-nmm@2`, `x-mif-fixture-nmm@2`,
`x-mif-fixture-dooz@2`, `x-mif-fixture-delay@2` and
`x-mif-fixture-stateful@2`, and `x-mif-fixture-nmm@2`. These identities are
deliberately not repeated inside the MFEN records.

### 7.4.1 Initial position

```text
MFEN/0.4 mill24-state-v1 ......../......../........ w p p 9,9 - 0 0 -
```

### 7.4.2 Pending board removal

White has completed a primary placement. The board target set contains two
Black pieces, and Black is the next primary player after resolution.

```text
MFEN/0.4 mill24-state-v1 WWW...B./......B./........ w p r 6,7 w:mill:b:b:1:004040:b 0 5 -
```

This state shall not be silently converted to the post-removal state.

### 7.4.3 Pending hand removal

The hand count still shows Black's token because the supplementary hand
removal has not yet occurred. Removing an opponent reserve token after a mill
is a ruleset variant, not standard Nine Men's Morris; that is why this example
uses the diagonal `x-mif-fixture-dooz@2` fixture.

```text
MFEN/0.4 mill24-state-v1 WWW...../B......B/........ w p r 9,10 w:mill:h:b:1:-:b 0 5 -
```

After the explicit removal, Black's hand is 9. The state does not claim that
Black placed three tokens; historical placements are not inferable.

### 7.4.4 Delayed marker

The lower-case `b` is inactive, owner-preserving and blocked:

```text
MFEN/0.4 mill24-state-v1 WWW...../b......B/........ b p p 9,10 - 0 5 -
```

### 7.4.5 Choice branches and sequence-dependent fields

```text
MFEN/0.4 mill24-state-v1 BWBW.WB./.W.W..B./.W...... w p r 3,5 w:intervention:b:b:2:000005:b|w:custodian:b:b:1:000040:b|w:mill:b:b:1:004000:b 7 20 - lm=-,-;-,- ul=0000,0000
```

The first selected target commits to exactly one of the three branches.

### 7.4.6 Moving while the opponent still has reserve

White has no unplaced reserve and is therefore in phase `m`; Black still has
one reserve token and will be in phase `p` when Black becomes active. Phase is
synchronized with the active player, not inferred from the opponent's hand.

```text
MFEN/0.4 mill24-state-v1 WWW.BBB./......../........ w m m 0,1 - 0 17 -
```

## 7.5 Ruleset context and integrity metadata

MFEN carries neither ruleset identity nor manifest digest. Before semantic
validation, the caller shall supply:

```text
(ruleset id, ruleset version)
```

Both components are required. A bare regional, language or community label,
an unversioned ID, or a single-letter application code is insufficient.

The consumer shall query a caller-supplied local manifest resolver using that
identity. The consumer shall not access a network automatically. An
application may define a documented UI default, but that default is not part
of MFEN and shall not be inferred by a context-free interchange validator.
Such a UI shall expose the resolved full identity rather than presenting the
default as a fact encoded by MFEN.

An absent ruleset context or failure to locate its manifest is
`manifest-missing`. Multiple distinct local manifests claiming the same ID
and version are `manifest-conflict`. When an envelope or caller supplies an
expected digest, a supplied manifest whose JCS digest differs from it is
`manifest-digest-mismatch`.

MSTATE is the standard self-contained envelope for carrying a private
manifest and its digest with positions. Another transport may supply
equivalent integrity metadata, but that metadata is outside MFEN and does not
alter canonical MFEN serialization.

# 8 MPK/0.4 — Stable structural analysis key

## 8.1 Purpose and limits

MPK/0.4 provides a stable textual key for structural analysis under an
explicit key profile.

MPK deliberately omits:

- no-progress;
- primary-ply;
- repetition multiplicity and observation history;
- claims and draw offers;
- final result; and
- event provenance.

It is suitable for structural analysis datasets and for tablebase-like
datasets **only when the dataset's state equivalence is fully captured by the
selected key profile**.

## 8.2 Eligibility

An MFEN is eligible for the structural profiles in this edition only if:

a) it is structurally valid;

b) it is ongoing;

c) obligations is `-`;

d) action is `p` or `m`;

e) every semantic extension required by the ruleset is understood by the key
profile;

f) every private extension that affects legal play has a registered transform
under the key profile; and

g) the application does not treat omitted adjudication state as part of its
equivalence relation.

For `structural-aut16-v1`, the application shall additionally possess the
external ring-exchange-invariance declaration required by 8.4.2.

An unresolved removal is not eligible. A producer shall not complete it
automatically to obtain a key.

## 8.3 Syntax and projection

The normative ABNF is in Annex C.

```text
MPK/0.4 <state-profile> <ruleset> <key-profile> <board24>
<side> <phase> <hands> [<key-extension> ...]
```

`board24` is the three MFEN rings concatenated without `/`.

The projection shall contain:

- state profile;
- ruleset;
- key profile;
- board, including delayed tokens;
- side;
- phase;
- direct hands;
- every extension mapped from `semanticState`;
- any understood private semantic extension required by the key profile.

Unlike MFEN, MPK identifies a ruleset by ID and version so keys from different
rulesets do not collide. An MPK producer projecting an MFEN shall copy that
identity from the MFEN's caller-supplied context. MPK carries no manifest
digest; a dataset or containing envelope may bind its identity to a digest
outside the key.

MPK shall contain exactly the extensions selected by the key profile and by
the ruleset's semantic-state mapping for that key. A private non-semantic
extension shall not occur in MPK. A private semantic extension may occur only
when the key profile defines its projection, canonical representation,
point/line transform and comparison semantics.

Derived live counts shall not be repeated. Historical placement count occurs
only when `placement-count` is declared and `pc` is therefore semantic.

## 8.4 Registered key profiles

### 8.4.1 `structural-d4-v1`

This profile uses the eight visual geometric transforms in Table A.3. It does
not claim to be the complete topology automorphism group.

### 8.4.2 `structural-aut16-v1`

This profile uses the eight D4 transforms and the same eight transforms
composed with the outer/inner ring exchange in A.6.

The ring exchange preserves adjacency and all registered mill lines for both
topologies in this edition.

Graph preservation alone does not prove game-state equivalence. This profile
shall be used for a ruleset only when an external, versioned declaration
states that outer/inner ring exchange preserves every rule-relevant feature
of that resolved ruleset and dataset. The declaration is configuration or
dataset metadata, is bound to the complete ruleset identity and is not an MRS
field. A producer shall not infer it from topology alone.

A database using this profile shall record the profile ID and the identity or
version of that declaration in its metadata. This profile is not a
general-purpose transposition-table key unless the table's equality relation
has the same declared invariance.

## 8.5 Canonicalization algorithm

For each transform in the profile's ordered transform list, the producer
shall:

1. transform every board point;
2. transform each coordinate in `lm` and any registered coordinate
   extension;
3. transform every set bit in `ul` through the line permutation for the
   selected topology;
4. leave scalar colour-specific values such as hands and `pc` attached to
   their colours;
5. transform each understood private semantic extension according to its
   registration;
6. serialize the complete MPK candidate canonically; and
7. compare the candidate's US-ASCII octets lexicographically.

The lexicographically least complete candidate shall be the MPK.

If multiple transforms produce the same least candidate, the transform with
the lowest profile ordinal shall be selected for mapping moves and
coordinates back to the source frame.

Comparison shall not be performed on the board alone when a transformed
semantic extension is present.

## 8.6 Move and result coordinates

An application associating moves, principal variations or annotations with
an MPK shall record the selected transform or otherwise retain an invertible
frame mapping.

Coordinates stored with a normalized key are in the normalized frame.
Returning them directly as source-frame moves is an interoperability error.

Any line identifier associated with an MPK-normalized action, including
`interventionLine` on a place or move event, shall be transformed using the
selected topology's line permutation for the same selected transform.

## 8.7 Examples

A single White piece at source coordinate `d7` has source board:

```text
.W......................
```

Under `structural-d4-v1`, the least board places it at `a4`:

```text
MPK/0.4 mill24-state-v1 x-mif-fixture-nmm@2 structural-d4-v1 .......W................ b p 8,9
```

Under `structural-aut16-v1`, the ring exchange extends the orbit and the least
board places it at `c4`:

```text
MPK/0.4 mill24-state-v1 x-mif-fixture-nmm@2 structural-aut16-v1 .......................W b p 8,9
```

The Aut16 example assumes the versioned external fixture declaration recorded
by `MPK-VALID-0003`. These are intentionally different keys. A database
shall identify which key profile it uses.

Semantic state participates in the comparison. For the
`x-mif-fixture-stateful@2` source used by `MPK-VALID-0004`:

```text
MFEN/0.4 mill24-state-v1 W.W.W.../B.B.B.../........ w m m 0,0 - 4 18 - lm=d1,d7;-,- ul=0003,0000
```

the `r90cw` and `mirror-h` candidates have the same least board string, but
their transformed state differs:

| Transform | Board | `lm` | `ul` |
|---|---|---|---|
| `r90cw` | `..W.W.W...B.B.B.........` | `a4,g4;-,-` | `0006,0000` |
| `mirror-h` | `..W.W.W...B.B.B.........` | `d7,d1;-,-` | `0006,0000` |

Full-candidate comparison selects `r90cw`; comparing the board in isolation
would discard authoritative information.

# 9 MSTATE/0.4 — Resumable game state

## 9.1 Purpose

MSTATE/0.4 represents:

- an exact origin MFEN;
- an ordered sequence of user or adjudication events;
- the exact current MFEN checkpoint;
- the active repetition-observation window; and
- an auditable draw-offer and draw-claim record.

An MSTATE can end at a pending obligation. A user can therefore copy, paste
and resume an intermediate removal-selection state.

## 9.2 JSON, I-JSON and JCS

An MSTATE and every embedded MRS manifest shall conform to RFC 8259 and RFC
7493 I-JSON.

In addition:

a) object member names shall be unique after JSON escape decoding;

b) an unpaired Unicode surrogate shall be rejected;

c) exact integers shall satisfy 5.3;

d) strings shall not be Unicode-normalized during parsing, hashing or
serialization;

e) canonical MSTATE and manifest bytes shall use RFC 8785 JCS; and

f) a parser shall detect duplicate names before conversion to a map that could
discard them.

Pretty-printed JSON may be accepted as input. Canonical output and digest
input shall be JCS.

## 9.3 Required top-level members

An MSTATE object shall contain exactly the standard members in Table 4, plus
permitted `x-` members.

**Table 4 — MSTATE members**

| Member | Type | Meaning |
|---|---|---|
| `format` | string | `MSTATE/0.4` |
| `positionFormat` | string | format of `origin` and `current`; `MFEN/0.4` in this edition |
| `stateProfile` | string | state profile used by embedded positions |
| `ruleset` | object | ruleset identity, digest and optional or required manifest |
| `origin` | string | canonical starting MFEN |
| `events` | array | ordered event sequence |
| `current` | string | canonical replay checkpoint |
| `repetitionHistory` | array | ordered active repetition window |
| `preOriginClaims` | array | claim-audit seed at the origin boundary |
| `claims` | array | ordered offer and claim audit records |

`positionFormat` makes MSTATE versioning explicit. A future MSTATE edition can
support another position format without pretending that MSTATE and MFEN
versions are independent while silently hard-coding one another.

The state profile in `origin` and `current` shall match the top-level
`stateProfile` member. The top-level `ruleset` object supplies the ruleset
context for both positions; that identity is not repeated inside either MFEN.

## 9.4 Ruleset member and manifest envelope

The `ruleset` object shall contain:

- `id`;
- `version`;
- `digest`; and
- `manifest`, when required by this subclause.

For an `x-` ruleset, `manifest` shall be present. For a registered public
ruleset it may be omitted when the local resolver returns the exact
`(id, version, digest)` object.

When `manifest` is present:

- it shall conform to MRS/0.4;
- its `id` and `version` shall match the containing members;
- its JCS SHA-256 shall match `digest`; and
- it shall be used for replay only after successful validation.

A digest provides integrity identification, not authenticity or publisher
trust.

## 9.5 Event sequence and common requirements

Each event shall be an object with:

- `seq`, an integer;
- `actor`, `w`, `b` or `system`; and
- `type`, a registered event type.

An event shall contain exactly the standard members required or permitted for
its type, plus zero or more `x-` members. An `x-` member is non-semantic
metadata unless an external specification explicitly declares otherwise. A
producer shall not use an `x-` member to alter a standard event's gameplay
effect.

`events` is an ordered history, not a set. `seq` values shall be consecutive
integers beginning at 1. Array order shall equal `seq` order.

Events shall be applied one at a time. After each event, every deterministic
effect in Clause 11 shall be performed before the next event is validated.

Actor validation for gameplay events shall be type-specific:

- a `place` or `move` event actor shall equal `side`;
- a `remove` event actor shall equal `side` and every selected branch-head
  actor; and
- other player events shall satisfy the event-specific actor rules in 9.8.

`system` shall not perform `place`, `move`, `remove`, draw negotiation, claim
or resignation events.

Unknown unprefixed event types shall be rejected. An `x-` gameplay event shall
also be rejected unless:

a) an external semantic event specification is explicitly identified;

b) the consumer implements it; and

c) the ruleset authorizes it.

An unknown gameplay event shall never be ignored as if it were a
non-semantic private member.

## 9.6 Primary gameplay events

### 9.6.1 Place

```json
{"seq":1,"actor":"w","type":"place","at":"a7"}
```

`actor` shall be the active player. `at` shall be a legal, available point.
The event shall increment primary-ply and, when `placement-count` is semantic,
that player's `pc`.

When intervention capture is enabled for phase `p`, a place event may also
contain `interventionLine`, a Table A.2 line ID used by 11.7.2. Absence
selects the first raw candidate line. The member shall be present only when
the event creates more than one raw candidate and its value identifies a
candidate other than the first. Naming the default line is non-canonical;
naming a line outside the raw candidate set is invalid.

### 9.6.2 Move

```json
{"seq":19,"actor":"w","type":"move","from":"a7","to":"a4"}
```

`from` and `to` shall identify a legal movement under the current phase,
adjacency, flying, leap and repeated-mill rules. The event shall increment
primary-ply.

When intervention capture is enabled for the applicable phase, a move event
may contain `interventionLine` under the same rules as 9.6.1.

## 9.7 Remove event

A remove event shall have a structured `target`.

Board removal:

```json
{
  "seq": 6,
  "actor": "w",
  "type": "remove",
  "target": {
    "zone": "board",
    "at": "b6"
  }
}
```

Hand removal:

```json
{
  "seq": 6,
  "actor": "w",
  "type": "remove",
  "target": {
    "zone": "hand",
    "player": "b"
  }
}
```

The actor shall match every branch head. The target shall select a target in
one branch head.

For a board target, the target bit shall be set and the live owner shall match
the branch head. For a hand target, the branch head shall have zone `h`, its
target owner shall equal `player`, and `targets` shall be `-`.

The legacy shape `"at":"b6"` directly on the event is invalid.

A hand removal is not an automatic hidden side effect of `place`. The place
event creates the hand obligation; the remove event decrements the hand.

## 9.8 Draw, resignation and adjudication events

The standard non-board events are:

| Type | Actor | Required additional members | Effect |
|---|---|---|---|
| `offer-draw` | active player (`side`) | none | open an offer |
| `accept-draw` | non-offering player | `offerEventSeq` | terminal draw by agreement |
| `decline-draw` | non-offering player | `offerEventSeq` | close offer as declined |
| `withdraw-draw` | offerer | `offerEventSeq` | close offer as withdrawn |
| `claim-draw` | active player (`side`) | `reason` (`no-progress` or `repetition`) | accept only if the selected claim condition is currently satisfied |
| `resign` | `w` or `b` | none | opponent wins by resignation |
| `adjudicate` | `system` | `result`, `reason`, `authority` | terminal external adjudication |

Draw negotiation does not change side, phase, action, hands, obligations,
no-progress or primary-ply.

Actor rules for these events are independent of the place/move/remove side
match in 9.5:

- `offer-draw` and `claim-draw` shall be performed only by `side`;
- `accept-draw` and `decline-draw` shall be performed by the non-offering
  player and may therefore have `actor` unequal to `side`;
- `withdraw-draw` shall be performed by the offerer and may be performed
  while it is the opponent's turn;
- `resign` may be performed by either player in any ongoing state, including
  while a removal obligation is pending; and
- while a removal obligation is pending, `offer-draw`, `accept-draw`,
  `decline-draw`, `withdraw-draw` and `resign` remain permitted under the
  rules above; `claim-draw` remains restricted to `side` and to a satisfied
  claim condition.

An offer shall close as `expired` at the boundary selected by
`draw.offers.expiry`. `explicit-only` never expires it automatically.
`on-opponent-primary-action` expires it immediately before that opponent's
successful place or move is applied.

Every terminal transition other than `accept-draw` shall close every
still-open offer as `expired` immediately before terminal normalization.
Agreement acceptance records status `accepted` instead.

At most one offer shall be open. A new `offer-draw` while an offer is open is
invalid. An accept, decline or withdrawal shall reference that exact open
offer. The accepting or declining actor shall be the non-offering player; the
withdrawing actor shall be the offerer.

A `claim-draw` in `automatic` mode is invalid because the condition would
already have ended the game. In `claim` mode an unsatisfied claim is invalid;
it is not recorded as a failed gameplay event.

For `adjudicate`, `result` shall be `w`, `b` or `d`; `reason` shall satisfy
Annex B for that result; and `authority` shall be a non-empty string. The
result and reason become the terminal MFEN outcome.

`system` is restricted to `adjudicate`. It shall not place, move, remove,
offer, accept, decline, withdraw, claim or resign.

## 9.9 Mark-and-delay event effects

`mark-opponent-board-until-moving` does not introduce a `mark` event.

The ordinary structured board `remove` event is the player action. Its
ruleset-selected effect changes the target from `W` to `w`, or `B` to `b`.

Clearing lower-case tokens is a deterministic transition at
`on-enter-moving-v1`; it is not an event. A producer shall not insert a
`clear-mark` event.

## 9.10 Repetition history

### 9.10.1 General

`repetitionHistory` is the current ordered observation window. It is neither
an unordered set nor an array of implementation hashes.

Each entry shall contain:

- `source`, equal to `pre-origin`, `origin` or `event`;
- `eventSeq` when source is `event`; and
- `key`, a `legal-state-v1` object.

Leading `pre-origin` entries seed an imported history. They shall occur before
any `origin` or `event` entry. Their array order is chronological.

An `origin` entry is generated automatically when origin satisfies the
manifest's observation boundary. An `event` entry identifies the final event
of the primary sequence that reached the observed stable state.

### 9.10.2 `legal-state-v1` key

The key object shall contain:

- `stateProfile`;
- `ruleset`;
- `board`;
- `side`;
- `phase`;
- `action`;
- `hands`; and
- `semantic`, an object containing every extension mapped from
  `semanticState` and no other gameplay field.

The key excludes no-progress, primary-ply, outcome and claims. It is compared
as a semantic object; implementations may hash its JCS bytes internally but
shall not substitute an undocumented hash for the object in MSTATE.

### 9.10.3 Observation algorithm

For `stable-moving-v1`:

1. seed the window with leading `pre-origin` records;
2. when a listed reset event or deterministic trigger occurs, clear the
   active window before any subsequent observation;
3. do not observe a primary action while its obligation queue is non-empty;
4. finish every non-repetition deterministic transition through the stalemate
   step of 11.20;
5. if the resulting origin is ongoing, phase `m`, action `m` and obligations
   `-`, append one `origin` observation;
6. when a primary sequence first reaches such a final stable moving state,
   append one `event` observation and identify the event that closed the
   sequence;
7. if the occurrence count reaches the configured value, apply automatic or
   claim semantics; and
8. do not append another observation for the terminal mutation caused by the
   repetition decision.

An imported pending origin is not observed until its obligation closes and a
stable moving boundary is reached.

## 9.11 Pre-origin claim seed and claims array

`claims` is an audit projection of draw offers and accepted draw claims. It
shall be reconstructed during replay and compared to the supplied array.

`preOriginClaims` is a separate replay seed. Each seed record shall contain:

- `actor`;
- `kind`, equal to `draw-offer`;
- `status`, using the offer statuses below; and
- no `source`, `eventSeq` or `resolvedEventSeq`.

Its array order is chronological. At most one seed offer may have status
`open`.

Each `claims` record shall contain:

- `source`, equal to `pre-origin` or `event` (omitted `source` means `event`);
- `actor`;
- `eventSeq` when source is `event`;
- `kind`, `draw-offer` or `draw-claim`;
- `status`; and
- `resolvedEventSeq` when resolution occurred in a later event.

Offer status shall be one of `open`, `accepted`, `declined`, `withdrawn` or
`expired`. A valid draw claim has status `accepted`.

Replay shall copy every `preOriginClaims` seed record into the initial audit
in the same order and add `source=pre-origin`. The supplied `claims` array
shall begin with exactly one final projection for each seed record, followed
by event-sourced records. Seed values are origin-time state; `claims` values
are post-replay audit state.

A seed offer that is open at origin is referenced by a later `accept-draw`,
`decline-draw` or `withdraw-draw` event through reserved `offerEventSeq=0`.
When an event resolves it, the final projection shall contain that event's
`resolvedEventSeq`. When deterministic origin processing expires it before
event 1, the final projection has status `expired` and no
`resolvedEventSeq`.

Event-sourced records shall be in strictly increasing `eventSeq` order.
`eventSeq` is unique among event-sourced records. Multiple records of the
same kind are allowed when they refer to different events.

JCS does not reorder arrays; this ordering rule is therefore required for
semantic canonicalization.

## 9.12 Replay and checkpoint verification

A replayer shall:

1. validate I-JSON without discarding duplicate names;
2. resolve and verify the manifest;
3. parse and validate origin under 6.7 except items (m) and (n), which
   apply only to independent MFEN interchange;
4. take only leading `pre-origin` repetition entries as initial history;
5. initialize the claim audit from `preOriginClaims`;
6. when origin is ongoing and obligations is `-`, run the stable-boundary
   pipeline of 11.20 after seeding repetition history and claim audit,
   regardless of whether origin is a repetition-observation boundary;
7. apply each event and all deterministic transitions;
8. canonicalize the resulting MFEN;
9. compare it byte-for-byte with `current`;
10. compare the generated repetition array semantically with
    `repetitionHistory`; and
11. compare the generated claim audit semantically with `claims`.

An ongoing pending origin is not passed through 11.20 until its selected
obligation branch becomes empty. When an arbitrary origin directly enters the
global placing boundary and `turn.placingEndActivePlayer=retain`, retain means
the origin's current `side`.

A mismatch shall not be repaired. It shall be reported as
`checkpoint-mismatch`, `repetition-history-mismatch` or `claims-mismatch`.

The conformance corpus includes a self-contained private-manifest envelope
whose replay ends at a pending removal.

# 10 MRS/0.4 — Finite ruleset manifest

## 10.1 Design boundary

MRS/0.4 follows the finite-mechanism approach.

An MRS manifest is not a general rule language and is not a bag of
implementation switches. It selects only mechanisms whose complete
transitions, target sets, ordering and adjudication boundaries are defined in
Clause 11.

MRS selects mechanisms; it does not independently select their trigger or
terminal priority. Those priorities belong to the identified semantics
profile.

A private game with semantics outside those mechanisms requires a separately
identified semantics profile and specification. Merely adding an unknown
member to `mif-finite-rules-v2` does not make that game replayable by a
conforming implementation.

## 10.2 Required members

An MRS manifest shall be an I-JSON object containing the members in Table 5.

**Table 5 — MRS members**

| Member | Type | Meaning |
|---|---|---|
| `format` | string | `MRS/0.4` |
| `id` | string | ruleset identifier without `@version` |
| `version` | positive integer | gameplay semantics version |
| `title` | string | human-readable English title |
| `status` | string | `fixture`, `experimental`, `registered` or `deprecated` |
| `semanticsProfile` | string | `mif-finite-rules-v2` |
| `topology` | string | registered topology |
| `pieces` | object | initial material and loss threshold |
| `turn` | object | initial and placing-end control |
| `flying` | object | flying mechanism |
| `placing` | object | placing-regime mechanism |
| `mills` | object | mill formation consequences |
| `captures` | object | finite capture mechanisms |
| `boardFull` | object | full-board consequence |
| `stalemate` | object | no-legal-movement consequence |
| `draw` | object | no-progress, repetition and offer rules |
| `semanticState` | array | required sequence-dependent state features |

Evaluation weights, search settings, UI state, animation, notation style,
database packing and network locations shall not occur as gameplay semantics
in an MRS manifest.

## 10.3 Canonical arrays

JCS preserves array order. Every MRS array is therefore classified in Table
6.

**Table 6 — MRS array semantics**

| Array | Semantics | Canonical requirement |
|---|---|---|
| capture `phases` | set | unique, ascending US-ASCII |
| `countedPrimaryActions` | set | unique, ascending US-ASCII |
| draw `resetEvents` | set | unique, ascending US-ASCII |
| `semanticState` | set | unique, ascending US-ASCII |

An MRS/0.4 manifest has no order-sensitive mechanism array. Within
`mif-finite-rules-v2`, trigger and terminal priorities are profile policy,
not manifest choices and not a universal rule for every possible semantics
profile. A different priority requires a different identified semantics
profile; it shall not be encoded as an underspecified arbitrary MRS array.

## 10.4 Topology, pieces and turn

`topology` shall be:

- `mill24-orthogonal-v1`; or
- `mill24-diagonal-v1`.

`pieces` shall contain:

- `white`, the initial White token count;
- `black`, the initial Black token count; and
- `minimumLive`, the minimum of live pieces plus hand pieces required to
  remain in the game.

`turn` shall contain:

- `initial`, `w` or `b`; and
- `placingEndActivePlayer`, `w`, `b` or `retain`.

`retain` means the player selected by the immediately preceding primary
sequence remains active when the global placing boundary is crossed.

## 10.5 Flying and placing

The *placing regime* is the global interval before both unplaced reserves
reach zero (or early stop sets them to zero). During that interval, the active
player's phase is synchronized under 11.12; it can therefore be `m` when that
player's reserve is empty while the opponent still has reserve pieces.

`flying` shall contain:

- `enabled`, Boolean; and
- `maximumLive`, positive integer.

When enabled, a player in phase `m` with no more than `maximumLive` live
pieces may move a live piece to any `.` point. Delayed-token points are not
destinations.

For example, with `maximumLive=3`, an active player with three live pieces
may move to any empty point, while the same player with four live pieces
remains restricted to adjacency unless another mechanism applies.

`placing` shall contain:

- `movementAllowed`, Boolean; and
- `earlyStop`, an object containing `emptyPoints` and `boundary`.

`emptyPoints` zero disables early stop. A non-zero value is supported in this
edition only with:

```text
boundary = after-unobligated-place-v1
```

The exact boundary is specified in 11.12.

## 10.6 Mills object

`mills` shall contain:

- `placingEffect`;
- `movingEffect`;
- `removalMultiplicity`;
- `targetProtection`;
- `lineReuse`;
- `reverseReformation`; and
- `delayedClearBoundary`.

`placingEffect` shall be one of:

| Value | Meaning |
|---|---|
| `remove-opponent-board` | forming player removes opponent live board token |
| `remove-opponent-hand-change` | remove opponent hand tokens first, overflow to board, then opponent becomes primary player |
| `remove-opponent-hand-retain` | same target order, then forming player remains primary player |
| `opponent-remove-own-board` | opponent removes the opponent's own board token |
| `mark-opponent-board-until-moving` | board removal changes the target to a blocked lower-case token |
| `remove-by-current-mill-count-at-placing-end` | defer the special current-mill-count removal calculation to the global placing boundary |

`movingEffect` shall be `remove-opponent-board` in MRS/0.4.

`removalMultiplicity` shall be:

- `one-per-primary`; or
- `one-per-new-line`.

`targetProtection` shall be:

- `outside-mill-first`; or
- `all-opponent`.

`targetProtection` is the retained wire identifier for **mill-capture
protection**: whether an opponent token inside a complete mill is protected
while an outside token exists.

`lineReuse` shall be `unlimited` or `once-per-player`.

`reverseReformation` shall be `allowed` or `prohibit-immediate`.

`reverseReformation` is the retained wire identifier for **immediate
reversal reformation**, the move-away-and-immediately-back pattern specified
in 11.5.

`delayedClearBoundary` shall be `on-enter-moving-v1`. It shall remain present
even when the placing effect does not create delayed tokens.

## 10.7 Captures object

`captures` shall contain:

- `resolution`, equal to `target-commits-v1`;
- `custodian`;
- `intervention`; and
- `leap`.

Each capture mechanism object shall contain:

- `enabled`, Boolean;
- `lines`, with Boolean `squareEdges`, `cross` and `diagonal`;
- `phases`, a set containing `moving`, `placing` or both; and
- `maximumOwnLivePieces`, a positive integer or `null`.

The diagonal family is empty on `mill24-orthogonal-v1`, even when its Boolean
is true.

For custodian and intervention, `maximumOwnLivePieces` applies in phase `m`
only. For leap it applies in every listed phase. `null` means no material
limit.

Disabled mechanisms shall retain all members so a manifest has one canonical
shape, but their other values have no gameplay effect.

## 10.8 Board-full and stalemate objects

`boardFull.action` shall be:

- `disabled`;
- `first-player-loses`;
- `first-then-second-remove`;
- `second-then-first-remove`;
- `active-player-removes`; or
- `draw`.

`stalemate` shall contain:

- `action`; and
- `boardRemovalTargets`, equal to `adjacent-opponent`.

`stalemate.action` shall be:

- `loss`;
- `change-player`;
- `remove-and-retain`;
- `remove-and-change`;
- `draw`; or
- `both-remove`.

## 10.9 Draw object

`draw` shall contain `noProgress`, `repetition` and `offers`.

`noProgress` shall contain:

- `normalLimit`;
- `endgameLimit`;
- `endgamePredicate`;
- `mode`;
- `countedPrimaryActions`;
- `resetEvents`; and
- `evaluationBoundary`.

Limits are non-negative integers. Zero disables that selected limit.
`endgamePredicate` shall be `none` or
`either-player-live-equals-3`. `mode` shall be `automatic` or `claim`.
`evaluationBoundary` shall be `stable-after-primary-sequence-v1`.

The supported counted primary actions are `move` and `place`. The supported
reset occurrences are `board-remove`, `hand-remove`, `mill-formation` and
`place`. The first, second and fourth occur when the corresponding event's
physical mutation succeeds. `mill-formation` occurs when 11.4 detects at
least one usable new line, whether or not the resulting branch is later
selected.

`repetition` shall contain:

- `count`, zero or an integer not less than 2;
- `mode`, `automatic` or `claim`;
- `observation`, `stable-moving-v1`;
- `projection`, `legal-state-v1`; and
- `resetEvents`.

Count zero disables repetition. The reset-event values are the same as for
no-progress.

`offers.expiry` shall be `explicit-only` or
`on-opponent-primary-action`.

## 10.10 Semantic state

The supported semantic features and MFEN mappings are:

| Feature | Required extension | Update rule |
|---|---|---|
| `last-mill` | `lm` | 11.4 |
| `placement-count` | `pc` | successful place increments actor |
| `used-lines` | `ul` | 11.4 |

The following manifest implications shall hold:

- `lineReuse=once-per-player` requires `used-lines`;
- `reverseReformation=prohibit-immediate` requires `last-mill`;
- `placement-count`, when declared, is included in legal-state equality even
  if no other mechanism currently reads it.

Intervention line selection is primary-event context, not persistent position
state. A non-default selection is carried by `interventionLine` in the
causing `place` or `move` event and is fully consumed during that event.

No MRS/0.4 mechanism uses a point-union substitute for `used-lines`.

## 10.11 Manifest consistency constraints

In addition to type and value validation:

a) initial White and Black token counts and `minimumLive` shall be positive,
and `minimumLive` shall not exceed either initial token count;

b) enabled flying shall have `maximumLive` not less than `minimumLive`;

c) `opponent-remove-own-board` shall not be combined with a capture
mechanism enabled in phase `p`, because its mill branch is headed by the
opponent while a placing capture branch is headed by the primary actor,
violating the single branch-head actor invariant in 11.8;

d) `mark-opponent-board-until-moving` requires
`delayedClearBoundary=on-enter-moving-v1`;

e) the semantic-state implications in 10.10 shall hold;

f) `endgamePredicate=none` requires `endgameLimit=0`;

g) disabled repetition shall have count zero and shall not generate
observations; and

h) manifest set arrays shall satisfy Table 6 before JCS hashing; and

i) every enabled capture mechanism shall select at least one non-empty line
family for the chosen topology.

`remove-by-current-mill-count-at-placing-end` may be combined with capture
mechanisms enabled in phase `p`. Placing capture branches resolve during the
causing primary sequence; the deferred mill-count obligations are generated
later at the global placing boundary under 11.14.

# 11 `mif-finite-rules-v2` transition semantics

## 11.1 Initial state

Unless an application intentionally supplies another origin, the manifest's
normal initial state shall have:

- all points `.`;
- hands equal to `pieces.white,pieces.black`;
- side equal to `turn.initial`;
- phase `p`;
- action `p`;
- obligations `-`;
- no-progress zero;
- primary-ply zero;
- outcome `-`;
- required line and placement counters zero;
- `lm=-,-;-,-`.

## 11.2 Primary-event validation

A primary event is accepted only in an ongoing stable state.

For `place`:

- action shall be `p`;
- the actor shall have at least one hand token;
- the target shall be `.`;
- the hand is decremented; and
- a live actor piece is placed.

For `move`:

- action shall be `m`, or action `p` with
  `placing.movementAllowed=true`;
- `from` shall contain the actor's live piece;
- `to` shall be `.`;
- the movement shall be adjacent unless flying or an enabled leap applies;
  and
- the reverse-reformation rule shall permit it.

Primary-ply increments exactly once after successful physical mutation.
No-progress and `pc` are then updated as declared.

## 11.3 Trigger-detection order

After a successful place or move, triggers shall be detected from the
post-action board in this order:

1. leap capture for an endpoint-to-endpoint move;
2. newly formed usable mill lines through the destination;
3. intervention capture;
4. custodian capture.

This is a detection order. Branch construction and overlapping-target
resolution are specified in 11.8.

If leap has at least one legal target, leap is exclusive for that primary
action: mill, intervention and custodian branches are not generated. Detection
of a usable mill remains a semantic occurrence: 11.4 still updates `lm` and
`ul`, and `mill-formation` still resets no-progress when configured.
Leap exclusivity therefore suppresses competing removal branches, not the
mill occurrence or its configured no-progress reset.

## 11.4 Mill lines formed by an action

A line is newly formed by a primary action when:

- all three line points contain the actor's live pieces after the action;
- the destination belongs to the line; and
- the line is not filtered by `lineReuse`.

For `once-per-player`, a line whose bit is already set in that player's `ul`
is not usable. The other player's bit for the same line is independent.

`one-per-primary` yields one mill removal obligation when at least one usable
line exists. `one-per-new-line` yields one removal for each usable line.

For example, placing at `d7` on
`W.W...../.W....../.W......` forms both line 0
(`a7,d7,g7`) and line 12 (`d7,d6,d5`). With `one-per-primary` the
ordinary mill branch has remaining 1; with `one-per-new-line` it has
remaining 2, capped by available target material as in 11.9.

When usable lines trigger:

- their per-player `ul` bits are set when `used-lines` is semantic; and
- `lm` is set to the action's `from,to` for a move, or `-,to` for a placement,
  when `last-mill` is semantic.

After every successful primary action that forms no usable mill, clear the
actor's `lm` entry to `-,-` when `last-mill` is semantic. This applies to both
movement and placement.

## 11.5 Immediate reverse reformation

With `prohibit-immediate`, a proposed move `from -> to` is prohibited only
when all of the following hold:

a) that player's `lm` equals `to,from`;

b) the piece at `from` currently belongs to at least one usable complete mill;
and

c) vacating `from` and occupying `to` would form at least one usable mill.

With `once-per-player`, a line already used is not “usable” for this test.

## 11.6 Ordinary mill-removal targets

For `all-opponent`, the target set is every opponent live piece.

For `outside-mill-first`:

1. calculate the union of opponent live pieces belonging to any currently
   complete opponent mill;
2. if any opponent live piece lies outside that union, only outside pieces
   are targets; otherwise
3. every opponent live piece is a target.

Thus the protection is a preference, not immunity. If all opponent live
pieces are in complete mills—for example exactly `a7,d7,g7`—all three are
legal targets under step 3.

Delayed tokens and hand tokens are not board targets.

For `opponent-remove-own-board`, the target owner and actor are the opponent.
Every opponent live piece is a target; ordinary opponent-mill protection does
not apply to choosing one's own token.

## 11.7 Capture mechanisms

Capture mechanisms use the ordered line families in Table A.2.

### 11.7.1 Custodian

Custodian is triggered on a line `[a,m,b]` when the primary action ends at
`a` and the actor already occupies `b`, or ends at `b` and the actor already
occupies `a`, while `m` contains an opponent live piece.

All qualifying middle points are collected and filtered by ordinary
mill-removal protection. The branch has cause `custodian`, remaining 1 and
the resulting target set.

### 11.7.2 Intervention

Intervention is triggered when the primary action ends at middle point `m`
of `[a,m,b]` and both endpoints contain opponent live pieces.

Candidate raw lines are in Table A.2 order. If the causing primary event has
an `interventionLine`, that candidate line is selected. Otherwise the first
candidate line is selected.

Ordinary mill-removal protection is applied **after** line selection. If both
endpoints are filtered out, intervention does not trigger and the algorithm
shall not fall back to a later line.

The branch has cause `intervention`, remaining equal to the number of
surviving endpoints and targets equal to those endpoints. After the first of
two endpoints is removed, only the paired endpoint remains a target.

### 11.7.3 Leap

Leap applies to a move from one endpoint of `[a,m,b]` to the other endpoint
when:

- the destination is `.`;
- `m` contains an opponent live piece;
- the configured phase, line family and material limit permit leap; and
- the middle piece survives ordinary mill-removal protection.

The move and capture are still separate events. The move creates an exclusive
cause `leap` board-removal branch with remaining 1 and target `m`.

## 11.8 Branch construction and target commitment

If leap triggered, the only branch is leap.

Otherwise the implementation shall construct non-empty branches in canonical
cause order:

1. intervention;
2. custodian;
3. mill.

A capture branch ends with the opponent as the next primary player.

A mill branch uses 11.9 or 11.10 and can contain multiple semicolon-separated
obligations. Its final `after` is determined by the selected placing or
moving effect. Earlier obligations in that branch use `after=q`.

Every board obligation at a branch head is materialized with its current
target bit set. Every later board obligation is serialized with targets `~`
until 11.11 promotes it. Hand obligations always use `-`.

Every first branch obligation has the same actor, except combinations
prohibited by 10.11.

The state before a removal publishes all branches separated by `|`. The first
remove target selects the first matching branch in canonical order; every
other branch is discarded before applying the removal.

This target-commit rule is normative. Implementations shall not add counts
from alternative capture contexts as if all alternatives were sequential.

## 11.9 Placing mill effects

Let `R` be the mill removal multiplicity. For an ordinary mill board-removal
sequence created by this subclause or by 11.10, remaining shall equal
`min(R, number of live board tokens owned by the target owner)`. The current
head target set is still calculated under 11.6 and is recomputed after every
removal. A target set that expands after protection is recomputed therefore
remains available to the same sequence. A zero-count board obligation shall
not be created.

Mechanism-specific capture branches retain their own finite capacities:
intervention uses its surviving endpoints, and custodian and leap use their
selected target sets.

### 11.9.1 `remove-opponent-board`

Create one board obligation for the forming player against the opponent with
remaining capped as above and targets from 11.6. The opponent is the next
primary player. If remaining would be zero, create no mill branch for this
effect.

### 11.9.2 Hand-first effects

For `remove-opponent-hand-change` and
`remove-opponent-hand-retain`:

1. create a hand obligation for `min(R, opponent hand)`;
2. if `R` exceeds the opponent hand, append a board obligation for the
   remainder after the board-remaining cap above, using targets `~` while it
   follows the hand obligation;
3. omit a zero-count obligation; and
4. set the final next primary player to the opponent for `change` or the
   forming player for `retain`.

Every hand decrement is represented by a remove event. It is not performed
inside the causing place event.

### 11.9.3 `opponent-remove-own-board`

Create a board obligation whose actor and target owner are the opponent,
remaining is capped as above, and next primary player is the opponent. If
remaining would be zero, create no mill branch for this effect.

### 11.9.4 `mark-opponent-board-until-moving`

Construct the same target branch as `remove-opponent-board`.

When the remove event is applied, change the selected live opponent character
to its lower-case owner marker. The point becomes blocked and the live
material count decreases immediately.

### 11.9.5 Deferred current-mill-count effect

No immediate mill branch is generated during phase `p`. The special
calculation occurs only at the global placing boundary in 11.14.

## 11.10 Moving mill effect

In phase `m`, a usable mill creates a board-removal branch for the forming
player against the opponent. Remaining is capped as in 11.9. The opponent is
the next primary player after the branch. If remaining would be zero, create
no mill branch.

## 11.11 Resolving an obligation

After a remove target selects a branch:

1. discard every unselected branch;
2. apply the selected board or hand removal effect;
3. decrement `remaining`;
4. reset no-progress when the event is in `resetEvents`;
5. apply the immediate minimum-material test in 11.17;
6. if remaining is non-zero, recompute that mechanism's authoritative target
   set; if it is non-empty, keep action `r`, otherwise apply that constructor's
   zero-target fallback;
7. if the obligation is complete and another obligation follows in the
   selected branch, remove the completed item, set side to the next item's
   actor, materialize its board targets when they are `~`, and either keep
   action `r` when the set is non-empty or apply its zero-target fallback;
   otherwise
8. empty obligations, set side to the final `after` player, synchronize phase
   with that player under 11.12, and restart the stable-boundary pipeline at
   step 1.

For intervention with two removals, step 6 leaves only the paired endpoint.
For ordinary multiple mill removal, step 6 recomputes protection against the
new board. A `mill-count` or `board-full` obligation with no target is omitted
and deterministic processing continues. A `stalemate` obligation with no
target immediately makes its actor lose with reason `no-legal-move`.

If the material test ends the game, all remaining obligations are discarded
and the terminal state rules apply.

## 11.12 Primary sequence without an obligation

When branch construction produces no branch:

- side changes to the opponent, unless another selected finite effect says
  retain;
- phase is synchronized with the new actor;
- early stop is evaluated as specified below; and
- the stable-boundary pipeline continues.

Phase synchronization with an active player means:

- after the global placing boundary, phase is `m`;
- while the global placing regime continues, an actor with a hand token is in
  phase `p`;
- while that regime continues, an actor with no hand token is in phase `m`,
  even if the opponent still has hand tokens; and
- `movementAllowed=true` additionally permits movement as a primary event
  while action is `p`.

For `after-unobligated-place-v1`, early stop is tested only after a successful
place for which no branch was generated. If `emptyPoints` is non-zero and the
number of `.` points is no greater than it, both hands become zero and the
global placing boundary is entered.

It is not evaluated before an unresolved removal and is not retroactively
evaluated when that removal completes.

## 11.13 Global placing boundary and delayed clear

The global placing boundary occurs when both hands are zero or early stop sets
them to zero.

At the boundary:

1. phase becomes `m`;
2. every `w` and `b` delayed token is changed to `.`;
3. side is set from `turn.placingEndActivePlayer`, with `retain` preserving
   the player selected by the preceding sequence; and
4. deterministic processing continues with the deferred mill-count step of
   11.20. Action is not finalized until that pipeline reaches its last step.

The lower-case clear is deterministic and produces no MSTATE event.

For example, at the boundary the board fragment
`WWW...../b......B/........` becomes
`WWW...../.......B/........`: the delayed Black marker clears to an empty
point before later stable-boundary tests, without an additional remove event.

## 11.14 Removal by current mill count

At the global placing boundary, count the current complete live mill lines
for White (`Wm`) and Black (`Bm`). Delayed tokens do not participate.

The sequential removal quantities are:

| Condition | White removes | Black removes | Target ownership |
|---|---:|---:|---|
| `Wm=0`, `Bm=0` | 1 | 1 | each removes own token |
| `Wm>0`, `Bm=0` | 2 | 1 | opponent |
| `Bm>0`, `Wm=0` | 1 | 2 | opponent |
| `Wm=Bm>0` | `Wm` | `Bm` | opponent |
| `Wm>Bm>0` | `Bm+1` | `Bm` | opponent |
| `Bm>Wm>0` | `Wm` | `Wm+1` | opponent |

Cap each quantity by the current number of live board tokens owned by its
target owner, then omit every zero-count obligation. Build one branch from the
remaining White obligation followed by the remaining Black obligation. Its
cause is `mill-count`. The first uses `after=q` when the second exists. The
final next player is `turn.placingEndActivePlayer`, resolving `retain` to the
player selected before the boundary. A later board obligation uses targets
`~` until promoted.

Ordinary mill protection applies when removing an opponent. It does not apply
when removing one's own token. If no obligation survives the caps, continue
the pipeline without pausing.

## 11.15 Full-board transition

Full-board evaluation occurs at every ongoing stable boundary, in either
active phase, when obligations are empty and no point is `.`. It is not
restricted to the global placing boundary; this makes manifests whose total
initial material exceeds 24 deterministic instead of leaving a phase-`p`
player with no legal placement.

Actions are:

- `disabled`: no effect;
- `first-player-loses`: Black wins with reason `board-full`;
- `draw`: draw with reason `board-full`;
- `first-then-second-remove`: one White-removes-Black obligation followed by
  one Black-removes-White obligation with targets `~`, then White is active;
- `second-then-first-remove`: the reverse sequence, then Black is active; and
- `active-player-removes`: the current player removes one opponent token,
  then the opponent is active.

Board-full removal ignores stalemate adjacency filtering and uses ordinary
mill protection. Each requested removal is capped at one current live target.
A zero-target board-full obligation is omitted; if every requested obligation
is omitted, continue to the simultaneous minimum-material step. A later
zero-target obligation is omitted when promoted under 11.11.

## 11.16 Stalemate transition

Stalemate is evaluated only in an ongoing, stable phase-`m` position after
flying capability has been considered.

When the active player has no legal movement:

- `loss`: the opponent wins with reason `no-legal-move`;
- `draw`: draw with reason `no-legal-move`;
- `change-player`: side changes to the opponent at most once for the current
  stable-boundary evaluation, phase is synchronized with the new actor, and
  the pipeline restarts at step 1; if the stalemate step is reached again in
  phase `m` and the newly active player also has no legal movement, the game
  ends immediately as draw with reason `no-legal-move`;
- `remove-and-retain`: the stalemated player removes one adjacent opponent
  live piece and then remains active;
- `remove-and-change`: the stalemated player removes one adjacent opponent
  live piece and then the opponent is active; or
- `both-remove`: the stalemated player removes one adjacent opponent piece,
  then the opponent removes one adjacent piece whose targets are deferred as
  `~`, then the original stalemated player is active.

For these stalemate removals, a target is legal when it is an opponent live
piece adjacent to at least one live piece of the remover. Mill protection is
not applied. If the first target set is empty, the stalemated player loses
immediately with reason `no-legal-move`. If a deferred later stalemate
obligation materializes to an empty target set, that obligation's actor loses
with the same reason.

The one-change limit for `change-player` applies across restarts inside one
evaluation of the stable-boundary pipeline in 11.20. Implementations shall not
loop side changes until a movable player appears. If synchronization selects
phase `p`, stalemate is no longer applicable and no movement test is made for
that player.

## 11.17 Minimum material

Immediately after every board or hand removal, calculate for the affected
owner:

```text
live board pieces + hand pieces
```

Delayed tokens are already removed material and are excluded.

If the total is less than `minimumLive`, that owner loses immediately with
reason `fewer-than-minimum`. This test applies during placing as well as
moving. It does not wait for both hands to become zero.

If a player is ordered to remove that player's own token and falls below the
minimum, the other player wins.

At the stable-boundary minimum-material step, evaluate both players from the
same pre-step state. If exactly one player is below `minimumLive`, the other
player wins. If both are below it, the game is a draw with reason
`fewer-than-minimum`.

## 11.18 No-progress

After a successful primary event:

1. if its type is in `countedPrimaryActions`, increment no-progress;
2. if the primary event, a consequent removal event or a detected
   mill-formation occurrence is listed in `resetEvents`, reset it to zero;
3. preserve the intermediate value while obligations remain; and
4. evaluate only when the primary sequence becomes stable.

If `endgamePredicate=either-player-live-equals-3` and either player has
exactly three live board pieces, use `endgameLimit`; otherwise use
`normalLimit`.

A selected zero limit is disabled. At or above a non-zero limit:

- `automatic` ends the game as `d:no-progress`; or
- `claim` enables a valid `claim-draw` event but does not change MFEN by
  itself.

## 11.19 Repetition

Repetition observations and resets shall follow 9.10.

Equality shall be equality of every member of `legal-state-v1`, including all
declared semantic state. It shall not be equality of board alone.

At the configured occurrence count:

- `automatic` ends the game as `d:repetition`; or
- `claim` enables a valid `claim-draw` event.

## 11.20 Stable-boundary and terminal priority

Whenever an obligation queue becomes empty or a primary action creates no
obligation, deterministic processing shall use this order and stop at the
first terminal result:

1. enter the global placing boundary and clear delayed tokens, when due;
2. generate deferred mill-count obligations, when due;
3. evaluate full board;
4. evaluate minimum material for both players simultaneously;
5. evaluate stalemate, carrying the one-change guard across any pipeline
   restart as in 11.16;
6. perform repetition observation and automatic repetition adjudication;
7. evaluate automatic no-progress; and
8. set action from the resulting phase when still ongoing.

If step 2, 3 or 5 creates a non-empty obligation queue, side shall equal every
branch-head actor, action shall become `r`, and the pipeline shall pause
immediately. It resumes only after the selected branch becomes empty, and then
restarts at step 1. Constructor-specific zero-target rules in 11.14 to 11.16
are applied before a queue is exposed.

The immediate post-removal minimum test in 11.17 occurs before this
stable-boundary list. Stalemate precedes repetition so observations describe
the final non-terminal stable state after every deterministic side change.

An MSTATE replayer shall run this pipeline on every ongoing origin whose
obligations field is `-`, after origin validation and after seeding leading
`pre-origin` repetition history and `preOriginClaims`, before applying events.
Repetition observation inside the pipeline remains conditional on the
manifest's observation rule.

This ordering, together with the trigger order in 11.3 and branch commitment
in 11.8, is policy of `mif-finite-rules-v2` and is part of that profile's
rules semantics. MRS selects the mechanisms to which the policy applies; it
does not encode a priority list. An implementation shall not choose a
different priority while claiming this semantics profile and the same
manifest digest. Another semantics profile can specify another order without
making that order a universal MIF policy.

## 11.21 Outcome normalization

A terminal transition shall:

- set phase `o`;
- set action `o`;
- set side `-`;
- set obligations `-`;
- retain board, hands, counters and semantic extensions as post-event state;
  and
- set one outcome reason from Annex B.

# 12 Parsing, validation and errors

## 12.1 Validation order

A consumer should validate in this order:

1. byte encoding and resource limits;
2. lexical grammar or I-JSON;
3. duplicate names or extension keys;
4. format signature and canonical ordering;
5. state, semantics and key profile support;
6. manifest lookup and digest;
7. structural state consistency;
8. ruleset-specific semantic consistency;
9. replay and checkpoints; and
10. optional reachability.

Later validation shall not be used to reinterpret an earlier invalid token.

## 12.2 No silent inference

A consumer shall not:

- derive hand from initial count minus placement count;
- derive phase solely from hands or live material;
- derive primary-ply from side-to-move parity;
- complete an obligation;
- replace an obligation target set with a guessed set;
- convert an ownerless delayed marker to an arbitrary owner;
- reconstruct used mill lines from a point union;
- choose D4 or ring exchange without the declared key profile; or
- fetch a missing manifest from the network.

An application may offer an explicit repair or legacy-import mode, but its
output shall be identified as repaired or lossy and shall not be presented as
a lossless parse of the source.

## 12.3 Error categories

Errors shall be classified as:

| Category | Meaning |
|---|---|
| `syntax` | bytes, JSON or ABNF do not parse |
| `canonical` | data model can parse but wire ordering or spelling is not canonical |
| `unsupported` | required format, profile, ruleset or semantic event is unknown |
| `integrity` | digest or manifest identity fails |
| `inconsistent` | authoritative fields conflict |
| `ineligible` | valid state cannot be projected to requested MPK |
| `replay` | event, checkpoint, repetition or claims do not reproduce |
| `resource` | declared implementation limit or safe integer range is exceeded |
| `unreachable` | optional initial-position reachability failed |

The machine-readable corpus defines stable example codes, including:

- `duplicate-member-after-unescape`;
- `duplicate-extension`;
- `extension-order`;
- `integer-out-of-range`;
- `manifest-missing`;
- `manifest-conflict`;
- `manifest-digest-mismatch`;
- `ring-exchange-invariance-undeclared`;
- `required-semantic-state-missing`;
- `remove-without-obligation`;
- `side-obligation-actor-mismatch`;
- `mixed-obligation-actors`;
- `obligation-target-mismatch`;
- `intervention-line-not-candidate`;
- `redundant-intervention-line`;
- `unsupported-semantic-event`;
- `checkpoint-mismatch`;
- `repetition-history-mismatch`;
- `claims-mismatch`;
- `automatic-terminal-ongoing`;
- `unstabilized-boundary`; and
- `private-nonsemantic-extension`.

An implementation may add diagnostic detail but should retain the standard
category and applicable code.

## 12.4 Conversion status contract

A conforming `MIF converter` shall report exactly one of the statuses in
Table 7 for each requested conversion.

**Table 7 — Conversion statuses**

| Status | Meaning |
|---|---|
| `lossless` | every authoritative source value required for the target semantics is preserved |
| `lossy-history` | the instantaneous gameplay state is preserved, but event, repetition, claim, offer or provenance history is omitted |
| `lossy-semantic-state` | known sequence-dependent gameplay state cannot be preserved in the target |
| `requires-ruleset-resolution` | a complete versioned ruleset context must be resolved before representability can be decided |
| `unrepresentable-under-profile` | the selected target format or profile cannot represent required known state |

The report envelope and API are implementation-defined. The status names and
the behaviour below are normative; this edition does not add another wire
format.

The converter shall select the status in this order:

1. `requires-ruleset-resolution` when required ruleset identity or semantics
   are unresolved;
2. `unrepresentable-under-profile` when the resolved target cannot encode
   required known state;
3. `lossy-semantic-state` when conversion can emit a useful target only by
   omitting known sequence-dependent gameplay state;
4. `lossy-history` when only non-instantaneous history is omitted; otherwise
5. `lossless`.

For `requires-ruleset-resolution` and
`unrepresentable-under-profile`, the converter shall not emit an apparently
valid target record. For either lossy status, it shall identify the omitted
information and shall emit target output only after explicit caller
acceptance. It shall not label repaired, guessed or defaulted state as
`lossless`.

The normative conversion vectors cover an NMM_LLM atomic move-plus-capture,
a Sanmill ownerless delayed marker, absent `ul` history and absent ruleset
context.

# 13 Canonicalization, versioning, extensions and registration

## 13.1 Canonical equality

Canonical MFEN textual equality is byte equality of its US-ASCII records.
Because MFEN is not self-describing, semantic position equality additionally
requires the same caller-supplied ruleset ID and version.

Canonical MPK equality is byte equality of its US-ASCII records; MPK carries
its ruleset ID and version.

Canonical MSTATE and MRS equality is byte equality of their RFC 8785 JCS
UTF-8 octets after all semantic array-order requirements have been enforced.

JCS alone does not canonicalize sets represented as arrays. Clause 9 and Table
6 apply before JCS.

## 13.2 Draft format versions

The signatures in this edition are:

```text
MFEN/0.4
MPK/0.4
MSTATE/0.4
MRS/0.4
```

They are deliberately not the previously proposed `MFEN/2`, `MPK/1`,
`MSTATE/2` or `MRS/1`. No stable version is frozen by this working draft.

A producer shall emit only a signature it implements. A consumer shall not
interpret an unknown signature as the nearest known version.

This edition uses a closed lexical profile. The Annex C ABNF enumerates the
standard outcome reasons, standard extension keys and obligation causes.
Adding a new non-`x-` standard token requires a format or state-profile
upgrade. A registry entry alone shall not extend those closed enumerations.
Private `x-` identifiers remain the extension path for experiment.

Splitting MRS digests into a gameplay `semanticDigest` and a full-document
`documentDigest` is deferred beyond this edition.

## 13.3 Ruleset changes

A ruleset version shall change when gameplay behaviour can change, including
legal actions, trigger priority, targets, turn control, draw semantics or
terminal outcomes.

A ruleset version need not change solely because:

- another state profile can encode the same authoritative state;
- another MPK key profile is selected;
- a database changes binary packing; or
- informative metadata changes without changing the canonical manifest.

Because the canonical manifest includes title and status in this edition, a
publisher wishing to change those members without changing the gameplay
version shall publish a registry annotation rather than mutate the manifest
bytes.

## 13.4 Private extensions

A private identifier shall begin `x-`.

Unknown private object members and MFEN extensions that are explicitly
non-semantic may be retained and round-tripped. They shall not alter legal
actions, replay, outcome or a key. They shall not appear in MPK.

A private extension declared semantic by an external profile shall be
rejected by a consumer that does not implement that profile. It shall not be
ignored.

Unknown unprefixed members, extension keys and event types shall be rejected.

## 13.5 Registration policy

A public ruleset registration should require:

a) a canonical manifest and digest;

b) documented rules provenance and governance;

c) unambiguous examples for every non-default transition;

d) two independent implementations, or one implementation plus a complete
normative corpus pending a second implementation;

e) cross-implementation replay agreement;

f) settled repetition, no-progress and outcome semantics; and

g) no unresolved wire or key-profile question.

A fixture or experiment shall use `x-` until these conditions are met.

The provenance in item (b) shall identify a source or rule authority and a
source edition, date or version. Bare labels such as “German”, “Hungarian” or
“English” shall not be registered as authoritative ruleset identities because
they do not identify one fixed global rule. Such words may occur in a title
only when qualified by the actual authority and version.

State and key profiles shall be registered independently of rulesets.

## 13.6 Media types

No media type is registered by this working draft.

Future work may evaluate names such as:

```text
application/mill-state+json
application/mill-ruleset+json
application/mill-position
application/mill-position-key
```

Any registration shall follow BCP 13 as specified by RFC 6838 and updated by
RFC 9694. A JSON representation can use the `+json` structured syntax suffix
defined by RFC 6839.

# 14 Security and resource considerations

## 14.1 Untrusted input

All formats in this document shall be treated as untrusted input.

A parser or resolver shall not, as a consequence of parsing:

- execute script or native code;
- load a dynamic library named by the input;
- open arbitrary local paths;
- contact a network service;
- install a plugin; or
- trust a manifest publisher solely because a SHA-256 digest matches.

## 14.2 Resource limits

An implementation may impose documented limits on:

- MFEN and MPK byte length;
- JSON byte length and nesting depth;
- manifest string length;
- event count;
- repetition and claims count;
- replay work; and
- extension count and value length.

Recommended default acceptance limits for general applications are:

| Item | Recommended limit |
|---|---:|
| MFEN or MPK record | 4 KiB |
| MRS document | 1 MiB |
| MSTATE document | 8 MiB |
| JSON nesting | 64 |
| events | 100 000 |
| repetition entries | 100 000 |
| extensions in one text record | 256 |

Exceeding a local limit shall produce a `resource` error, not truncated
semantic state.

## 14.3 Replay complexity

A replayer should bound cumulative legal-action generation and event replay
work. Checkpoint comparison shall not be used as permission to skip event
validation.

The standard MPK profiles require at most 16 transformations of 24 points and
20 line bits per candidate. They do not require graph-isomorphism search at
runtime.

## 14.4 Hashes and authenticity

SHA-256 identifies canonical manifest bytes and detects accidental or
malicious substitution when an expected digest is already trusted. It does
not establish authorship, authority, tournament approval or safety.

Applications requiring authenticity should sign an outer envelope or obtain
the expected digest through a trusted registry.

## 14.5 Claim and adjudication injection

An untrusted MSTATE can contain resignation, claim or system adjudication
events. A user interface shall not present their result as authoritative
without showing provenance appropriate to the application.

# Annex A (normative)

## Mill24 coordinates, topology, lines and transformations

### A.1 Coordinate axes

Files `a` to `g` increase from left to right. Ranks `1` to `7` increase from
bottom to top.

For geometric transforms, the centre is `(0,0)`. Files map as
`a=-3`, `b=-2`, `c=-1`, `d=0`, `e=1`, `f=2`, `g=3`. Ranks map as
`1=-3`, `2=-2`, `3=-1`, `4=0`, `5=1`, `6=2`, `7=3`.

### A.2 Public point order

The standard 16-line topology is the familiar orthogonal board:

```text
a7-----------d7-----------g7
|             |             |
|   b6-------d6-------f6    |
|   |         |         |   |
|   |   c5---d5---e5    |   |
a4--b4--c4         e4--f4--g4
|   |   c3---d3---e3    |   |
|   |         |         |   |
|   b2-------d2-------f2    |
|             |             |
a1-----------d1-----------g1
```

The 20-line diagonal variant adds these four corner-to-inner chains:

```text
a7-b6-c5    g7-f6-e5    g1-f2-e3    a1-b2-c3
```

These diagrams are explanatory; the ordered tables below define coordinates,
adjacency and line IDs.

**Table A.1 — Point and bit order**

| Index | Coordinate | Ring | Ring position | `(x,y)` |
|---:|---|---|---:|---|
| 0 | `a7` | outer | 0 | `(-3,3)` |
| 1 | `d7` | outer | 1 | `(0,3)` |
| 2 | `g7` | outer | 2 | `(3,3)` |
| 3 | `g4` | outer | 3 | `(3,0)` |
| 4 | `g1` | outer | 4 | `(3,-3)` |
| 5 | `d1` | outer | 5 | `(0,-3)` |
| 6 | `a1` | outer | 6 | `(-3,-3)` |
| 7 | `a4` | outer | 7 | `(-3,0)` |
| 8 | `b6` | middle | 0 | `(-2,2)` |
| 9 | `d6` | middle | 1 | `(0,2)` |
| 10 | `f6` | middle | 2 | `(2,2)` |
| 11 | `f4` | middle | 3 | `(2,0)` |
| 12 | `f2` | middle | 4 | `(2,-2)` |
| 13 | `d2` | middle | 5 | `(0,-2)` |
| 14 | `b2` | middle | 6 | `(-2,-2)` |
| 15 | `b4` | middle | 7 | `(-2,0)` |
| 16 | `c5` | inner | 0 | `(-1,1)` |
| 17 | `d5` | inner | 1 | `(0,1)` |
| 18 | `e5` | inner | 2 | `(1,1)` |
| 19 | `e4` | inner | 3 | `(1,0)` |
| 20 | `e3` | inner | 4 | `(1,-1)` |
| 21 | `d3` | inner | 5 | `(0,-1)` |
| 22 | `c3` | inner | 6 | `(-1,-1)` |
| 23 | `c4` | inner | 7 | `(-1,0)` |

This public order is an interchange convention. It is not asserted to be an
official 0-to-23 numbering issued by an international Mill federation or a
European championship.

### A.3 Adjacency

Each ring point is adjacent to its preceding and following ring point, with
wraparound.

The orthogonal cross-ring adjacency pairs are:

```text
d7-d6 d6-d5
g4-f4 f4-e4
d1-d2 d2-d3
a4-b4 b4-c4
```

For `mill24-diagonal-v1`, add:

```text
a7-b6 b6-c5
g7-f6 f6-e5
g1-f2 f2-e3
a1-b2 b2-c3
```

### A.4 Mill and capture line IDs

The same ordered triples are used for mill detection and, when enabled, the
capture line families.

**Table A.2 — Line IDs**

| ID | Family | Ordered triple |
|---:|---|---|
| 0 | square edge | `a7,d7,g7` |
| 1 | square edge | `g7,g4,g1` |
| 2 | square edge | `g1,d1,a1` |
| 3 | square edge | `a1,a4,a7` |
| 4 | square edge | `b6,d6,f6` |
| 5 | square edge | `f6,f4,f2` |
| 6 | square edge | `f2,d2,b2` |
| 7 | square edge | `b2,b4,b6` |
| 8 | square edge | `c5,d5,e5` |
| 9 | square edge | `e5,e4,e3` |
| 10 | square edge | `e3,d3,c3` |
| 11 | square edge | `c3,c4,c5` |
| 12 | cross | `d7,d6,d5` |
| 13 | cross | `g4,f4,e4` |
| 14 | cross | `d1,d2,d3` |
| 15 | cross | `a4,b4,c4` |
| 16 | diagonal | `a7,b6,c5` |
| 17 | diagonal | `g7,f6,e5` |
| 18 | diagonal | `g1,f2,e3` |
| 19 | diagonal | `a1,b2,c3` |

`mill24-orthogonal-v1` uses IDs 0 to 15.
`mill24-diagonal-v1` uses IDs 0 to 19.

For a capture triple `[a,m,b]`, `a` and `b` are endpoints and `m` is the
middle point. Table order is the intervention fallback order.

### A.5 D4 transforms

**Table A.3 — D4 profile order**

| Ordinal | ID | Coordinate transform |
|---:|---|---|
| 0 | `i` | `(x,y) -> (x,y)` |
| 1 | `r90ccw` | `(x,y) -> (-y,x)` |
| 2 | `r180` | `(x,y) -> (-x,-y)` |
| 3 | `r90cw` | `(x,y) -> (y,-x)` |
| 4 | `mirror-v` | `(x,y) -> (-x,y)` |
| 5 | `mirror-h` | `(x,y) -> (x,-y)` |
| 6 | `mirror-main` | `(x,y) -> (y,x)` |
| 7 | `mirror-anti` | `(x,y) -> (-y,-x)` |

### A.6 Outer/inner ring exchange

The independent exchange transform is:

```text
a7 <-> c5    d7 <-> d5    g7 <-> e5    g4 <-> e4
g1 <-> e3    d1 <-> d3    a1 <-> c3    a4 <-> c4
```

Every middle-ring coordinate maps to itself.

`structural-aut16-v1` uses the eight Table A.3 transforms first, followed by
the exchange composed with each Table A.3 transform in the same order. The
machine-readable IDs are `exchange-i`, `exchange-r90ccw`, and so on.

### A.7 Transforming bit sets

A point bit set is transformed by moving each source bit to the transformed
point index.

A line bit set is transformed by:

1. transforming all three coordinates of each set line;
2. finding the unique Table A.2 line with the same coordinate set; and
3. setting that target line ID.

The normative source-index-to-target-index point and line permutations for all
16 transforms are in `conformance/vectors/transforms.json`.

# Annex B (normative)

## Registries

### B.1 Obligation cause order

**Table B.1 — Causes and canonical branch order**

| Order | Cause | Meaning |
|---:|---|---|
| 0 | `leap` | leap middle-token removal |
| 1 | `intervention` | intervention endpoint removal |
| 2 | `custodian` | bracketed middle-token removal |
| 3 | `mill` | ordinary mill consequence |
| 4 | `mill-count` | placing-end current-mill-count consequence |
| 5 | `stalemate` | no-legal-movement consequence |
| 6 | `board-full` | full-board consequence |

When branch heads have the same cause, compare their complete serialized
branches as US-ASCII.

### B.2 Outcome reasons

**Table B.2 — Standard reasons**

| Reason | Permitted result |
|---|---|
| `fewer-than-minimum` | win or draw |
| `no-legal-move` | win or draw |
| `board-full` | win or draw |
| `no-progress` | draw |
| `repetition` | draw |
| `agreement` | draw |
| `resignation` | win |
| `adjudication` | win or draw |

A private reason shall begin `x-`.

### B.3 Extension subgrammars

The standard values are:

```text
lm=<W-from>,<W-to>;<B-from>,<B-to>
pc=<White-placements>,<Black-placements>
ul=<White-line-bits>,<Black-line-bits>
```

For `lm`, a side with no remembered formation shall use `-,-`. A placement
formation can use `-,<to>`.

For `ul`, both sides shall use the width selected by the topology. Mixed
widths are invalid.

### B.4 State and key profiles

This edition registers:

- state profile `mill24-state-v1`;
- semantics profile `mif-finite-rules-v2`;
- key profile `structural-d4-v1`; and
- key profile `structural-aut16-v1`.

# Annex C (normative)

## ABNF

The following grammar is interpreted according to RFC 5234 and RFC 7405.
All quoted literals are case-sensitive. It is a closed lexical profile as
defined in 13.2. MPK `key-extension` admits private identifiers
syntactically; Clause 8 forbids non-semantic private extensions in
conforming MPK output.

```abnf
mfen = mfen-signature SP state-profile SP board SP side
       SP phase SP action SP hands SP obligations SP no-progress
       SP primary-ply SP outcome *(SP extension)

mfen-signature = %s"MFEN/0.4"

mpk = mpk-signature SP state-profile SP ruleset SP key-profile
      SP mpk-board SP player SP active-phase SP hands
      *(SP key-extension)

mpk-signature = %s"MPK/0.4"

state-profile = identifier
key-profile = identifier
ruleset = identifier %s"@" positive-integer

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
                  %s"board-full" / %s"no-progress" /
                  %s"repetition" / %s"agreement" /
                  %s"resignation" / %s"adjudication"

extension = extension-key %s"=" *value-character
key-extension = extension
extension-key = standard-extension-key / private-identifier
standard-extension-key = %s"lm" / %s"pc" / %s"ul"
value-character = %x21-3C / %x3E-7E

; Registered extension-value subgrammars.
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

The standalone `conformance/mif-0.4.abnf` file is the machine-readable copy.
If a publication defect causes the two copies to differ, the working group
shall correct both before advancing the draft; neither difference may be
silently chosen by an implementation.

# Annex D (normative)

## Conformance corpus

### D.1 Status

The `conformance/` directory delivered with this draft is normative.

An implementation shall pass every vector applicable to its claimed classes
and profiles. A vector's `expected=reject` requires rejection with the stated
category and code, or a documented equivalent code mapped to them.

### D.2 Layout

```text
conformance/
  README.md
  index.json
  mif-0.4.abnf
  examples/
    mstate-pending-board.json
  manifests/
    x-mif-fixture-delay@2.json
    x-mif-fixture-dooz@2.json
    x-mif-fixture-mill-multi@2.json
    x-mif-fixture-nmm@2.json
    x-mif-fixture-nmm-claim@2.json
    x-mif-fixture-stalemate-change@2.json
    x-mif-fixture-stateful@2.json
  vectors/
    conversion.json
    implementation-mappings.json
    json-jcs.json
    mfen.json
    mpk.json
    mstate.json
    rules.json
    transforms.json
```

### D.3 Fixture manifest digests

**Table D.1 — Fixture digests**

| Ruleset | SHA-256 of JCS manifest |
|---|---|
| `x-mif-fixture-nmm@2` | `eeb1e3495e02a004b0d9589ab43ee25455613dda6b024e25a8296c3c3f727913` |
| `x-mif-fixture-dooz@2` | `8abe001b123ddee3ff88e4da8ef6970f2f847ace68bbb695927ab4a0d68872b6` |
| `x-mif-fixture-delay@2` | `59f08e0ec2317973f8ff7bf56a9ab6f699cd550ef8f065be7356dedfc88f5c3e` |
| `x-mif-fixture-stateful@2` | `ff9ddf44f2d0335b34021f161ccc2550f6b5bf820df59445ffe9049c13bf14c6` |
| `x-mif-fixture-nmm-claim@2` | `e56e246b150a046ba605701b0459f1de5aa8913aaf329dba7719bfedf1f8b3a0` |
| `x-mif-fixture-stalemate-change@2` | `70cbff2f7140dbb66718ce01f0fedc5d43f475b3cff8f58f97b15834175386ae` |
| `x-mif-fixture-mill-multi@2` | `244157e6946614090259133893fe2519f0330917d3dc7bcef6c705a3d160ae88` |

These are conformance fixtures, not proposed registrations for the common
game names in their titles.

### D.4 Minimum vector coverage

The corpus covers:

- canonical parse model and output;
- invalid grammar and cross-field state;
- pending board and hand obligations;
- delayed-token effects;
- line-ID history, primary-event intervention line selection and branch
  commitment;
- empty private extension round trip;
- D4 and 16-transform point and line permutations;
- different MPK results under different key profiles;
- origin plus events to current replay;
- independent pre-origin claim seeds and deterministic origin expiry;
- structured board and hand remove events;
- phase synchronization after pending removals and arbitrary-origin stabilization;
- active-player moving phase while the opponent still has reserve;
- dynamic multi-removal sequence capacity;
- double-mill multiplicity, all-in-mills fallback, three-versus-four flying
  and delayed-marker clearing;
- acceptance of deferred mill-count removal with placing captures, and
  rejection of mixed-actor opponent-self-removal with placing captures;
- leap-exclusive branches that retain mill semantic state;
- simultaneous minimum-material adjudication;
- draw-offer lifecycle and accepted claim audit;
- stalemate-before-repetition and automatic repetition at origin boundaries;
- repetition checkpoint mismatch;
- duplicate JSON names after unescaping;
- I-JSON integer boundaries and invalid Unicode;
- manifest JCS bytes and SHA-256; and
- all five conversion statuses, including NMM_LLM atomic capture, Sanmill
  ownerless markers, missing `ul` and unresolved rulesets; and
- fixed implementation mappings.

Advancement beyond Community Working Draft should add independently generated
cross-language outputs, parser fuzz seeds and longer automatic/claim draw
sequences without weakening these vectors.

# Annex E (informative)

## Existing implementation mappings

### E.1 General

This annex records formats observed at fixed implementation commits. It does
not make either implementation, repository or rule name normative.

The normative mapping data is in
`conformance/vectors/implementation-mappings.json`, whose SHA-256 file digest
is:

```text
5e6b902e71bb0e255a339016a068699f5a9784a91dcaa4cdceafabaf460104ce
```

### E.2 NMM_LLM

Repository:
[https://github.com/benmarkbrandwood-blip/NMM_LLM](https://github.com/benmarkbrandwood-blip/NMM_LLM)

Examined commit:

```text
234f542c9d3e7c3ebddd97f4d80edbbdb5f00991
```

Relevant files:

```text
game/board.py
ai/board_symmetry.py
ai/trajectory_db.py
tools/build_fullgame_db.py
```

The examined compact board string is:

```text
<24 board characters>|<turn>|<White placed>|<Black placed>
```

The examined `game/board.py` point order is exactly Table A.1. The examined
trajectory key adds D4 normalization, the active player's phase, placement
counts and explicit on-board counts. The examined full-game binary key packs
the D4-canonical board, turn and placement counts.

NMM_LLM's design contributes useful properties adopted here:

- concise `W`, `B`, `.` board symbols;
- outer, middle, inner ring order;
- one contiguous eight-character block per ring;
- stable D4 normalization;
- retention of the selected transform for move mapping; and
- separation between a human position string and packed database keys.

For its stable standard-form nine-token profile only:

```text
White hand = 9 - White placed
Black hand = 9 - Black placed
```

That conversion is not valid for a ruleset that removes hand tokens, permits
non-standard setup material or otherwise makes hand count independent of
placement count.

The examined `BoardState.apply_move` treats a primary move and optional board
capture atomically. Such stable states map well to MPK. The representation
does not losslessly encode every MFEN pending state or the separate remove
event required by MSTATE.

When the atomic record supplies the exact move and capture target and the
resolved ruleset makes that capture legal, a converter can emit a primary
MSTATE event followed by its remove event with status `lossless`. A snapshot
without that atomic history can still convert to an eligible instantaneous
state but cannot claim the same MSTATE event history.

### E.3 Sanmill

Repository:
[https://github.com/calcitem/Sanmill](https://github.com/calcitem/Sanmill)

Examined commit:

```text
aa6b0c99ee3fca13b0d34e6f929257959ed51414
```

Relevant files include:

```text
crates/tgf-mill/src/human_db_codec.rs
crates/tgf-mill/src/presets.rs
crates/tgf-mill/src/rules/captures.rs
crates/tgf-mill/src/rules/fen.rs
crates/tgf-mill/src/rules/legal_apply.rs
crates/tgf-mill/src/rules/lines.rs
crates/tgf-mill/src/rules/mod.rs
crates/tgf-mill/src/rules/rules_setup.rs
crates/tgf-mill/src/rules/transitions.rs
crates/tgf-mill/src/rules/types.rs
crates/tgf-mill/src/topology.rs
```

The examined FEN dialect uses:

- inner, middle, outer ring order;
- `O`, `@`, `*` and ownerless `X`;
- 17 positional fields;
- an `ids:nodes` marker;
- internal numeric nodes in coordinate-like fields; and
- trailing capture-context tokens.

The Table A.1 index to examined Sanmill dense node ID mapping is:

```text
[23,16,17,18,19,20,21,22,
 15, 8, 9,10,11,12,13,14,
  7, 0, 1, 2, 3, 4, 5, 6]
```

Symbol mapping is:

| Sanmill | MIF |
|---|---|
| `O` | `W` |
| `@` | `B` |
| `*` | `.` |
| `X` | `w` or `b` only when owner is independently known |

Without authoritative owner data, a Sanmill `X` conversion to
`mill24-state-v1` is `unrepresentable-under-profile`; the converter shall not
guess `w` or `b`.

The examined state maps as follows:

| Sanmill category | MIF disposition |
|---|---|
| board and delayed-mark owner | MFEN board |
| side, phase and action | direct MFEN core |
| hand counts | direct `hands` |
| pending counts plus context flags/targets | one or more direct obligation branches |
| no-progress and exact primary ply | direct core when the source has exact values |
| terminal winner and reason | `outcome` |
| last mill from/to | `lm` when semantic |
| preferred removal target | resolve its raw candidate line and emit `interventionLine` on the causing MSTATE primary event |
| custodian, intervention and leap targets | direct branch target sets |
| repetition history | MSTATE repetition objects, after projection conversion |
| mobility and Zobrist values | derived caches; recompute |

Sanmill's examined per-player formed-mill value is a point union, and its
examined `used_mill_lines` value is a global union. Neither value alone can
always reconstruct the per-player line-ID sets required by `ul`. A converter
shall use additional history or report `lossy-semantic-state` and require
caller acceptance before emitting reduced output; it shall not guess which
line produced the same point union.

The examined preferred-removal value is an application hint consumed while
applying the primary action that creates an intervention context. It is not
persistent legal state in this edition. A converter shall resolve the hinted
raw candidate line and, when that line is non-default, emit its Table A.2 ID
as `interventionLine` on the MSTATE `place` or `move` event. Once a pending
MFEN has been produced, the published obligation branches carry the required
context directly.

The `ids:nodes` marker has no MIF equivalent. Coordinates and public bit order
are fixed by Annex A.

A chess-like full-move counter and side parity cannot always reconstruct
primary-ply because Mill variants can retain the same active player.

### E.4 Internal layout and performance

Neither examined implementation needs to adopt Table A.1 as its search
layout.

Import and export can use a fixed 24-entry permutation. The conversion occurs
once at a text, API or database boundary. Move generation, evaluation,
Zobrist updates and recursive search can continue using native bit positions.

Under this architecture:

- textual ring order adds no work to the search hot path;
- native bit operations remain unchanged;
- MPK normalization can operate on a copied 24-cell projection; and
- a database may pack the canonical result into its own binary key.

# Annex F (informative)

## Design decisions and draft advancement

### F.1 Retained architecture

The three representations remain separate because they answer different
questions:

| Representation | Question |
|---|---|
| MFEN | What exact rules state exists now? |
| MPK | Which structural analysis bucket does this stable state use? |
| MSTATE | How can this game, history and claims be resumed and audited? |

MRS identifies how actions change state; it is not a fourth position format.

### F.2 Breaking changes from Community Working Draft 0.1

The 0.2 edition:

- changes experimental signatures to `0.2`;
- removes the `ready` phase;
- separates state profile, ruleset and key profile;
- replaces pending counts and global flags with typed obligation branches;
- makes hand removal an explicit structured MSTATE remove event;
- defines mark-and-delay as a remove effect and its clear as deterministic;
- replaces formed-point history for once-per-line rules with per-player line
  bit sets;
- registers both D4 and full 16-transform structural profiles;
- adopts I-JSON and exact array canonicalization;
- defines repetition observation boundaries;
- limits MRS to finite mechanisms with a normative transition pipeline; and
- publishes machine-readable conformance data.

These changes are intentionally incompatible with the earlier draft. No
automatic field-by-field upgrade can recover semantics that the earlier form
did not carry.

### F.3 Breaking changes from Community Working Draft 0.2

This edition:

- changes experimental signatures to `0.3`;
- narrows MSTATE actor validation so draw negotiation need not match `side`;
- rejects independent ongoing MFENs that already imply an automatic terminal
  other than repetition;
- limits `stalemate.action=change-player` to one side change per
  stable-boundary evaluation, then draws if both players are immobile;
- caps board-removal `remaining` to the number of legal board targets;
- forbids non-semantic private extensions in MPK;
- clears `lm` after every successful primary action that forms no usable mill;
- allows leading `pre-origin` claim records and expires open offers on
  non-agreement terminals; and
- requires line identifiers associated with MPK-normalized actions to use the
  selected topology's line permutation.

MRS document digests continue to cover title and status in this edition;
splitting semantic and document digests is deferred.

### F.4 Breaking changes from Community Working Draft 0.3

This edition:

- changes experimental signatures to `0.4` and finite semantics to
  `mif-finite-rules-v2`;
- removes ruleset identity and version from MFEN and requires the caller or
  MSTATE envelope to supply that context;
- separates `preOriginClaims` replay seed from the final `claims` audit;
- synchronizes phase after every actor-changing transition;
- pauses and restarts the stable-boundary pipeline around generated
  obligations and defines every zero-target fallback;
- evaluates stalemate before repetition so observations describe the final
  stable actor;
- uses sequence capacity for ordinary multiple mill removal;
- evaluates full board during placing as well as moving;
- defines simultaneous minimum-material results and independent-MFEN fixed
  points; and
- expires open offers on every non-acceptance terminal transition.

Fixture rulesets advance to version 2 because these changes can alter legal
actions, replay checkpoints or outcomes. WD 0.3 remains the immutable
`3f1ffc30ab8c838eaeae54102c37e20bdaa00c7a` baseline.

### F.5 Why phase and action remain

Phase describes the rules regime; action describes the next input. The final
placement can leave phase `p`, hand zero and action `r`. Asymmetric hand
removal can also make one player move while the other still places. Removing
either field would make some intermediate states ambiguous or force hidden
inference.

### F.6 Why hand is direct

The state must answer how many tokens are available now. Placement count is
history and can diverge from material after hand removal. Direct hands are
therefore core; optional `pc` is separate.

### F.7 Why obligations remain in MFEN

A user can pause during capture selection. An analysis or UI tool can also
need to inspect that exact choice. Turning it into an already-completed stable
position changes legal state and is not lossless.

### F.8 Why two structural key profiles exist

D4 matches visual board symmetries and deployed NMM_LLM normalization. The
outer/inner exchange is an additional topology automorphism. Both are useful;
neither should be hidden in a ruleset version or silently substituted in an
existing database.

### F.9 Conditions before a stable candidate

The working group should not freeze stable signatures until:

- two independent implementations replay the corpus identically;
- at least two non-trivial manifests pass cross-language replay;
- every transform and semantic extension has inverse-coordinate tests;
- automatic and claim draw cycles have long-form vectors;
- legacy conversion reports have explicit loss categories;
- parser fuzzing covers ABNF, duplicate JSON names and resource limits; and
- ruleset/profile registry governance is agreed.

# Bibliography

- RFC 6838, *Media Type Specifications and Registration Procedures*.
- RFC 6839, *Additional Media Type Structured Syntax Suffixes*.
- RFC 9694, *Guidelines for the Definition of New Top-Level Media Types*.
- [WMD coordinate notation reference](https://muehlespieler.de/x_uebungen/index.php?page=begriffe_notation).
- [ISO name and logo guidance](https://committee.iso.org/sites/isoorg/footer-links/iso-name-and-logo.html).
- [ISO house style](https://www.iso.org/ISO-house-style.html).
- [NMM_LLM repository](https://github.com/benmarkbrandwood-blip/NMM_LLM).
- [Sanmill repository](https://github.com/calcitem/Sanmill).
