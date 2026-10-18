"""
Nirantar Phase 7 Escalation Engine (MongoDB)
Executes exact escalation rules against MongoDB settings demo clock.
"""
from datetime import datetime
from db_mongo import get_db

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

def run_escalation(db=None):
    """
    Executes escalation logic against the MongoDB demo clock.
    Returns:
        dict: {
            "demo_date": current_date_str,
            "escalated_count": len(changes),
            "changes": [...]
        }
    """
    if db is None:
        db = get_db()
        
    settings = db.settings.find_one({"_id": "system"}) or {}
    demo_date_str = settings.get("demo_date", "2026-10-18")
    demo_date = parse_date(demo_date_str)
    
    # Escalation rules
    rules = {}
    for r in db.escalation_rules.find({}):
        rules[r["trigger"]] = {
            "after_days": r.get("after_days", 0),
            "target_role": r.get("target_role", "supervisor")
        }
        
    unresolved_window = rules.get("unresolved_after_escalation", {}).get("after_days", 2)
    
    # Candidate cases: not resolved, not closed_lost, not yet program_manager
    candidate_cases = list(db.cases.find({
        "status": {"$nin": ["resolved", "closed_lost"]},
        "escalated_to": {"$ne": "program_manager"}
    }))
    
    changes = []
    
    for case in candidate_cases:
        case_id = case.get("id") or str(case.get("_id"))
        status = case.get("status")
        due_date = parse_date(case.get("due_date"))
        escalation_level = case.get("escalation_level", 0)
        escalated_to = case.get("escalated_to", "worker")
        escalated_at = parse_date(case.get("escalated_at"))
        reason = case.get("reason", "") or ""
        
        changed = False
        new_level = escalation_level
        new_target = escalated_to
        trigger_applied = None
        
        # RULE 3: Any escalated case (supervisor or doctor) still unresolved
        # after the rule's after_days since escalated_at -> escalate to program manager.
        if escalated_to in ("supervisor", "doctor"):
            if escalated_at is not None:
                days_since_esc = (demo_date - escalated_at).days
                if days_since_esc >= unresolved_window:
                    new_level = 2
                    new_target = "program_manager"
                    trigger_applied = "unresolved_after_escalation"
                    changed = True
                    
        # If not moved to program_manager above, check urgent reason or past due
        if not changed:
            # RULE 2: Reason is urgent (side_effects) -> straight to doctor immediately
            if reason == "side_effects" and escalated_to not in ("doctor", "program_manager"):
                new_level = 2
                new_target = "doctor"
                trigger_applied = "urgent_reason"
                changed = True
            # RULE 1: Past due (< demo_date) & still at worker level -> escalate to supervisor
            elif due_date is not None and due_date < demo_date:
                if escalation_level == 0 or escalated_to == "worker":
                    new_level = 1
                    new_target = "supervisor"
                    trigger_applied = "past_due"
                    changed = True
                    
        if changed:
            new_escalated_at = case.get("escalated_at") if case.get("escalated_at") else demo_date_str
            
            db.cases.update_one(
                {"_id": case["_id"]},
                {"$set": {
                    "escalation_level": new_level,
                    "escalated_to": new_target,
                    "status": "escalated",
                    "escalated_at": new_escalated_at
                }}
            )
            
            # Fetch patient name for reporting
            p = db.patients.find_one({"$or": [{"_id": case.get("patient_id")}, {"id": case.get("patient_id")}]})
            p_name = p.get("name") if p else case.get("patient_id")
            
            changes.append({
                "case_id": case_id,
                "patient_name": p_name,
                "previous_level": escalation_level,
                "previous_target": escalated_to,
                "new_level": new_level,
                "escalated_to": new_target,
                "trigger": trigger_applied,
                "reason": reason
            })
            
    return {
        "demo_date": demo_date_str,
        "escalated_count": len(changes),
        "changes": changes
    }
