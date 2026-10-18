"""
Nirantar Phase 7 Seed Script
Seeds synthetic demo data idempotently into MongoDB without dropping database or cluster.
Safe to run multiple times.
"""
import os
import bcrypt
from dotenv import load_dotenv
from db_mongo import get_db, ensure_indexes

load_dotenv()

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "NirantarDemo2026!")

def hash_pw(password_str):
    return bcrypt.hashpw(password_str.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def seed_database(db=None):
    if db is None:
        db = get_db()
        
    ensure_indexes(db)
    demo_pw_hash = hash_pw(DEMO_PASSWORD)
    
    # -------------------------------------------------------------
    # 1. SETTINGS & DEMO CLOCK
    # -------------------------------------------------------------
    db.settings.update_one(
        {"_id": "system"},
        {"$set": {
            "_id": "system",
            "demo_date": "2026-10-18",
            "minutes_per_followup": 25,
            "synthetic": True
        }},
        upsert=True
    )
    
    # -------------------------------------------------------------
    # 2. ESCALATION RULES
    # -------------------------------------------------------------
    rules = [
        {
            "_id": "rule_past_due",
            "trigger": "past_due",
            "after_days": 0,
            "target_role": "supervisor",
            "label": "placeholders to set with the NGO",
            "description": "Past due and still at worker level -> escalate to supervisor",
            "synthetic": True
        },
        {
            "_id": "rule_urgent_reason",
            "trigger": "urgent_reason",
            "after_days": 0,
            "target_role": "doctor",
            "label": "placeholders to set with the NGO",
            "description": "Reason is urgent (side_effects) -> escalate straight to doctor immediately",
            "synthetic": True
        },
        {
            "_id": "rule_unresolved_after_escalation",
            "trigger": "unresolved_after_escalation",
            "after_days": 2,
            "target_role": "program_manager",
            "label": "placeholders to set with the NGO",
            "description": "Unresolved 2 days after escalation -> escalate to program manager",
            "synthetic": True
        }
    ]
    for r in rules:
        db.escalation_rules.update_one({"_id": r["_id"]}, {"$set": r}, upsert=True)
        
    # -------------------------------------------------------------
    # 3. USERS (4 workers, 1 supervisor, 1 doctor, 1 PM, 1 coordinator)
    # -------------------------------------------------------------
    users = [
        {
            "_id": "PM-401",
            "id": "PM-401",
            "name": "Vikram Malhotra",
            "email": "vikram.pm@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "program_manager",
            "facility_id": "HQ-1",
            "village_coverage": "District Program Office",
            "theme": "clinical_teal",
            "synthetic": True
        },
        {
            "_id": "COORD-501",
            "id": "COORD-501",
            "name": "Priya Nambiar",
            "email": "priya.coord@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "coordinator",
            "facility_id": "HQ-1",
            "village_coverage": "Central Sector Coordination",
            "theme": "clinical_teal",
            "synthetic": True
        },
        {
            "_id": "SUP-201",
            "id": "SUP-201",
            "name": "Dr. Rajesh Rao",
            "email": "rajesh.sup@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "supervisor",
            "facility_id": "FAC-1",
            "village_coverage": "Block A Supervisor",
            "theme": "clinical_teal",
            "synthetic": True
        },
        {
            "_id": "DOC-301",
            "id": "DOC-301",
            "name": "Dr. Ananya Sen",
            "email": "ananya.doc@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "doctor",
            "facility_id": "FAC-3",
            "village_coverage": "CHC Central Clinical Lead",
            "theme": "clinical_teal",
            "synthetic": True
        },
        {
            "_id": "W-101",
            "id": "W-101",
            "name": "Sunita Sharma",
            "email": "sunita.worker@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "care_worker",
            "facility_id": "FAC-4",
            "village_coverage": "Kalyanpur Basti, Chandpur Gaon",
            "theme": "clinical_teal",
            "synthetic": True
        },
        {
            "_id": "W-102",
            "id": "W-102",
            "name": "Pooja Verma",
            "email": "pooja.worker@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "care_worker",
            "facility_id": "FAC-1",
            "village_coverage": "Rampur Dehat, Haripur Mandi",
            "theme": "clinical_teal",
            "synthetic": True
        },
        {
            "_id": "W-103",
            "id": "W-103",
            "name": "Manoj Kumar",
            "email": "manoj.worker@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "care_worker",
            "facility_id": "FAC-2",
            "village_coverage": "Bilaspur Kalan, Shivpur Khurd",
            "theme": "clinical_teal",
            "synthetic": True
        },
        {
            "_id": "W-104",
            "id": "W-104",
            "name": "Rekha Patel",
            "email": "rekha.worker@nirantar.org",
            "password_hash": demo_pw_hash,
            "role": "care_worker",
            "facility_id": "FAC-2",
            "village_coverage": "Shivpur Outreach",
            "theme": "clinical_teal",
            "synthetic": True
        }
    ]
    for u in users:
        db.users.update_one({"_id": u["_id"]}, {"$set": u}, upsert=True)
        
    # -------------------------------------------------------------
    # 4. FACILITIES
    # -------------------------------------------------------------
    facilities = [
        {
            "_id": "FAC-1",
            "id": "FAC-1",
            "name": "Rampur Primary Health Centre",
            "type": "PHC",
            "distance_km": 4.2,
            "lat": 28.6139,
            "lng": 77.2090,
            "stockouts": 1,
            "synthetic": True
        },
        {
            "_id": "FAC-2",
            "id": "FAC-2",
            "name": "Bilaspur Health Sub-centre",
            "type": "Sub-centre",
            "distance_km": 9.8,
            "lat": 28.6250,
            "lng": 77.2400,
            "stockouts": 3,
            "synthetic": True
        },
        {
            "_id": "FAC-3",
            "id": "FAC-3",
            "name": "Chandpur Community Health Centre",
            "type": "CHC",
            "distance_km": 2.1,
            "lat": 28.5900,
            "lng": 77.1950,
            "stockouts": 0,
            "synthetic": True
        },
        {
            "_id": "FAC-4",
            "id": "FAC-4",
            "name": "Kalyanpur Health & Wellness",
            "type": "HWC",
            "distance_km": 7.5,
            "lat": 28.6400,
            "lng": 77.1800,
            "stockouts": 2,
            "synthetic": True
        }
    ]
    for f in facilities:
        db.facilities.update_one({"_id": f["_id"]}, {"$set": f}, upsert=True)
        
    # -------------------------------------------------------------
    # 5. STOCK INVENTORY
    # -------------------------------------------------------------
    stock_items = [
        # FAC-1 (1 stockout: Telmisartan)
        {"_id": "FAC-1_MED-1", "facility_id": "FAC-1", "medicine_id": "MED-1", "medicine_name": "Amlodipine 5mg", "condition": "Hypertension", "stock_days": 45, "units_available": 1200, "synthetic": True},
        {"_id": "FAC-1_MED-2", "facility_id": "FAC-1", "medicine_id": "MED-2", "medicine_name": "Telmisartan 40mg", "condition": "Hypertension", "stock_days": 0, "units_available": 0, "synthetic": True},
        {"_id": "FAC-1_MED-3", "facility_id": "FAC-1", "medicine_id": "MED-3", "medicine_name": "Metformin 500mg", "condition": "Type 2 Diabetes", "stock_days": 30, "units_available": 800, "synthetic": True},
        {"_id": "FAC-1_MED-4", "facility_id": "FAC-1", "medicine_id": "MED-4", "medicine_name": "Glimepiride 1mg", "condition": "Type 2 Diabetes", "stock_days": 12, "units_available": 140, "synthetic": True},
        {"_id": "FAC-1_MED-5", "facility_id": "FAC-1", "medicine_id": "MED-5", "medicine_name": "Isoniazid 300mg", "condition": "Tuberculosis", "stock_days": 60, "units_available": 450, "synthetic": True},

        # FAC-2 (3 stockouts: Amlodipine, Metformin, Isoniazid)
        {"_id": "FAC-2_MED-1", "facility_id": "FAC-2", "medicine_id": "MED-1", "medicine_name": "Amlodipine 5mg", "condition": "Hypertension", "stock_days": 0, "units_available": 0, "synthetic": True},
        {"_id": "FAC-2_MED-2", "facility_id": "FAC-2", "medicine_id": "MED-2", "medicine_name": "Telmisartan 40mg", "condition": "Hypertension", "stock_days": 20, "units_available": 300, "synthetic": True},
        {"_id": "FAC-2_MED-3", "facility_id": "FAC-2", "medicine_id": "MED-3", "medicine_name": "Metformin 500mg", "condition": "Type 2 Diabetes", "stock_days": 0, "units_available": 0, "synthetic": True},
        {"_id": "FAC-2_MED-4", "facility_id": "FAC-2", "medicine_id": "MED-4", "medicine_name": "Glimepiride 1mg", "condition": "Type 2 Diabetes", "stock_days": 8, "units_available": 90, "synthetic": True},
        {"_id": "FAC-2_MED-5", "facility_id": "FAC-2", "medicine_id": "MED-5", "medicine_name": "Isoniazid 300mg", "condition": "Tuberculosis", "stock_days": 0, "units_available": 0, "synthetic": True},

        # FAC-3 (0 stockouts: all safe)
        {"_id": "FAC-3_MED-1", "facility_id": "FAC-3", "medicine_id": "MED-1", "medicine_name": "Amlodipine 5mg", "condition": "Hypertension", "stock_days": 60, "units_available": 2500, "synthetic": True},
        {"_id": "FAC-3_MED-2", "facility_id": "FAC-3", "medicine_id": "MED-2", "medicine_name": "Telmisartan 40mg", "condition": "Hypertension", "stock_days": 45, "units_available": 1800, "synthetic": True},
        {"_id": "FAC-3_MED-3", "facility_id": "FAC-3", "medicine_id": "MED-3", "medicine_name": "Metformin 500mg", "condition": "Type 2 Diabetes", "stock_days": 40, "units_available": 1500, "synthetic": True},
        {"_id": "FAC-3_MED-4", "facility_id": "FAC-3", "medicine_id": "MED-4", "medicine_name": "Glimepiride 1mg", "condition": "Type 2 Diabetes", "stock_days": 35, "units_available": 900, "synthetic": True},
        {"_id": "FAC-3_MED-5", "facility_id": "FAC-3", "medicine_id": "MED-5", "medicine_name": "Isoniazid 300mg", "condition": "Tuberculosis", "stock_days": 50, "units_available": 600, "synthetic": True},

        # FAC-4 (2 stockouts: Telmisartan, Glimepiride)
        {"_id": "FAC-4_MED-1", "facility_id": "FAC-4", "medicine_id": "MED-1", "medicine_name": "Amlodipine 5mg", "condition": "Hypertension", "stock_days": 10, "units_available": 150, "synthetic": True},
        {"_id": "FAC-4_MED-2", "facility_id": "FAC-4", "medicine_id": "MED-2", "medicine_name": "Telmisartan 40mg", "condition": "Hypertension", "stock_days": 0, "units_available": 0, "synthetic": True},
        {"_id": "FAC-4_MED-3", "facility_id": "FAC-4", "medicine_id": "MED-3", "medicine_name": "Metformin 500mg", "condition": "Type 2 Diabetes", "stock_days": 14, "units_available": 200, "synthetic": True},
        {"_id": "FAC-4_MED-4", "facility_id": "FAC-4", "medicine_id": "MED-4", "medicine_name": "Glimepiride 1mg", "condition": "Type 2 Diabetes", "stock_days": 0, "units_available": 0, "synthetic": True},
        {"_id": "FAC-4_MED-5", "facility_id": "FAC-4", "medicine_id": "MED-5", "medicine_name": "Isoniazid 300mg", "condition": "Tuberculosis", "stock_days": 25, "units_available": 180, "synthetic": True}
    ]
    for s in stock_items:
        db.stock.update_one({"_id": s["_id"]}, {"$set": s}, upsert=True)
        
    # -------------------------------------------------------------
    # 6. VILLAGES (Full names matching screenshot & exact gap score targets)
    # -------------------------------------------------------------
    villages = [
        # 1. Kalyanpur Basti: 8.4km to FAC-4 (2 stockouts). D=21.0, S=30.0. Needs R=40 (100% high risk) -> Target 91.0
        {
            "_id": "VIL-2",
            "id": "VIL-2",
            "name": "Kalyanpur Basti",
            "nearest_facility_id": "FAC-4",
            "distance_to_facility_km": 8.4,
            "population": 980,
            "lat": 28.6450,
            "lng": 77.1720,
            "synthetic": True
        },
        # 2. Bilaspur Kalan: 11.2km to FAC-2 (3 stockouts). D=28.0, S=30.0. Needs R=30 (75% high risk) -> Target 88.0
        {
            "_id": "VIL-1",
            "id": "VIL-1",
            "name": "Bilaspur Kalan",
            "nearest_facility_id": "FAC-2",
            "distance_to_facility_km": 11.2,
            "population": 1420,
            "lat": 28.6320,
            "lng": 77.2450,
            "synthetic": True
        },
        # 3. Shivpur Khurd: 6.4km to FAC-2 (3 stockouts). D=16.0, S=30.0. Needs R=20 (50% high risk) -> Target 66.0
        {
            "_id": "VIL-4",
            "id": "VIL-4",
            "name": "Shivpur Khurd",
            "nearest_facility_id": "FAC-2",
            "distance_to_facility_km": 6.4,
            "population": 1150,
            "lat": 28.6210,
            "lng": 77.2350,
            "synthetic": True
        },
        # 4. Rampur Dehat: 5.6km to FAC-1 (1 stockout). D=14.0, S=15.0. Needs R=30 (75% high risk) -> Target 59.0
        {
            "_id": "VIL-3",
            "id": "VIL-3",
            "name": "Rampur Dehat",
            "nearest_facility_id": "FAC-1",
            "distance_to_facility_km": 5.6,
            "population": 2100,
            "lat": 28.6080,
            "lng": 77.2150,
            "synthetic": True
        },
        # 5. Haripur Mandi: 3.8km to FAC-1 (1 stockout). D=9.5, S=15.0. Needs R=0 (0% high risk) -> Target 24.5
        {
            "_id": "VIL-5",
            "id": "VIL-5",
            "name": "Haripur Mandi",
            "nearest_facility_id": "FAC-1",
            "distance_to_facility_km": 3.8,
            "population": 1850,
            "lat": 28.6180,
            "lng": 77.2020,
            "synthetic": True
        },
        # 6. Chandpur Gaon: 1.8km to FAC-3 (0 stockouts). D=4.5, S=0.0. Needs R=0 (0% high risk) -> Target 4.5
        {
            "_id": "VIL-6",
            "id": "VIL-6",
            "name": "Chandpur Gaon",
            "nearest_facility_id": "FAC-3",
            "distance_to_facility_km": 1.8,
            "population": 2400,
            "lat": 28.5880,
            "lng": 77.1980,
            "synthetic": True
        }
    ]
    for v in villages:
        db.villages.update_one({"_id": v["_id"]}, {"$set": v}, upsert=True)
        
    # -------------------------------------------------------------
    # 7. PATIENTS (Exactly 14 patients across Hypertension, Diabetes, TB)
    # -------------------------------------------------------------
    # High risk patients are those with risk_score >= 0.6
    patients = [
        # Kalyanpur Basti (2 patients, 2 high risk -> 100% -> R=40.0)
        {"_id": "P-006", "id": "P-006", "name": "Sita Ram", "age": 67, "gender": "M", "village_id": "VIL-2", "condition": "Hypertension", "risk_score": 0.76, "risk_category": "Urgent", "assigned_facility_id": "FAC-4", "primary_medicine_id": "MED-2", "refill_due_date": "2026-10-21", "assigned_worker_id": "W-101", "synthetic": True},
        {"_id": "P-007", "id": "P-007", "name": "Damyanti", "age": 54, "gender": "F", "village_id": "VIL-2", "condition": "Type 2 Diabetes", "risk_score": 0.81, "risk_category": "Urgent", "assigned_facility_id": "FAC-4", "primary_medicine_id": "MED-4", "refill_due_date": "2026-10-25", "assigned_worker_id": "W-101", "synthetic": True},

        # Bilaspur Kalan (4 patients, 3 high risk -> 75% -> R=30.0)
        {"_id": "P-003", "id": "P-003", "name": "Shiv Dayal", "age": 51, "gender": "M", "village_id": "VIL-1", "condition": "Type 2 Diabetes", "risk_score": 0.84, "risk_category": "Urgent", "assigned_facility_id": "FAC-2", "primary_medicine_id": "MED-3", "refill_due_date": "2026-10-20", "assigned_worker_id": "W-103", "synthetic": True},
        {"_id": "P-004", "id": "P-004", "name": "Meera Bai", "age": 45, "gender": "F", "village_id": "VIL-1", "condition": "Hypertension", "risk_score": 0.92, "risk_category": "Urgent", "assigned_facility_id": "FAC-2", "primary_medicine_id": "MED-1", "refill_due_date": "2026-10-22", "assigned_worker_id": "W-103", "synthetic": True},
        {"_id": "P-008", "id": "P-008", "name": "Bablu Yadav", "age": 49, "gender": "M", "village_id": "VIL-1", "condition": "Hypertension", "risk_score": 0.72, "risk_category": "Urgent", "assigned_facility_id": "FAC-2", "primary_medicine_id": "MED-2", "refill_due_date": "2026-11-05", "assigned_worker_id": "W-103", "synthetic": True},
        {"_id": "P-014", "id": "P-014", "name": "Rani Kaur", "age": 55, "gender": "F", "village_id": "VIL-1", "condition": "Type 2 Diabetes", "risk_score": 0.33, "risk_category": "Safe", "assigned_facility_id": "FAC-2", "primary_medicine_id": "MED-4", "refill_due_date": "2026-11-19", "assigned_worker_id": "W-103", "synthetic": True},

        # Shivpur Khurd (2 patients, 1 high risk -> 50% -> R=20.0)
        {"_id": "P-005", "id": "P-005", "name": "Gopal Singh", "age": 39, "gender": "M", "village_id": "VIL-4", "condition": "Tuberculosis", "risk_score": 0.95, "risk_category": "Urgent", "assigned_facility_id": "FAC-2", "primary_medicine_id": "MED-5", "refill_due_date": "2026-10-24", "assigned_worker_id": "W-104", "synthetic": True},
        {"_id": "P-013", "id": "P-013", "name": "Brij Mohan", "age": 69, "gender": "M", "village_id": "VIL-4", "condition": "Hypertension", "risk_score": 0.31, "risk_category": "Safe", "assigned_facility_id": "FAC-2", "primary_medicine_id": "MED-2", "refill_due_date": "2026-11-15", "assigned_worker_id": "W-104", "synthetic": True},

        # Rampur Dehat (4 patients, 3 high risk -> 75% -> R=30.0)
        {"_id": "P-001", "id": "P-001", "name": "Ram Charan", "age": 58, "gender": "M", "village_id": "VIL-3", "condition": "Hypertension", "risk_score": 0.88, "risk_category": "Urgent", "assigned_facility_id": "FAC-1", "primary_medicine_id": "MED-2", "refill_due_date": "2026-10-21", "assigned_worker_id": "W-102", "synthetic": True},
        {"_id": "P-002", "id": "P-002", "name": "Kamla Devi", "age": 62, "gender": "F", "village_id": "VIL-3", "condition": "Hypertension", "risk_score": 0.79, "risk_category": "Urgent", "assigned_facility_id": "FAC-1", "primary_medicine_id": "MED-2", "refill_due_date": "2026-10-23", "assigned_worker_id": "W-102", "synthetic": True},
        {"_id": "P-010", "id": "P-010", "name": "Dhanraj", "age": 63, "gender": "M", "village_id": "VIL-3", "condition": "Hypertension", "risk_score": 0.65, "risk_category": "Urgent", "assigned_facility_id": "FAC-1", "primary_medicine_id": "MED-1", "refill_due_date": "2026-11-02", "assigned_worker_id": "W-102", "synthetic": True},
        {"_id": "P-012", "id": "P-012", "name": "Harish Chandra", "age": 58, "gender": "M", "village_id": "VIL-3", "condition": "Type 2 Diabetes", "risk_score": 0.28, "risk_category": "Safe", "assigned_facility_id": "FAC-1", "primary_medicine_id": "MED-3", "refill_due_date": "2026-11-22", "assigned_worker_id": "W-102", "synthetic": True},

        # Haripur Mandi (1 patient, 0 high risk -> 0% -> R=0.0)
        {"_id": "P-011", "id": "P-011", "name": "Vidya Devi", "age": 44, "gender": "F", "village_id": "VIL-5", "condition": "Type 2 Diabetes", "risk_score": 0.48, "risk_category": "Watch", "assigned_facility_id": "FAC-1", "primary_medicine_id": "MED-3", "refill_due_date": "2026-10-29", "assigned_worker_id": "W-102", "synthetic": True},

        # Chandpur Gaon (1 patient, 0 high risk -> 0% -> R=0.0)
        {"_id": "P-009", "id": "P-009", "name": "Prem Lata", "age": 41, "gender": "F", "village_id": "VIL-6", "condition": "Hypertension", "risk_score": 0.22, "risk_category": "Safe", "assigned_facility_id": "FAC-3", "primary_medicine_id": "MED-1", "refill_due_date": "2026-11-20", "assigned_worker_id": "W-101", "synthetic": True}
    ]
    for p in patients:
        db.patients.update_one({"_id": p["_id"]}, {"$set": p}, upsert=True)
        
    # -------------------------------------------------------------
    # 8. CASES (Mixed states: assigned, resolved, escalated, past due)
    # Including Damyanti (P-007) assigned with past due date 2026-10-10
    # -------------------------------------------------------------
    cases = [
        # Case 1: Assigned to W-101, due tomorrow (2026-10-19)
        {
            "_id": "CASE-101",
            "id": "CASE-101",
            "patient_id": "P-001",
            "owner_id": "W-101",
            "status": "assigned",
            "due_date": "2026-10-19",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": None,
            "reason": "no_stock",
            "action": "alternate_phc",
            "notes": "Patient needs stock transfer",
            "created_at": "2026-10-17",
            "synthetic": True
        },
        # Case 2: Past due case (due 2026-10-16 < 2026-10-18) at worker level -> ready to escalate to supervisor
        {
            "_id": "CASE-102",
            "id": "CASE-102",
            "patient_id": "P-003",
            "owner_id": "W-102",
            "status": "assigned",
            "due_date": "2026-10-16",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": None,
            "reason": "cant_travel",
            "action": "doorstep_refill",
            "notes": "Doorstep delivery pending",
            "created_at": "2026-10-14",
            "synthetic": True
        },
        # Case 3: Urgent reason case (side_effects) -> goes straight to doctor
        {
            "_id": "CASE-103",
            "id": "CASE-103",
            "patient_id": "P-005",
            "owner_id": "W-103",
            "status": "assigned",
            "due_date": "2026-10-20",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": None,
            "reason": "side_effects",
            "action": "doctor_consult",
            "notes": "Severe dizziness & nausea reported",
            "created_at": "2026-10-18",
            "synthetic": True
        },
        # Case 4: Already escalated to supervisor 3 days ago (escalated_at: 2026-10-15) -> ready for program manager
        {
            "_id": "CASE-104",
            "id": "CASE-104",
            "patient_id": "P-004",
            "owner_id": "W-103",
            "status": "escalated",
            "due_date": "2026-10-14",
            "escalation_level": 1,
            "escalated_to": "supervisor",
            "escalated_at": "2026-10-15",
            "resolved_at": None,
            "reason": "lost_wages",
            "action": "flexible_slot",
            "notes": "Supervisor follow up pending",
            "created_at": "2026-10-12",
            "synthetic": True
        },
        # Case 5: Resolved case 1 (created 2026-10-10, resolved 2026-10-13, diff = 3 days)
        {
            "_id": "CASE-105",
            "id": "CASE-105",
            "patient_id": "P-011",
            "owner_id": "W-102",
            "status": "resolved",
            "due_date": "2026-10-14",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": "2026-10-13",
            "reason": "feels_fine",
            "action": "counselling",
            "notes": "Counselling done",
            "created_at": "2026-10-10",
            "synthetic": True
        },
        # Case 6: Resolved case 2 (created 2026-10-11, resolved 2026-10-15, diff = 4 days)
        {
            "_id": "CASE-106",
            "id": "CASE-106",
            "patient_id": "P-012",
            "owner_id": "W-102",
            "status": "resolved",
            "due_date": "2026-10-15",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": "2026-10-15",
            "reason": "cant_travel",
            "action": "doorstep_refill",
            "notes": "Delivered refill",
            "created_at": "2026-10-11",
            "synthetic": True
        },
        # Case 7: Resolved case 3 (created 2026-10-08, resolved 2026-10-10, diff = 2 days)
        {
            "_id": "CASE-107",
            "id": "CASE-107",
            "patient_id": "P-013",
            "owner_id": "W-101",
            "status": "resolved",
            "due_date": "2026-10-12",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": "2026-10-10",
            "reason": "feels_fine",
            "action": "counselling",
            "notes": "Adherence logged",
            "created_at": "2026-10-08",
            "synthetic": True
        },
        # Case 8: Resolved case 4 (created 2026-10-09, resolved 2026-10-14, diff = 5 days)
        {
            "_id": "CASE-108",
            "id": "CASE-108",
            "patient_id": "P-014",
            "owner_id": "W-101",
            "status": "resolved",
            "due_date": "2026-10-15",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": "2026-10-14",
            "reason": "no_stock",
            "action": "alternate_phc",
            "notes": "Stock transfer routed",
            "created_at": "2026-10-09",
            "synthetic": True
        },
        # Case 9: In-progress case at worker level
        {
            "_id": "CASE-109",
            "id": "CASE-109",
            "patient_id": "P-006",
            "owner_id": "W-101",
            "status": "in_progress",
            "due_date": "2026-10-20",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": None,
            "reason": "feels_fine",
            "action": "counselling",
            "notes": "Call scheduled",
            "created_at": "2026-10-17",
            "synthetic": True
        },
        # Case 10: Damyanti's past-due assigned case (Damyanti P-007, due 2026-10-10 < demo date 2026-10-18)
        # Fixes screenshot bug: Status is Assigned, but due date is past due, action is Resolve, will escalate to supervisor on run!
        {
            "_id": "CASE-110",
            "id": "CASE-110",
            "patient_id": "P-007",
            "owner_id": "W-101",
            "status": "assigned",
            "due_date": "2026-10-10",
            "escalation_level": 0,
            "escalated_to": "worker",
            "escalated_at": None,
            "resolved_at": None,
            "reason": "lost_wages",
            "action": "flexible_slot",
            "notes": "Old follow-up needing escalation",
            "created_at": "2026-10-08",
            "synthetic": True
        }
    ]
    for c in cases:
        db.cases.update_one({"_id": c["_id"]}, {"$set": c}, upsert=True)
        
    # -------------------------------------------------------------
    # 9. OUTCOMES ("What Works" historical data)
    # -------------------------------------------------------------
    outcomes = [
        {"_id": "out_1", "condition": "Hypertension", "reason": "Feels fine (asymptomatic)", "action": "Adherence counselling + family buddy nudge", "cases_count": 142, "returned_count": 118, "return_rate": 0.831, "avg_days_to_return": 3.2, "synthetic": True},
        {"_id": "out_2", "condition": "Hypertension", "reason": "No medicine stock at PHC", "action": "Stock transfer / redirect to nearest CHC", "cases_count": 98, "returned_count": 76, "return_rate": 0.776, "avg_days_to_return": 2.4, "synthetic": True},
        {"_id": "out_3", "condition": "Hypertension", "reason": "Cannot afford travel / lost wages", "action": "Evening outreach slot + travel subsidy voucher", "cases_count": 65, "returned_count": 49, "return_rate": 0.754, "avg_days_to_return": 4.1, "synthetic": True},
        {"_id": "out_4", "condition": "Hypertension", "reason": "Side effects (headache/cough)", "action": "Escalate to MO for dose adjustment", "cases_count": 44, "returned_count": 38, "return_rate": 0.864, "avg_days_to_return": 1.8, "synthetic": True},
        {"_id": "out_5", "condition": "Type 2 Diabetes", "reason": "Feels fine (no sugar spikes)", "action": "Self-monitoring chart + micro-nudge", "cases_count": 120, "returned_count": 95, "return_rate": 0.792, "avg_days_to_return": 3.8, "synthetic": True},
        {"_id": "out_6", "condition": "Type 2 Diabetes", "reason": "No stock of Metformin/Glimepiride", "action": "Doorstep refill batch from central store", "cases_count": 88, "returned_count": 74, "return_rate": 0.841, "avg_days_to_return": 2.1, "synthetic": True},
        {"_id": "out_7", "condition": "Type 2 Diabetes", "reason": "Work schedule clash", "action": "Community weekend collection point", "cases_count": 52, "returned_count": 39, "return_rate": 0.750, "avg_days_to_return": 4.5, "synthetic": True},
        {"_id": "out_8", "condition": "Tuberculosis", "reason": "Severe nausea / side effects", "action": "Doctor consultation + supportive anti-emetic", "cases_count": 34, "returned_count": 31, "return_rate": 0.912, "avg_days_to_return": 1.5, "synthetic": True},
        {"_id": "out_9", "condition": "Tuberculosis", "reason": "Distance / mobility barrier", "action": "Directly observed therapy at home doorstep", "cases_count": 28, "returned_count": 25, "return_rate": 0.893, "avg_days_to_return": 2.0, "synthetic": True}
    ]
    for o in outcomes:
        db.outcomes.update_one({"_id": o["_id"]}, {"$set": o}, upsert=True)
        
    print("[Nirantar Seed] Database seeded successfully (idempotent upsert).")

def reset_synthetic_data(db=None):
    """
    Manager-only reset that restores synthetic demo documents to initial state.
    CRITICAL: Never touches accounts created through user signup (synthetic != True).
    """
    if db is None:
        db = get_db()
        
    collections = ["cases", "settings", "patients", "villages", "facilities", "stock", "escalation_rules", "outcomes"]
    for col in collections:
        db[col].delete_many({"synthetic": True})
        
    # In users, only delete synthetic demo users, preserve signed up users
    db.users.delete_many({"synthetic": True})
    
    seed_database(db)
    print("[Nirantar Reset] Synthetic demo documents reset to initial state. User-registered accounts preserved.")

if __name__ == "__main__":
    seed_database()
