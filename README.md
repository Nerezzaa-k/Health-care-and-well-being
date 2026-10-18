# 🏥 Nirantar — AI-Powered Treatment Continuity Platform

### Helping Patients Stay on Track with Long-Term Treatment

Nirantar is an AI-powered healthcare follow-up platform designed to help hospitals, healthcare workers, NGOs, and caregivers identify patients at risk of dropping out of long-term treatment.

Unlike systems that focus primarily on appointment reminders, Nirantar aims to identify patients who may discontinue treatment, understand the reasons behind missed follow-ups, recommend appropriate support actions, and track whether patients successfully return to care.

The platform is designed to support multiple medical departments, including diabetes care, hypertension, tuberculosis, oncology, cardiology, and other long-term treatment programs.

**Our mission is simple: Don't just remind patients. Understand why they drop out and help them stay in care.**

---

## 🚨 The Problem

Many patients receiving long-term treatment miss follow-up appointments or discontinue treatment before completing their recommended care.

This can happen for several reasons:
- 💰 Financial difficulties and treatment-related expenses.
- 🚍 Transportation problems and geographical barriers.
- 💊 Medication availability and concerns about side effects.
- 🧠 Lack of awareness about the importance of continuing treatment.
- 📅 Forgotten appointments and scheduling conflicts.
- ❤️ Limited follow-up support from healthcare providers.

Traditional appointment reminders may not address the underlying reasons patients miss their appointments.

Healthcare workers may also struggle to identify high-risk patients, prioritize follow-up efforts, and track whether their interventions are successful.

**The challenge is not just identifying missed appointments. It is understanding why patients disengage and coordinating the right response.**

---

## 💡 Our Solution

Nirantar introduces a predictive, reason-aware patient follow-up workflow that helps healthcare teams move from passive appointment tracking to proactive patient support.

The platform follows four key stages:

### 1. 🔍 Predict — Identify Patients at Risk
Identify patients who may be at risk of treatment interruption using explainable risk scores and relevant patient follow-up information.

The system highlights the factors contributing to each risk assessment so healthcare workers can understand why a case needs attention.

### 2. 🧩 Ask Why — Understand the Barrier
Capture the reasons behind missed appointments or potential treatment interruption through patient check-ins or input from authorized healthcare workers and caregivers.

Possible barriers include transportation difficulties, financial constraints, medication availability, side effects, and missed reminders.

The system does not assume a reason without confirmation.

### 3. 🎯 Act — Match Barriers with Appropriate Support
Recommend relevant follow-up actions based on the reported barrier.

For example:
- Forgotten appointment → Offer an appropriate reminder.
- Transportation difficulty → Check for available transport assistance.
- Financial difficulty → Identify applicable support programs.
- Reported side effects → Refer the concern to an appropriate healthcare professional.

Recommendations depend on available resources and healthcare-approved workflows.

### 4. 📊 Learn — Track Outcomes and Improve
Record follow-up actions and their outcomes to help healthcare organizations understand which approaches appear effective.

The platform can track whether patients were contacted, appointments were rescheduled, and follow-ups were completed.

Over time, these records can support evaluation and improvement of patient follow-up strategies.

---

## ✨ Key Features

### 1. Smart Follow-up Prioritization
Prioritize overdue cases using transparent rules and relevant patient follow-up information.

### 2. Barrier-to-Support Matching
Connect reported patient barriers with appropriate, available support options.

### 3. Patient Journey Dashboard
Provide authorized healthcare staff with a consolidated view of a patient's treatment follow-up journey, including scheduled appointments, missed visits, recorded barriers, assigned actions, and follow-up outcomes.

### 4. Follow-up Recovery Tracker
Track the progress of unresolved cases, from initial contact attempts to rescheduling and completion of follow-up appointments.

### 5. Explainable Risk Assessment
Display the factors contributing to a patient's risk classification instead of presenting an unexplained prediction.

### 6. Multi-Role Platform
Support different user roles with appropriate access and functionality:

- **Frontline Healthcare Workers:** Review prioritized cases and coordinate follow-ups.
- **Patients:** Complete check-ins and report barriers to continuing treatment.
- **Family Caregivers:** Support follow-up coordination when authorized by the patient.
- **Healthcare Administrators:** Monitor unresolved cases, follow-up performance, and program-level trends.

### 7. Healthcare Program Insights
Help organizations understand recurring barriers to treatment continuity and evaluate the outcomes of their follow-up interventions.

### 8. Offline-First Accessibility
Use Progressive Web App capabilities to support essential workflows in areas with unreliable internet connectivity, with synchronization when connectivity returns.

### 9. Voice-Assisted Reason Capture
Support voice-based input to make recording patient-reported barriers more accessible for users who have difficulty typing.

### 10. Configurable, Multi-Department Design
Adapt follow-up schedules, prioritization rules, and support workflows for different medical departments without requiring a separate application for every condition.

---

## 👥 Target Users

| User | Purpose |
|---|---|
| Hospitals and Clinics | Manage missed follow-ups and coordinate patient support. |
| ASHA/ANM Workers and NGOs | Identify patients requiring attention and coordinate follow-up activities. |
| Patients | Report barriers and stay informed about scheduled follow-ups. |
| Family Caregivers | Assist with treatment follow-up when authorized. |
| PHC and District Administrators | Monitor program performance and identify recurring barriers. |

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Frontend | React |
| Application Architecture | Progressive Web App (PWA) |
| Backend | FastAPI (Python) |
| Database | Supabase / PostgreSQL |
| Maps | Leaflet |
| Charts and Analytics | Recharts |
| Voice Input | Browser Speech API |
| AI Integration | LLM-based assistance, where configured |
| Communication | SMS / IVR integration (currently mocked) |

---

## 🔄 How Nirantar Works

```text
Patient Treatment Journey
          |
          v
Appointment or Follow-up Scheduled
          |
          v
Missed Follow-up / Potential Dropout Risk
          |
          v
Explainable Risk Assessment
          |
          v
Patient Barrier Identification
          |
          v
Barrier-to-Support Matching
          |
          v
Follow-up Action Assigned
          |
          v
Patient Contact and Rescheduling
          |
          v
Recovery Tracker Records Outcome
          |
          v
Program Insights and Evaluation
