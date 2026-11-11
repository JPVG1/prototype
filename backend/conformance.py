"""
Petri-Net (Workflow-Net) Engine & Online Prefix-Alignment Conformance Tracker.

Models a formal Workflow Net (Places, Transitions, Arcs, Initial & Final Markings)
and evaluates arriving event streams via A* prefix-alignment search.
"""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

Marking = FrozenSet[str]


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    short_label: str = ""


@dataclass(frozen=True)
class Transition:
    id: str
    label: str
    short_label: str = ""
    unit: str = "System"
    sla_limit_min: int = 30
    cost_model_skip: float = 0.9


@dataclass
class WorkflowNet:
    places: Dict[str, Place]
    transitions: Dict[str, Transition]
    preset: Dict[str, Set[str]]
    postset: Dict[str, Set[str]]
    initial_marking: Marking
    final_marking: Marking

    def is_enabled(self, marking: Marking, trans_id: str) -> bool:
        required = self.preset.get(trans_id, set())
        return required.issubset(marking)

    def fire(self, marking: Marking, trans_id: str) -> Marking:
        required = self.preset.get(trans_id, set())
        produced = self.postset.get(trans_id, set())
        return frozenset((set(marking) - required) | produced)

    def enabled_transitions(self, marking: Marking) -> List[Transition]:
        return [t for tid, t in self.transitions.items() if self.is_enabled(marking, tid)]

    def to_dict(self) -> dict:
        arcs = []
        for tid, pre_places in self.preset.items():
            for pid in sorted(pre_places):
                arcs.append({"source": pid, "target": tid, "type": "place_to_trans"})
        for tid, post_places in self.postset.items():
            for pid in sorted(post_places):
                arcs.append({"source": tid, "target": pid, "type": "trans_to_place"})

        return {
            "places": [
                {
                    "id": p.id,
                    "name": p.name,
                    "short_label": p.short_label or p.name,
                }
                for p in self.places.values()
            ],
            "transitions": [
                {
                    "id": t.id,
                    "name": t.label,
                    "short_label": t.short_label or t.label,
                    "unit": t.unit,
                    "sla_limit_min": t.sla_limit_min,
                }
                for t in self.transitions.values()
            ],
            "arcs": arcs,
            "initial_marking": list(self.initial_marking),
            "final_marking": list(self.final_marking),
        }


@dataclass
class AlignmentMove:
    move_type: str  # 'SYNC', 'REWORK', 'LOG_ONLY', 'MODEL_VISIBLE'
    transition_id: Optional[str]
    transition_name: str

    def to_dict(self) -> dict:
        return {
            "move_type": self.move_type,
            "transition_id": self.transition_id,
            "transition_name": self.transition_name,
        }


@dataclass(order=True)
class _SearchNode:
    f_score: float
    g_score: float = field(compare=False)
    trace_idx: int = field(compare=False)
    marking: Marking = field(compare=False)
    moves: Tuple[AlignmentMove, ...] = field(compare=False)


class OnlineAlignmentTracker:
    """
    Incremental prefix-alignment engine for an active case in a Workflow Net.
    """

    def __init__(self, wf_net: WorkflowNet) -> None:
        self.net = wf_net
        self.events: List[str] = []
        self.best_marking: Marking = wf_net.initial_marking
        self.best_moves: List[AlignmentMove] = []

    def ingest_event(self, activity: str) -> dict:
        self.events.append(activity)
        new_marking, step_moves = self._align_next_event(self.best_marking, activity)
        self.best_marking = new_marking
        self.best_moves.extend(step_moves)
        return self.compute_incremental_metrics()

    def _align_next_event(
        self, start_marking: Marking, next_event: str
    ) -> Tuple[Marking, List[AlignmentMove]]:
        start_node = _SearchNode(
            f_score=0.0,
            g_score=0.0,
            trace_idx=0,
            marking=start_marking,
            moves=tuple(),
        )
        open_heap: List[_SearchNode] = [start_node]
        visited: Dict[Tuple[int, Marking], float] = {}

        while open_heap:
            curr = heapq.heappop(open_heap)

            if curr.trace_idx == 1:
                return curr.marking, list(curr.moves)

            state_key = (curr.trace_idx, curr.marking)
            if state_key in visited and visited[state_key] <= curr.g_score:
                continue
            visited[state_key] = curr.g_score

            enabled = self.net.enabled_transitions(curr.marking)

            # 1. Synchronous move (or loop/rework transition t7)
            for trans in enabled:
                if trans.label == next_event:
                    next_marking = self.net.fire(curr.marking, trans.id)
                    is_rework = trans.id == "t7"
                    move_cost = 0.5 if is_rework else 0.0
                    move_type = "REWORK" if is_rework else "SYNC"
                    move = AlignmentMove(
                        move_type=move_type,
                        transition_id=trans.id,
                        transition_name=trans.label,
                    )
                    new_g = curr.g_score + move_cost
                    heapq.heappush(
                        open_heap,
                        _SearchNode(
                            f_score=new_g,
                            g_score=new_g,
                            trace_idx=1,
                            marking=next_marking,
                            moves=curr.moves + (move,),
                        ),
                    )

            # 2. Log move (unexpected / repeated activity at current marking)
            if len(curr.moves) == 0:
                log_move_cost = 2.0
                log_move = AlignmentMove(
                    move_type="LOG_ONLY",
                    transition_id=None,
                    transition_name=f"Unexpected / Repeated: {next_event}",
                )
                new_g_log = curr.g_score + log_move_cost
                heapq.heappush(
                    open_heap,
                    _SearchNode(
                        f_score=new_g_log,
                        g_score=new_g_log,
                        trace_idx=1,
                        marking=curr.marking,
                        moves=curr.moves + (log_move,),
                    ),
                )

            # 3. Model move (skipped mandatory transition in Petri net; rework loop t7 cannot be skipped)
            if len(curr.moves) < 3:
                for trans in enabled:
                    if trans.id == "t7":
                        continue
                    next_marking = self.net.fire(curr.marking, trans.id)
                    move_cost = trans.cost_model_skip
                    model_move = AlignmentMove(
                        move_type="MODEL_VISIBLE",
                        transition_id=trans.id,
                        transition_name=trans.label,
                    )
                    new_g_mod = curr.g_score + move_cost
                    heapq.heappush(
                        open_heap,
                        _SearchNode(
                            f_score=new_g_mod,
                            g_score=new_g_mod,
                            trace_idx=0,
                            marking=next_marking,
                            moves=curr.moves + (model_move,),
                        ),
                    )

        return start_marking, []

    def compute_incremental_metrics(self) -> dict:
        return {
            "current_marking": sorted(list(self.best_marking)),
            "alignment_moves": [m.to_dict() for m in self.best_moves],
        }
