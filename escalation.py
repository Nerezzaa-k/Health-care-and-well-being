"""
Nirantar Phase 6 Escalation Engine
Implements the exact escalation rules against the demo clock.
"""
from datetime import datetime
import sqlite3
from db import get_connection

def parse_date(date_str):
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def run_escalation(db_conn=None):
    """
    Runs the escalation logic against the current demo date.
    Returns:
        dict: {
            "demo_date": current_date_str,
            "escalated_count": count_of_changed_cases,
            "changes": [
                {
                    "case_id": ...,
                    "patient_name": ...,
                    "previous_level": ...,
                    "new_level": ...,
                    "escalated_to": ...,
                    "trigger": ...,
                    "reason": ...
                }
            ]
        }
    """
    conn = db_conn or get_connection()
    c = conn.cursor()
    
    # 1. Fetch current demo date
    c.execute("SELECT demo_date FROM demo_clock WHERE id = 1")
    row = c.fetchone()
    current_date_str = row["demo_date"] if row else "2026-10-18"
    demo_date = parse_date(current_date_str)
    
    # 2. Fetch escalation rules
    c.execute("SELECT trigger, after_days, target_role FROM escalation_rules")
    rules = {r["trigger"]: {"after_days": r["after_days"], "target_role": r["target_role"]} for r in c.fetchall()}
    
    unresolved_rule_days = rules.get("unresolved_after_escalation", {}).get("after_days", 2)
    
    # 3. Fetch candidate cases that are NOT resolved or closed_lost, and not yet at program_manager
    c.execute("""
    SELECT c.*, p.name as patient_name
    FROM cases c
    JOIN patients p ON c.patient_id = p.id
    WHERE c.status NOT IN ('resolved', 'closed_lost')
      AND c.escalated_to != 'program_manager'
    """)
    candidate_cases = c.fetchall()
    
    changes = []
    
    for case in candidate_cases:
        case_id = case["id"]
        status = case["status"]
        due_date = parse_date(case["due_date"])
        escalation_level = case["escalation_level"]
        escalated_to = case["escalated_to"]
        escalated_at = parse_date(case["escalated_at"])
        reason = case["reason"] or ""
        
        changed = False
        new_level = escalation_level
        new_target = escalated_to
        trigger_applied = None
        
        # RULE 3: Any escalated case (supervisor or doctor level) still unresolved
        # after the rule's after_days since escalated_at -> escalate to program manager.
        if escalated_to in ("supervisor", "doctor"):
            if escalated_at is not None:
                days_since_escalation = (demo_date - escalated_at).days
                if days_since_escalation >= unresolved_rule_days:
                    new_level = 2
                    new_target = "program_manager"
                    trigger_applied = "unresolved_after_escalation"
                    changed = True
        
        # If not escalated to program manager above, check urgent reason or past due
        if not changed:
            # RULE 2: Reason is urgent (side_effects) -> escalate straight to doctor, immediately.
            # Only if not already at doctor or program manager level
            if reason == "side_effects" and escalated_to not in ("doctor", "program_manager"):
                new_level = 2
                new_target = "doctor"
                trigger_applied = "urgent_reason"
                changed = True
            
            # RULE 1: A case is past due when due_date is before demo date (not on due date).
            # Past due and still at the worker level -> escalate to supervisor.
            elif due_date is not None and due_date < demo_date:
                if escalation_level == 0 or escalated_to == "worker":
                    new_level = 1
                    new_target = "supervisor"
                    trigger_applied = "past_due"
                    changed = True
        
        if changed:
            # If escalating for the first time, record escalated_at as demo_date.
            # If moving to program_manager from supervisor/doctor, preserve original escalated_at or set if null.
            new_escalated_at = case["escalated_at"] if case["escalated_at"] else current_date_str
            
            c.execute("""
            UPDATE cases
            SET escalation_level = ?,
                escalated_to = ?,
                status = 'escalated',
                escalated_at = ?
            WHERE id = ?
            """, (new_level, new_target, new_escalated_at, case_id))
            
            changes.append({
                "case_id": case_id,
                "patient_name": case["patient_name"],
                "previous_level": escalation_level,
                "previous_target": escalated_to,
                "new_level": new_level,
                "escalated_to": new_target,
                "trigger": trigger_applied,
                "reason": reason
            })
            
    conn.commit()
    if not db_conn:
        conn.close()
        
    return {
        "demo_date": current_date_str,
        "escalated_count": len(changes),
        "changes": changes
    }
