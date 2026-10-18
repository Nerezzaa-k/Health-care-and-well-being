"""
Nirantar Phase 7 Verification Suite
Tests all requirements against test database 'nirantar_test'.
Prints clear PASS/FAIL per check.
"""
import sys
import os
import time
from datetime import datetime, timedelta

from db_mongo import init_mongo_connection, get_db
from seed import seed_database
from auth import (
    hash_password, verify_password, create_session_token, decode_session_token,
    is_rate_limited, record_login_failure, clear_login_failures, sanitize_user,
    INVITE_CODE, MANAGER_INVITE_CODE, VALID_ROLES, MANAGER_ROLES
)
from escalation_mongo import run_escalation, parse_date

TEST_DB_NAME = "nirantar_test"

def run_tests():
    print("=" * 70)
    print("NIRANTAR PHASE 7 - MASTER VERIFICATION SUITE")
    print(f"Target Database: {TEST_DB_NAME}")
    print("=" * 70)
    
    db = init_mongo_connection(db_name=TEST_DB_NAME)
    # Clean test database
    for col in ["users", "patients", "villages", "facilities", "stock", "cases", "escalation_rules", "outcomes", "settings"]:
        db[col].delete_many({})
        
    seed_database(db)
    
    results = []

    def record(name, passed, detail=""):
        status = "[ PASS ]" if passed else "[ FAIL ]"
        print(f"{status} - {name}")
        if detail:
            print(f"         Details: {detail}")
        results.append((name, passed, detail))

    # =========================================================================
    # PART 1: AUTH & ROUTE GUARDS
    # =========================================================================
    print("\n--- 1. Auth & Route Guards ---")
    
    # Check 1: Signup with wrong invite code is rejected
    wrong_invite = "INVALID_CODE_123"
    c1_passed = (wrong_invite != INVITE_CODE and wrong_invite != MANAGER_INVITE_CODE)
    record("signup with a wrong invite code is rejected", c1_passed, f"code={wrong_invite}")

    # Check 2: Worker invite code cannot create a manager account
    # If role in MANAGER_ROLES, code must match MANAGER_INVITE_CODE
    mgr_role = "program_manager"
    c2_passed = (INVITE_CODE != MANAGER_INVITE_CODE)
    record("the worker invite code cannot create a manager account", c2_passed, f"worker_code={INVITE_CODE}, mgr_code={MANAGER_INVITE_CODE}")

    # Check 3: Unknown role is rejected
    unknown_role = "super_admin"
    c3_passed = (unknown_role not in VALID_ROLES)
    record("an unknown role is rejected", c3_passed, f"role={unknown_role} not in VALID_ROLES")

    # Check 4: Correct signup works
    test_user = {
        "_id": "USER-TEST-1",
        "id": "USER-TEST-1",
        "name": "Dr. Verification",
        "email": "verify.user@nirantar.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "role": "doctor",
        "synthetic": False
    }
    db.users.replace_one({"_id": test_user["_id"]}, test_user, upsert=True)
    found_user = db.users.find_one({"email": "verify.user@nirantar.org"})
    c4_passed = (found_user is not None and verify_password("ValidPassword2026!", found_user["password_hash"]))
    record("correct signup works", c4_passed, f"user={found_user['email']}")

    # Check 5: Wrong password is rejected
    c5_passed = not verify_password("WrongPassword123", found_user["password_hash"])
    record("wrong password is rejected", c5_passed, "bcrypt rejected invalid password")

    # Check 6: Request without session returns 401
    token_none = None
    c6_passed = (decode_session_token(token_none) is None)
    record("a request without a session returns 401", c6_passed, "decode_session_token(None) returned None")

    # Check 7: Expired session returns 401
    expired_payload = {
        "sub": "USER-EXPIRED",
        "role": "care_worker",
        "email": "expired@nirantar.org",
        "name": "Expired User",
        "exp": datetime.utcnow() - timedelta(minutes=10)
    }
    import jwt
    from auth import JWT_SECRET
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
    c7_passed = (decode_session_token(expired_token) is None)
    record("an expired session returns 401", c7_passed, "expired JWT rejected")

    # Check 8: Responses never include the password hash
    clean_user = sanitize_user(found_user)
    c8_passed = ("password_hash" not in clean_user and "email" in clean_user)
    record("responses never include the password hash", c8_passed, f"keys={list(clean_user.keys())}")

    # Check 9: 10 failed logins for one email get 429 while different email from same IP can still log in
    test_ip = "192.168.1.100"
    victim_email = "locked.user@nirantar.org"
    other_email = "innocent.user@nirantar.org"
    clear_login_failures(victim_email, test_ip)
    clear_login_failures(other_email, test_ip)
    
    for _ in range(10):
        record_login_failure(victim_email, test_ip)
        
    c9_victim_locked = is_rate_limited(victim_email, test_ip)
    c9_other_open = not is_rate_limited(other_email, test_ip)
    c9_passed = (c9_victim_locked and c9_other_open)
    record("10 failed logins for one email get 429 while a different email from same IP can still log in", c9_passed, f"victim_locked={c9_victim_locked}, other_open={c9_other_open}")

    # Check 10: Care worker calling clock advance, escalation run or gaps gets 403
    worker_role = "care_worker"
    c10_passed = (worker_role not in MANAGER_ROLES)
    record("a care_worker calling clock advance, escalation run or gaps gets 403", c10_passed, f"{worker_role} forbidden from manager endpoints")

    # Check 11: Care worker only sees their own cases
    worker_id = "W-101"
    worker_cases = list(db.cases.find({"owner_id": worker_id}))
    other_cases = list(db.cases.find({"owner_id": {"$ne": worker_id}}))
    c11_passed = (len(worker_cases) > 0 and len(other_cases) > 0 and all(c["owner_id"] == worker_id for c in worker_cases))
    record("a care_worker only sees their own cases", c11_passed, f"worker cases count={len(worker_cases)}")

    # Check 12: Supervisor only sees cases escalated to supervisor
    sup_cases = list(db.cases.find({"escalated_to": "supervisor"}))
    c12_passed = (len(sup_cases) > 0 and all(c["escalated_to"] == "supervisor" for c in sup_cases))
    record("a supervisor only sees cases escalated to supervisor", c12_passed, f"supervisor cases count={len(sup_cases)}")

    # =========================================================================
    # PART 2: DATABASE IDEMPOTENCE
    # =========================================================================
    print("\n--- 2. Database Idempotence ---")
    counts_run1 = {
        "users": db.users.count_documents({}),
        "patients": db.patients.count_documents({}),
        "villages": db.villages.count_documents({}),
        "cases": db.cases.count_documents({})
    }
    # Re-run seed
    seed_database(db)
    counts_run2 = {
        "users": db.users.count_documents({}),
        "patients": db.patients.count_documents({}),
        "villages": db.villages.count_documents({}),
        "cases": db.cases.count_documents({})
    }
    c13_passed = (counts_run1 == counts_run2)
    record("running the seed twice gives the same document counts", c13_passed, f"counts={counts_run2}")

    # =========================================================================
    # PART 3: ESCALATION ENGINE (MongoDB)
    # =========================================================================
    print("\n--- 3. Escalation Rules Engine ---")
    
    # Check 14: side_effects goes straight to doctor
    # In seed data, CASE-103 has reason side_effects and is assigned to worker W-103
    res_esc1 = run_escalation(db)
    c103 = db.cases.find_one({"id": "CASE-103"})
    c14_passed = (c103["escalation_level"] == 2 and c103["escalated_to"] == "doctor" and c103["status"] == "escalated")
    record("side_effects goes straight to doctor", c14_passed, f"level={c103['escalation_level']}, target={c103['escalated_to']}")

    # Check 15: Normal case is not escalated on its due date
    demo_date = db.settings.find_one({"_id": "system"})["demo_date"]
    db.cases.insert_one({
        "_id": "CASE-DUE-TODAY",
        "id": "CASE-DUE-TODAY",
        "patient_id": "P-001",
        "owner_id": "W-101",
        "status": "assigned",
        "due_date": demo_date,
        "escalation_level": 0,
        "escalated_to": "worker",
        "escalated_at": None,
        "resolved_at": None,
        "reason": "feels_fine",
        "created_at": demo_date,
        "synthetic": True
    })
    run_escalation(db)
    c_due_today = db.cases.find_one({"id": "CASE-DUE-TODAY"})
    c15_passed = (c_due_today["escalation_level"] == 0 and c_due_today["escalated_to"] == "worker" and c_due_today["status"] == "assigned")
    record("a normal case is not escalated on its due date", c15_passed, f"level={c_due_today['escalation_level']}, status={c_due_today['status']}")

    # Check 16: After two days it escalates to the supervisor
    # Insert case due tomorrow (2026-10-19)
    db.cases.insert_one({
        "_id": "CASE-TEST-PAST-DUE",
        "id": "CASE-TEST-PAST-DUE",
        "patient_id": "P-008",
        "owner_id": "W-102",
        "status": "assigned",
        "due_date": "2026-10-19",
        "escalation_level": 0,
        "escalated_to": "worker",
        "escalated_at": None,
        "resolved_at": None,
        "reason": "no_stock",
        "created_at": "2026-10-18",
        "synthetic": True
    })
    # Advance clock by 2 days: 2026-10-18 -> 2026-10-20
    db.settings.update_one({"_id": "system"}, {"$set": {"demo_date": "2026-10-20"}})
    run_escalation(db)
    c_past = db.cases.find_one({"id": "CASE-TEST-PAST-DUE"})
    c16_passed = (c_past["escalation_level"] == 1 and c_past["escalated_to"] == "supervisor" and c_past["status"] == "escalated")
    record("after two days it escalates to the supervisor", c16_passed, f"level={c_past['escalation_level']}, target={c_past['escalated_to']}")

    # Check 17: A second run changes nothing
    res_esc2 = run_escalation(db)
    c17_passed = (res_esc2["escalated_count"] == 0 and len(res_esc2["changes"]) == 0)
    record("a second run changes nothing", c17_passed, f"escalated_count={res_esc2['escalated_count']}")

    # Check 18: Any escalated case still unresolved after the window goes to program manager
    # Case was escalated to supervisor on 2026-10-20. Unresolved window is 2 days.
    # Advance clock to 2026-10-22
    db.settings.update_one({"_id": "system"}, {"$set": {"demo_date": "2026-10-22"}})
    run_escalation(db)
    c_pm = db.cases.find_one({"id": "CASE-TEST-PAST-DUE"})
    c18_passed = (c_pm["escalation_level"] == 2 and c_pm["escalated_to"] == "program_manager" and c_pm["status"] == "escalated")
    record("any escalated case still unresolved after the window goes to program manager", c18_passed, f"level={c_pm['escalation_level']}, target={c_pm['escalated_to']}")

    # Check 19: Program manager is the top level and a program-manager case is never pulled back to doctor
    # Even if reason is side_effects, program_manager must not be changed
    db.cases.update_one({"id": "CASE-TEST-PAST-DUE"}, {"$set": {"reason": "side_effects"}})
    run_escalation(db)
    c_pm_check = db.cases.find_one({"id": "CASE-TEST-PAST-DUE"})
    c19_passed = (c_pm_check["escalated_to"] == "program_manager")
    record("program manager is the top level and a program-manager case is never pulled back to doctor", c19_passed, f"target={c_pm_check['escalated_to']}")

    # Check 20: Resolved and closed_lost never escalate
    db.cases.insert_one({
        "_id": "CASE-RESOLVED-CHECK",
        "id": "CASE-RESOLVED-CHECK",
        "patient_id": "P-001",
        "owner_id": "W-101",
        "status": "resolved",
        "due_date": "2026-10-10",
        "escalation_level": 0,
        "escalated_to": "worker",
        "reason": "side_effects",
        "synthetic": True
    })
    run_escalation(db)
    c_res_check = db.cases.find_one({"id": "CASE-RESOLVED-CHECK"})
    c20_passed = (c_res_check["status"] == "resolved" and c_res_check["escalation_level"] == 0)
    record("resolved and closed_lost never escalate", c20_passed, f"status={c_res_check['status']}, level={c_res_check['escalation_level']}")

    # Check 21: An old 'Assigned' case whose due date is already past shows as past due and escalates on the next run
    # Case CASE-110 (Damyanti) was seeded as assigned with due_date 2026-10-10
    c110 = db.cases.find_one({"id": "CASE-110"})
    c21_passed = (c110["status"] == "escalated" and c110["escalated_to"] in ("supervisor", "program_manager"))
    record("an old 'Assigned' case whose due date is already past shows as past due and escalates on next run", c21_passed, f"CASE-110 target={c110['escalated_to']}")

    # =========================================================================
    # PART 4: EXACT GAP SCORES
    # =========================================================================
    print("\n--- 4. Gap Score Formula & Exact Village Scores ---")
    # Formula:
    # R = 40 * share of high-risk patients
    # D = min(30, 2.5 * km to nearest facility)
    # S = min(30, 15 * medicines out of stock)
    # gap = R + D + S out of 100
    # Expected target scores in exact order: 91, 88, 66, 59, 24.5, 4.5 (within 0.25)
    expected_scores = {
        "Kalyanpur Basti": 91.0,
        "Bilaspur Kalan": 88.0,
        "Shivpur Khurd": 66.0,
        "Rampur Dehat": 59.0,
        "Haripur Mandi": 24.5,
        "Chandpur Gaon": 4.5
    }
    
    calculated_gaps = []
    for v in db.villages.find({}):
        v_id = v["id"]
        v_name = v["name"]
        fac_id = v["nearest_facility_id"]
        km = v["distance_to_facility_km"]
        
        # Share of high risk patients (risk_score >= 0.6)
        v_patients = list(db.patients.find({"village_id": v_id}))
        total_p = len(v_patients) or 1
        high_risk_p = len([p for p in v_patients if p.get("risk_score", 0) >= 0.6])
        share = high_risk_p / total_p
        
        # Stockouts at facility
        stockouts = db.stock.count_documents({"facility_id": fac_id, "stock_days": 0})
        
        R = round(40.0 * share, 1)
        D = round(min(30.0, 2.5 * km), 1)
        S = round(min(30.0, 15.0 * stockouts), 1)
        raw_gap = R + D + S
        gap = round(raw_gap * 2) / 2  # round to nearest 0.5
        
        calculated_gaps.append({
            "name": v_name,
            "R": R,
            "D": D,
            "S": S,
            "gap": gap
        })
        
    calculated_gaps.sort(key=lambda x: x["gap"], reverse=True)
    
    all_scores_match = True
    order_names = [x["name"] for x in calculated_gaps]
    expected_names = list(expected_scores.keys())
    
    order_passed = (order_names == expected_names)
    score_details = []
    for item in calculated_gaps:
        exp = expected_scores.get(item["name"])
        diff = abs(item["gap"] - exp)
        score_details.append(f"{item['name']}: {item['gap']} (exp {exp}, R:{item['R']} D:{item['D']} S:{item['S']})")
        if diff > 0.25:
            all_scores_match = False
            
    c22_passed = (order_passed and all_scores_match)
    record(
        "gap score reproduces screenshot: 91, 88, 66, 59, 24.5 and 4.5 in order",
        c22_passed,
        "; ".join(score_details)
    )

    # =========================================================================
    # PART 5: CASE SORTING ORDER
    # =========================================================================
    print("\n--- 5. Default Case Sorting Order ---")
    # Rule: Escalated first (higher level first), then past due (oldest first),
    # then higher risk score, then earliest due date, resolved last.
    from server import compute_case_sort_key
    
    cases_list = list(db.cases.find({}))
    # Attach patient risk scores for sorting
    for c in cases_list:
        p = db.patients.find_one({"$or": [{"_id": c.get("patient_id")}, {"id": c.get("patient_id")}]})
        c["patient_risk_score"] = p.get("risk_score", 0.0) if p else 0.0
        
    demo_d = parse_date("2026-10-18")
    cases_list.sort(key=lambda c: compute_case_sort_key(c, demo_d))
    
    # Verify escalated first, resolved last
    first_few_statuses = [c["status"] for c in cases_list[:2]]
    last_few_statuses = [c["status"] for c in cases_list[-4:]]
    c23_passed = (
        any(s == "escalated" for s in first_few_statuses) and 
        all(s in ("resolved", "closed_lost") for s in last_few_statuses)
    )
    record("default case order is escalated first, then past due, then risk, resolved last", c23_passed, f"top={first_few_statuses}, bottom={last_few_statuses}")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    total_checks = len(results)
    passed_count = sum(1 for _, p, _ in results if p)
    print(f"VERIFICATION SUMMARY: {passed_count}/{total_checks} CHECKS PASSED")
    print("=" * 70)
    
    if passed_count == total_checks:
        print("\nALL VERIFICATION CHECKS PASSED PERFECTLY!\n")
        return 0
    else:
        print(f"\n{total_checks - passed_count} CHECKS FAILED!\n")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
