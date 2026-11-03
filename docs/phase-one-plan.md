# Phase One Plan — Design & Definition

Goal: finish everything that can be reviewed on paper, before writing feature code.
No Django models or views get written until §3 is signed off.

Deliverables are written as Markdown in `docs/` with **Mermaid** diagrams, so they
live in git, diff cleanly, and render on GitHub. No draw.io files to lose.

---

## 1. Define the application — `docs/01-scope.md`

| Section | Content |
| --- | --- |
| Problem statement | 1 paragraph: who is in pain, why, what the app replaces (phone calls / paper book) |
| Users & actors | `patient`, `doctor`, (`admin` — Django admin only, no custom UI) |
| Scope — in | Everything in the AGENTS.md feature list, nothing more |
| Scope — out | Payments, video consults, prescriptions, multi-clinic, mobile app. List explicitly so the report can defend it |
| Functional requirements | Numbered `FR-01..FR-nn`, grouped by role, one line each, each traceable to a use case in §2 |
| Non-functional requirements | NFR-01..: auth on every route, no double booking, responsive/simple UI, response < 2s locally, Postgres-only data |
| Assumptions & constraints | Single clinic, one timezone, English only, desktop-first |
| Acceptance criteria | What "working" means, per feature, in testable sentences |
| Glossary | `slot`, `schedule`, `working hours`, `exception day`, `appointment status` |

Exit criteria: every AGENTS.md feature maps to at least one FR id, and every FR is
either in scope or explicitly excluded.

---

## 2. Design the processes — `docs/02-processes.md`

**a. Use case diagram** (Mermaid) — 2 actors, ~9 use cases:
sign up, log in, manage profile/specialty, define weekly availability, add day off,
search doctors, view slots, book appointment, cancel appointment, view appointments
(+ send confirmation/reminder as «extend» from book).

**b. Use case descriptions** — one small table per major use case:
`ID, actor, preconditions, main flow (numbered), alternative flows, postconditions`.
Write full descriptions only for: **Book appointment**, **Cancel appointment**,
**Define availability**. The rest get one-liners.

**c. Activity / flow diagrams** (Mermaid `flowchart`) for the three flows that carry
the real logic:
1. **Booking** — search → pick doctor → pick date → slots computed from schedule →
   slot free? → create appointment → email confirm. Branch: slot taken → re-show slots.
2. **Slot generation** — weekly hours − approved day off − already-booked appointments.
3. **Cancellation** — owns appointment? → status allows cancel? → mark cancelled →
   free the slot → notify.

**d. State diagram** for `Appointment`: `booked → completed` / `booked → cancelled`.
Decide now whether `completed` is manual or automatic (recommend: scheduled job later,
manual now).

**e. Sequence diagram** (one only, bonus marks) — Patient → View → Form → Model →
DB for booking, showing the uniqueness check.

**f. Screen map** — flat list of ~8 pages + which FR they satisfy:
`/`, `/login`, `/signup`, `/doctors`, `/doctors/<id>`, `/book/<doctor>/<date>`,
`/my-appointments`, `/doctor/dashboard`, `/doctor/schedule`. No visual mockups needed;
a table of page → purpose → role → FRs is enough for Phase One.

**g. Validation rules table** — where each rule is enforced (form / model / DB):
unique slot, no booking in the past, no booking outside working hours, one appointment
per slot, password rules.

Exit criteria: a reader can trace every FR → use case → diagram → screen.

---

## 3. Define and design the models — `docs/03-data-model.md`

**a. Entity list** with rationale — keep it to 4 core entities:

| Entity | Purpose | Key fields |
| --- | --- | --- |
| `User` | Custom auth user, `role ∈ {doctor, patient}` | email (login), password, first/last name, role, phone |
| `DoctorProfile` | Doctor-specific data, 1:1 with User | specialty, bio, clinic name/address, lat/lng (map bonus), visit_fee, avg_rating |
| `WorkingHours` | Recurring weekly availability | doctor FK, weekday 0–6, start_time, end_time |
| `TimeOff` | Exceptions to the weekly pattern | doctor FK, date, reason |
| `Appointment` | The booking itself | patient FK, doctor FK, date, start_time, end_time, status, created_at |
| `Review` *(bonus, optional)* | Rating a completed visit | appointment 1:1, rating 1–5, comment |

**b. ERD** (Mermaid `erDiagram`) with cardinalities and a written note on each
relationship: User 1—1 DoctorProfile, Doctor 1—N WorkingHours, Doctor 1—N TimeOff,
Patient 1—N Appointment, Doctor 1—N Appointment.

**c. Model spec per entity** — field name, Django field type, null/blank, default,
constraints, index. Plus these decisions to lock:

- **Slots are not stored** — computed on the fly from `WorkingHours` minus `TimeOff`
  minus booked `Appointment`s. Avoids stale rows; the cost is a small query in the view.
  (Alternative — pre-generating a `Slot` table — is noted and rejected, so the report
  shows the trade-off.)
- **Slot length** — fixed 30 min, as a constant `SLOT_MINUTES` in settings.
- **Double-booking prevention** — `UniqueConstraint(doctor, date, start_time)` at the
  DB level, not just a form check. This is the single most likely mark-losing bug.
- **Status** — `TextChoices` on `Appointment.status`, not a boolean.
- **Custom user** — `AbstractUser` with `role` field, `AUTH_USER_MODEL` set **before**
  the first migration. Cheap now, painful later.
- **Deletion** — `on_delete=PROTECT` for appointments, `CASCADE` for WorkingHours/TimeOff.

**d. Model sketches** — plain Python for the 6 models (no migration yet). This is the
contract the rest of the project builds on, so it gets reviewed like code.

**e. Admin plan** — what's registered, why (demo/report screenshots).

Exit criteria: ERD matches the sketches; every field in the spec appears in a sketch;
the uniqueness constraint is present in both.

---

## 4. Order of work

| Step | Output | Blocked by |
| --- | --- | --- |
| 1 | `01-scope.md` | — |
| 2 | `02-processes.md` use cases + screen map | 1 |
| 3 | `02-processes.md` diagrams | 2 |
| 4 | `03-data-model.md` entities + ERD | 1 |
| 5 | `03-data-model.md` field spec + sketches | 4 |
| 6 | Cross-check: FR → use case → model, fix gaps | 3, 5 |

Steps 1 and 4 can run in parallel; step 6 is the gate into Phase Two.

## 5. Decisions I need from you before step 3

1. **Slot length** — 30 min fixed? (affects every diagram)
2. **Doctor signup** — open self-registration, or admin creates doctors? (affects use cases)
3. **Email/SMS** — real sending in Phase Two, or mock/console backend? (affects sequence diagram)
4. **Cancellation rule** — free cancellation any time, or blocked within X hours?
5. **Report language** — English docs, or Arabic/other for the write-up?

Default answers if you don't care: 30 min · open signup · console backend · free
cancellation · English.
