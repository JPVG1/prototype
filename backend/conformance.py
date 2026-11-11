"""
Scalable Online Conformance Checking Using Incremental Prefix-Alignment Computation
Based on: Daniel Schuster & Gero J. Kolhof (2020) - arXiv:2101.00958v1
"""

from __future__ import annotations
import heapq
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Transition:
    id: str
    label: Optional[str]
    name: str
    short_label: str
    in_places: List[str]
    out_places: List[str]
    sla_limit_min: int = 30
    is_rework: bool = False


@dataclass
class Place:
    id: str
    name: str
    short_label: str


class WorkflowNet:
    """
    Sound Workflow Net (WF-net) with places p1..p7 and transitions t1..t7.
    Can be instantiated with custom place/transition definitions for different processes.
    """

    def __init__(
        self,
        places: Dict[str, Place],
        transitions: Dict[str, Transition],
        initial_marking: Tuple[str, ...] = ("p1",),
    ) -> None:
        self.places = places
        self.transitions = transitions
        self.initial_marking = initial_marking

    def is_enabled(self, marking: Tuple[str, ...], trans_id: str) -> bool:
        t = self.transitions[trans_id]
        marking_set = set(marking)
        return all(p in marking_set for p in t.in_places)

    def fire(self, marking: Tuple[str, ...], trans_id: str) -> Tuple[str, ...]:
        t = self.transitions[trans_id]
        m_list = list(marking)
        for p in t.in_places:
            if p in m_list:
                m_list.remove(p)
        for p in t.out_places:
            m_list.append(p)
        return tuple(sorted(m_list))

    def to_dict(self) -> dict:
        return {
            "places": [
                {"id": p.id, "name": p.name, "short_label": p.short_label}
                for p in self.places.values()
            ],
            "transitions": [
                {
                    "id": t.id,
                    "label": t.label or "τ",
                    "name": t.name,
                    "short_label": t.short_label,
                    "in_places": t.in_places,
                    "out_places": t.out_places,
                    "sla_limit_min": t.sla_limit_min,
                    "is_rework": t.is_rework,
                }
                for t in self.transitions.values()
            ],
            "initial_marking": list(self.initial_marking),
        }


@dataclass
class AlignmentMove:
    """
    Represents a single column in a prefix-alignment γ:
    - move_type: 'SYNC' | 'REWORK' | 'MODEL_VISIBLE' | 'MODEL_INVISIBLE' | 'LOG'
    - log_activity: activity observed in trace (or '>>' for skip)
    - model_transition: transition label in WF-net (or '>>' for skip)
    - transition_id: ID of transition in WF-net if applicable
    - cost: 0 for SYNC, 0.5 for REWORK, 0.9 for MODEL_VISIBLE, 2.0 for LOG
    """
    move_type: str
    log_activity: str
    model_transition: str
    transition_id: Optional[str]
    cost: float

    def to_dict(self) -> dict:
        return {
            "move_type": self.move_type,
            "log_activity": self.log_activity,
            "model_transition": self.model_transition,
            "transition_id": self.transition_id,
            "cost": self.cost,
        }


@dataclass
class SearchState:
    """Intermediate search state in the Synchronous Product Net (SPN) state space."""
    cost: float
    trace_idx: int
    net_marking: Tuple[str, ...]
    moves: Tuple[AlignmentMove, ...] = field(compare=False)

    def __lt__(self, other: SearchState) -> bool:
        if round(self.cost, 4) != round(other.cost, 4):
            return self.cost < other.cost
        return self.trace_idx > other.trace_idx


@dataclass
class CaseAggregate:
    """Aggregate stored per running case for incremental prefix-alignment continuation."""
    case_id: str
    observed_prefix: List[str] = field(default_factory=list)
    prefix_alignment: List[AlignmentMove] = field(default_factory=list)
    current_marking: Tuple[str, ...] = ("p1",)
    alignment_cost: float = 0.0
    explored_states: Dict[Tuple[int, Tuple[str, ...]], SearchState] = field(default_factory=dict)


@dataclass
class PrefixCacheEntry:
    prefix: Tuple[str, ...]
    prefix_alignment: List[AlignmentMove]
    current_marking: Tuple[str, ...]
    alignment_cost: float
    explored_states: Dict[Tuple[int, Tuple[str, ...]], SearchState]
    frequency: int = 1


