# Health-care-and-well-being
IIITD Hackathon


# Nirantar

**Helping people on long-term treatment stay in care.**

Nirantar predicts which patients are about to drop out of long-term treatment, finds out the real reason, and matches the most suitable rescue action — whether the user is a frontline health worker, a family caregiver, or the patient themselves.

---

### The Problem

Many patients diagnosed with chronic conditions (Hypertension, Diabetes, TB, Asthma, etc.) receive free medicine but never return for follow-up.  

Generic reminders have shown limited impact. In one Punjab hypertension trial, attendance stayed around **20%** even with WhatsApp reminders and myth-busting messages.

Existing tools mostly track patients *after* they miss a visit. Rescue is usually a manual phone call.

---

### The Solution

Nirantar follows a simple but powerful loop:

1. **Predict** – An explainable risk score ranks patients likely to drop out, with clear reasons.
2. **Ask Why** – Worker, patient, or family member selects the real barrier (feels fine, no stock, can’t travel, money, side effects…).
3. **Act** – The system suggests a targeted action matched to that reason.
4. **Learn** – Outcomes are logged so the system improves over time (“what works” for each reason and condition).

It is **condition-agnostic** — one engine that works across diseases through simple configuration.

---

### Who It’s For

| Role                    | How they use it                              |
|-------------------------|----------------------------------------------|
| Frontline Worker (ASHA/ANM/NGO) | Daily ranked risk list + one-tap actions    |
| Patient                 | Weekly self check-in + reason reporting      |
| Family Caregiver        | View relative’s status + send nudge          |
| PHC / District Staff    | Single dashboard with insights & escalations |

---

### Key Features

- Explainable dropout risk prediction
- Reason-aware rescue actions
- Multi-role mobile app (Worker / Patient / Family)
- “Why they drop out” system-level insights
- “What works” learning loop
- Condition-agnostic design
- Offline-first Progressive Web App
- Voice input support for reason capture

---

### Tech Stack

- **Frontend**: React PWA (Offline-first)
- **Backend**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **Maps & Charts**: Leaflet + Recharts
- **Voice**: Browser Speech API + LLM
- **Communication**: SMS / IVR (mocked in current version)

---

### Current Status

This is a working prototype built for a hackathon / demonstration.  
It uses synthetic data and is intended to validate the concept of **reason-aware, predictive rescue** for long-term treatment adherence.

---

### Pitch Line

> “Reminders alone don’t bring patients back.  
> Nirantar finds out why someone is slipping and matches the rescue to the reason.”
