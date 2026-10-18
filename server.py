"""
Nirantar Phase 7 Backend Server
MongoDB-backed REST API server with JWT cookie auth, role-based route guards,
rate limiting, demo clock, and static UI file serving.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta
import statistics

from db_mongo import get_db, is_db_healthy
from seed import seed_database, reset_synthetic_data
from auth import (
    hash_password, verify_password, create_session_token, decode_session_token,
    extract_cookie_token, sanitize_user, is_rate_limited, record_login_failure,
    clear_login_failures, INVITE_CODE, MANAGER_INVITE_CODE, VALID_ROLES,
    MANAGER_ROLES, FIELD_ROLES
)
from escalation_mongo import run_escalation, parse_date

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

def compute_case_sort_key(case, demo_date):
    """
    Default sort order:
    1. Escalated first (higher level first: level 2, then level 1)
    2. Then past due (oldest due date first)
    3. Then higher risk score
    4. Then earliest due date
    5. Resolved / closed_lost last
    """
    is_resolved = case.get("status") in ("resolved", "closed_lost")
    is_escalated = (case.get("status") == "escalated")
    esc_level = case.get("escalation_level", 0) if is_escalated else -1
    
    due_date = parse_date(case.get("due_date"))
    is_past_due = (not is_resolved and due_date and due_date < demo_date)
    risk_score = case.get("patient_risk_score", 0.0)
    due_str = case.get("due_date") or "9999-99-99"
    
    if is_resolved:
        tier = 4
    elif is_escalated:
        tier = 0 if esc_level >= 2 else 1
    elif is_past_due:
        tier = 2
    else:
        tier = 3
        
    return (
        tier,
        due_str if is_past_due else "",
        -risk_score,
        due_str
    )

class NirantarAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data, status_code=200, set_cookie=None, clear_cookie=False):
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Credentials", "true")
        
        if set_cookie:
            # Set 8 hour httpOnly session cookie
            cookie_val = f"nirantar_session={set_cookie}; HttpOnly; Path=/; SameSite=Lax; Max-Age=28800"
            self.send_header("Set-Cookie", cookie_val)
        elif clear_cookie:
            self.send_header("Set-Cookie", "nirantar_session=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0")
            
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.end_headers()

    def get_client_ip(self):
        client_address = self.client_address[0] if self.client_address else "127.0.0.1"
        return client_address

    def get_current_user(self):
        """
        Extracts and verifies session JWT from cookie or Bearer header.
        """
        token = extract_cookie_token(self.headers.get("Cookie", ""))
        if not token:
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                
        if not token:
            return None
            
        payload = decode_session_token(token)
        if not payload:
            return None
            
        db = get_db()
        user = db.users.find_one({"$or": [{"_id": payload["sub"]}, {"id": payload["sub"]}]})
        return user

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Health endpoint (public)
        if path == "/api/health":
            healthy, status = is_db_healthy()
            db = get_db()
            settings = db.settings.find_one({"_id": "system"}) or {}
            self._send_json({
                "status": "ok" if healthy else "error",
                "db": status,
                "database": db.name,
                "demo_date": settings.get("demo_date", "2026-10-18")
            }, status_code=200 if healthy else 503)
            return

        # 2. Auth: Current user profile
        if path == "/api/auth/me":
            user = self.get_current_user()
            if not user:
                self._send_json({"error": "Authentication required"}, status_code=401)
                return
            self._send_json({"user": sanitize_user(user)})
            return

        # 3. Environment info (demo mode flag)
        if path == "/api/config":
            demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
            self._send_json({"demo_mode": demo_mode})
            return

        # Static files (UI assets: HTML, CSS, JS, etc.)
        if not path.startswith("/api/"):
            if path == "/static" or path == "/static/":
                self.path = "/"
            elif path.startswith("/static/"):
                self.path = path[7:]
            return super().do_GET()

        # ------------------ PROTECTED ROUTES ------------------
        user = self.get_current_user()
        if not user:
            self._send_json({"error": "Authentication required. Please log in."}, status_code=401)
            return

        role = user.get("role", "")
        db = get_db()
        settings = db.settings.find_one({"_id": "system"}) or {}
        demo_date_str = settings.get("demo_date", "2026-10-18")
        demo_date = parse_date(demo_date_str)

        # Demo clock
        if path == "/api/clock":
            self._send_json({"current_date": demo_date_str})
            return

        # Manager Scorecard (Manager roles only)
        if path == "/api/scorecard":
            if role not in MANAGER_ROLES:
                self._send_json({"error": "Access forbidden: Manager role required"}, status_code=403)
                return

            active_patients = db.patients.count_documents({})
            patients_at_risk = db.patients.count_documents({"risk_score": {"$gte": 0.6}})

            all_cases = list(db.cases.find({}))
            total_cases = len(all_cases)
            resolved_cases = [c for c in all_cases if c.get("status") == "resolved"]
            resolved_count = len(resolved_cases)
            completion_rate = (resolved_count / total_cases) if total_cases > 0 else 0.0

            resolution_days = []
            for c in resolved_cases:
                if c.get("resolved_at") and c.get("created_at"):
                    try:
                        d1 = parse_date(c["created_at"])
                        d2 = parse_date(c["resolved_at"])
                        diff = (d2 - d1).days
                        if diff >= 0:
                            resolution_days.append(diff)
                    except Exception:
                        pass
            median_days = statistics.median(resolution_days) if resolution_days else 3.5

            open_and_escalated = len([
                c for c in all_cases 
                if c.get("status") in ("open", "assigned", "in_progress", "escalated")
            ])
            past_due_cases = len([
                c for c in all_cases
                if c.get("status") not in ("resolved", "closed_lost")
                and parse_date(c.get("due_date")) and parse_date(c.get("due_date")) < demo_date
            ])

            # Cases per worker
            worker_counts = {}
            for w in db.users.find({"role": "care_worker"}):
                w_id = w.get("id") or str(w.get("_id"))
                worker_counts[w_id] = {
                    "worker_id": w_id,
                    "worker_name": w.get("name"),
                    "case_count": 0
                }
            for c in all_cases:
                if c.get("status") not in ("resolved", "closed_lost") and c.get("owner_id") in worker_counts:
                    worker_counts[c["owner_id"]]["case_count"] += 1

            assumption_minutes = float(query.get("assumption", [settings.get("minutes_per_followup", 25)])[0])
            coordinator_hours_saved = round((resolved_count * assumption_minutes) / 60.0, 1)

            self._send_json({
                "current_date": demo_date_str,
                "active_patients": active_patients,
                "patients_at_risk": patients_at_risk,
                "total_cases": total_cases,
                "resolved_cases": resolved_count,
                "completion_rate": round(completion_rate, 3),
                "completion_rate_percent": round(completion_rate * 100, 1),
                "follow_up_completion_rate": round(completion_rate * 100, 1),
                "median_days_to_resolve": round(float(median_days), 1),
                "open_and_escalated": open_and_escalated,
                "open_and_escalated_cases": open_and_escalated,
                "cases_past_due": past_due_cases,
                "cases_per_worker": list(worker_counts.values()),
                "coordinator_hours_saved": coordinator_hours_saved,
                "hours_saved": coordinator_hours_saved,
                "assumption_minutes_per_followup": assumption_minutes,
                "assumption_label": "assumption"
            })
            return

        # Medicine availability (Manager roles only)
        if path == "/api/medicine-availability":
            if role not in MANAGER_ROLES:
                self._send_json({"error": "Access forbidden: Manager role required"}, status_code=403)
                return

            facilities = list(db.facilities.find({}))
            fac_map = {}
            for f in facilities:
                f_id = f.get("id") or str(f.get("_id"))
                fac_map[f_id] = {
                    "id": f_id,
                    "name": f.get("name"),
                    "type": f.get("type"),
                    "distance_km": f.get("distance_km"),
                    "inventory": [],
                    "stock": []
                }
            for item in db.stock.find({}):
                f_id = item.get("facility_id")
                if f_id in fac_map:
                    days = item.get("stock_days", 0)
                    status = "urgent" if days == 0 else ("watch" if days < 15 else "safe")
                    entry = {
                        "medicine_id": item.get("medicine_id"),
                        "medicine_name": item.get("medicine_name"),
                        "condition": item.get("condition"),
                        "stock_days": days,
                        "days_left": days,
                        "units_available": item.get("units_available", 0),
                        "status": status
                    }
                    fac_map[f_id]["inventory"].append(entry)
                    fac_map[f_id]["stock"].append(entry)

            # Critical refill alerts: refill due within 7 days (or overdue) at 0-stock facility
            critical_alerts = []
            for p in db.patients.find({}):
                refill_date = parse_date(p.get("refill_due_date"))
                f_id = p.get("assigned_facility_id")
                med_id = p.get("primary_medicine_id")
                stock_entry = db.stock.find_one({"facility_id": f_id, "medicine_id": med_id})
                if stock_entry and stock_entry.get("stock_days", 0) == 0 and refill_date:
                    days_diff = (refill_date - demo_date).days
                    if -30 <= days_diff <= 7:
                        fac = db.facilities.find_one({"$or": [{"_id": f_id}, {"id": f_id}]}) or {}
                        vil = db.villages.find_one({"$or": [{"_id": p.get("village_id")}, {"id": p.get("village_id")}]}) or {}
                        wrk = db.users.find_one({"$or": [{"_id": p.get("assigned_worker_id")}, {"id": p.get("assigned_worker_id")}]}) or {}
                        critical_alerts.append({
                            "patient_id": p.get("id") or str(p.get("_id")),
                            "patient_name": p.get("name"),
                            "condition": p.get("condition"),
                            "refill_due_date": p.get("refill_due_date"),
                            "days_until_refill": days_diff,
                            "medicine_name": stock_entry.get("medicine_name"),
                            "facility_id": f_id,
                            "facility_name": fac.get("name"),
                            "village_name": vil.get("name"),
                            "worker_name": wrk.get("name"),
                            "risk_category": p.get("risk_category")
                        })
            critical_alerts.sort(key=lambda x: x["days_until_refill"])
            self._send_json({
                "facilities": list(fac_map.values()),
                "critical_refill_alerts": critical_alerts,
                "critical_alerts": critical_alerts
            })
            return

        # Gap Ranking (Manager roles only)
        if path == "/api/gaps":
            if role not in MANAGER_ROLES:
                self._send_json({"error": "Access forbidden: Manager role required"}, status_code=403)
                return

            gap_list = []
            for v in db.villages.find({}):
                v_id = v.get("id") or str(v.get("_id"))
                v_name = v.get("name")
                fac_id = v.get("nearest_facility_id")
                km = float(v.get("distance_to_facility_km", 0.0))

                v_patients = list(db.patients.find({"village_id": v_id}))
                total_p = len(v_patients) or 1
                high_risk_p = len([p for p in v_patients if p.get("risk_score", 0.0) >= 0.6])
                share = high_risk_p / total_p

                stockouts = db.stock.count_documents({"facility_id": fac_id, "stock_days": 0})
                fac = db.facilities.find_one({"$or": [{"_id": fac_id}, {"id": fac_id}]}) or {}

                # Formula:
                # R = 40 * share of high-risk patients
                # D = min(30, 2.5 * km to nearest facility)
                # S = min(30, 15 * medicines out of stock)
                # gap = R + D + S out of 100, rounded to nearest 0.5
                R = round(40.0 * share, 1)
                D = round(min(30.0, 2.5 * km), 1)
                S = round(min(30.0, 15.0 * stockouts), 1)
                raw_gap = R + D + S
                gap_score = round(raw_gap * 2) / 2

                gap_list.append({
                    "village_id": v_id,
                    "village_name": v_name,
                    "population": v.get("population", 1000),
                    "distance_km": km,
                    "lat": v.get("lat", 28.6),
                    "lng": v.get("lng", 77.2),
                    "facility_id": fac_id,
                    "facility_name": fac.get("name", "PHC"),
                    "facility_type": fac.get("type", "PHC"),
                    "total_patients": total_p,
                    "high_risk_patients": high_risk_p,
                    "share_high_risk": round(share, 3),
                    "share_high_risk_percent": round(share * 100, 1),
                    "stockout_count": stockouts,
                    "gap_score": gap_score,
                    "factors": {
                        "risk_factor": R,
                        "distance_factor": D,
                        "stock_factor": S
                    }
                })
            gap_list.sort(key=lambda x: x["gap_score"], reverse=True)
            for idx, item in enumerate(gap_list, 1):
                item["rank"] = idx
            self._send_json({"villages": gap_list})
            return

        # Case Queue (Filtered & protected by role)
        if path == "/api/cases":
            cases_query = {}
            user_id = user.get("id") or str(user.get("_id"))
            
            # Field worker can ONLY see their own cases
            if role == "care_worker":
                cases_query["owner_id"] = user_id
            # Supervisor sees cases escalated to supervisor
            elif role == "supervisor":
                cases_query["escalated_to"] = "supervisor"
            # Doctor sees cases escalated to doctor
            elif role == "doctor":
                cases_query["escalated_to"] = "doctor"
            # Managers see all cases (can filter by query params)
            else:
                if query.get("owner_id"):
                    cases_query["owner_id"] = query.get("owner_id")[0]
                if query.get("status"):
                    cases_query["status"] = query.get("status")[0]

            cases_raw = list(db.cases.find(cases_query))
            cases_hydrated = []

            for item in cases_raw:
                c = dict(item)
                c["id"] = c.get("id") or str(c.get("_id"))
                c["_id"] = str(c.get("_id"))
                
                # Hydrate patient details
                p = db.patients.find_one({"$or": [{"_id": c.get("patient_id")}, {"id": c.get("patient_id")}]}) or {}
                c["patient_name"] = p.get("name", c.get("patient_id"))
                c["age"] = p.get("age", 50)
                c["gender"] = p.get("gender", "M")
                c["condition"] = p.get("condition", "General")
                c["risk_score"] = p.get("risk_score", 0.5)
                c["risk_category"] = p.get("risk_category", "Watch")
                c["patient_risk_score"] = c["risk_score"]

                # Hydrate village
                vil = db.villages.find_one({"$or": [{"_id": p.get("village_id")}, {"id": p.get("village_id")}]}) or {}
                c["village_name"] = vil.get("name", "Unknown Village")

                # Hydrate worker
                wrk = db.users.find_one({"$or": [{"_id": c.get("owner_id")}, {"id": c.get("owner_id")}]}) or {}
                c["owner_name"] = wrk.get("name", c.get("owner_id"))
                c["owner_role"] = wrk.get("role", "worker")

                # Compute past due based on demo clock
                due = parse_date(c.get("due_date"))
                c["is_past_due"] = bool(due and due < demo_date and c.get("status") not in ("resolved", "closed_lost"))
                c["is_due_today"] = bool(due and due == demo_date)

                cases_hydrated.append(c)

            # Sort using required default order:
            # Escalated first (higher level first), then past due (oldest first),
            # then higher risk score, then earliest due date, resolved last.
            cases_hydrated.sort(key=lambda c: compute_case_sort_key(c, demo_date))

            self._send_json({"cases": cases_hydrated, "demo_date": demo_date_str})
            return

        # Patients list
        if path == "/api/patients":
            patients = []
            for p in db.patients.find({}):
                item = dict(p)
                item["id"] = item.get("id") or str(item.get("_id"))
                item["_id"] = str(item.get("_id"))
                vil = db.villages.find_one({"$or": [{"_id": item.get("village_id")}, {"id": item.get("village_id")}]}) or {}
                item["village_name"] = vil.get("name")
                patients.append(item)
            self._send_json({"patients": patients})
            return

        # What Works
        if path == "/api/what-works":
            outcomes = []
            for o in db.outcomes.find({}):
                item = dict(o)
                item["_id"] = str(item.get("_id"))
                outcomes.append(item)
            outcomes.sort(key=lambda x: x.get("return_rate", 0), reverse=True)
            self._send_json({"what_works": outcomes})
            return

        # Facilities
        if path == "/api/facilities":
            facs = []
            for f in db.facilities.find({}):
                item = dict(f)
                item["_id"] = str(item.get("_id"))
                facs.append(item)
            self._send_json({"facilities": facs})
            return

        # Unknown API endpoint
        self._send_json({"error": "Endpoint not found"}, status_code=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self.get_client_ip()

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        # ------------------ AUTH ENDPOINTS (Public) ------------------
        if path == "/api/auth/signup":
            name = payload.get("name", "").strip()
            email = payload.get("email", "").strip().lower()
            password = payload.get("password", "")
            role = payload.get("role", "")
            invite_code = payload.get("invite_code", "").strip()

            if not name or not email or not password or not role:
                self._send_json({"error": "All fields are required"}, status_code=400)
                return

            if role not in VALID_ROLES:
                self._send_json({"error": f"Invalid role: {role}. Must be one of {list(VALID_ROLES)}"}, status_code=400)
                return

            if len(password) < 8:
                self._send_json({"error": "Password must be at least 8 characters long"}, status_code=400)
                return

            # Invite code checks
            if role in MANAGER_ROLES:
                if invite_code != MANAGER_INVITE_CODE:
                    self._send_json({"error": "Invalid manager invite code"}, status_code=400)
                    return
            else:
                if invite_code != INVITE_CODE:
                    self._send_json({"error": "Invalid field worker invite code"}, status_code=400)
                    return

            db = get_db()
            if db.users.find_one({"email": email}):
                self._send_json({"error": "Email is already registered"}, status_code=400)
                return

            user_id = f"U-{int(datetime.utcnow().timestamp())}"
            pw_hash = hash_password(password)
            new_user = {
                "_id": user_id,
                "id": user_id,
                "name": name,
                "email": email,
                "password_hash": pw_hash,
                "role": role,
                "facility_id": payload.get("facility_id", "HQ-1"),
                "village_coverage": payload.get("village_coverage", "General"),
                "theme": "clinical_teal",
                "synthetic": False,
                "created_at": datetime.utcnow().isoformat()
            }
            db.users.insert_one(new_user)
            token = create_session_token(user_id, role, email, name)
            self._send_json({
                "message": "Account created successfully",
                "user": sanitize_user(new_user),
                "token": token
            }, status_code=201, set_cookie=token)
            return

        if path == "/api/auth/login":
            email = payload.get("email", "").strip().lower()
            password = payload.get("password", "")

            # Rate limit check: 10 failed attempts per 15 mins per IP + email
            if is_rate_limited(email, client_ip):
                self._send_json({
                    "error": "Too many failed login attempts. Please try again in 15 minutes."
                }, status_code=429)
                return

            db = get_db()
            user = db.users.find_one({"email": email})
            if not user or not verify_password(password, user.get("password_hash", "")):
                record_login_failure(email, client_ip)
                self._send_json({"error": "Invalid email or password"}, status_code=401)
                return

            # Login success
            clear_login_failures(email, client_ip)
            u_id = user.get("id") or str(user.get("_id"))
            token = create_session_token(u_id, user.get("role"), email, user.get("name"))
            self._send_json({
                "message": "Login successful",
                "user": sanitize_user(user),
                "token": token
            }, status_code=200, set_cookie=token)
            return

        if path == "/api/auth/logout":
            self._send_json({"message": "Logged out successfully"}, status_code=200, clear_cookie=True)
            return

        # ------------------ PROTECTED POST ROUTES ------------------
        user = self.get_current_user()
        if not user:
            self._send_json({"error": "Authentication required. Please log in."}, status_code=401)
            return

        role = user.get("role", "")
        db = get_db()

        # Update preferred theme on user profile
        if path == "/api/user/theme":
            new_theme = payload.get("theme", "clinical_teal")
            db.users.update_one({"_id": user["_id"]}, {"$set": {"theme": new_theme}})
            self._send_json({"message": "Theme updated", "theme": new_theme})
            return

        # Advance demo clock (Manager roles only)
        if path == "/api/clock":
            if role not in MANAGER_ROLES:
                self._send_json({"error": "Access forbidden: Manager role required"}, status_code=403)
                return

            settings = db.settings.find_one({"_id": "system"}) or {}
            current_date_str = settings.get("demo_date", "2026-10-18")
            cur_date = parse_date(current_date_str)

            action = payload.get("action", "advance_day")
            days = int(payload.get("days", 1))
            new_date_str = payload.get("current_date")

            if new_date_str:
                target_date = parse_date(new_date_str)
            elif action == "advance_day":
                target_date = cur_date + timedelta(days=days)
            else:
                target_date = cur_date

            final_date_str = target_date.strftime("%Y-%m-%d")
            db.settings.update_one({"_id": "system"}, {"$set": {"demo_date": final_date_str}}, upsert=True)
            esc_res = run_escalation(db)

            self._send_json({
                "previous_date": current_date_str,
                "current_date": final_date_str,
                "days_advanced": days if not new_date_str else None,
                "escalation_result": esc_res
            })
            return

        # Run escalation (Manager roles only)
        if path == "/api/escalation/run":
            if role not in MANAGER_ROLES:
                self._send_json({"error": "Access forbidden: Manager role required"}, status_code=403)
                return
            res = run_escalation(db)
            self._send_json(res)
            return

        # Reset demo data (Manager roles only)
        if path == "/api/reset":
            if role not in MANAGER_ROLES:
                self._send_json({"error": "Access forbidden: Manager role required"}, status_code=403)
                return
            reset_synthetic_data(db)
            self._send_json({"message": "Demo data reset successfully (user accounts preserved)"})
            return

        # Assign task (Manager roles only)
        if path == "/api/cases":
            if role not in MANAGER_ROLES:
                self._send_json({"error": "Access forbidden: Manager role required to assign tasks"}, status_code=403)
                return

            settings = db.settings.find_one({"_id": "system"}) or {}
            demo_date_str = settings.get("demo_date", "2026-10-18")
            demo_date = parse_date(demo_date_str)

            patient_id = payload.get("patient_id")
            owner_id = payload.get("owner_id", "W-101")
            due_date = payload.get("due_date")
            reason = payload.get("reason", "feels_fine")
            action = payload.get("action", "counselling")
            notes = payload.get("notes", "")

            if not due_date:
                due_date = (demo_date + timedelta(days=2)).strftime("%Y-%m-%d")

            count = db.cases.count_documents({}) + 1
            case_id = f"CASE-{count:03d}"

            # Urgent side_effects goes straight to doctor immediately
            if reason == "side_effects":
                escalation_level = 2
                escalated_to = "doctor"
                status = "escalated"
                escalated_at = demo_date_str
            else:
                escalation_level = 0
                escalated_to = "worker"
                status = "assigned"
                escalated_at = None

            new_case = {
                "_id": case_id,
                "id": case_id,
                "patient_id": patient_id,
                "owner_id": owner_id,
                "status": status,
                "due_date": due_date,
                "escalation_level": escalation_level,
                "escalated_to": escalated_to,
                "escalated_at": escalated_at,
                "resolved_at": None,
                "reason": reason,
                "action": action,
                "notes": notes,
                "created_at": demo_date_str,
                "synthetic": True
            }
            db.cases.insert_one(new_case)
            self._send_json({
                "message": "Task assigned successfully",
                "case_id": case_id,
                "status": status,
                "escalated_to": escalated_to,
                "due_date": due_date
            }, status_code=201)
            return

        # Update case status / reason (Protected with role checks)
        if path.startswith("/api/cases/") and path.endswith("/status"):
            case_id = path.split("/")[3]
            case = db.cases.find_one({"$or": [{"_id": case_id}, {"id": case_id}]})
            if not case:
                self._send_json({"error": "Case not found"}, status_code=404)
                return

            user_id = user.get("id") or str(user.get("_id"))
            # Permissions:
            # - Care workers can only update their own cases
            # - Supervisors can update cases escalated to supervisor
            # - Doctors can update cases escalated to doctor
            # - Managers can update any case
            if role == "care_worker" and case.get("owner_id") != user_id:
                self._send_json({"error": "Access forbidden: you can only update your own cases"}, status_code=403)
                return
            if role == "supervisor" and case.get("escalated_to") != "supervisor":
                self._send_json({"error": "Access forbidden: case is not escalated to supervisor"}, status_code=403)
                return
            if role == "doctor" and case.get("escalated_to") != "doctor":
                self._send_json({"error": "Access forbidden: case is not escalated to doctor"}, status_code=403)
                return

            settings = db.settings.find_one({"_id": "system"}) or {}
            demo_date_str = settings.get("demo_date", "2026-10-18")

            new_status = payload.get("status")
            reason = payload.get("reason")
            action = payload.get("action")
            notes = payload.get("notes")

            update_doc = {}
            if new_status:
                update_doc["status"] = new_status
                if new_status == "resolved":
                    update_doc["resolved_at"] = demo_date_str
            if reason:
                update_doc["reason"] = reason
            if action:
                update_doc["action"] = action
            if notes is not None:
                update_doc["notes"] = notes

            # If reason updated to side_effects, escalate straight to doctor
            if reason == "side_effects" and case.get("escalated_to") not in ("doctor", "program_manager"):
                update_doc["escalation_level"] = 2
                update_doc["escalated_to"] = "doctor"
                update_doc["status"] = "escalated"
                update_doc["escalated_at"] = demo_date_str

            db.cases.update_one({"_id": case["_id"]}, {"$set": update_doc})
            self._send_json({
                "message": f"Case {case_id} updated",
                "case_id": case_id,
                "status": new_status or case.get("status")
            })
            return

        self._send_json({"error": "Endpoint not found"}, status_code=404)

def run_server(port=8000):
    db = get_db()
    seed_database(db)
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, NirantarAPIHandler)
    print(f"Nirantar Phase 7 Server running at http://localhost:{port} (http://127.0.0.1:{port})")
    httpd.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