class IncrementalPrefixAligner:
    """
    Implements Incremental Prefix-Alignment Computation with Direct Synchronizing (DS)
    and Prefix Caching (CA) as described in Schuster & Kolhof (2020).
    """

    def __init__(self, wf_net: WorkflowNet, cache_capacity: int = 200) -> None:
        self.wf_net = wf_net
        self.cache_capacity = cache_capacity
        self.aggregates: Dict[str, CaseAggregate] = {}
        self.prefix_cache: OrderedDict[Tuple[str, ...], PrefixCacheEntry] = OrderedDict()

    def reset(self) -> None:
        self.aggregates.clear()
        self.prefix_cache.clear()

    def process_event(self, case_id: str, activity: str) -> CaseAggregate:
        if case_id not in self.aggregates:
            agg = CaseAggregate(
                case_id=case_id,
                current_marking=self.wf_net.initial_marking,
                explored_states={
                    (0, self.wf_net.initial_marking): SearchState(
                        cost=0.0,
                        trace_idx=0,
                        net_marking=self.wf_net.initial_marking,
                        moves=(),
                    )
                },
            )
            self.aggregates[case_id] = agg
        else:
            agg = self.aggregates[case_id]

        agg.observed_prefix.append(activity)
        new_prefix_tuple = tuple(agg.observed_prefix)

        # Check Prefix Cache
        if new_prefix_tuple in self.prefix_cache:
            entry = self.prefix_cache[new_prefix_tuple]
            entry.frequency += 1
            self.prefix_cache.move_to_end(new_prefix_tuple)

            agg.prefix_alignment = list(entry.prefix_alignment)
            agg.current_marking = entry.current_marking
            agg.alignment_cost = entry.alignment_cost
            agg.explored_states = dict(entry.explored_states)
            return agg

        # Direct Synchronizing pre-check
        sync_trans = self._check_direct_synchronizing(agg.current_marking, activity)
        if sync_trans is not None:
            move_type = "REWORK" if sync_trans.is_rework else "SYNC"
            move_cost = 0.5 if sync_trans.is_rework else 0.0
            new_move = AlignmentMove(
                move_type=move_type,
                log_activity=activity,
                model_transition=sync_trans.name,
                transition_id=sync_trans.id,
                cost=move_cost,
            )
            agg.prefix_alignment.append(new_move)
            agg.current_marking = self.wf_net.fire(agg.current_marking, sync_trans.id)
            agg.alignment_cost = round(agg.alignment_cost + move_cost, 4)
            k = len(agg.observed_prefix)
            agg.explored_states[(k, agg.current_marking)] = SearchState(
                cost=agg.alignment_cost,
                trace_idx=k,
                net_marking=agg.current_marking,
                moves=tuple(agg.prefix_alignment),
            )
            self._admit_to_cache(new_prefix_tuple, agg)
            return agg

        # Incremental Shortest-Path Search on Extended SPN
        best_state = self._continue_shortest_path_search(agg)
        agg.prefix_alignment = list(best_state.moves)
        agg.current_marking = best_state.net_marking
        agg.alignment_cost = round(best_state.cost, 4)

        self._admit_to_cache(new_prefix_tuple, agg)
        return agg

    def _check_direct_synchronizing(
        self, current_marking: Tuple[str, ...], activity: str
    ) -> Optional[Transition]:
        for t in self.wf_net.transitions.values():
            if t.label == activity and self.wf_net.is_enabled(current_marking, t.id):
                return t
        return None

    def _continue_shortest_path_search(self, agg: CaseAggregate) -> SearchState:
        target_idx = len(agg.observed_prefix)
        pq: List[SearchState] = list(agg.explored_states.values())
        heapq.heapify(pq)

        best_costs: Dict[Tuple[int, Tuple[str, ...]], float] = {
            k: v.cost for k, v in agg.explored_states.items()
        }

        while pq:
            state = heapq.heappop(pq)

            if state.trace_idx == target_idx:
                return state

            state_key = (state.trace_idx, state.net_marking)
            if state.cost > best_costs.get(state_key, float("inf")) + 1e-6:
                continue

            next_activity = agg.observed_prefix[state.trace_idx]

            # 1. Synchronous Moves and Model Moves
            for t in self.wf_net.transitions.values():
                if self.wf_net.is_enabled(state.net_marking, t.id):
                    next_marking = self.wf_net.fire(state.net_marking, t.id)

                    if t.label == next_activity:
                        m_type = "REWORK" if t.is_rework else "SYNC"
                        m_cost = 0.5 if t.is_rework else 0.0
                        sync_move = AlignmentMove(
                            move_type=m_type,
                            log_activity=next_activity,
                            model_transition=t.name,
                            transition_id=t.id,
                            cost=m_cost,
                        )
                        nxt = SearchState(
                            cost=round(state.cost + m_cost, 4),
                            trace_idx=state.trace_idx + 1,
                            net_marking=next_marking,
                            moves=state.moves + (sync_move,),
                        )
                        nxt_key = (nxt.trace_idx, nxt.net_marking)
                        if nxt.cost < best_costs.get(nxt_key, float("inf")) - 1e-6:
                            best_costs[nxt_key] = nxt.cost
                            agg.explored_states[nxt_key] = nxt
                            heapq.heappush(pq, nxt)

                    # Do not fire optional rework loops as skipped model moves
                    if not t.is_rework:
                        move_cost = 0.0 if t.label is None else 0.9
                        move_type = "MODEL_INVISIBLE" if t.label is None else "MODEL_VISIBLE"
                        model_move = AlignmentMove(
                            move_type=move_type,
                            log_activity=">>",
                            model_transition=t.name if t.label else "τ",
                            transition_id=t.id,
                            cost=move_cost,
                        )
                        nxt_model = SearchState(
                            cost=round(state.cost + move_cost, 4),
                            trace_idx=state.trace_idx,
                            net_marking=next_marking,
                            moves=state.moves + (model_move,),
                        )
                        nxt_m_key = (nxt_model.trace_idx, nxt_model.net_marking)
                        if nxt_model.cost < best_costs.get(nxt_m_key, float("inf")) - 1e-6:
                            best_costs[nxt_m_key] = nxt_model.cost
                            agg.explored_states[nxt_m_key] = nxt_model
                            heapq.heappush(pq, nxt_model)

            # 2. Log Move (repeated or out-of-order step)
            log_move = AlignmentMove(
                move_type="LOG",
                log_activity=next_activity,
                model_transition=">>",
                transition_id=None,
                cost=2.0,
            )
            nxt_log = SearchState(
                cost=round(state.cost + 2.0, 4),
                trace_idx=state.trace_idx + 1,
                net_marking=state.net_marking,
                moves=state.moves + (log_move,),
            )
            nxt_l_key = (nxt_log.trace_idx, nxt_log.net_marking)
            if nxt_log.cost < best_costs.get(nxt_l_key, float("inf")) - 1e-6:
                best_costs[nxt_l_key] = nxt_log.cost
                agg.explored_states[nxt_l_key] = nxt_log
                heapq.heappush(pq, nxt_log)

        fallback_move = AlignmentMove("LOG", agg.observed_prefix[-1], ">>", None, 2.0)
        return SearchState(
            cost=round(agg.alignment_cost + 2.0, 4),
            trace_idx=target_idx,
            net_marking=agg.current_marking,
            moves=tuple(agg.prefix_alignment) + (fallback_move,),
        )

    def _admit_to_cache(
        self, prefix_tuple: Tuple[str, ...], agg: CaseAggregate
    ) -> None:
        if prefix_tuple in self.prefix_cache:
            entry = self.prefix_cache[prefix_tuple]
            entry.frequency += 1
            self.prefix_cache.move_to_end(prefix_tuple)
            return

        if len(self.prefix_cache) >= self.cache_capacity:
            victim_key = min(
                self.prefix_cache.keys(),
                key=lambda k: self.prefix_cache[k].frequency,
            )
            del self.prefix_cache[victim_key]

        self.prefix_cache[prefix_tuple] = PrefixCacheEntry(
            prefix=prefix_tuple,
            prefix_alignment=list(agg.prefix_alignment),
            current_marking=agg.current_marking,
            alignment_cost=agg.alignment_cost,
            explored_states=dict(agg.explored_states),
            frequency=1,
        )
