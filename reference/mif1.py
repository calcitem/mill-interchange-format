"""Executable reference model for the frozen MIF 1.0 Candidate Wire Contract.

The implementation intentionally favors traceable specification structure over
engine optimization. It supports the complete finite ``mif-finite-rules-v3``
mechanism set, MSTATE replay, repetition/claim state, and Clause 12 identities.
Unknown semantic extension profiles fail closed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import struct
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .jcs import jcs_bytes, jcs_digest


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "mif-1.0"
SCHEMA_DIR = ARTIFACT / "schema"
MILL24 = json.loads(
    (ARTIFACT / "registry" / "mill24.json").read_text(encoding="utf-8")
)

POINTS: tuple[str, ...] = tuple(MILL24["pointOrder"])
POINT_INDEX = {point: index for index, point in enumerate(POINTS)}
LINES: dict[int, tuple[int, int, int]] = {
    item["id"]: tuple(POINT_INDEX[point] for point in item["points"])
    for item in MILL24["lineIds"]
}
CAUSE_ORDER = {cause: index for index, cause in enumerate(MILL24["causeOrder"])}
FEATURE_KEYS = {
    "last-mill": "lm",
    "placement-count": "pc",
    "used-lines": "ul",
}
PLAYER_ORDER = {"w": 0, "b": 1}
ACTION_ORDER = {"accept": 0, "decline": 1, "withdraw": 2}
UINT_MAX = 9007199254740991

IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
UINT_RE = re.compile(r"^(0|[1-9][0-9]*)$")


class MIFError(Exception):
    """A fail-closed MIF validation or replay error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        category: str = "inconsistent",
        event_seq: int | None = None,
        instance_path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.category = category
        self.event_seq = event_seq
        self.instance_path = instance_path

    def diagnostic(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "category": self.category,
            "code": self.code,
            "message": str(self),
        }
        if self.instance_path is not None:
            error["instancePath"] = self.instance_path
        if self.event_seq is not None:
            error["eventSeq"] = self.event_seq
        return {"format": "MIFDIAG/1.0", "errors": [error]}


def require(
    condition: bool,
    code: str,
    message: str,
    *,
    category: str = "inconsistent",
    event_seq: int | None = None,
    instance_path: str | None = None,
) -> None:
    if not condition:
        raise MIFError(
            code,
            message,
            category=category,
            event_seq=event_seq,
            instance_path=instance_path,
        )


def other(player: str) -> str:
    return "b" if player == "w" else "w"


def live_character(player: str) -> str:
    return "W" if player == "w" else "B"


def delayed_character(player: str) -> str:
    return player


@lru_cache(maxsize=1)
def _schema_resources() -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry = Registry()
    documents: dict[str, dict[str, Any]] = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(document)
        registry = registry.with_resource(
            document["$id"], Resource.from_contents(document)
        )
        documents[path.name] = document
    return registry, documents


