"""
Real-Time Process Monitor — Stream Orchestrator & Multi-Process Case Generator.

Manages:
  - 3 Intraday Processes with Petri-Net (WorkflowNet) models designed for a 1–3 hour horizon
  - 4 Stream Time Snapshots (09:00, 11:00, 13:30, 16:00)
  - 2 Detection Methods:
      1) Petri-Net Conformance Checking (Online A* Prefix Alignment)
      2) SLA & Timestamp Monitoring (Step Deadlines + Overall 3-Hour Case SLA)
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.conformance import (
    OnlineAlignmentTracker,
    Place,
    Transition,
    WorkflowNet,
)


def _create_linear_rework_net(
    place_specs: List[tuple],
    trans_specs: List[tuple],
) -> WorkflowNet:
    places = {
        pid: Place(pid, pname, pshort)
        for pid, pname, pshort in place_specs
    }
    transitions = {
        tid: Transition(
            id=tid,
            label=tlabel,
            short_label=tshort,
            unit=tunit,
            sla_limit_min=tsla,
        )
        for tid, tlabel, tshort, tunit, tsla in trans_specs
    }
    preset = {
        "t1": {"p1"},
        "t2": {"p2"},
        "t3": {"p3"},
        "t4": {"p4"},
        "t5": {"p5"},
        "t6": {"p6"},
        "t7": {"p3"},
    }
    postset = {
        "t1": {"p2"},
        "t2": {"p3"},
        "t3": {"p4"},
        "t4": {"p5"},
        "t5": {"p6"},
        "t6": {"p7"},
        "t7": {"p2"},
    }
    return WorkflowNet(
        places=places,
        transitions=transitions,
        preset=preset,
        postset=postset,
        initial_marking=frozenset(["p1"]),
        final_marking=frozenset(["p7"]),
    )


def _build_process_definitions() -> List[dict]:
    # Process 1: Order-to-Cash & Credit Approval (Intraday 3-hour SLA)
    net_1 = _create_linear_rework_net(
        place_specs=[
            ("p1", "Application Received", "p1 (Start)"),
            ("p2", "Application Created", "p2 (App Created)"),
            ("p3", "Identity Verified", "p3 (ID Verified)"),
            ("p4", "Credit Risk Checked", "p4 (Risk Checked)"),
            ("p5", "Credit Approved", "p5 (Approved)"),
            ("p6", "Binding Offer Sent", "p6 (Offer Sent)"),
            ("p7", "Completed & Disbursed", "p7 (Sink)"),
        ],
        trans_specs=[
            ("t1", "Create Application", "Create App", "Sales Desk", 20),
            ("t2", "Verify Identity", "Verify ID", "KYC Service", 30),
            ("t3", "Check Credit Risk", "Credit Check", "Risk Engine", 40),
            ("t4", "Approve Credit", "Approve", "Underwriting", 35),
            ("t5", "Send Binding Offer", "Send Offer", "Sales Desk", 25),
            ("t6", "Finalize & Disburse", "Finalize", "Core Banking", 30),
            ("t7", "Re-verify Identity", "Re-verify ID", "KYC Service", 25),
        ],
    )

    # Process 2: Purchase-to-Pay & Express Invoice Approval (Intraday 3-hour SLA)
    net_2 = _create_linear_rework_net(
        place_specs=[
            ("p1", "Requisition Created", "p1 (Start)"),
            ("p2", "Requisition Submitted", "p2 (Submitted)"),
            ("p3", "Vendor Validated", "p3 (Vendor OK)"),
            ("p4", "Budget Checked", "p4 (Budget OK)"),
            ("p5", "PO Issued", "p5 (PO Issued)"),
            ("p6", "Invoice Verified", "p6 (Invoice OK)"),
            ("p7", "Payment Executed", "p7 (Paid)"),
        ],
        trans_specs=[
            ("t1", "Submit Requisition", "Submit Req", "Requester", 20),
            ("t2", "Validate Vendor Data", "Validate Vendor", "Procurement", 30),
            ("t3", "Check Budget Limit", "Budget Check", "Controlling", 35),
            ("t4", "Issue Purchase Order", "Issue PO", "Procurement Lead", 30),
            ("t5", "Verify E-Invoice", "Verify Invoice", "Accounts Payable", 35),
            ("t6", "Execute Payment", "Pay Invoice", "Treasury", 30),
            ("t7", "Re-validate Vendor", "Re-validate", "Procurement", 25),
        ],
    )

    # Process 3: Customer Onboarding & KYC Compliance (Intraday 3-hour SLA)
    net_3 = _create_linear_rework_net(
        place_specs=[
            ("p1", "Registration Started", "p1 (Start)"),
            ("p2", "Customer Registered", "p2 (Registered)"),
            ("p3", "ID Documents Checked", "p3 (Docs Checked)"),
            ("p4", "PEP & Sanctions Cleared", "p4 (Sanctions OK)"),
            ("p5", "Compliance Signed Off", "p5 (Compliance OK)"),
            ("p6", "Contract Countersigned", "p6 (Contract OK)"),
            ("p7", "Account Activated", "p7 (Active)"),
        ],
        trans_specs=[
            ("t1", "Register Customer", "Register", "Onboarding Portal", 15),
            ("t2", "Check ID Documents", "Check ID", "Document AI", 30),
            ("t3", "Sanctions & PEP Check", "Sanctions Check", "Compliance Screening", 35),
            ("t4", "Compliance Sign-Off", "Compliance Sign", "AML Officer", 35),
            ("t5", "Countersign Contract", "Sign Contract", "Legal Desk", 25),
            ("t6", "Activate Account", "Activate", "Core Platform", 20),
            ("t7", "Re-check ID Docs", "Re-check ID", "Document AI", 25),
        ],
    )

    return [
        {
            "process_id": "PROC-001",
            "case_prefix": "CRD",
            "name": "Express Credit Application & Loan Disbursement",
            "log_file": "express_credit_disbursement.xes",
            "created_date": "2025-05-12 06:00",
            "status": "Active",
            "case_sla_limit_min": 180,
            "detection_methods": [
                "Petri-Net Conformance Checking",
                "SLA & Timestamp Monitoring",
            ],
            "wf_net_obj": net_1,
        },
        {
            "process_id": "PROC-002",
            "case_prefix": "INV",
            "name": "Urgent Purchase Order & E-Invoice Payment",
            "log_file": "urgent_po_einvoice_payment.xes",
            "created_date": "2025-05-12 06:00",
            "status": "Active",
            "case_sla_limit_min": 180,
            "detection_methods": [
                "Petri-Net Conformance Checking",
                "SLA & Timestamp Monitoring",
            ],
            "wf_net_obj": net_2,
        },
        {
            "process_id": "PROC-003",
            "case_prefix": "KYC",
            "name": "Digital Bank Account Opening & KYC Check",
            "log_file": "digital_account_kyc_stream.csv",
            "created_date": "2025-05-12 06:00",
            "status": "Active",
            "case_sla_limit_min": 180,
            "detection_methods": [
                "Petri-Net Conformance Checking",
                "SLA & Timestamp Monitoring",
            ],
            "wf_net_obj": net_3,
        },
    ]


TIME_SNAPSHOTS: List[dict] = [
    {
        "id": "T1",
        "short_label": "09:00",
        "timestamp": "2025-05-12 09:00:00",
        "prev_timestamp": "2025-05-12 06:00:00",
    },
    {
        "id": "T2",
        "short_label": "11:00",
        "timestamp": "2025-05-12 11:00:00",
        "prev_timestamp": "2025-05-12 09:00:00",
    },
    {
        "id": "T3",
        "short_label": "13:30",
        "timestamp": "2025-05-12 13:30:00",
        "prev_timestamp": "2025-05-12 11:00:00",
    },
    {
        "id": "T4",
        "short_label": "16:00 (Latest)",
        "timestamp": "2025-05-12 16:00:00",
        "prev_timestamp": "2025-05-12 13:30:00",
    },
]


class StreamOrchestrator:
    """
    Manages the multi-process case stream across the 4 intraday time snapshots.
    """

    def __init__(self) -> None:
        self.process_defs: List[dict] = _build_process_definitions()
        self.process_map: Dict[str, dict] = {
            p["process_id"]: p for p in self.process_defs
        }
        self.settings: dict = {
            "notify_yellow": False,
            "notify_red": True,
        }
        self.selected_time_id: str = "T4"
        self.master_raw_cases: List[dict] = self._generate_master_raw_cases()

    def _generate_master_raw_cases(self) -> List[dict]:
        """
        Generates 100 cases per process (300 total across the day) distributed across
        the 4 stream batches (T1..T4). Every event timestamp advances by its true
        step duration (`dur_min`) from `arrival_timestamp`, fitting a realistic
        1 to 3.5 hour case execution horizon.
        """
        batch_configs = [
            # (batch_id, window_start_str, cutoff_str, count_per_process)
            ("T1", "2025-05-12 06:15:00", "2025-05-12 09:00:00", 25),
            ("T2", "2025-05-12 09:02:00", "2025-05-12 11:00:00", 25),
            ("T3", "2025-05-12 11:02:00", "2025-05-12 13:30:00", 25),
            ("T4", "2025-05-12 13:32:00", "2025-05-12 16:00:00", 25),
        ]

        # 25 archetypes per batch per process covering all Conformance & SLA combinations
        batch_archetypes = [
            "CLEAN_GREEN", "CLEAN_GREEN", "CLEAN_GREEN", "CLEAN_GREEN", "CLEAN_GREEN",
            "CLEAN_GREEN", "CLEAN_GREEN", "CLEAN_GREEN", "CLEAN_GREEN", "CLEAN_GREEN",
            "CLEAN_GREEN", "CLEAN_GREEN",
            "CLEAN_SLA_ORANGE", "CLEAN_SLA_ORANGE", "CLEAN_SLA_ORANGE",
            "CLEAN_SLA_RED", "CLEAN_SLA_RED",
            "REWORK_T2", "REWORK_T2",
            "REPEAT_T2", "REPEAT_T2",
            "SKIP_T3",
            "SKIP_T4_APPROVAL", "SKIP_T4_APPROVAL",
            "SKIP_AND_SLA_RED",
        ]

        raw_cases: List[dict] = []

        for p_idx, pdef in enumerate(self.process_defs):
            wf_net: WorkflowNet = pdef["wf_net_obj"]
            t_map = wf_net.transitions
            prefix = pdef["case_prefix"]
            case_counter = 1

            for b_idx, (batch_id, win_start_str, cutoff_str, count) in enumerate(batch_configs):
                win_start_dt = datetime.strptime(win_start_str, "%Y-%m-%d %H:%M:%S")
                cutoff_dt = datetime.strptime(cutoff_str, "%Y-%m-%d %H:%M:%S")
                window_minutes = int((cutoff_dt - win_start_dt).total_seconds() // 60)

                for i in range(count):
                    case_id = f"{prefix}-{1000 + case_counter}"
                    case_counter += 1
                    archetype = batch_archetypes[i % len(batch_archetypes)]

                    # Build step sequence (transition_id, duration_min)
                    seq: List[tuple] = []

                    if archetype == "CLEAN_GREEN":
                        # Full 6-step valid trace (~95-110 min total, well within 180m SLA).
                        # Depending on arrival time within the batch, some finish inside the
                        # current snapshot while later arrivals are in flight (p2..p6) and
                        # progress in subsequent snapshots.
                        seq = [
                            ("t1", 11 + (i % 4)),
                            ("t2", 16 + (i % 5)),
                            ("t3", 20 + (i % 5)),
                            ("t4", 17 + (i % 4)),
                            ("t5", 15 + (i % 4)),
                            ("t6", 15 + (i % 4)),
                        ]
                        # For the last snapshot (T4), also keep a few green cases at 2..5 steps
                        # so active in-flight positions p2..p6 are always populated at 16:00.
                        if batch_id == "T4" and i < 8:
                            target_len = 2 + (i % 4)  # 2, 3, 4, 5 steps
                            seq = seq[:target_len]

                    elif archetype == "CLEAN_SLA_ORANGE":
                        # Valid conformance order, but t2 or t3 exceeds its step SLA moderately (36-44m vs 30-35m)
                        seq = [
                            ("t1", 12 + (i % 3)),
                            ("t2", 38 + (i % 5)),
                            ("t3", 22 + (i % 4)),
                            ("t4", 18 + (i % 4)),
                        ]
                        if i % 2 == 1:
                            seq.append(("t5", 16 + (i % 3)))

                    elif archetype == "CLEAN_SLA_RED":
                        # Valid conformance order, but severe bottleneck on t2 & t3
                        # (t2 takes 56-62m vs 30m SLA -> severe step SLA breach;
                        #  5-step total reaches ~190-200m vs 180m Case SLA)
                        seq = [
                            ("t1", 14),
                            ("t2", 58 + (i % 5)),
                            ("t3", 68 + (i % 6)),
                            ("t4", 26),
                            ("t5", 22),
                        ]

                    elif archetype == "REWORK_T2":
                        # Minor conformance deviation: executes rework loop t7 after t2
                        seq = [
                            ("t1", 11),
                            ("t2", 18),
                            ("t7", 15 + (i % 4)),
                            ("t2", 16),
                            ("t3", 21),
                        ]
                        if i % 2 == 0:
                            seq.append(("t4", 18))

                    elif archetype == "REPEAT_T2":
                        # Minor conformance deviation: duplicate/repeated t2 event without rework transition
                        seq = [
                            ("t1", 12),
                            ("t2", 17),
                            ("t2", 14 + (i % 4)),
                            ("t3", 20),
                        ]
                        if i % 2 == 1:
                            seq.append(("t4", 18))

                    elif archetype == "SKIP_T3":
                        # Severe conformance deviation: skips mandatory risk/budget/sanctions check (t3)
                        seq = [
                            ("t1", 12),
                            ("t2", 18),
                            ("t4", 19),
                            ("t5", 16),
                        ]

                    elif archetype == "SKIP_T4_APPROVAL":
                        # Severe conformance deviation: skips mandatory approval/PO/compliance sign-off (t4)
                        seq = [
                            ("t1", 11),
                            ("t2", 17),
                            ("t3", 21),
                            ("t5", 16),
                        ]
                        if i % 2 == 0:
                            seq.append(("t6", 15))

                    elif archetype == "SKIP_AND_SLA_RED":
                        # Both Severe Conformance (skips t4) AND Severe SLA Breach (t3 takes 72m)
                        seq = [
                            ("t1", 14),
                            ("t2", 24),
                            ("t3", 72),
                            ("t5", 22),
                        ]

                    # Compute arrival timestamp (`start_dt`) within the batch window:
                    # - Deviating archetypes (i >= 12) arrive in the first half of the batch window
                    #   so their deviating step is already visible within the batch's own snapshot.
                    # - Clean green archetypes (i < 12) are spread across the entire batch window
                    #   so earlier ones finish within the snapshot and later ones are in-flight (p2..p6)
                    #   at the current snapshot and advance in the next snapshot.
                    if i >= 12:
                        # Ensure all steps up to the key deviating step finish before cutoff_dt
                        req_min = sum(d for _, d in seq[:4]) + 4
                        max_offset = max(4, window_minutes - req_min)
                        offset_min = ((i - 12) * max(1, max_offset // 13) + p_idx * 2) % max(1, max_offset)
                    else:
                        # Spread clean cases across the window, keeping at least 18 min before cutoff_dt
                        # so t1 always finishes before cutoff_dt
                        max_offset = max(6, window_minutes - 18)
                        offset_min = (i * (max_offset // 12) + p_idx * 3 + b_idx) % max_offset

                    start_dt = win_start_dt + timedelta(minutes=offset_min, seconds=(i * 13 + p_idx * 17) % 50)
                    cur_dt = start_dt

                    events: List[dict] = []
                    for tid, dur_min in seq:
                        tr = t_map[tid]
                        cur_dt = cur_dt + timedelta(minutes=dur_min)
                        events.append(
                            {
                                "transition_id": tid,
                                "activity": tr.label,
                                "unit": tr.unit,
                                "duration_min": dur_min,
                                "sla_limit_min": tr.sla_limit_min,
                                "timestamp": cur_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            }
                        )

                    raw_cases.append(
                        {
                            "case_id": case_id,
                            "process_id": pdef["process_id"],
                            "process_name": pdef["name"],
                            "case_sla_limit_min": pdef["case_sla_limit_min"],
                            "arrival_batch": batch_id,
                            "arrival_timestamp": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            "events": events,
                        }
                    )

        return raw_cases

    def set_time_snapshot(self, time_id: str) -> dict:
        valid_ids = {s["id"] for s in TIME_SNAPSHOTS}
        if time_id in valid_ids:
            self.selected_time_id = time_id
        return self.get_full_state()

    def update_settings(self, notify_yellow: bool, notify_red: bool) -> dict:
        self.settings["notify_yellow"] = bool(notify_yellow)
        self.settings["notify_red"] = bool(notify_red)
        return self.get_full_state()

    def _evaluate_case_at_snapshot(
        self,
        rc: dict,
        cutoff_ts: str,
        prev_cutoff_ts: str,
    ) -> Optional[dict]:
        """
        Filters a case's events up to `cutoff_ts` and evaluates both:
        1) Petri-Net Conformance Checking
        2) SLA & Timestamp Monitoring
        """
        visible_raw_events = [
            ev for ev in rc["events"] if ev["timestamp"] <= cutoff_ts
        ]
        if not visible_raw_events:
            return None

        arrival_ts = rc["arrival_timestamp"]
        last_ts = visible_raw_events[-1]["timestamp"]
        is_from_last_update = prev_cutoff_ts < arrival_ts <= cutoff_ts

        pdef = self.process_map[rc["process_id"]]
        wf_net: WorkflowNet = pdef["wf_net_obj"]
        tracker = OnlineAlignmentTracker(wf_net)

        evaluated_events: List[dict] = []
        prev_moves_len = 0
        cumulative_min = 0

        has_severe_conf = False
        has_minor_conf = False
        has_severe_sla = False
        has_minor_sla = False

        for idx, ev in enumerate(visible_raw_events):
            act = ev["activity"]
            dur = ev["duration_min"]
            limit = ev["sla_limit_min"]
            cumulative_min += dur

            res = tracker.ingest_event(act)
            new_moves = res["alignment_moves"][prev_moves_len:]
            prev_moves_len = len(res["alignment_moves"])

            # 1. Conformance evaluation for this event
            skipped_models = [
                m for m in new_moves if m["move_type"] == "MODEL_VISIBLE"
            ]
            log_only_moves = [
                m for m in new_moves if m["move_type"] == "LOG_ONLY"
            ]
            rework_moves = [
                m for m in new_moves if m["move_type"] == "REWORK"
            ]

            is_dev = False
            dev_type = "None"
            dev_severity = "GREEN"
            dev_explanation = "Step executed in valid Petri net order."

            if skipped_models:
                is_dev = True
                has_severe_conf = True
                dev_severity = "RED"
                skipped_names = ", ".join(
                    f"'{m['transition_name']}'" for m in skipped_models
                )
                dev_type = f"Skipped Mandatory Step ({skipped_names})"
                dev_explanation = (
                    f"Severe Deviation: Mandatory transition {skipped_names} was skipped "
                    f"before executing '{act}'."
                )
            elif log_only_moves:
                is_dev = True
                has_minor_conf = True
                dev_severity = "ORANGE"
                dev_type = "Unexpected / Repeated Activity"
                dev_explanation = (
                    f"Minor Deviation: Activity '{act}' was repeated or executed out of sequence."
                )
            elif rework_moves:
                is_dev = True
                has_minor_conf = True
                dev_severity = "ORANGE"
                dev_type = "Rework Loop"
                dev_explanation = (
                    f"Minor Deviation: Case took rework loop '{act}' back to an earlier checkpoint."
                )

            # 2. SLA & Timestamp evaluation for this event
            overrun = max(0, dur - limit)
            if dur <= limit:
                sla_status = "GREEN"
                sla_badge = "✓ ON TIME"
                sla_expl = f"Completed in {dur} min (within step SLA limit of ≤ {limit} min)."
            elif dur >= int(limit * 1.65):
                sla_status = "RED"
                has_severe_sla = True
                sla_badge = f"🚨 +{overrun}m BREACH"
                sla_expl = (
                    f"Severe Step SLA Breach: Step took {dur} min vs. {limit} min limit "
                    f"(+{overrun} min overdue)."
                )
            else:
                sla_status = "ORANGE"
                has_minor_sla = True
                sla_badge = f"⚠ +{overrun}m DELAY"
                sla_expl = (
                    f"Minor Step Delay: Step took {dur} min vs. {limit} min limit "
                    f"(+{overrun} min over target)."
                )

            evaluated_events.append(
                {
                    "step": idx + 1,
                    "transition_id": ev["transition_id"],
                    "activity": act,
                    "unit": ev["unit"],
                    "timestamp": ev["timestamp"],
                    "duration_min": dur,
                    "sla_limit_min": limit,
                    "cumulative_min": cumulative_min,
                    "marking_after": res["current_marking"],
                    "is_deviation": is_dev,
                    "deviation_type": dev_type,
                    "deviation_severity": dev_severity,
                    "deviation_explanation": dev_explanation,
                    "sla_status": sla_status,
                    "sla_badge": sla_badge,
                    "sla_explanation": sla_expl,
                }
            )

        case_sla_limit = rc["case_sla_limit_min"]
        if cumulative_min > case_sla_limit:
            has_severe_sla = True

        # Overall Case Conformance Classification
        conf_deviating_events = [
            e for e in evaluated_events if e["is_deviation"]
        ]
        if has_severe_conf:
            conf_cat = "RED"
            conf_label = "Severe Deviations"
            conf_reason = (
                "Online Petri-Net Conformance Checking detected skipped mandatory process step(s) "
                "in this trace."
            )
        elif has_minor_conf:
            conf_cat = "ORANGE"
            conf_label = "Minor Deviations"
            conf_reason = (
                "Online Petri-Net Conformance Checking detected rework or repeated activities, "
                "but no mandatory steps were skipped."
            )
        else:
            conf_cat = "GREEN"
            conf_label = "No Deviations"
            conf_reason = (
                "All executed events strictly follow the reference Petri net in valid order."
            )

        # Overall Case SLA Classification
        sla_deviating_events = [
            e for e in evaluated_events if e["sla_status"] in ("ORANGE", "RED")
        ]
        if has_severe_sla:
            sla_cat = "RED"
            sla_label = "Severe SLA Breach"
            if cumulative_min > case_sla_limit:
                sla_reason = (
                    f"Total case elapsed time ({cumulative_min} min) exceeded the maximum process "
                    f"SLA deadline of {case_sla_limit} min (+{cumulative_min - case_sla_limit} min overdue)."
                )
            else:
                sla_reason = (
                    f"Critical step deadline breach detected (total elapsed: {cumulative_min} min / "
                    f"{case_sla_limit} min case SLA)."
                )
        elif has_minor_sla:
            sla_cat = "ORANGE"
            sla_label = "Minor Deadline Delay"
            sla_reason = (
                f"One or more steps exceeded their target step deadline, while total case duration "
                f"({cumulative_min} min / {case_sla_limit} min) remains within the overall SLA."
            )
        else:
            sla_cat = "GREEN"
            sla_label = "Within SLA"
            sla_reason = (
                f"All executed steps completed on time (total elapsed: {cumulative_min} min / "
                f"{case_sla_limit} min case SLA)."
            )

        final_metrics = tracker.compute_incremental_metrics()
        current_marking = final_metrics["current_marking"]
        place_labels = [
            wf_net.places[pid].name if pid in wf_net.places else pid
            for pid in current_marking
        ]

        return {
            "case_id": rc["case_id"],
            "process_id": rc["process_id"],
            "process_name": rc["process_name"],
            "arrival_batch": rc["arrival_batch"],
            "is_from_last_update": is_from_last_update,
            "arrival_timestamp": arrival_ts,
            "last_timestamp": last_ts,
            "conformance_category": conf_cat,
            "conformance_label": conf_label,
            "conformance_reason": conf_reason,
            "conformance_deviating_events": conf_deviating_events,
            "sla_category": sla_cat,
            "sla_label": sla_label,
            "sla_reason": sla_reason,
            "sla_deviating_events": sla_deviating_events,
            "total_elapsed_min": cumulative_min,
            "case_sla_limit_min": case_sla_limit,
            "current_marking": current_marking,
            "current_place_label": (
                f"{current_marking[0]} — {place_labels[0]}"
                if current_marking
                else "Unknown"
            ),
            "events": evaluated_events,
            "alignment_moves": final_metrics["alignment_moves"],
        }

    def get_full_state(self) -> dict:
        snap = next(
            (s for s in TIME_SNAPSHOTS if s["id"] == self.selected_time_id),
            TIME_SNAPSHOTS[-1],
        )
        cutoff_ts = snap["timestamp"]
        prev_cutoff_ts = snap["prev_timestamp"]

        active_cases: List[dict] = []
        for rc in self.master_raw_cases:
            evaluated = self._evaluate_case_at_snapshot(
                rc, cutoff_ts, prev_cutoff_ts
            )
            if evaluated is not None:
                active_cases.append(evaluated)

        active_cases.sort(key=lambda c: c["last_timestamp"], reverse=True)

        counts_by_method = {
            "CONFORMANCE": {"GREEN": 0, "ORANGE": 0, "RED": 0},
            "SLA": {"GREEN": 0, "ORANGE": 0, "RED": 0},
        }
        for c in active_cases:
            counts_by_method["CONFORMANCE"][c["conformance_category"]] += 1
            counts_by_method["SLA"][c["sla_category"]] += 1

        processes_out: List[dict] = []
        for pdef in self.process_defs:
            pid = pdef["process_id"]
            wf_net: WorkflowNet = pdef["wf_net_obj"]
            p_cases = [c for c in active_cases if c["process_id"] == pid]

            p_counts = {
                "CONFORMANCE": {
                    "GREEN": sum(
                        1 for c in p_cases if c["conformance_category"] == "GREEN"
                    ),
                    "ORANGE": sum(
                        1 for c in p_cases if c["conformance_category"] == "ORANGE"
                    ),
                    "RED": sum(
                        1 for c in p_cases if c["conformance_category"] == "RED"
                    ),
                    "TOTAL": len(p_cases),
                },
                "SLA": {
                    "GREEN": sum(
                        1 for c in p_cases if c["sla_category"] == "GREEN"
                    ),
                    "ORANGE": sum(
                        1 for c in p_cases if c["sla_category"] == "ORANGE"
                    ),
                    "RED": sum(
                        1 for c in p_cases if c["sla_category"] == "RED"
                    ),
                    "TOTAL": len(p_cases),
                },
            }

            # How many active cases executed each transition up to the selected snapshot
            trans_case_counts: Dict[str, int] = {
                tid: 0 for tid in wf_net.transitions
            }
            place_case_counts: Dict[str, int] = {
                pl_id: 0 for pl_id in wf_net.places
            }

            for c in p_cases:
                executed_tids = {
                    ev["transition_id"]
                    for ev in c["events"]
                    if ev.get("transition_id")
                }
                for tid in executed_tids:
                    if tid in trans_case_counts:
                        trans_case_counts[tid] += 1
                for pl_id in c["current_marking"]:
                    if pl_id in place_case_counts:
                        place_case_counts[pl_id] += 1

            last_update_proc_count = sum(
                1 for c in p_cases if c["is_from_last_update"]
            )

            processes_out.append(
                {
                    "process_id": pid,
                    "name": pdef["name"],
                    "log_file": pdef["log_file"],
                    "created_date": pdef["created_date"],
                    "status": pdef["status"],
                    "case_sla_limit_min": pdef["case_sla_limit_min"],
                    "detection_methods": pdef["detection_methods"],
                    "counts_by_method": p_counts,
                    "last_update_count": last_update_proc_count,
                    "transition_case_counts": trans_case_counts,
                    "place_case_counts": place_case_counts,
                    "wf_net": wf_net.to_dict(),
                }
            )

        last_update_cases = [
            c for c in active_cases if c["is_from_last_update"]
        ]

        return {
            "selected_time_id": self.selected_time_id,
            "active_snapshot": snap,
            "time_snapshots": TIME_SNAPSHOTS,
            "counts_by_method": counts_by_method,
            "last_update_count": len(last_update_cases),
            "processes": processes_out,
            "cases": active_cases,
            "settings": self.settings,
        }
