"""
Real-Time Streaming Events - Orchestration Backend
Supports:
- Multiple Processes (with up to ~50 cases) and per-process Workflow Nets (Petri Nets)
- Time Snapshot Simulation (4 selectable timestamps showing cases arriving and progressing over time)
- Tracking newly arrived cases from the Last Update
- Two Detection Methods (Sequence Pattern Matching removed):
  1. Petri-Net Conformance Checking
  2. SLA & Timestamp Monitoring (visual deadline tracking per step and per case)
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from backend.conformance import IncrementalPrefixAligner, Place, Transition, WorkflowNet


TIME_SNAPSHOTS = [
    {
        "id": "T1",
        "timestamp": "2026-11-03 09:00:00",
        "prev_timestamp": "2026-11-03 00:00:00",
        "short_label": "09:00",
        "label": "2026-11-03 09:00 (Update 1 — Morning Batch)",
        "description": "Initial morning stream batch across all active processes.",
    },
    {
        "id": "T2",
        "timestamp": "2026-11-03 11:00:00",
        "prev_timestamp": "2026-11-03 09:00:00",
        "short_label": "11:00",
        "label": "2026-11-03 11:00 (Update 2 — Mid-Morning Stream)",
        "description": "Earlier cases progress further; new mid-morning cases arrive.",
    },
    {
        "id": "T3",
        "timestamp": "2026-11-03 13:30:00",
        "prev_timestamp": "2026-11-03 11:00:00",
        "short_label": "13:30",
        "label": "2026-11-03 13:30 (Update 3 — Afternoon Stream)",
        "description": "Midday progression and newly arrived afternoon cases.",
    },
    {
        "id": "T4",
        "timestamp": "2026-11-03 16:00:00",
        "prev_timestamp": "2026-11-03 13:30:00",
        "short_label": "16:00 (Latest)",
        "label": "2026-11-03 16:00 (Update 4 — Latest Stream State)",
        "description": "Latest stream state with up to 48 cases in Order-to-Cash.",
    },
]


def _build_process_definitions() -> Tuple[Dict[str, WorkflowNet], List[dict]]:
    nets: Dict[str, WorkflowNet] = {}

    # Process 1: Order-to-Cash & Credit Approval (up to 48 cases)
    nets["PROC-001"] = WorkflowNet(
        places={
            "p1": Place("p1", "Source (Start)", "p1 (Start)"),
            "p2": Place("p2", "App Registered", "p2 (Registered)"),
            "p3": Place("p3", "Identity Checked", "p3 (ID Checked)"),
            "p4": Place("p4", "Risk Assessed", "p4 (Risk Checked)"),
            "p5": Place("p5", "Approved", "p5 (Approved)"),
            "p6": Place("p6", "Offer Sent", "p6 (Offer Sent)"),
            "p7": Place("p7", "Sink (Closed)", "p7 (Closed)"),
        },
        transitions={
            "t1": Transition("t1", "Create Application", "Create Application", "Create App", ["p1"], ["p2"], sla_limit_min=15),
            "t2": Transition("t2", "Verify Identity", "Verify Identity", "Verify ID", ["p2"], ["p3"], sla_limit_min=30),
            "t3": Transition("t3", "Credit & Risk Check", "Credit & Risk Check", "Credit Check", ["p3"], ["p4"], sla_limit_min=45),
            "t4": Transition("t4", "Manager Approval", "Manager Approval", "Mgr Approval", ["p4"], ["p5"], sla_limit_min=45),
            "t5": Transition("t5", "Send Offer", "Send Offer", "Send Offer", ["p5"], ["p6"], sla_limit_min=25),
            "t6": Transition("t6", "Finalize & Disburse", "Finalize & Disburse", "Finalize", ["p6"], ["p7"], sla_limit_min=40),
            "t7": Transition("t7", "Request Documents", "Request Documents", "Request Docs", ["p3"], ["p2"], sla_limit_min=35, is_rework=True),
        },
    )

    # Process 2: Purchase-to-Pay & Invoice Approval (up to 28 cases)
    nets["PROC-002"] = WorkflowNet(
        places={
            "p1": Place("p1", "Source (Start)", "p1 (Start)"),
            "p2": Place("p2", "Requisition Logged", "p2 (PR Logged)"),
            "p3": Place("p3", "Vendor Verified", "p3 (Vendor OK)"),
            "p4": Place("p4", "Budget Cleared", "p4 (Budget OK)"),
            "p5": Place("p5", "PO Issued", "p5 (PO Sent)"),
            "p6": Place("p6", "Goods Received", "p6 (Goods Recv)"),
            "p7": Place("p7", "Sink (Paid)", "p7 (Paid)"),
        },
        transitions={
            "t1": Transition("t1", "Create Purchase Req", "Create Purchase Req", "Create PR", ["p1"], ["p2"], sla_limit_min=20),
            "t2": Transition("t2", "Verify Vendor", "Verify Vendor", "Verify Vendor", ["p2"], ["p3"], sla_limit_min=30),
            "t3": Transition("t3", "Budget Approval", "Budget Approval", "Budget Appr", ["p3"], ["p4"], sla_limit_min=45),
            "t4": Transition("t4", "Issue Purchase Order", "Issue Purchase Order", "Issue PO", ["p4"], ["p5"], sla_limit_min=25),
            "t5": Transition("t5", "Confirm Goods Receipt", "Confirm Goods Receipt", "Goods Receipt", ["p5"], ["p6"], sla_limit_min=50),
            "t6": Transition("t6", "Release Invoice Payment", "Release Invoice Payment", "Pay Invoice", ["p6"], ["p7"], sla_limit_min=30),
            "t7": Transition("t7", "Revise Quote", "Revise Quote", "Revise Quote", ["p3"], ["p2"], sla_limit_min=35, is_rework=True),
        },
    )

    # Process 3: Customer Onboarding & KYC Compliance (up to 16 cases)
    nets["PROC-003"] = WorkflowNet(
        places={
            "p1": Place("p1", "Source (Start)", "p1 (Start)"),
            "p2": Place("p2", "Profile Created", "p2 (Profile)"),
            "p3": Place("p3", "ID Docs Checked", "p3 (Docs OK)"),
            "p4": Place("p4", "Sanctions Screened", "p4 (KYC OK)"),
            "p5": Place("p5", "Compliance Approved", "p5 (Cleared)"),
            "p6": Place("p6", "Contract Signed", "p6 (Signed)"),
            "p7": Place("p7", "Sink (Active)", "p7 (Active)"),
        },
        transitions={
            "t1": Transition("t1", "Register Customer", "Register Customer", "Register", ["p1"], ["p2"], sla_limit_min=15),
            "t2": Transition("t2", "Check ID Documents", "Check ID Documents", "Check Docs", ["p2"], ["p3"], sla_limit_min=30),
            "t3": Transition("t3", "Sanctions & PEP Check", "Sanctions & PEP Check", "KYC Check", ["p3"], ["p4"], sla_limit_min=40),
            "t4": Transition("t4", "Compliance Sign-Off", "Compliance Sign-Off", "Compliance", ["p4"], ["p5"], sla_limit_min=45),
            "t5": Transition("t5", "Countersign Contract", "Countersign Contract", "Sign Contract", ["p5"], ["p6"], sla_limit_min=25),
            "t6": Transition("t6", "Activate Account", "Activate Account", "Activate", ["p6"], ["p7"], sla_limit_min=25),
            "t7": Transition("t7", "Re-Upload ID Scan", "Re-Upload ID Scan", "Re-Upload ID", ["p3"], ["p2"], sla_limit_min=30, is_rework=True),
        },
    )

    processes_meta = [
        {
            "process_id": "PROC-001",
            "name": "Order-to-Cash & Credit Approval Process",
            "created_date": "2026-10-28",
            "description": "High-volume order intake, identity verification, credit risk scoring, manager approval, and disbursement.",
            "log_file": "order_to_cash_events.xes",
            "status": "Active",
            "case_sla_limit_min": 200,
            "detection_methods": [
                "Petri-Net Conformance Checking",
                "SLA & Timestamp Monitoring",
            ],
        },
        {
            "process_id": "PROC-002",
            "name": "Purchase-to-Pay & Invoice Approval",
            "created_date": "2026-10-30",
            "description": "Corporate procurement workflow from purchase requisition and vendor verification to goods receipt and payment release.",
            "log_file": "purchase_to_pay_stream.xes",
            "status": "Active",
            "case_sla_limit_min": 200,
            "detection_methods": [
                "Petri-Net Conformance Checking",
                "SLA & Timestamp Monitoring",
            ],
        },
        {
            "process_id": "PROC-003",
            "name": "Customer Onboarding & KYC Compliance",
            "created_date": "2026-11-01",
            "description": "End-to-end onboarding of commercial clients with identity document checks, sanctions screening, and compliance sign-off.",
            "log_file": "kyc_onboarding_stream.xes",
            "status": "Active",
            "case_sla_limit_min": 180,
            "detection_methods": [
                "Petri-Net Conformance Checking",
                "SLA & Timestamp Monitoring",
            ],
        },
    ]

    return nets, processes_meta


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _generate_Master_Raw_Cases(nets: Dict[str, WorkflowNet]) -> List[dict]:
    """
    Generates realistic, domain-consistent cases across the 3 processes:
    - PROC-001: 48 cases (CASE-101 .. CASE-148)
    - PROC-002: 28 cases (P2P-201 .. P2P-228)
    - PROC-003: 16 cases (KYC-301 .. KYC-316)
    Each event has (activity_name, timestamp_str, unit_name, duration_min).
    Timestamps are distributed across the 4 update windows (T1 <= 09:00, T2 <= 11:00, T3 <= 13:30, T4 <= 16:00)
    so cases realistically arrive and progress over time.
    """
    all_raw: List[dict] = []

    process_configs = [
        {
            "process_id": "PROC-001",
            "prefix": "CASE",
            "start_num": 101,
            "total_cases": 48,
            "batch_Counts": [16, 12, 11, 9],  # T1: 16, T2: +12 (28), T3: +11 (39), T4: +9 (48)
            "units": {
                "t1": "Intake-Portal",
                "t2": "ID-Verification-Team",
                "t3": "Credit-Risk-Engine",
                "t4": "Credit-Approval-Board",
                "t5": "Offer-Desk",
                "t6": "Settlement-Unit",
                "t7": "Document-Clearing",
            },
        },
        {
            "process_id": "PROC-002",
            "prefix": "P2P",
            "start_num": 201,
            "total_cases": 28,
            "batch_Counts": [9, 7, 6, 6],  # T1: 9, T2: +7 (16), T3: +6 (22), T4: +6 (28)
            "units": {
                "t1": "Requester-Dept",
                "t2": "Vendor-Master-Desk",
                "t3": "Finance-Controlling",
                "t4": "Procurement-Buyer",
                "t5": "Central-Warehouse",
                "t6": "Accounts-Payable",
                "t7": "Sourcing-Team",
            },
        },
        {
            "process_id": "PROC-003",
            "prefix": "KYC",
            "start_num": 301,
            "total_cases": 16,
            "batch_Counts": [5, 4, 4, 3],  # T1: 5, T2: +4 (9), T3: +4 (13), T4: +3 (16)
            "units": {
                "t1": "Client-Gateway",
                "t2": "KYC-Doc-Specialists",
                "t3": "AML-Screening-System",
                "t4": "Compliance-Officer",
                "t5": "Legal-Contracting",
                "t6": "Core-Banking-Ops",
                "t7": "KYC-Support-Desk",
            },
        },
    ]

    # Batch start base times on 2026-11-03:
    # Batch 0: arrives between 07:35 and 08:52 (<= 09:00 T1)
    # Batch 1: arrives between 09:06 and 10:48 (<= 11:00 T2)
    # Batch 2: arrives between 11:06 and 13:18 (<= 13:30 T3)
    # Batch 3: arrives between 13:35 and 15:42 (<= 16:00 T4)
    batch_windows = [
        (datetime(2026, 11, 3, 7, 35, 0), 75),
        (datetime(2026, 11, 3, 9, 6, 0), 98),
        (datetime(2026, 11, 3, 11, 6, 0), 125),
        (datetime(2026, 11, 3, 13, 35, 0), 115),
    ]

    # Archetypes cycle to give a realistic mix of Conformance & SLA outcomes:
    # 0: Conformant + On-Time SLA (Clean Green in both) - full 6 steps
    # 1: Conformant + On-Time SLA (In progress: 4 steps)
    # 2: Conformant + Minor SLA Delay on t3 (Green Conformance, Orange SLA)
    # 3: Minor Conformance (Rework loop t1->t2->t7->t2->t3->t4) + On-Time SLA
    # 4: Minor Conformance (Repeated step t1->t2->t2->t3->t4->t5) + Minor SLA Delay
    # 5: Severe Conformance (Skips t4 Approval: t1->t2->t3->t5->t6) + On-Time SLA
    # 6: Conformant + Severe SLA Breach on t3 & t4 (Green Conformance, Red SLA)
    # 7: Conformant + On-Time SLA (In progress: 3 steps)
    # 8: Minor Conformance (Repeated t1->t1->t2->t3) + On-Time SLA
    # 9: Severe Conformance (Skips t3 & t4: t1->t2->t5->t6) + Severe SLA Breach (Red in both)
    archetypes = [
        "CLEAN_FULL",
        "CLEAN_4",
        "CLEAN_SLA_ORANGE",
        "REWORK_LOOP",
        "REPEATED_VERIFY",
        "SKIP_T4_APPROVAL",
        "CLEAN_SLA_RED",
        "CLEAN_3",
        "REPEATED_START",
        "SKIP_T3_T4_SLA_RED",
    ]

    for pconf in process_configs:
        pid = pconf["process_id"]
        net = nets[pid]
        trans = net.transitions
        units = pconf["units"]
        case_idx = 0

        for b_idx, b_count in enumerate(pconf["batch_Counts"]):
            win_start, win_span_min = batch_windows[b_idx]
            for i in range(b_count):
                cid = f"{pconf['prefix']}-{pconf['start_num'] + case_idx}"
                arch = archetypes[(case_idx + b_idx * 2) % len(archetypes)]

                # Spread arrival times evenly within the batch window
                offset_min = int((i / max(1, b_count)) * win_span_min) + (case_idx % 4)
                start_dt = win_start + timedelta(minutes=offset_min, seconds=(case_idx * 13) % 50)

                # Build planned transition sequence & step durations (minutes)
                if arch == "CLEAN_FULL":
                    seq = [
                        ("t1", 10),
                        ("t2", 22),
                        ("t3", 32),
                        ("t4", 34),
                        ("t5", 18),
                        ("t6", 28),
                    ]
                elif arch == "CLEAN_4":
                    seq = [
                        ("t1", 11),
                        ("t2", 24),
                        ("t3", 35),
                        ("t4", 36),
                    ]
                elif arch == "CLEAN_3":
                    seq = [
                        ("t1", 12),
                        ("t2", 21),
                        ("t3", 30),
                    ]
                elif arch == "CLEAN_SLA_ORANGE":
                    # Conformance is 100% valid, but t3 exceeds its step deadline moderately (+16m over limit)
                    t3_limit = trans["t3"].sla_limit_min
                    seq = [
                        ("t1", 12),
                        ("t2", 25),
                        ("t3", t3_limit + 16),
                        ("t4", 38),
                        ("t5", 20),
                    ]
                elif arch == "CLEAN_SLA_RED":
                    # Conformance is 100% valid, but t3 and t4 severely exceed SLA deadlines
                    t3_limit = trans["t3"].sla_limit_min
                    t4_limit = trans["t4"].sla_limit_min
                    seq = [
                        ("t1", 14),
                        ("t2", 28),
                        ("t3", int(t3_limit * 1.85) + 15),
                        ("t4", int(t4_limit * 1.75) + 12),
                        ("t5", 22),
                    ]
                elif arch == "REWORK_LOOP":
                    # Executes rework loop t7 (p3 -> p2) and then re-verifies t2 (p2 -> p3)
                    seq = [
                        ("t1", 11),
                        ("t2", 24),
                        ("t7", 26),
                        ("t2", 19),
                        ("t3", 33),
                        ("t4", 35),
                    ]
                elif arch == "REPEATED_VERIFY":
                    # Repeats t2 (Verify) twice and has a minor SLA overrun on the second t2
                    t2_limit = trans["t2"].sla_limit_min
                    seq = [
                        ("t1", 12),
                        ("t2", 25),
                        ("t2", t2_limit + 12),
                        ("t3", 34),
                        ("t4", 36),
                    ]
                elif arch == "REPEATED_START":
                    # Duplicate initial event t1
                    seq = [
                        ("t1", 10),
                        ("t1", 8),
                        ("t2", 23),
                        ("t3", 31),
                    ]
                elif arch == "SKIP_T4_APPROVAL":
                    # Skips mandatory approval t4 (goes from t3 directly to t5 -> t6)
                    seq = [
                        ("t1", 11),
                        ("t2", 22),
                        ("t3", 33),
                        ("t5", 19),
                        ("t6", 27),
                    ]
                else:  # SKIP_T3_T4_SLA_RED
                    # Skips both t3 and t4 AND has a severe SLA delay on t5
                    t5_limit = trans["t5"].sla_limit_min
                    seq = [
                        ("t1", 13),
                        ("t2", 27),
                        ("t5", int(t5_limit * 2.2) + 15),
                        ("t6", 35),
                    ]

                # Generate chronological timestamps
                # Ensure the first 2-3 events happen relatively quickly so that even in the arrival batch
                # deviations / progress are visible, while later steps stretch across subsequent time snapshots
                cur_dt = start_dt
                events_list = []
                for step_i, (tid, dur_min) in enumerate(seq):
                    if step_i == 0:
                        ev_dt = start_dt
                    else:
                        # Pace progression so early steps occur within the arrival window and later steps cross snapshots
                        time_step = dur_min if step_i >= 3 else min(dur_min, 16)
                        cur_dt = cur_dt + timedelta(minutes=time_step, seconds=15)
                        ev_dt = cur_dt

                    # Cap timestamps at 15:58 so all planned events for latest snapshot are <= 16:00:00
                    latest_cap = datetime(2026, 11, 3, 15, 58, 0)
                    if ev_dt > latest_cap:
                        ev_dt = latest_cap - timedelta(minutes=(len(seq) - step_i) * 2)

                    events_list.append({
                        "transition_id": tid,
                        "activity": trans[tid].name,
                        "timestamp": _fmt_ts(ev_dt),
                        "unit": units[tid],
                        "duration_min": dur_min,
                        "sla_limit_min": trans[tid].sla_limit_min,
                    })

                all_raw.append({
                    "case_id": cid,
                    "process_id": pid,
                    "arrival_batch": f"T{b_idx + 1}",
                    "events": events_list,
                })
                case_idx += 1

    return all_raw


class StreamOrchestrator:
    def __init__(self) -> None:
        self.nets, self.processes = _build_process_definitions()
        self.raw_cases = _generate_Master_Raw_Cases(self.nets)
        self.selected_time_id: str = "T4"

        # Notification Settings (Yellow and/or Red cases)
        self.settings: dict = {
            "notify_yellow": False,
            "notify_red": True,
        }

    def set_time_snapshot(self, time_id: str) -> dict:
        valid_ids = {t["id"] for t in TIME_SNAPSHOTS}
        if time_id in valid_ids:
            self.selected_time_id = time_id
        return self.get_full_state()

    def update_settings(self, notify_yellow: bool, notify_red: bool) -> dict:
        self.settings["notify_yellow"] = bool(notify_yellow)
        self.settings["notify_red"] = bool(notify_red)
        return self.get_full_state()

    def get_full_state(self, time_id: str | None = None) -> dict:
        if time_id:
            valid_ids = {t["id"] for t in TIME_SNAPSHOTS}
            if time_id in valid_ids:
                self.selected_time_id = time_id

        active_snap = next(
            (t for t in TIME_SNAPSHOTS if t["id"] == self.selected_time_id),
            TIME_SNAPSHOTS[-1],
        )
        cutoff_ts = active_snap["timestamp"]
        prev_cutoff_ts = active_snap["prev_timestamp"]

        # Create fresh aligners per process for the current time snapshot evaluation
        aligners: Dict[str, IncrementalPrefixAligner] = {
            pid: IncrementalPrefixAligner(net) for pid, net in self.nets.items()
        }
        proc_map = {p["process_id"]: p for p in self.processes}

        # Track per-process transition counts (how many cases had each event up to cutoff_ts)
        transition_case_counts: Dict[str, Dict[str, int]] = {
            pid: {tid: 0 for tid in net.transitions}
            for pid, net in self.nets.items()
        }
        place_case_counts: Dict[str, Dict[str, int]] = {
            pid: {pl_id: 0 for pl_id in net.places}
            for pid, net in self.nets.items()
        }

        evaluated_cases: List[dict] = []

        for rc in self.raw_cases:
            # Filter events that have occurred up to cutoff_ts
            visible_events = [
                ev for ev in rc["events"] if ev["timestamp"] <= cutoff_ts
            ]
            if not visible_events:
                continue

            cid = rc["case_id"]
            pid = rc["process_id"]
            p_meta = proc_map[pid]
            wf_net = self.nets[pid]
            aligner = aligners[pid]

            first_ts = visible_events[0]["timestamp"]
            last_ts = visible_events[-1]["timestamp"]
            is_from_last_update = prev_cutoff_ts < first_ts <= cutoff_ts

            detailed_events = []
            prev_cost = 0.0
            agg = None
            prev_moves_len = 0

            has_skipped_mandatory = False
            total_elapsed_min = 0
            sla_orange_steps = 0
            sla_red_steps = 0
            executed_tids_in_case = set()

            for idx, ev in enumerate(visible_events):
                act_name = ev["activity"]
                tid = ev["transition_id"]
                executed_tids_in_case.add(tid)

                agg = aligner.process_event(cid, act_name)
                new_moves = agg.prefix_alignment[prev_moves_len:]
                prev_moves_len = len(agg.prefix_alignment)

                cost_delta = round(agg.alignment_cost - prev_cost, 4)
                is_dev = cost_delta > 0

                # Determine Conformance step explanation
                dev_type = "Valid Step"
                dev_severity = "GREEN"
                dev_explanation = "Step executed in expected Petri net order."

                if is_dev:
                    skipped_in_step = [
                        m.model_transition
                        for m in new_moves
                        if m.move_type == "MODEL_VISIBLE"
                    ]
                    rework_in_step = any(m.move_type == "REWORK" for m in new_moves)

                    if skipped_in_step:
                        has_skipped_mandatory = True
                        dev_type = "Skipped Required Step"
                        dev_severity = "RED"
                        dev_explanation = (
                            f"Event '{act_name}' was executed prematurely: mandatory step(s) "
                            f"[{', '.join(skipped_in_step)}] were skipped!"
                        )
                    elif rework_in_step:
                        dev_type = "Rework Loop Step"
                        dev_severity = "ORANGE"
                        dev_explanation = (
                            f"Rework loop triggered via '{act_name}': case returned to "
                            f"{', '.join(agg.current_marking)} for re-verification."
                        )
                    else:
                        dev_type = "Repeated / Out-of-Turn Step"
                        dev_severity = "ORANGE"
                        dev_explanation = (
                            f"Duplicate or out-of-order execution of '{act_name}' at position "
                            f"[{', '.join(agg.current_marking)}]."
                        )

                # Determine SLA & Timestamp step status
                dur_min = ev["duration_min"]
                limit_min = ev["sla_limit_min"]
                total_elapsed_min += dur_min
                overrun_min = max(0, dur_min - limit_min)

                if dur_min <= limit_min:
                    step_sla_status = "GREEN"
                    step_sla_badge = f"✓ On Time ({dur_min}m / {limit_min}m)"
                    step_sla_explanation = (
                        f"Completed in {dur_min} min (Step Deadline: {limit_min} min) — Within SLA."
                    )
                elif dur_min <= int(limit_min * 1.55):
                    step_sla_status = "ORANGE"
                    sla_orange_steps += 1
                    step_sla_badge = f"⚠ Deadline Exceeded (+{overrun_min}m)"
                    step_sla_explanation = (
                        f"Step deadline of {limit_min} min exceeded by +{overrun_min} min "
                        f"(Actual duration: {dur_min} min)."
                    )
                else:
                    step_sla_status = "RED"
                    sla_red_steps += 1
                    step_sla_badge = f"🚨 Severe SLA Breach (+{overrun_min}m)"
                    step_sla_explanation = (
                        f"Critical deadline breach: step took {dur_min} min vs. {limit_min} min deadline "
                        f"(+{overrun_min} min overdue)."
                    )

                detailed_events.append({
                    "step": idx + 1,
                    "transition_id": tid,
                    "activity": act_name,
                    "timestamp": ev["timestamp"],
                    "unit": ev["unit"],
                    "marking_after": list(agg.current_marking),
                    # Conformance fields
                    "is_deviation": is_dev,
                    "deviation_severity": dev_severity,
                    "deviation_type": dev_type,
                    "deviation_explanation": dev_explanation,
                    # SLA & Timestamp fields
                    "duration_min": dur_min,
                    "sla_limit_min": limit_min,
                    "overrun_min": overrun_min,
                    "cumulative_min": total_elapsed_min,
                    "sla_status": step_sla_status,
                    "sla_badge": step_sla_badge,
                    "sla_explanation": step_sla_explanation,
                })
                prev_cost = agg.alignment_cost

            # Increment transition case counts for this process
            for tid in executed_tids_in_case:
                if tid in transition_case_counts[pid]:
                    transition_case_counts[pid][tid] += 1

            current_marking = list(agg.current_marking) if agg else ["p1"]
            for pl_id in current_marking:
                if pl_id in place_case_counts[pid]:
                    place_case_counts[pid][pl_id] += 1

            place_names = [
                f"{pl_id} ({wf_net.places[pl_id].name})"
                for pl_id in current_marking
                if pl_id in wf_net.places
            ]
            current_place_label = ", ".join(place_names)

            # 1. Conformance Classification (derived from actual alignment at current time)
            conf_deviating_events = [e for e in detailed_events if e["is_deviation"]]
            if not conf_deviating_events:
                conf_category = "GREEN"
                conf_label = "No Deviations"
                conf_reason = (
                    "Petri-Net Conformance Check found 0 deviations. All executed steps follow the reference model."
                )
            elif has_skipped_mandatory:
                conf_category = "RED"
                conf_label = "Severe Deviations"
                skipped_all = [
                    m.model_transition
                    for m in (agg.prefix_alignment if agg else [])
                    if m.move_type == "MODEL_VISIBLE"
                ]
                conf_reason = (
                    f"Petri-Net Conformance Check detected mandatory step skip(s): "
                    f"[{', '.join(skipped_all)}]."
                )
            else:
                conf_category = "ORANGE"
                conf_label = "Minor Deviations"
                conf_reason = (
                    f"Petri-Net Conformance Check detected {len(conf_deviating_events)} minor deviation(s) "
                    f"(repeated step or rework loop without skipping mandatory approvals)."
                )

            # 2. SLA & Timestamp Classification (derived from actual step durations & case SLA limit)
            case_sla_limit = p_meta["case_sla_limit_min"]
            sla_deviating_events = [
                e for e in detailed_events if e["sla_status"] in ("ORANGE", "RED")
            ]
            if sla_red_steps > 0 or total_elapsed_min > case_sla_limit:
                sla_category = "RED"
                sla_label = "Severe SLA Breach"
                sla_reason = (
                    f"SLA & Timestamp Monitoring detected severe deadline breach ({len(sla_deviating_events)} "
                    f"delayed step(s); total elapsed {total_elapsed_min} min vs. {case_sla_limit} min SLA limit)."
                )
            elif sla_orange_steps > 0 or total_elapsed_min > int(case_sla_limit * 0.85):
                sla_category = "ORANGE"
                sla_label = "Minor Deadline Delay"
                sla_reason = (
                    f"SLA & Timestamp Monitoring detected minor step deadline overrun ({len(sla_deviating_events)} "
                    f"delayed step(s); total elapsed {total_elapsed_min} min / {case_sla_limit} min SLA limit)."
                )
            else:
                sla_category = "GREEN"
                sla_label = "Within SLA Deadlines"
                sla_reason = (
                    f"All {len(detailed_events)} step(s) completed within allowed deadlines "
                    f"(Total elapsed: {total_elapsed_min} min / {case_sla_limit} min case SLA limit)."
                )

            evaluated_cases.append({
                "case_id": cid,
                "process_id": pid,
                "process_name": p_meta["name"],
                "case_date": first_ts.split(" ")[0],
                "arrival_timestamp": first_ts,
                "last_timestamp": last_ts,
                "arrival_batch": rc["arrival_batch"],
                "is_from_last_update": is_from_last_update,
                "current_marking": current_marking,
                "current_place_label": current_place_label,
                "events": detailed_events,
                "alignment_moves": [m.to_dict() for m in agg.prefix_alignment] if agg else [],
                # Conformance status
                "conformance_category": conf_category,
                "conformance_label": conf_label,
                "conformance_reason": conf_reason,
                "conformance_deviating_events": conf_deviating_events,
                # SLA status
                "sla_category": sla_category,
                "sla_label": sla_label,
                "sla_reason": sla_reason,
                "sla_deviating_events": sla_deviating_events,
                "total_elapsed_min": total_elapsed_min,
                "case_sla_limit_min": case_sla_limit,
                # Default aliases (Conformance)
                "category": conf_category,
                "category_label": conf_label,
                "category_reason": conf_reason,
                "deviating_events": conf_deviating_events,
            })

        # Build enriched process objects with their WF-net, transition counts, and case counts
        enriched_processes = []
        for p in self.processes:
            pid = p["process_id"]
            p_cases = [c for c in evaluated_cases if c["process_id"] == pid]
            enriched_processes.append({
                **p,
                "wf_net": self.nets[pid].to_dict(),
                "transition_case_counts": transition_case_counts[pid],
                "place_case_counts": place_case_counts[pid],
                "counts_by_method": {
                    "CONFORMANCE": {
                        "GREEN": sum(1 for c in p_cases if c["conformance_category"] == "GREEN"),
                        "ORANGE": sum(1 for c in p_cases if c["conformance_category"] == "ORANGE"),
                        "RED": sum(1 for c in p_cases if c["conformance_category"] == "RED"),
                        "TOTAL": len(p_cases),
                    },
                    "SLA": {
                        "GREEN": sum(1 for c in p_cases if c["sla_category"] == "GREEN"),
                        "ORANGE": sum(1 for c in p_cases if c["sla_category"] == "ORANGE"),
                        "RED": sum(1 for c in p_cases if c["sla_category"] == "RED"),
                        "TOTAL": len(p_cases),
                    },
                },
                "last_update_count": sum(1 for c in p_cases if c["is_from_last_update"]),
            })

        counts_by_method = {
            "CONFORMANCE": {
                "GREEN": sum(1 for c in evaluated_cases if c["conformance_category"] == "GREEN"),
                "ORANGE": sum(1 for c in evaluated_cases if c["conformance_category"] == "ORANGE"),
                "RED": sum(1 for c in evaluated_cases if c["conformance_category"] == "RED"),
                "TOTAL": len(evaluated_cases),
            },
            "SLA": {
                "GREEN": sum(1 for c in evaluated_cases if c["sla_category"] == "GREEN"),
                "ORANGE": sum(1 for c in evaluated_cases if c["sla_category"] == "ORANGE"),
                "RED": sum(1 for c in evaluated_cases if c["sla_category"] == "RED"),
                "TOTAL": len(evaluated_cases),
            },
        }

        last_update_cases_count = sum(1 for c in evaluated_cases if c["is_from_last_update"])

        return {
            "settings": self.settings,
            "time_snapshots": TIME_SNAPSHOTS,
            "selected_time_id": self.selected_time_id,
            "active_snapshot": active_snap,
            "last_update_count": last_update_cases_count,
            "processes": enriched_processes,
            "cases": evaluated_cases,
            "counts": counts_by_method["CONFORMANCE"],
            "counts_by_method": counts_by_method,
        }