def validate_schema(instance: Any, entry_name: str) -> None:
    registry, documents = _schema_resources()
    schema = documents[entry_name]
    errors = sorted(
        Draft202012Validator(schema, registry=registry).iter_errors(instance),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        first = errors[0]
        pointer = "".join(f"/{token}" for token in first.absolute_path)
        raise MIFError(
            "x-schema-invalid",
            first.message,
            category="syntax",
            instance_path=pointer,
        )


def semantic_projection(manifest: Mapping[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {
        "profile": "mrs-semantic-v1",
        "semanticsProfile": copy.deepcopy(manifest["semanticsProfile"]),
        "topology": copy.deepcopy(manifest["topology"]),
        "pieces": copy.deepcopy(manifest["pieces"]),
        "turn": copy.deepcopy(manifest["turn"]),
        "flying": copy.deepcopy(manifest["flying"]),
        "placing": copy.deepcopy(manifest["placing"]),
        "mills": copy.deepcopy(manifest["mills"]),
        "captures": copy.deepcopy(manifest["captures"]),
        "boardFull": copy.deepcopy(manifest["boardFull"]),
        "stalemate": copy.deepcopy(manifest["stalemate"]),
        "draw": copy.deepcopy(manifest["draw"]),
        "semanticState": sorted(set(manifest["semanticState"])),
    }
    if not projection["flying"]["enabled"]:
        projection["flying"] = {"enabled": False}
    if projection["placing"]["earlyStop"]["emptyPoints"] == 0:
        projection["placing"]["earlyStop"] = {"emptyPoints": 0}
    for name in ("leap", "intervention", "custodian"):
        if not projection["captures"][name]["enabled"]:
            projection["captures"][name] = {"enabled": False}
    no_progress = projection["draw"]["noProgress"]
    if no_progress["normalLimit"] == 0 and no_progress["endgameLimit"] == 0:
        projection["draw"]["noProgress"] = {"enabled": False}
    if projection["draw"]["repetition"]["count"] == 0:
        projection["draw"]["repetition"] = {"count": 0}
    if manifest.get("extensions"):
        projection["extensions"] = copy.deepcopy(manifest["extensions"])
    return projection


def _set_array(value: list[str], name: str) -> None:
    require(
        value == sorted(set(value)),
        "x-manifest-inconsistent",
        f"{name} must be sorted and unique",
    )


class Rules:
    """Validated finite-rules-v3 manifest and resolved mill24 topology."""

    def __init__(self, manifest: Mapping[str, Any]) -> None:
        self.manifest = copy.deepcopy(dict(manifest))
        validate_schema(self.manifest, "mrs-1.0.schema.json")
        require(
            self.manifest["semanticsProfile"] == "mif-finite-rules-v3",
            "unsupported-profile",
            "reference runner implements only mif-finite-rules-v3",
            category="unsupported",
        )
        require(
            not self.manifest.get("extensions"),
            "unsupported-profile",
            "reference runner has no registered semantic MRS extensions",
            category="unsupported",
        )
        self._validate_consistency()
        self.semantic_projection = semantic_projection(self.manifest)
        self.semantic_digest = jcs_digest(self.semantic_projection)
        self.document_digest = jcs_digest(self.manifest)
        topology_ids = next(
            item["lineIds"]
            for item in MILL24["topologies"]
            if item["id"] == self.manifest["topology"]
        )
        self.line_ids = tuple(topology_ids)
        self.lines = {line_id: LINES[line_id] for line_id in self.line_ids}
        self.adjacency = self._build_adjacency()

    def _validate_consistency(self) -> None:
        manifest = self.manifest
        pieces = manifest["pieces"]
        require(
            pieces["minimumLive"] <= min(pieces["white"], pieces["black"]),
            "x-manifest-inconsistent",
            "minimumLive exceeds initial material",
        )
        if manifest["flying"]["enabled"]:
            require(
                manifest["flying"]["maximumLive"] >= pieces["minimumLive"],
                "x-manifest-inconsistent",
                "enabled flying maximumLive is below minimumLive",
            )
        semantic_state = manifest["semanticState"]
        _set_array(semantic_state, "semanticState")
        if manifest["mills"]["lineReuse"] == "once-per-player":
            require(
                "used-lines" in semantic_state,
                "required-semantic-state-missing",
                "once-per-player requires used-lines",
            )
        if manifest["mills"]["reverseReformation"] == "prohibit-immediate":
            require(
                "last-mill" in semantic_state,
                "required-semantic-state-missing",
                "prohibit-immediate requires last-mill",
            )
        no_progress = manifest["draw"]["noProgress"]
        if no_progress["endgamePredicate"] == "none":
            require(
                no_progress["endgameLimit"] == 0,
                "x-manifest-inconsistent",
                "endgamePredicate none requires a zero endgameLimit",
            )
        _set_array(no_progress["countedPrimaryActions"], "countedPrimaryActions")
        _set_array(no_progress["resetEvents"], "noProgress.resetEvents")
        repetition = manifest["draw"]["repetition"]
        _set_array(repetition["resetEvents"], "repetition.resetEvents")
        require(
            repetition["count"] == 0 or repetition["count"] >= 2,
            "x-manifest-inconsistent",
            "repetition count must be zero or at least two",
        )
        if manifest["placing"]["noLegalPrimaryAction"] == "apply-board-full":
            require(
                manifest["boardFull"]["action"] != "disabled",
                "no-legal-primary-action-policy-invalid",
                "apply-board-full cannot target disabled boardFull",
            )
        placing_captures = any(
            mechanism["enabled"] and "placing" in mechanism["phases"]
            for mechanism in manifest["captures"].values()
            if isinstance(mechanism, dict)
        )
        require(
            not (
                manifest["mills"]["placingEffect"] == "opponent-remove-own-board"
                and placing_captures
            ),
            "x-manifest-inconsistent",
            "opponent-remove-own-board conflicts with placing capture branch actors",
        )
        for name in ("leap", "intervention", "custodian"):
            mechanism = manifest["captures"][name]
            _set_array(mechanism["phases"], f"captures.{name}.phases")
            if not mechanism["enabled"]:
                continue
            selected = self._selected_line_ids_from_manifest(mechanism)
            require(
                bool(selected),
                "x-manifest-inconsistent",
                f"enabled {name} selects no non-empty line family",
            )

    def _selected_line_ids_from_manifest(self, mechanism: Mapping[str, Any]) -> list[int]:
        topology_max = 15 if self.manifest["topology"] == "mill24-orthogonal-v1" else 19
        result: list[int] = []
        if mechanism["lines"]["squareEdges"]:
            result.extend(range(0, 12))
        if mechanism["lines"]["cross"]:
            result.extend(range(12, 16))
        if mechanism["lines"]["diagonal"] and topology_max == 19:
            result.extend(range(16, 20))
        return result

    def selected_capture_lines(self, name: str) -> tuple[int, ...]:
        return tuple(self._selected_line_ids_from_manifest(self.manifest["captures"][name]))

    def _build_adjacency(self) -> tuple[frozenset[int], ...]:
        edges: set[tuple[int, int]] = set()
        for start in (0, 8, 16):
            for offset in range(8):
                left = start + offset
                right = start + ((offset + 1) % 8)
                edges.add(tuple(sorted((left, right))))
        for first, second in MILL24["orthogonalCrossRingEdges"]:
            edges.add(tuple(sorted((POINT_INDEX[first], POINT_INDEX[second]))))
        if self.manifest["topology"] == "mill24-diagonal-v1":
            for first, second in MILL24["diagonalEdges"]:
                edges.add(tuple(sorted((POINT_INDEX[first], POINT_INDEX[second]))))
        adjacency = [set() for _ in POINTS]
        for left, right in edges:
            adjacency[left].add(right)
            adjacency[right].add(left)
        return tuple(frozenset(items) for items in adjacency)

    @property
    def required_state_keys(self) -> tuple[str, ...]:
        return tuple(FEATURE_KEYS[name] for name in self.manifest["semanticState"])

    def normal_initial_state(self) -> "State":
        semantic: dict[str, Any] = {}
        if "lm" in self.required_state_keys:
            semantic["lm"] = {"w": (None, None), "b": (None, None)}
        if "pc" in self.required_state_keys:
            semantic["pc"] = {"w": 0, "b": 0}
        if "ul" in self.required_state_keys:
            semantic["ul"] = {"w": 0, "b": 0}
        return State(
            board=["."] * 24,
            side=self.manifest["turn"]["initial"],
            phase="p",
            action="p",
            hands={
                "w": self.manifest["pieces"]["white"],
                "b": self.manifest["pieces"]["black"],
            },
            obligations=[],
            no_progress=0,
            primary_ply=0,
            outcome="-",
            semantic=semantic,
        )


@dataclass
class Obligation:
    actor: str
    cause: str
    zone: str
    owner: str
    remaining: int
    targets: set[int] | None
    after: str
    scope: set[int] | None = None

    def wire(self, *, deferred: bool = False) -> str:
        if self.zone == "h":
            target_text = "-"
        elif deferred or self.targets is None:
            target_text = "~"
        else:
            mask = sum(1 << target for target in self.targets)
            target_text = f"{mask:06x}"
        return ":".join(
            (
                self.actor,
                self.cause,
                self.zone,
                self.owner,
                str(self.remaining),
                target_text,
                self.after,
            )
        )


@dataclass
class State:
    board: list[str]
    side: str
    phase: str
    action: str
    hands: dict[str, int]
    obligations: list[list[Obligation]]
    no_progress: int
    primary_ply: int
    outcome: str
    semantic: dict[str, Any] = field(default_factory=dict)

    def clone(self) -> "State":
        return copy.deepcopy(self)

    def board_text(self) -> str:
        return "/".join(
            "".join(self.board[start : start + 8]) for start in (0, 8, 16)
        )

    def live_count(self, player: str) -> int:
        return self.board.count(live_character(player))

    def material_count(self, player: str) -> int:
        return self.live_count(player) + self.hands[player]

    def empty_points(self) -> list[int]:
        return [index for index, value in enumerate(self.board) if value == "."]

    def semantic_wire_value(self, key: str, rules: Rules) -> str:
        if key == "lm":
            def endpoint(value: int | None) -> str:
                return "-" if value is None else POINTS[value]

            white = self.semantic[key]["w"]
            black = self.semantic[key]["b"]
            return (
                f"{endpoint(white[0])},{endpoint(white[1])};"
                f"{endpoint(black[0])},{endpoint(black[1])}"
            )
        if key == "pc":
            return f"{self.semantic[key]['w']},{self.semantic[key]['b']}"
        if key == "ul":
            width = 4 if rules.manifest["topology"] == "mill24-orthogonal-v1" else 5
            return f"{self.semantic[key]['w']:0{width}x},{self.semantic[key]['b']:0{width}x}"
        raise MIFError("unsupported-profile", f"unknown state extension {key}", category="unsupported")

    def obligations_text(self) -> str:
        if not self.obligations:
            return "-"
        return "|".join(
            ";".join(
                obligation.wire(deferred=(position > 0 and obligation.zone == "b"))
                for position, obligation in enumerate(branch)
            )
            for branch in self.obligations
        )

    def serialize(self, rules: Rules) -> str:
        fields = [
            "MFEN/1.0",
            "mill24-state-v1",
            self.board_text(),
            self.side,
            self.phase,
            self.action,
            f"{self.hands['w']},{self.hands['b']}",
            self.obligations_text(),
            str(self.no_progress),
            str(self.primary_ply),
            self.outcome,
        ]
        for key in sorted(self.semantic):
            fields.append(f"{key}={self.semantic_wire_value(key, rules)}")
        return " ".join(fields)


def _parse_uint(value: str, name: str) -> int:
    require(
        bool(UINT_RE.fullmatch(value)),
        "x-mfen-syntax",
        f"invalid unsigned integer for {name}",
        category="syntax",
    )
    result = int(value)
    require(
        result <= UINT_MAX,
        "integer-out-of-range",
        f"integer exceeds I-JSON range for {name}",
        category="syntax",
    )
    return result


def _parse_obligations(value: str) -> list[list[Obligation]]:
    if value == "-":
        return []
    branches: list[list[Obligation]] = []
    for branch_text in value.split("|"):
        branch: list[Obligation] = []
        records = branch_text.split(";")
        for position, record in enumerate(records):
            parts = record.split(":")
            require(
                len(parts) == 7,
                "x-mfen-syntax",
                "obligation must have seven colon-delimited fields",
                category="syntax",
            )
            actor, cause, zone, owner, remaining_text, target_text, after = parts
            require(actor in {"w", "b"} and owner in {"w", "b"}, "x-mfen-syntax", "invalid obligation player", category="syntax")
            require(cause in CAUSE_ORDER, "unsupported-profile", f"unknown obligation cause {cause}", category="unsupported")
            require(zone in {"b", "h"}, "x-mfen-syntax", "invalid obligation zone", category="syntax")
            remaining = _parse_uint(remaining_text, "obligation remaining")
            require(remaining > 0, "x-mfen-syntax", "obligation remaining must be positive", category="syntax")
            if zone == "h":
                require(target_text == "-", "x-mfen-syntax", "hand obligation target must be -", category="syntax")
                targets = None
            elif position == 0:
                require(bool(re.fullmatch(r"[0-9a-f]{6}", target_text)), "x-mfen-syntax", "board head requires six lowercase hex digits", category="syntax")
                mask = int(target_text, 16)
                require(mask != 0 and mask < (1 << 24), "x-mfen-syntax", "board head target mask is empty or out of range", category="syntax")
                targets = {index for index in range(24) if mask & (1 << index)}
            else:
                require(target_text == "~", "x-mfen-syntax", "later board obligation target must be ~", category="syntax")
                targets = None
            if position + 1 < len(records):
                require(after == "q", "x-mfen-syntax", "non-final obligation after must be q", category="syntax")
            else:
                require(after in {"w", "b"}, "x-mfen-syntax", "final obligation after must name a player", category="syntax")
            branch.append(
                Obligation(
                    actor=actor,
                    cause=cause,
                    zone=zone,
                    owner=owner,
                    remaining=remaining,
                    targets=targets,
                    after=after,
                    scope=copy.deepcopy(targets),
                )
            )
        branches.append(branch)
    return branches


def parse_mfen(value: str, rules: Rules) -> State:
    require(
        value == value.strip() and "  " not in value and "\t" not in value,
        "x-mfen-syntax",
        "MFEN requires exact single-space framing",
        category="syntax",
    )
    parts = value.split(" ")
    require(len(parts) >= 11, "x-mfen-syntax", "MFEN has too few fields", category="syntax")
    require(parts[0] == "MFEN/1.0", "x-mfen-syntax", "wrong MFEN signature", category="syntax")
    require(parts[1] == "mill24-state-v1", "unsupported-profile", "unsupported state profile", category="unsupported")
    rings = parts[2].split("/")
    require(len(rings) == 3 and all(len(ring) == 8 for ring in rings), "x-mfen-syntax", "invalid board ring shape", category="syntax")
    board = list("".join(rings))
    require(all(piece in "WBwb." for piece in board), "x-mfen-syntax", "invalid board character", category="syntax")
    side, phase, action = parts[3:6]
    hand_parts = parts[6].split(",")
    require(len(hand_parts) == 2, "x-mfen-syntax", "invalid hands", category="syntax")
    hands = {"w": _parse_uint(hand_parts[0], "white hand"), "b": _parse_uint(hand_parts[1], "black hand")}
    obligations = _parse_obligations(parts[7])
    no_progress = _parse_uint(parts[8], "no-progress")
    primary_ply = _parse_uint(parts[9], "primary-ply")
    outcome = parts[10]
    semantic: dict[str, Any] = {}
    prior_key = ""
    for extension in parts[11:]:
        require("=" in extension, "x-mfen-syntax", "invalid extension field", category="syntax")
        key, raw = extension.split("=", 1)
        require(key > prior_key, "extension-order", "MFEN extension keys must be sorted and unique", category="canonical")
        prior_key = key
        require(key in {"lm", "pc", "ul"}, "unsupported-profile", f"unsupported MFEN extension {key}", category="unsupported")
        if key == "lm":
            players = raw.split(";")
            require(len(players) == 2, "x-mfen-syntax", "invalid lm value", category="syntax")
            semantic[key] = {}
            for player, player_raw in zip(("w", "b"), players):
                endpoints = player_raw.split(",")
                require(len(endpoints) == 2, "x-mfen-syntax", "invalid lm endpoint pair", category="syntax")
                parsed: list[int | None] = []
                for endpoint in endpoints:
                    require(endpoint == "-" or endpoint in POINT_INDEX, "x-mfen-syntax", "invalid lm coordinate", category="syntax")
                    parsed.append(None if endpoint == "-" else POINT_INDEX[endpoint])
                semantic[key][player] = tuple(parsed)
        elif key == "pc":
            counts = raw.split(",")
            require(len(counts) == 2, "x-mfen-syntax", "invalid pc value", category="syntax")
            semantic[key] = {"w": _parse_uint(counts[0], "pc white"), "b": _parse_uint(counts[1], "pc black")}
        else:
            bitsets = raw.split(",")
            width = 4 if rules.manifest["topology"] == "mill24-orthogonal-v1" else 5
            require(len(bitsets) == 2 and all(re.fullmatch(rf"[0-9a-f]{{{width}}}", item) for item in bitsets), "x-mfen-syntax", "invalid ul value", category="syntax")
            semantic[key] = {"w": int(bitsets[0], 16), "b": int(bitsets[1], 16)}
    state = State(
        board=board,
        side=side,
        phase=phase,
        action=action,
        hands=hands,
        obligations=obligations,
        no_progress=no_progress,
        primary_ply=primary_ply,
        outcome=outcome,
        semantic=semantic,
    )
    validate_state(state, rules)
    require(state.serialize(rules) == value, "x-noncanonical-mfen", "MFEN is not canonical", category="canonical")
    return state


def validate_state(state: State, rules: Rules) -> None:
    terminal = state.outcome != "-"
    if terminal:
        require(state.side == "-" and state.phase == "o" and state.action == "o", "x-state-inconsistent", "terminal side/phase/action mismatch")
        require(not state.obligations, "x-state-inconsistent", "terminal state has obligations")
        require(bool(re.fullmatch(r"[wbd]:[a-z0-9][a-z0-9.-]{0,62}", state.outcome)), "x-state-inconsistent", "invalid terminal outcome")
    else:
        require(state.side in {"w", "b"} and state.phase in {"p", "m"}, "x-state-inconsistent", "ongoing side/phase mismatch")
        if state.obligations:
            require(state.action == "r", "x-state-inconsistent", "pending obligation requires action r")
            require(all(branch and branch[0].actor == state.side for branch in state.obligations), "side-obligation-actor-mismatch", "branch-head actor differs from side")
        else:
            require(state.action == state.phase, "x-state-inconsistent", "stable action must match phase")
    branch_keys: list[tuple[int, str]] = []
    for branch in state.obligations:
        require(bool(branch), "x-state-inconsistent", "empty obligation branch")
        for position, obligation in enumerate(branch):
            if obligation.zone == "h":
                require(
                    obligation.remaining <= state.hands[obligation.owner],
                    "obligation-target-mismatch",
                    "hand obligation exceeds current reserve",
                )
            elif position == 0:
                targets = obligation.targets or set()
                require(
                    bool(targets)
                    and all(state.board[target] == live_character(obligation.owner) for target in targets),
                    "obligation-target-mismatch",
                    "board head targets do not contain matching live material",
                )
            else:
                require(
                    obligation.targets is None,
                    "x-state-inconsistent",
                    "later board obligation must remain deferred",
                )
        serialized = ";".join(
            item.wire(deferred=index > 0 and item.zone == "b")
            for index, item in enumerate(branch)
        )
        branch_keys.append((CAUSE_ORDER[branch[0].cause], serialized))
    require(branch_keys == sorted(branch_keys), "x-noncanonical-mfen", "obligation branches are not canonical", category="canonical")
    for player in ("w", "b"):
        initial = rules.manifest["pieces"]["white" if player == "w" else "black"]
        occupied = state.live_count(player) + state.board.count(delayed_character(player)) + state.hands[player]
        require(occupied <= initial, "x-state-inconsistent", f"{player} material exceeds manifest initial count")
    if any(piece in {"w", "b"} for piece in state.board):
        require(rules.manifest["mills"]["placingEffect"] == "mark-opponent-board-until-moving", "x-state-inconsistent", "delayed tokens are not enabled")
    for key in rules.required_state_keys:
        require(key in state.semantic, "required-semantic-state-missing", f"required MFEN extension {key} is missing")


@dataclass
class ReplayResult:
    state: State
    repetition_history: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    claim_rights: dict[str, Any] | None
    resumption_state: dict[str, Any]
    resumption_digest: str
    decision_state: dict[str, Any]
    decision_digest: str


class Session:
    """Stateful execution context carrying history not present in bare MFEN."""

    def __init__(
        self,
        rules: Rules,
        state: State,
        *,
        repetition_seed: Iterable[Mapping[str, Any]] = (),
        pre_origin_claims: Iterable[Mapping[str, Any]] = (),
    ) -> None:
        self.rules = rules
        self.state = state.clone()
        self.repetition_history = [copy.deepcopy(dict(item)) for item in repetition_seed]
        require(
            self.rules.manifest["draw"]["repetition"]["count"] > 0
            or not self.repetition_history,
            "repetition-history-mismatch",
            "disabled repetition cannot carry an active observation window",
            category="replay",
        )
        self.claims: list[dict[str, Any]] = []
        self.open_offer_index: int | None = None
        self.claim_rights: dict[str, Any] | None = None
        self.last_event_seq = 0
        self.placing_done = not (
            any(self.state.hands.values())
            or self.state.phase == "p"
            or any(piece in {"w", "b"} for piece in self.state.board)
        )
        self._seed_claims(pre_origin_claims)

    def _seed_claims(self, seeds: Iterable[Mapping[str, Any]]) -> None:
        for seed in seeds:
            record = copy.deepcopy(dict(seed))
            require(record.get("kind") == "draw-offer", "x-claim-seed-invalid", "pre-origin claim must be a draw offer")
            record = {"source": "pre-origin", **record}
            if record["status"] == "open":
                require(self.open_offer_index is None, "x-claim-seed-invalid", "multiple pre-origin offers are open")
                self.open_offer_index = len(self.claims)
            self.claims.append(record)

    def stabilize_origin(self) -> None:
        if self.state.outcome != "-":
            return
        self._synchronize_phase()
        if self.state.obligations:
            return
        boundary_pending = (
            not self.placing_done
            and self.state.hands["w"] == 0
            and self.state.hands["b"] == 0
        )
        self._stabilize(source="origin", event_seq=None, boundary_pending=boundary_pending)

    def complete_mills(self, player: str, board: list[str] | None = None) -> set[int]:
        position = self.state.board if board is None else board
        piece = live_character(player)
        return {
            line_id
            for line_id, line in self.rules.lines.items()
            if all(position[index] == piece for index in line)
        }

    def usable_mills_at(self, player: str, destination: int, board: list[str] | None = None) -> list[int]:
        complete = self.complete_mills(player, board)
        used = self.state.semantic.get("ul", {}).get(player, 0)
        return [
            line_id
            for line_id in sorted(complete)
            if destination in self.rules.lines[line_id]
            and not (
                self.rules.manifest["mills"]["lineReuse"] == "once-per-player"
                and used & (1 << line_id)
            )
        ]

    def ordinary_targets(self, actor: str, owner: str) -> set[int]:
        live = {
            index
            for index, value in enumerate(self.state.board)
            if value == live_character(owner)
        }
        if actor == owner or self.rules.manifest["mills"]["targetProtection"] == "all-opponent":
            return live
        protected: set[int] = set()
        for line_id in self.complete_mills(owner):
            protected.update(self.rules.lines[line_id])
        outside = live - protected
        return outside if outside else live

    def _mechanism_active(self, name: str, phase: str, actor: str) -> bool:
        mechanism = self.rules.manifest["captures"][name]
        phase_name = "placing" if phase == "p" else "moving"
        if not mechanism["enabled"] or phase_name not in mechanism["phases"]:
            return False
        maximum = mechanism["maximumOwnLivePieces"]
        if maximum is None:
            return True
        if name in {"custodian", "intervention"} and phase != "m":
            return True
        return self.state.live_count(actor) <= maximum

    def _leap_line(self, actor: str, source: int, target: int, phase: str) -> tuple[int, int] | None:
        if not self._mechanism_active("leap", phase, actor):
            return None
        for line_id in self.rules.selected_capture_lines("leap"):
            left, middle, right = self.rules.lines[line_id]
            if {source, target} != {left, right}:
                continue
            if self.state.board[middle] != live_character(other(actor)):
                continue
            if middle not in self.ordinary_targets(actor, other(actor)):
                continue
            return line_id, middle
        return None

    def _reverse_reformation_forbidden(self, actor: str, source: int, target: int) -> bool:
        if self.rules.manifest["mills"]["reverseReformation"] != "prohibit-immediate":
            return False
        lm = self.state.semantic.get("lm", {}).get(actor)
        if lm != (target, source):
            return False
        current_usable = self.usable_mills_at(actor, source)
        if not current_usable:
            return False
        board = self.state.board.copy()
        board[source] = "."
        board[target] = live_character(actor)
        return bool(self.usable_mills_at(actor, target, board))

    def legal_move_pairs(self, actor: str | None = None) -> Iterator[tuple[int, int]]:
        player = self.state.side if actor is None else actor
        if self.state.action not in {"m", "p"}:
            return
        if self.state.action == "p" and not self.rules.manifest["placing"]["movementAllowed"]:
            return
        sources = [
            index
            for index, value in enumerate(self.state.board)
            if value == live_character(player)
        ]
        destinations = self.state.empty_points()
        flying = (
            self.state.phase == "m"
            and self.rules.manifest["flying"]["enabled"]
            and self.state.live_count(player) <= self.rules.manifest["flying"]["maximumLive"]
        )
        for source in sources:
            for target in destinations:
                adjacent = target in self.rules.adjacency[source]
                leap = self._leap_line(player, source, target, self.state.phase)
                if not (adjacent or flying or leap is not None):
                    continue
                if self._reverse_reformation_forbidden(player, source, target):
                    continue
                yield source, target

    def has_legal_primary(self) -> bool:
        if self.state.action == "p":
            if self.state.hands[self.state.side] > 0 and self.state.empty_points():
                return True
            if self.rules.manifest["placing"]["movementAllowed"]:
                return next(self.legal_move_pairs(), None) is not None
            return False
        if self.state.action == "m":
            return next(self.legal_move_pairs(), None) is not None
        return False

    def legal_actions(self) -> list[dict[str, Any]]:
        if self.state.outcome != "-":
            return []
        actor = self.state.side
        if self.state.action == "r":
            actions: list[dict[str, Any]] = []
            board_seen: set[int] = set()
            hand_seen: set[str] = set()
            for branch in self.state.obligations:
                head = branch[0]
                if head.zone == "b":
                    for target in sorted(head.targets or set()):
                        if target not in board_seen:
                            actions.append({"actor": actor, "type": "remove", "target": {"zone": "board", "at": POINTS[target]}})
                            board_seen.add(target)
                elif head.owner not in hand_seen:
                    actions.append({"actor": actor, "type": "remove", "target": {"zone": "hand", "player": head.owner}})
                    hand_seen.add(head.owner)
            return actions
        actions = []
        if self.state.action == "p" and self.state.hands[actor] > 0:
            actions.extend({"actor": actor, "type": "place", "at": POINTS[target]} for target in self.state.empty_points())
        if self.state.action == "m" or (
            self.state.action == "p" and self.rules.manifest["placing"]["movementAllowed"]
        ):
            actions.extend(
                {"actor": actor, "type": "move", "from": POINTS[source], "to": POINTS[target]}
                for source, target in self.legal_move_pairs(actor)
            )
        return actions

    def apply_event(self, event: Mapping[str, Any]) -> None:
        seq = event.get("seq")
        require(isinstance(seq, int) and seq == self.last_event_seq + 1, "x-event-sequence", "event sequence must be consecutive", category="replay", event_seq=seq if isinstance(seq, int) else None)
        require(self.state.outcome == "-", "x-event-after-terminal", "cannot apply an event after terminal state", category="replay", event_seq=seq)
        event_type = event.get("type")
        if event_type in {"place", "move"}:
            self._apply_primary(dict(event))
        elif event_type == "remove":
            self._apply_remove(dict(event))
        elif event_type in {"offer-draw", "accept-draw", "decline-draw", "withdraw-draw"}:
            self._apply_offer_event(dict(event))
        elif event_type == "claim-draw":
            self._apply_claim(dict(event))
        elif event_type == "resign":
            self._apply_resign(dict(event))
        elif event_type == "adjudicate":
            self._apply_adjudicate(dict(event))
        else:
            raise MIFError("unsupported-profile", f"unsupported event type {event_type}", category="unsupported", event_seq=seq)
        self.last_event_seq = seq

    def _validate_event_members(self, event: dict[str, Any], required: set[str], optional: set[str] = set()) -> None:
        common = {"seq", "actor", "type"}
        allowed = common | required | optional | {"annotations", "extensions"}
        require(set(event) <= allowed and required <= set(event), "x-event-shape", "event has missing or unknown members", category="syntax", event_seq=event["seq"])
        require(not event.get("extensions"), "unsupported-profile", "event semantic extensions are unsupported", category="unsupported", event_seq=event["seq"])

    def _apply_primary(self, event: dict[str, Any]) -> None:
        seq = event["seq"]
        event_type = event["type"]
        required = {"at"} if event_type == "place" else {"from", "to"}
        self._validate_event_members(event, required, {"interventionLine"})
        actor = event["actor"]
        require(actor == self.state.side, "x-illegal-event", "primary actor is not side", event_seq=seq)
        require(not self.state.obligations and self.state.action in {"p", "m"}, "x-illegal-event", "primary event requires a stable primary boundary", event_seq=seq)
        phase_before = self.state.phase
        source: int | None = None
        if event_type == "place":
            require(self.state.action == "p", "x-illegal-event", "place requires action p", event_seq=seq)
            require(self.state.hands[actor] > 0, "x-illegal-event", "place actor has no hand token", event_seq=seq)
            require(event["at"] in POINT_INDEX, "x-illegal-event", "place coordinate is invalid", event_seq=seq)
            target = POINT_INDEX[event["at"]]
            require(self.state.board[target] == ".", "x-illegal-event", "place target is unavailable", event_seq=seq)
        else:
            require(self.state.action == "m" or (self.state.action == "p" and self.rules.manifest["placing"]["movementAllowed"]), "x-illegal-event", "move is not permitted in current action", event_seq=seq)
            require(event["from"] in POINT_INDEX and event["to"] in POINT_INDEX, "x-illegal-event", "move coordinate is invalid", event_seq=seq)
            source = POINT_INDEX[event["from"]]
            target = POINT_INDEX[event["to"]]
            require((source, target) in set(self.legal_move_pairs(actor)), "x-illegal-event", "move is not legal", event_seq=seq)

        raw_intervention = self._intervention_candidates(actor, target, phase_before, board_after=None, preview_event=(source, target))
        selected_line = event.get("interventionLine")
        if selected_line is not None:
            require(len(raw_intervention) > 1 and selected_line in raw_intervention and selected_line != raw_intervention[0], "x-illegal-event", "interventionLine is absent, default, or not a raw candidate", event_seq=seq)

        self._expire_claim_right()
        self._expire_offer_before_primary(actor, seq)
        if event_type == "place":
            self.state.hands[actor] -= 1
            self.state.board[target] = live_character(actor)
            if "pc" in self.state.semantic:
                self.state.semantic["pc"][actor] += 1
        else:
            assert source is not None
            self.state.board[source] = "."
            self.state.board[target] = live_character(actor)
        self.state.primary_ply += 1

        new_mills = self.usable_mills_at(actor, target)
        if new_mills:
            if "ul" in self.state.semantic:
                for line_id in new_mills:
                    self.state.semantic["ul"][actor] |= 1 << line_id
            if "lm" in self.state.semantic:
                self.state.semantic["lm"][actor] = (source, target)
        elif "lm" in self.state.semantic:
            self.state.semantic["lm"][actor] = (None, None)

        occurrences = {event_type}
        if new_mills:
            occurrences.add("mill-formation")
        self._update_primary_no_progress(event_type, occurrences)
        self._apply_repetition_resets(occurrences)

        leap = None if source is None else self._leap_line(actor, source, target, phase_before)
        branches: list[list[Obligation]] = []
        retained_without_branch = False
        if leap is not None:
            _, middle = leap
            branches.append([
                Obligation(actor, "leap", "b", other(actor), 1, {middle}, other(actor), {middle})
            ])
        else:
            intervention = self._intervention_branch(actor, target, phase_before, selected_line)
            custodian = self._custodian_branch(actor, target, phase_before)
            mill_branch, retained_without_branch = self._mill_branch(actor, phase_before, new_mills)
            for branch in (intervention, custodian, mill_branch):
                if branch:
                    branches.append(branch)
        if branches:
            self._publish_branches(branches)
            return

        next_player = actor if retained_without_branch else other(actor)
        self.state.side = next_player
        self._synchronize_phase()
        boundary_pending = not self.placing_done and not any(self.state.hands.values())
        early = self.rules.manifest["placing"]["earlyStop"]
        if (
            event_type == "place"
            and early["emptyPoints"] > 0
            and len(self.state.empty_points()) <= early["emptyPoints"]
        ):
            self.state.hands = {"w": 0, "b": 0}
            boundary_pending = True
        self._stabilize(source="event", event_seq=seq, boundary_pending=boundary_pending)

    def _intervention_candidates(
        self,
        actor: str,
        target: int,
        phase: str,
        *,
        board_after: list[str] | None,
        preview_event: tuple[int | None, int] | None = None,
    ) -> list[int]:
        if not self._mechanism_active("intervention", phase, actor):
            return []
        board = self.state.board.copy() if board_after is None else board_after.copy()
        if preview_event is not None:
            source, destination = preview_event
            if source is not None:
                board[source] = "."
            board[destination] = live_character(actor)
        opponent_piece = live_character(other(actor))
        return [
            line_id
            for line_id in self.rules.selected_capture_lines("intervention")
            if self.rules.lines[line_id][1] == target
            and board[self.rules.lines[line_id][0]] == opponent_piece
            and board[self.rules.lines[line_id][2]] == opponent_piece
        ]

    def _intervention_branch(self, actor: str, target: int, phase: str, selected_line: int | None) -> list[Obligation] | None:
        candidates = self._intervention_candidates(actor, target, phase, board_after=self.state.board)
        if not candidates:
            return None
        line_id = candidates[0] if selected_line is None else selected_line
        left, _, right = self.rules.lines[line_id]
        targets = {left, right} & self.ordinary_targets(actor, other(actor))
        if not targets:
            return None
        return [Obligation(actor, "intervention", "b", other(actor), len(targets), targets, other(actor), set(targets))]

    def _custodian_branch(self, actor: str, target: int, phase: str) -> list[Obligation] | None:
        if not self._mechanism_active("custodian", phase, actor):
            return None
        opponent_piece = live_character(other(actor))
        actor_piece = live_character(actor)
        raw: set[int] = set()
        for line_id in self.rules.selected_capture_lines("custodian"):
            left, middle, right = self.rules.lines[line_id]
            if target == left and self.state.board[right] == actor_piece and self.state.board[middle] == opponent_piece:
                raw.add(middle)
            if target == right and self.state.board[left] == actor_piece and self.state.board[middle] == opponent_piece:
                raw.add(middle)
        targets = raw & self.ordinary_targets(actor, other(actor))
        if not targets:
            return None
        return [Obligation(actor, "custodian", "b", other(actor), 1, targets, other(actor), set(targets))]

    def _mill_branch(self, actor: str, phase: str, new_mills: list[int]) -> tuple[list[Obligation] | None, bool]:
        if not new_mills:
            return None, False
        multiplicity = 1 if self.rules.manifest["mills"]["removalMultiplicity"] == "one-per-primary" else len(new_mills)
        if phase == "m":
            targets = self.ordinary_targets(actor, other(actor))
            remaining = min(multiplicity, self.state.live_count(other(actor)))
            if remaining == 0:
                return None, False
            return [Obligation(actor, "mill", "b", other(actor), remaining, targets, other(actor), set(targets))], False

        effect = self.rules.manifest["mills"]["placingEffect"]
        if effect == "remove-by-current-mill-count-at-placing-end":
            return None, False
        if effect in {"remove-opponent-board", "mark-opponent-board-until-moving"}:
            targets = self.ordinary_targets(actor, other(actor))
            remaining = min(multiplicity, self.state.live_count(other(actor)))
            if remaining == 0:
                return None, False
            return [Obligation(actor, "mill", "b", other(actor), remaining, targets, other(actor), set(targets))], False
        if effect == "opponent-remove-own-board":
            remover = other(actor)
            targets = self.ordinary_targets(remover, remover)
            remaining = min(multiplicity, self.state.live_count(remover))
            if remaining == 0:
                return None, False
            return [Obligation(remover, "mill", "b", remover, remaining, targets, remover, set(targets))], False
        if effect in {"remove-opponent-hand-change", "remove-opponent-hand-retain"}:
            opponent = other(actor)
            retained = effect.endswith("retain")
            final_after = actor if retained else opponent
            hand_count = min(multiplicity, self.state.hands[opponent])
            board_count = min(max(0, multiplicity - hand_count), self.state.live_count(opponent))
            branch: list[Obligation] = []
            if hand_count:
                branch.append(Obligation(actor, "mill", "h", opponent, hand_count, None, "q" if board_count else final_after))
            if board_count:
                targets = self.ordinary_targets(actor, opponent) if not branch else None
                branch.append(Obligation(actor, "mill", "b", opponent, board_count, targets, final_after, copy.deepcopy(targets)))
            return (branch or None), retained
        raise MIFError("unsupported-profile", f"unsupported placing mill effect {effect}", category="unsupported")

    def _publish_branches(self, branches: list[list[Obligation]]) -> None:
        for branch in branches:
            self._normalize_branch_after(branch)
            if branch[0].zone == "b" and branch[0].targets is None:
                branch[0].targets = self._targets_for(branch[0])
                branch[0].scope = copy.deepcopy(branch[0].targets)
        branches.sort(key=lambda branch: (CAUSE_ORDER[branch[0].cause], ";".join(item.wire(deferred=index > 0 and item.zone == "b") for index, item in enumerate(branch))))
        actor = branches[0][0].actor
        require(all(branch[0].actor == actor for branch in branches), "side-obligation-actor-mismatch", "alternative branch heads have different actors")
        self.state.obligations = branches
        self.state.side = actor
        self.state.action = "r"
        self.claim_rights = None

    def _normalize_branch_after(self, branch: list[Obligation]) -> None:
        for index, obligation in enumerate(branch):
            if index + 1 < len(branch):
                obligation.after = "q"

    def _update_primary_no_progress(self, event_type: str, occurrences: set[str]) -> None:
        config = self.rules.manifest["draw"]["noProgress"]
        if config["normalLimit"] == 0 and config["endgameLimit"] == 0:
            return
        if event_type in config["countedPrimaryActions"]:
            self.state.no_progress += 1
        if occurrences.intersection(config["resetEvents"]):
            self.state.no_progress = 0

    def _apply_repetition_resets(self, occurrences: set[str]) -> None:
        repetition = self.rules.manifest["draw"]["repetition"]
        if repetition["count"] == 0:
            return
        if occurrences.intersection(repetition["resetEvents"]):
            self.repetition_history.clear()

    def _apply_remove(self, event: dict[str, Any]) -> None:
        seq = event["seq"]
        self._validate_event_members(event, {"target"})
        require(self.state.action == "r" and bool(self.state.obligations), "remove-without-obligation", "remove requires a pending obligation", event_seq=seq)
        require(event["actor"] == self.state.side, "side-obligation-actor-mismatch", "remove actor differs from side", event_seq=seq)
        target = event["target"]
        require(isinstance(target, dict) and set(target) in ({"zone", "at"}, {"zone", "player"}), "x-event-shape", "invalid structured remove target", category="syntax", event_seq=seq)
        selected_index: int | None = None
        selected_point: int | None = None
        for index, branch in enumerate(self.state.obligations):
            head = branch[0]
            if target.get("zone") == "board" and head.zone == "b" and target.get("at") in POINT_INDEX:
                point = POINT_INDEX[target["at"]]
                if point in (head.targets or set()) and self.state.board[point] == live_character(head.owner):
                    selected_index = index
                    selected_point = point
                    break
            if target.get("zone") == "hand" and head.zone == "h" and target.get("player") == head.owner and self.state.hands[head.owner] > 0:
                selected_index = index
                break
        require(selected_index is not None, "obligation-target-mismatch", "remove target selects no canonical branch", event_seq=seq)
        branch = self.state.obligations[selected_index]
        self.state.obligations = [branch]
        head = branch[0]
        self._expire_claim_right()
        was_placing = not self.placing_done
        if head.zone == "h":
            self.state.hands[head.owner] -= 1
            occurrence = "hand-remove"
        else:
            assert selected_point is not None
            delayed = (
                head.cause == "mill"
                and self.state.phase == "p"
                and self.rules.manifest["mills"]["placingEffect"] == "mark-opponent-board-until-moving"
            )
            self.state.board[selected_point] = delayed_character(head.owner) if delayed else "."
            occurrence = "board-remove"
            if head.scope is not None:
                head.scope.discard(selected_point)
        head.remaining -= 1
        config = self.rules.manifest["draw"]["noProgress"]
        if (
            (config["normalLimit"] > 0 or config["endgameLimit"] > 0)
            and occurrence in config["resetEvents"]
        ):
            self.state.no_progress = 0
        self._apply_repetition_resets({occurrence})
        if self.state.material_count(head.owner) < self.rules.manifest["pieces"]["minimumLive"]:
            self._terminal(other(head.owner), "fewer-than-minimum", event_seq=seq)
            return
        if head.remaining > 0:
            head.targets = self._targets_for(head)
            if head.targets:
                self.state.side = head.actor
                self.state.action = "r"
                return
            if head.cause == "stalemate":
                self._terminal(other(head.actor), "no-legal-move", event_seq=seq)
                return
        final_after = head.after
        branch.pop(0)
        while branch:
            next_head = branch[0]
            if next_head.zone == "b":
                next_head.targets = self._targets_for(next_head)
                next_head.scope = copy.deepcopy(next_head.targets)
                if not next_head.targets:
                    if next_head.cause == "stalemate":
                        self._terminal(other(next_head.actor), "no-legal-move", event_seq=seq)
                        return
                    final_after = next_head.after
                    branch.pop(0)
                    continue
            self.state.side = next_head.actor
            self.state.action = "r"
            return
        self.state.obligations = []
        self.state.side = final_after
        self._synchronize_phase()
        boundary_pending = was_placing and not any(self.state.hands.values())
        self._stabilize(source="event", event_seq=seq, boundary_pending=boundary_pending)

    def _targets_for(self, obligation: Obligation) -> set[int]:
        if obligation.zone == "h":
            return set()
        live = {
            index
            for index, value in enumerate(self.state.board)
            if value == live_character(obligation.owner)
        }
        if obligation.cause in {"leap", "intervention", "custodian"}:
            return live & (obligation.scope or set())
        if obligation.cause == "stalemate":
            actor_points = {
                index
                for index, value in enumerate(self.state.board)
                if value == live_character(obligation.actor)
            }
            adjacent = {
                target
                for target in live
                if any(target in self.rules.adjacency[source] for source in actor_points)
            }
            return adjacent
        return self.ordinary_targets(obligation.actor, obligation.owner)

    def _apply_offer_event(self, event: dict[str, Any]) -> None:
        seq = event["seq"]
        event_type = event["type"]
        if event_type == "offer-draw":
            self._validate_event_members(event, set())
            require(event["actor"] == self.state.side, "x-illegal-event", "offer actor is not side", event_seq=seq)
            require(self.open_offer_index is None, "x-illegal-event", "a draw offer is already open", event_seq=seq)
            self.claims.append({"source": "event", "actor": event["actor"], "eventSeq": seq, "kind": "draw-offer", "status": "open"})
            self.open_offer_index = len(self.claims) - 1
            return
        self._validate_event_members(event, {"offerEventSeq"})
        require(self.open_offer_index is not None, "x-illegal-event", "no draw offer is open", event_seq=seq)
        record = self.claims[self.open_offer_index]
        expected_seq = 0 if record["source"] == "pre-origin" else record["eventSeq"]
        require(event["offerEventSeq"] == expected_seq, "x-illegal-event", "offerEventSeq does not identify the open offer", event_seq=seq)
        if event_type in {"accept-draw", "decline-draw"}:
            require(event["actor"] == other(record["actor"]), "x-illegal-event", "offer response actor is not the non-offerer", event_seq=seq)
        else:
            require(event["actor"] == record["actor"], "x-illegal-event", "withdraw actor is not the offerer", event_seq=seq)
        status = {"accept-draw": "accepted", "decline-draw": "declined", "withdraw-draw": "withdrawn"}[event_type]
        record["status"] = status
        record["resolvedEventSeq"] = seq
        self.open_offer_index = None
        if event_type == "accept-draw":
            self._terminal("d", "agreement", event_seq=seq, agreement=True)

    def _apply_claim(self, event: dict[str, Any]) -> None:
        seq = event["seq"]
        self._validate_event_members(event, {"reason"})
        require(not self.state.obligations, "claim-during-obligation", "claim-draw is forbidden during an obligation", event_seq=seq)
        require(event["actor"] == self.state.side, "claim-right-unavailable", "claim actor is not side", event_seq=seq)
        reasons = [] if self.claim_rights is None else self.claim_rights["reasons"]
        require(event["reason"] in reasons, "claim-right-unavailable", "selected draw claim right is unavailable", event_seq=seq)
        self.claims.append({"source": "event", "actor": event["actor"], "eventSeq": seq, "kind": "draw-claim", "status": "accepted"})
        self.claim_rights = None
        self._terminal("d", event["reason"], event_seq=seq)

    def _apply_resign(self, event: dict[str, Any]) -> None:
        self._validate_event_members(event, set())
        require(event["actor"] in {"w", "b"}, "x-illegal-event", "resign actor must be a player", event_seq=event["seq"])
        self._terminal(other(event["actor"]), "resignation", event_seq=event["seq"])

    def _apply_adjudicate(self, event: dict[str, Any]) -> None:
        self._validate_event_members(event, {"result", "reason", "authority"})
        require(event["actor"] == "system", "x-illegal-event", "only system may adjudicate", event_seq=event["seq"])
        require(event["result"] in {"w", "b", "d"} and isinstance(event["authority"], str) and event["authority"], "x-illegal-event", "invalid adjudication result or authority", event_seq=event["seq"])
        require(bool(IDENTIFIER_RE.fullmatch(event["reason"])), "x-illegal-event", "invalid adjudication reason", event_seq=event["seq"])
        self._terminal(event["result"], event["reason"], event_seq=event["seq"])

    def _expire_offer_before_primary(self, actor: str, event_seq: int) -> None:
        if self.open_offer_index is None:
            return
        record = self.claims[self.open_offer_index]
        if self.rules.manifest["draw"]["offers"]["expiry"] == "on-opponent-primary-action" and actor != record["actor"]:
            self._expire_open_offer(event_seq)

    def _expire_open_offer(self, event_seq: int | None) -> None:
        if self.open_offer_index is None:
            return
        record = self.claims[self.open_offer_index]
        record["status"] = "expired"
        if event_seq is not None:
            record["resolvedEventSeq"] = event_seq
        self.open_offer_index = None

    def _expire_claim_right(self) -> None:
        self.claim_rights = None

    def _synchronize_phase(self) -> None:
        if self.placing_done:
            self.state.phase = "m"
        else:
            self.state.phase = "p" if self.state.hands[self.state.side] > 0 else "m"
        if not self.state.obligations:
            self.state.action = self.state.phase

    def _enter_global_boundary(self) -> bool:
        retained = self.state.side
        self.placing_done = True
        self.state.phase = "m"
        self.state.board = ["." if value in {"w", "b"} else value for value in self.state.board]
        configured = self.rules.manifest["turn"]["placingEndActivePlayer"]
        self.state.side = retained if configured == "retain" else configured
        self.state.action = "m"
        if self.rules.manifest["mills"]["placingEffect"] != "remove-by-current-mill-count-at-placing-end":
            return False
        white_mills = len(self.complete_mills("w"))
        black_mills = len(self.complete_mills("b"))
        if white_mills == 0 and black_mills == 0:
            specifications = [("w", "w", 1), ("b", "b", 1)]
        elif white_mills > 0 and black_mills == 0:
            specifications = [("w", "b", 2), ("b", "w", 1)]
        elif black_mills > 0 and white_mills == 0:
            specifications = [("w", "b", 1), ("b", "w", 2)]
        elif white_mills == black_mills:
            specifications = [("w", "b", white_mills), ("b", "w", black_mills)]
        elif white_mills > black_mills:
            specifications = [("w", "b", black_mills + 1), ("b", "w", black_mills)]
        else:
            specifications = [("w", "b", white_mills), ("b", "w", white_mills + 1)]
        branch: list[Obligation] = []
        for actor, owner, count in specifications:
            remaining = min(count, self.state.live_count(owner))
            if remaining:
                targets = self.ordinary_targets(actor, owner) if not branch else None
                branch.append(Obligation(actor, "mill-count", "b", owner, remaining, targets, self.state.side, copy.deepcopy(targets)))
        if not branch:
            return False
        for index, obligation in enumerate(branch):
            obligation.after = "q" if index + 1 < len(branch) else self.state.side
        self._publish_branches([branch])
        return True

    def _board_full_effect(self) -> bool:
        action = self.rules.manifest["boardFull"]["action"]
        if action == "disabled":
            return False
        if action == "white-loses":
            self._terminal("b", "board-full")
            return True
        if action == "draw":
            self._terminal("d", "board-full")
            return True
        if action == "white-then-black-remove":
            specs = [("w", "b"), ("b", "w")]
            final_after = "w"
        elif action == "black-then-white-remove":
            specs = [("b", "w"), ("w", "b")]
            final_after = "b"
        elif action == "active-player-removes":
            specs = [(self.state.side, other(self.state.side))]
            final_after = other(self.state.side)
        else:
            raise MIFError("unsupported-profile", f"unsupported board-full action {action}", category="unsupported")
        branch: list[Obligation] = []
        for actor, owner in specs:
            if self.state.live_count(owner) == 0:
                continue
            targets = self.ordinary_targets(actor, owner) if not branch else None
            branch.append(Obligation(actor, "board-full", "b", owner, 1, targets, final_after, copy.deepcopy(targets)))
        if not branch:
            return False
        for index, obligation in enumerate(branch):
            obligation.after = "q" if index + 1 < len(branch) else final_after
        self._publish_branches([branch])
        return True

    def _minimum_material(self) -> bool:
        minimum = self.rules.manifest["pieces"]["minimumLive"]
        deficient = [player for player in ("w", "b") if self.state.material_count(player) < minimum]
        if len(deficient) == 2:
            self._terminal("d", "fewer-than-minimum")
            return True
        if len(deficient) == 1:
            self._terminal(other(deficient[0]), "fewer-than-minimum")
            return True
        return False

    def _stalemate_targets(self, actor: str) -> set[int]:
        owner = other(actor)
        actor_points = {
            index
            for index, value in enumerate(self.state.board)
            if value == live_character(actor)
        }
        return {
            target
            for target, value in enumerate(self.state.board)
            if value == live_character(owner)
            and any(target in self.rules.adjacency[source] for source in actor_points)
        }

    def _stalemate_effect(self, changed_once: bool) -> tuple[bool, bool]:
        if self.state.phase != "m" or next(self.legal_move_pairs(), None) is not None:
            return False, changed_once
        action = self.rules.manifest["stalemate"]["action"]
        if action == "loss":
            self._terminal(other(self.state.side), "no-legal-move")
            return True, changed_once
        if action == "draw":
            self._terminal("d", "no-legal-move")
            return True, changed_once
        if action == "change-player":
            if changed_once:
                self._terminal("d", "no-legal-move")
                return True, changed_once
            self.state.side = other(self.state.side)
            self._synchronize_phase()
            return False, True
        original = self.state.side
        if action == "remove-and-retain":
            specs = [(original, other(original))]
            final_after = original
        elif action == "remove-and-change":
            specs = [(original, other(original))]
            final_after = other(original)
        elif action == "both-remove":
            specs = [(original, other(original)), (other(original), original)]
            final_after = original
        else:
            raise MIFError("unsupported-profile", f"unsupported stalemate action {action}", category="unsupported")
        branch: list[Obligation] = []
        for actor, owner in specs:
            targets = self._stalemate_targets(actor) if not branch else None
            if not branch and not targets:
                self._terminal(other(actor), "no-legal-move")
                return True, changed_once
            branch.append(Obligation(actor, "stalemate", "b", owner, 1, targets, final_after, copy.deepcopy(targets)))
        for index, obligation in enumerate(branch):
            obligation.after = "q" if index + 1 < len(branch) else final_after
        self._publish_branches([branch])
        return True, changed_once

    def _observation_applies(self) -> bool:
        config = self.rules.manifest["draw"]["repetition"]
        if config["count"] == 0 or self.state.outcome != "-" or self.state.obligations:
            return False
        if config["observation"] == "stable-moving-v1":
            return self.state.phase == "m" and self.state.action == "m"
        return self.state.phase in {"p", "m"} and self.state.action == self.state.phase

    def repetition_observation(self) -> dict[str, Any]:
        semantic = {
            key: self.state.semantic_wire_value(key, self.rules)
            for key in self.rules.required_state_keys
        }
        return {
            "profile": "repetition-observation-v1",
            "stateProfile": "mill24-state-v1",
            "semanticDigest": self.rules.semantic_digest,
            "board": self.state.board_text(),
            "side": self.state.side,
            "phase": self.state.phase,
            "action": self.state.action,
            "hands": [self.state.hands["w"], self.state.hands["b"]],
            "semantic": semantic,
        }

    def _observe_repetition(self, source: str, event_seq: int | None) -> int:
        if not self._observation_applies():
            return 0
        observation = self.repetition_observation()
        entry: dict[str, Any] = {"source": source, "key": observation}
        if source == "event":
            assert event_seq is not None
            entry["eventSeq"] = event_seq
        self.repetition_history.append(entry)
        canonical = jcs_bytes(observation)
        return sum(1 for item in self.repetition_history if jcs_bytes(item["key"]) == canonical)

    def _selected_no_progress_limit(self) -> int:
        config = self.rules.manifest["draw"]["noProgress"]
        if config["endgamePredicate"] == "either-player-live-equals-3" and any(
            self.state.live_count(player) == 3 for player in ("w", "b")
        ):
            return config["endgameLimit"]
        return config["normalLimit"]

    def _derive_claim_rights(self, repetition_count: int) -> None:
        reasons: list[str] = []
        no_progress = self.rules.manifest["draw"]["noProgress"]
        limit = self._selected_no_progress_limit()
        if no_progress["mode"] == "claim" and limit > 0 and self.state.no_progress >= limit:
            reasons.append("no-progress")
        repetition = self.rules.manifest["draw"]["repetition"]
        if repetition["mode"] == "claim" and repetition["count"] > 0 and repetition_count >= repetition["count"]:
            reasons.append("repetition")
        self.claim_rights = None if not reasons else {"actor": self.state.side, "reasons": reasons}

    def _stabilize(
        self,
        *,
        source: str,
        event_seq: int | None,
        boundary_pending: bool,
    ) -> None:
        changed_once = False
        for _ in range(64):
            if self.state.outcome != "-" or self.state.obligations:
                return
            if boundary_pending:
                boundary_pending = False
                if self._enter_global_boundary():
                    return
            if not self.state.empty_points() and self._board_full_effect():
                return
            if self._minimum_material():
                return
            self.state.action = self.state.phase
            if self.state.phase == "p" and not self.has_legal_primary():
                policy = self.rules.manifest["placing"]["noLegalPrimaryAction"]
                if policy == "loss":
                    self._terminal(other(self.state.side), "no-legal-primary-action", event_seq=event_seq)
                    return
                if policy == "draw":
                    self._terminal("d", "no-legal-primary-action", event_seq=event_seq)
                    return
                require(self.rules.manifest["boardFull"]["action"] != "disabled", "no-legal-primary-action-policy-invalid", "apply-board-full resolved to disabled", event_seq=event_seq)
                require(not self.state.empty_points(), "no-legal-primary-action-policy-invalid", "apply-board-full reached a non-full state", event_seq=event_seq)
                if self._board_full_effect():
                    return
            terminal_or_pending, new_guard = self._stalemate_effect(changed_once)
            if terminal_or_pending:
                return
            if new_guard != changed_once:
                changed_once = new_guard
                continue
            self.state.action = self.state.phase
            occurrence = self._observe_repetition(source, event_seq)
            repetition = self.rules.manifest["draw"]["repetition"]
            if repetition["mode"] == "automatic" and repetition["count"] > 0 and occurrence >= repetition["count"]:
                self._terminal("d", "repetition", event_seq=event_seq)
                return
            no_progress = self.rules.manifest["draw"]["noProgress"]
            limit = self._selected_no_progress_limit()
            if no_progress["mode"] == "automatic" and limit > 0 and self.state.no_progress >= limit:
                self._terminal("d", "no-progress", event_seq=event_seq)
                return
            self._derive_claim_rights(occurrence)
            self.state.action = self.state.phase
            return
        raise MIFError("x-stabilization-loop", "stable-boundary processing exceeded guard", category="resource")

    def _terminal(self, result: str, reason: str, *, event_seq: int | None = None, agreement: bool = False) -> None:
        if not agreement:
            self._expire_open_offer(event_seq)
        self.claim_rights = None
        self.state.side = "-"
        self.state.phase = "o"
        self.state.action = "o"
        self.state.obligations = []
        self.state.outcome = f"{result}:{reason}"

    def repetition_summary(self) -> dict[str, Any] | None:
        threshold = self.rules.manifest["draw"]["repetition"]["count"]
        if threshold == 0:
            return None
        observations: dict[bytes, tuple[bytes, int]] = {}
        for entry in self.repetition_history:
            canonical = jcs_bytes(entry["key"])
            digest = hashlib.sha256(canonical).digest()
            prior = observations.get(digest)
            if prior is not None and prior[0] != canonical:
                raise MIFError("repetition-observation-digest-collision", "unequal observations share a SHA-256 digest", category="integrity")
            count = 0 if prior is None else prior[1]
            observations[digest] = (canonical, min(threshold, count + 1))
        empty = [hashlib.sha256(b"\x00").digest()]
        for _ in range(256):
            empty.append(hashlib.sha256(b"\x02" + empty[-1] + empty[-1]).digest())
        nodes: dict[int, bytes] = {
            int.from_bytes(digest, "big"): hashlib.sha256(
                b"\x01" + digest + struct.pack(">Q", count)
            ).digest()
            for digest, (_, count) in observations.items()
        }
        for height in range(256):
            parents: dict[int, bytes] = {}
            for parent in {index >> 1 for index in nodes}:
                left = nodes.get(parent << 1, empty[height])
                right = nodes.get((parent << 1) | 1, empty[height])
                parents[parent] = hashlib.sha256(b"\x02" + left + right).digest()
            nodes = parents
        root = nodes.get(0, empty[256])
        return {"profile": "reset-count-smt-v1", "root": "sha256:" + root.hex()}

    def decision_state(self) -> dict[str, Any]:
        limits = [
            value
            for value in (
                self.rules.manifest["draw"]["noProgress"]["normalLimit"],
                self.rules.manifest["draw"]["noProgress"]["endgameLimit"],
            )
            if value > 0
        ]
        normalized_progress = None if not limits else min(self.state.no_progress, max(limits))
        semantic = {
            key: self.state.semantic_wire_value(key, self.rules)
            for key in self.rules.required_state_keys
        }
        open_offer = None
        if self.open_offer_index is not None:
            offerer = self.claims[self.open_offer_index]["actor"]
            available = [
                {"actor": other(offerer), "action": "accept"},
                {"actor": other(offerer), "action": "decline"},
                {"actor": offerer, "action": "withdraw"},
            ]
            available.sort(key=lambda item: (PLAYER_ORDER[item["actor"]], ACTION_ORDER[item["action"]]))
            open_offer = {"offerer": offerer, "available": available}
        return {
            "profile": "decision-state-v1",
            "stateProfile": "mill24-state-v1",
            "semanticDigest": self.rules.semantic_digest,
            "board": self.state.board_text(),
            "side": self.state.side,
            "phase": self.state.phase,
            "action": self.state.action,
            "hands": [self.state.hands["w"], self.state.hands["b"]],
            "obligations": self.state.obligations_text(),
            "noProgress": normalized_progress,
            "outcome": self.state.outcome,
            "semantic": semantic,
            "repetitionSummary": self.repetition_summary(),
            "openOffer": open_offer,
            "claimRights": copy.deepcopy(self.claim_rights),
        }

    def resumption_state(self, mstate: Mapping[str, Any]) -> dict[str, Any]:
        pre_origin_repetition: list[dict[str, Any]] = []
        for entry in mstate["repetitionHistory"]:
            if entry["source"] != "pre-origin":
                break
            pre_origin_repetition.append(copy.deepcopy(entry))
        replay_prefix = {
            "origin": copy.deepcopy(mstate["origin"]),
            "preOriginRepetition": pre_origin_repetition,
            "preOriginClaims": copy.deepcopy(mstate["preOriginClaims"]),
            "events": copy.deepcopy(mstate["events"]),
        }
        open_offer = None
        if self.open_offer_index is not None:
            record = self.claims[self.open_offer_index]
            open_offer = {
                "source": record["source"],
                "actor": record["actor"],
                "offerEventSeq": 0 if record["source"] == "pre-origin" else record["eventSeq"],
            }
        return {
            "profile": "resumption-state-v1",
            "positionFormat": "MFEN/1.0",
            "stateProfile": "mill24-state-v1",
            "semanticDigest": self.rules.semantic_digest,
            "current": self.state.serialize(self.rules),
            "replayPrefixDigest": jcs_digest(replay_prefix),
            "lastEventSeq": self.last_event_seq,
            "repetitionHistory": copy.deepcopy(self.repetition_history),
            "claims": copy.deepcopy(self.claims),
            "openOffer": open_offer,
            "claimRights": copy.deepcopy(self.claim_rights),
        }


def validate_ruleset_envelope(
    envelope: Mapping[str, Any],
    manifest: Mapping[str, Any] | None,
) -> Rules:
    if envelope["mode"] == "portable":
        embedded = envelope["manifest"]
        if manifest is not None:
            require(dict(manifest) == embedded, "manifest-conflict", "caller manifest differs from portable manifest", category="integrity")
        manifest = embedded
    else:
        require(manifest is not None, "manifest-missing", "reference ruleset requires caller resolver", category="integrity")
    assert manifest is not None
    rules = Rules(manifest)
    require(envelope["id"] == manifest["id"] and envelope["version"] == manifest["version"], "manifest-conflict", "ruleset ID/version mismatch", category="integrity")
    require(envelope["semanticDigest"] == rules.semantic_digest, "semantic-digest-mismatch", "ruleset semantic digest mismatch", category="integrity")
    if "documentDigest" in envelope:
        require(envelope["documentDigest"] == rules.document_digest, "document-digest-mismatch", "ruleset document digest mismatch", category="integrity")
    return rules


def replay_mstate(
    mstate: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any] | None = None,
) -> ReplayResult:
    document = copy.deepcopy(dict(mstate))
    validate_schema(document, "mstate-1.0.schema.json")
    rules = validate_ruleset_envelope(document["ruleset"], manifest)
    origin = parse_mfen(document["origin"], rules)
    parse_mfen(document["current"], rules)
    leading: list[dict[str, Any]] = []
    seen_non_pre_origin = False
    for entry in document["repetitionHistory"]:
        if entry["source"] == "pre-origin":
            require(not seen_non_pre_origin, "repetition-history-mismatch", "pre-origin repetition entry is not leading", category="replay")
            leading.append(copy.deepcopy(entry))
        else:
            seen_non_pre_origin = True
    for entry in leading:
        require(entry["key"]["semanticDigest"] == rules.semantic_digest, "semantic-digest-mismatch", "pre-origin observation semantic digest mismatch", category="integrity")
    session = Session(
        rules,
        origin,
        repetition_seed=leading,
        pre_origin_claims=document["preOriginClaims"],
    )
    session.stabilize_origin()
    for event in document["events"]:
        session.apply_event(event)
    current = session.state.serialize(rules)
    require(current == document["current"], "checkpoint-mismatch", "replayed current MFEN differs from checkpoint", category="replay")
    require(session.repetition_history == document["repetitionHistory"], "repetition-history-mismatch", "replayed repetition window differs from supplied history", category="replay")
    require(session.claims == document["claims"], "claims-mismatch", "replayed claim audit differs from supplied claims", category="replay")
    resumption = session.resumption_state(document)
    decision = session.decision_state()
    validate_schema(resumption, "resumption-state-v1.schema.json")
    validate_schema(decision, "decision-state-v1.schema.json")
    return ReplayResult(
        state=session.state.clone(),
        repetition_history=copy.deepcopy(session.repetition_history),
        claims=copy.deepcopy(session.claims),
        claim_rights=copy.deepcopy(session.claim_rights),
        resumption_state=resumption,
        resumption_digest=jcs_digest(resumption),
        decision_state=decision,
        decision_digest=jcs_digest(decision),
    )
