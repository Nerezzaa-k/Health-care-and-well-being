"""
Nirantar Phase 6 Database Module
SQLite database with synthetic data for cases, patients, facilities, medicines,
villages, what-works history, and escalation rules.
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nirantar.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(reset=False):
    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = get_connection()
    c = conn.cursor()
    
    # 1. System state (Demo clock)
    c.execute("""
    CREATE TABLE IF NOT EXISTS demo_clock (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        demo_date TEXT NOT NULL
    )
    """)
    
    # 2. Escalation Rules Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS escalation_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trigger TEXT NOT NULL UNIQUE,
        after_days INTEGER NOT NULL,
        target_role TEXT NOT NULL,
        label TEXT NOT NULL,
        description TEXT NOT NULL
    )
    """)
    
    # 3. Care Workers & Supervisors
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        facility_id TEXT,
        village_coverage TEXT
    )
    """)
    
    # 4. Facilities (PHCs, Sub-centres, CHCs)
    c.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        distance_km REAL NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL
    )
    """)
    
    # 5. Medicines & Facility Inventory
    c.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        condition TEXT NOT NULL
    )
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS facility_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id TEXT NOT NULL,
        medicine_id TEXT NOT NULL,
        stock_days INTEGER NOT NULL,
        units_available INTEGER NOT NULL,
        last_updated TEXT NOT NULL,
        FOREIGN KEY (facility_id) REFERENCES facilities (id),
        FOREIGN KEY (medicine_id) REFERENCES medicines (id)
    )
    """)
    
    # 6. Villages
    c.execute("""
    CREATE TABLE IF NOT EXISTS villages (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        nearest_facility_id TEXT NOT NULL,
        distance_to_facility_km REAL NOT NULL,
        population INTEGER NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        FOREIGN KEY (nearest_facility_id) REFERENCES facilities (id)
    )
    """)
    
    # 7. Patients
    c.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        village_id TEXT NOT NULL,
        condition TEXT NOT NULL,
        risk_score REAL NOT NULL,
        risk_category TEXT NOT NULL,
        assigned_facility_id TEXT NOT NULL,
        primary_medicine_id TEXT NOT NULL,
        refill_due_date TEXT NOT NULL,
        assigned_worker_id TEXT NOT NULL,
        FOREIGN KEY (village_id) REFERENCES villages (id),
        FOREIGN KEY (assigned_facility_id) REFERENCES facilities (id),
        FOREIGN KEY (primary_medicine_id) REFERENCES medicines (id),
        FOREIGN KEY (assigned_worker_id) REFERENCES users (id)
    )
    """)
    
    # 8. Cases (extending interventions)
    c.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        owner_id TEXT NOT NULL,
        status TEXT NOT NULL,
        due_date TEXT NOT NULL,
        escalation_level INTEGER NOT NULL DEFAULT 0,
        escalated_to TEXT NOT NULL DEFAULT 'worker',
        escalated_at TEXT,
        resolved_at TEXT,
        reason TEXT,
        action TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    """)
    
    # 9. What Works History Table (historical intervention outcomes)
    c.execute("""
    CREATE TABLE IF NOT EXISTS what_works (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition TEXT NOT NULL,
        reason TEXT NOT NULL,
        action TEXT NOT NULL,
        cases_count INTEGER NOT NULL,
        returned_count INTEGER NOT NULL,
        return_rate REAL NOT NULL,
        avg_days_to_return REAL NOT NULL
    )
    """)
    
    # Seed default data if empty
    c.execute("SELECT COUNT(*) FROM demo_clock")
    if c.fetchone()[0] == 0:
        seed_data(c)
        
    conn.commit()
    conn.close()

def seed_data(c):
    # Base Demo Date
    demo_start = "2026-10-18"
    c.execute("INSERT INTO demo_clock (id, demo_date) VALUES (1, ?)", (demo_start,))
    
    # Escalation Rules
    # trigger, after_days, target_role, label, description
    rules = [
        ("past_due", 0, "supervisor", "placeholders to set with the NGO", "Case is past due date and still at worker level -> escalate to supervisor"),
        ("urgent_reason", 0, "doctor", "placeholders to set with the NGO", "Reason is urgent (side_effects) -> escalate straight to doctor immediately"),
        ("unresolved_after_escalation", 2, "program_manager", "placeholders to set with the NGO", "Unresolved 2 days after escalation -> escalate to program manager")
    ]
    c.executemany("""
    INSERT INTO escalation_rules (trigger, after_days, target_role, label, description)
    VALUES (?, ?, ?, ?, ?)
    """, rules)
    
    # Care Workers & Supervisors
    users = [
        ("W-101", "Sunita Sharma", "worker", "FAC-1", "Kalyanpur, Chandpur"),
        ("W-102", "Pooja Verma", "worker", "FAC-1", "Rampur, Haripur"),
        ("W-103", "Manoj Kumar", "worker", "FAC-2", "Bilaspur, Shivpur"),
        ("SUP-201", "Dr. Rajesh Rao", "supervisor", "FAC-1", "All Sector A"),
        ("DOC-301", "Dr. Ananya Sen", "doctor", "FAC-1", "CHC Central"),
        ("PM-401", "Vikram Malhotra", "program_manager", "HQ-1", "District Program Office")
    ]
    c.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", users)
    
    # Facilities
    facilities = [
        ("FAC-1", "Rampur Primary Health Centre", "PHC", 4.2, 28.6139, 77.2090),
        ("FAC-2", "Bilaspur Health Sub-centre", "Sub-centre", 9.8, 28.6250, 77.2400),
        ("FAC-3", "Chandpur Community Health Centre", "CHC", 2.1, 28.5900, 77.1950),
        ("FAC-4", "Kalyanpur Health & Wellness", "HWC", 7.5, 28.6400, 77.1800)
    ]
    c.executemany("INSERT INTO facilities VALUES (?, ?, ?, ?, ?, ?)", facilities)
    
    # Medicines
    medicines = [
        ("MED-1", "Amlodipine 5mg", "Hypertension"),
        ("MED-2", "Telmisartan 40mg", "Hypertension"),
        ("MED-3", "Metformin 500mg", "Type 2 Diabetes"),
        ("MED-4", "Glimepiride 1mg", "Type 2 Diabetes"),
        ("MED-5", "Isoniazid 300mg", "Tuberculosis")
    ]
    c.executemany("INSERT INTO medicines VALUES (?, ?, ?)", medicines)
    
    # Facility Inventory (Stock status)
    # stock_days: 0 = Out of stock (Urgent), 1-14 = Watch, 15+ = Safe
    inventory = [
        # Rampur PHC
        ("FAC-1", "MED-1", 45, 1200, demo_start), # Amlodipine Safe
        ("FAC-1", "MED-2", 0, 0, demo_start),    # Telmisartan OUT OF STOCK
        ("FAC-1", "MED-3", 30, 800, demo_start),  # Metformin Safe
        ("FAC-1", "MED-4", 12, 140, demo_start),  # Glimepiride Watch
        ("FAC-1", "MED-5", 60, 450, demo_start),  # Isoniazid Safe
        
        # Bilaspur Sub-centre
        ("FAC-2", "MED-1", 0, 0, demo_start),    # Amlodipine OUT OF STOCK
        ("FAC-2", "MED-2", 20, 300, demo_start),  # Telmisartan Safe
        ("FAC-2", "MED-3", 0, 0, demo_start),    # Metformin OUT OF STOCK
        ("FAC-2", "MED-4", 8, 90, demo_start),    # Glimepiride Watch
        ("FAC-2", "MED-5", 0, 0, demo_start),    # Isoniazid OUT OF STOCK
        
        # Chandpur CHC
        ("FAC-3", "MED-1", 60, 2500, demo_start), # Safe
        ("FAC-3", "MED-2", 45, 1800, demo_start), # Safe
        ("FAC-3", "MED-3", 40, 1500, demo_start), # Safe
        ("FAC-3", "MED-4", 35, 900, demo_start),  # Safe
        ("FAC-3", "MED-5", 50, 600, demo_start),  # Safe
        
        # Kalyanpur HWC
        ("FAC-4", "MED-1", 10, 150, demo_start),  # Watch
        ("FAC-4", "MED-2", 0, 0, demo_start),    # OUT OF STOCK
        ("FAC-4", "MED-3", 14, 200, demo_start),  # Watch
        ("FAC-4", "MED-4", 0, 0, demo_start),    # OUT OF STOCK
        ("FAC-4", "MED-5", 25, 180, demo_start)   # Safe
    ]
    c.executemany("""
    INSERT INTO facility_inventory (facility_id, medicine_id, stock_days, units_available, last_updated)
    VALUES (?, ?, ?, ?, ?)
    """, inventory)
    
    # Villages
    villages = [
        ("VIL-1", "Bilaspur Kalan", "FAC-2", 11.2, 1420, 28.6320, 77.2450),
        ("VIL-2", "Kalyanpur Basti", "FAC-4", 8.4, 980, 28.6450, 77.1720),
        ("VIL-3", "Rampur Dehat", "FAC-1", 5.6, 2100, 28.6080, 77.2150),
        ("VIL-4", "Shivpur Khurd", "FAC-2", 9.1, 1150, 28.6210, 77.2350),
        ("VIL-5", "Haripur Mandi", "FAC-1", 3.8, 1850, 28.6180, 77.2020),
        ("VIL-6", "Chandpur Gaon", "FAC-3", 1.8, 2400, 28.5880, 77.1980)
    ]
    c.executemany("INSERT INTO villages VALUES (?, ?, ?, ?, ?, ?, ?)", villages)
    
    # Patients (Synthetic cohort of 24 patients)
    # refill_due_date set relative to demo_start (2026-10-18)
    patients = [
        # Patients whose refill runs out within 7 days at facilities with 0 stock:
        # FAC-1 has 0 stock of MED-2 (Telmisartan)
        ("P-001", "Ram Charan", 58, "M", "VIL-3", "Hypertension", 0.88, "Urgent", "FAC-1", "MED-2", "2026-10-21", "W-102"),
        ("P-002", "Kamla Devi", 62, "F", "VIL-3", "Hypertension", 0.79, "Urgent", "FAC-1", "MED-2", "2026-10-23", "W-102"),
        # FAC-2 has 0 stock of MED-1 (Amlodipine), MED-3 (Metformin), MED-5 (Isoniazid)
        ("P-003", "Shiv Dayal", 51, "M", "VIL-1", "Type 2 Diabetes", 0.84, "Urgent", "FAC-2", "MED-3", "2026-10-20", "W-103"),
        ("P-004", "Meera Bai", 45, "F", "VIL-1", "Hypertension", 0.92, "Urgent", "FAC-2", "MED-1", "2026-10-22", "W-103"),
        ("P-005", "Gopal Singh", 39, "M", "VIL-4", "Tuberculosis", 0.95, "Urgent", "FAC-2", "MED-5", "2026-10-24", "W-103"),
        # FAC-4 has 0 stock of MED-2 and MED-4
        ("P-006", "Sita Ram", 67, "M", "VIL-2", "Hypertension", 0.76, "Urgent", "FAC-4", "MED-2", "2026-10-21", "W-101"),
        ("P-007", "Damyanti", 54, "F", "VIL-2", "Type 2 Diabetes", 0.81, "Urgent", "FAC-4", "MED-4", "2026-10-25", "W-101"),
        
        # Other high risk patients
        ("P-008", "Bablu Yadav", 49, "M", "VIL-1", "Hypertension", 0.72, "Urgent", "FAC-2", "MED-2", "2026-11-05", "W-103"),
        ("P-009", "Sunita Bai", 59, "F", "VIL-2", "Type 2 Diabetes", 0.68, "Urgent", "FAC-4", "MED-3", "2026-11-12", "W-101"),
        ("P-010", "Dhanraj", 63, "M", "VIL-3", "Hypertension", 0.65, "Urgent", "FAC-1", "MED-1", "2026-11-02", "W-102"),
        
        # Watch patients (risk 0.35 - 0.59)
        ("P-011", "Vidya Devi", 44, "F", "VIL-5", "Type 2 Diabetes", 0.48, "Watch", "FAC-1", "MED-3", "2026-10-29", "W-102"),
        ("P-012", "Kishan Lal", 53, "M", "VIL-5", "Hypertension", 0.42, "Watch", "FAC-1", "MED-1", "2026-11-04", "W-102"),
        ("P-013", "Rajeshwari", 47, "F", "VIL-6", "Hypertension", 0.38, "Watch", "FAC-3", "MED-2", "2026-11-10", "W-101"),
        ("P-014", "Anand Mohan", 56, "M", "VIL-6", "Type 2 Diabetes", 0.45, "Watch", "FAC-3", "MED-3", "2026-11-08", "W-101"),
        ("P-015", "Om Prakash", 61, "M", "VIL-4", "Hypertension", 0.52, "Watch", "FAC-2", "MED-2", "2026-10-28", "W-103"),
        ("P-016", "Geeta Rani", 50, "F", "VIL-5", "Tuberculosis", 0.55, "Watch", "FAC-1", "MED-5", "2026-11-01", "W-102"),
        
        # Safe patients (risk < 0.35)
        ("P-017", "Prem Lata", 41, "F", "VIL-6", "Hypertension", 0.22, "Safe", "FAC-3", "MED-1", "2026-11-20", "W-101"),
        ("P-018", "Suraj Bhan", 38, "M", "VIL-6", "Type 2 Diabetes", 0.18, "Safe", "FAC-3", "MED-4", "2026-11-25", "W-101"),
        ("P-019", "Champa Devi", 65, "F", "VIL-5", "Hypertension", 0.25, "Safe", "FAC-1", "MED-1", "2026-11-18", "W-102"),
        ("P-020", "Harish Chandra", 58, "M", "VIL-3", "Type 2 Diabetes", 0.28, "Safe", "FAC-1", "MED-3", "2026-11-22", "W-102"),
        ("P-021", "Nirmala", 46, "F", "VIL-6", "Hypertension", 0.15, "Safe", "FAC-3", "MED-2", "2026-11-30", "W-101"),
        ("P-022", "Satish", 52, "M", "VIL-5", "Type 2 Diabetes", 0.20, "Safe", "FAC-1", "MED-3", "2026-11-28", "W-102"),
        ("P-023", "Brij Mohan", 69, "M", "VIL-4", "Hypertension", 0.31, "Safe", "FAC-2", "MED-2", "2026-11-15", "W-103"),
        ("P-024", "Rani Kaur", 55, "F", "VIL-1", "Type 2 Diabetes", 0.33, "Safe", "FAC-2", "MED-4", "2026-11-19", "W-103")
    ]
    c.executemany("INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", patients)
    
    # Cases (Initial seeded cases to support demo flow & metrics)
    # Demo date is 2026-10-18
    cases = [
        # Case 1: Assigned to W-101, due 2026-10-19 (Normal due date, tomorrow - not past due yet!)
        ("CASE-101", "P-001", "W-101", "assigned", "2026-10-19", 0, "worker", None, None, "no_stock", "alternate_phc", "Patient needs refill transfer", "2026-10-17"),
        
        # Case 2: Past due case (due 2026-10-16 < 2026-10-18) - currently assigned to W-102
        ("CASE-102", "P-003", "W-102", "assigned", "2026-10-16", 0, "worker", None, None, "cant_travel", "doorstep_refill", "Needs doorstep delivery", "2026-10-14"),
        
        # Case 3: Urgent reason case (side_effects) -> goes straight to doctor!
        ("CASE-103", "P-005", "W-103", "assigned", "2026-10-20", 0, "worker", None, None, "side_effects", "doctor_consult", "Complaining of severe dizziness & nausea", "2026-10-18"),
        
        # Case 4: Already escalated to supervisor 3 days ago (escalated_at: 2026-10-15), still unresolved -> ready to escalate to program manager!
        ("CASE-104", "P-004", "W-103", "escalated", "2026-10-14", 1, "supervisor", "2026-10-15", None, "lost_wages", "flexible_slot", "Supervisor follow up pending", "2026-10-12"),
        
        # Case 5: Resolved case 1 (created 2026-10-10, resolved 2026-10-13, days = 3)
        ("CASE-105", "P-011", "W-102", "resolved", "2026-10-14", 0, "worker", None, "2026-10-13", "feels_fine", "counselling", "Completed adherence counselling with family", "2026-10-10"),
        
        # Case 6: Resolved case 2 (created 2026-10-11, resolved 2026-10-15, days = 4)
        ("CASE-106", "P-012", "W-102", "resolved", "2026-10-15", 0, "worker", None, "2026-10-15", "cant_travel", "doorstep_refill", "Delivered blister packs", "2026-10-11"),
        
        # Case 7: Resolved case 3 (created 2026-10-08, resolved 2026-10-10, days = 2)
        ("CASE-107", "P-013", "W-101", "resolved", "2026-10-12", 0, "worker", None, "2026-10-10", "feels_fine", "counselling", "BP stabilized, agreed to daily log", "2026-10-08"),
        
        # Case 8: Resolved case 4 (created 2026-10-09, resolved 2026-10-14, days = 5)
        ("CASE-108", "P-014", "W-101", "resolved", "2026-10-15", 0, "worker", None, "2026-10-14", "no_stock", "alternate_phc", "Routed to Chandpur CHC with stock", "2026-10-09"),
        
        # Case 9: In-progress case at worker level
        ("CASE-109", "P-006", "W-101", "in_progress", "2026-10-20", 0, "worker", None, None, "feels_fine", "counselling", "First counselling call done", "2026-10-17"),
        
        # Case 10: Closed lost case (patient migrated, resolved/closed never escalates)
        ("CASE-110", "P-007", "W-101", "closed_lost", "2026-10-10", 0, "worker", None, None, "lost_wages", "flexible_slot", "Patient relocated to work site", "2026-10-08")
    ]
    c.executemany("""
    INSERT INTO cases (id, patient_id, owner_id, status, due_date, escalation_level, escalated_to, escalated_at, resolved_at, reason, action, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cases)
    
    # What Works Historical Table
    what_works_data = [
        ("Hypertension", "Feels fine (asymptomatic)", "Adherence counselling + family buddy nudge", 142, 118, 0.831, 3.2),
        ("Hypertension", "No medicine stock at PHC", "Stock transfer / redirect to nearest CHC", 98, 76, 0.776, 2.4),
        ("Hypertension", "Cannot afford travel / lost wages", "Evening outreach slot + travel subsidy voucher", 65, 49, 0.754, 4.1),
        ("Hypertension", "Side effects (headache/cough)", "Escalate to MO for dose adjustment", 44, 38, 0.864, 1.8),
        ("Type 2 Diabetes", "Feels fine (no sugar spikes)", "Self-monitoring chart + micro-nudge", 120, 95, 0.792, 3.8),
        ("Type 2 Diabetes", "No stock of Metformin/Glimepiride", "Doorstep refill batch from central store", 88, 74, 0.841, 2.1),
        ("Type 2 Diabetes", "Work schedule clash", "Community weekend collection point", 52, 39, 0.750, 4.5),
        ("Tuberculosis", "Severe nausea / side effects", "Doctor consultation + supportive anti-emetic", 34, 31, 0.912, 1.5),
        ("Tuberculosis", "Distance / mobility barrier", "Directly observed therapy at home doorstep", 28, 25, 0.893, 2.0)
    ]
    c.executemany("""
    INSERT INTO what_works (condition, reason, action, cases_count, returned_count, return_rate, avg_days_to_return)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, what_works_data)

if __name__ == "__main__":
    init_db(reset=True)
    print("Database initialized successfully at", DB_PATH)
