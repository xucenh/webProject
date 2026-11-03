# 01 — Application Definition

**Project:** Doctor Appointment Booking System
**Version:** Phase One (design only, no feature views yet)
**Stack:** Django 5.2 · PostgreSQL · server-rendered templates

---

## 1. Problem statement

Booking a doctor's appointment in a small clinic depends on phone calls and a
paper appointment book. Patients cannot see which doctors exist, what each one
specialises in, or when they are free, so they call during working hours, wait on
hold, and sometimes arrive to find the slot already taken. Reception staff keep
the schedule in their head and in a notebook, which makes double bookings and
missed cancellations routine.

This application replaces the notebook with a small web system: doctors publish
their weekly availability and exceptions, patients search for a doctor and book a
free 30-minute slot, and the system refuses to sell the same slot twice.

## 2. Actors

| Actor | Kind | Description |
| --- | --- | --- |
| **Patient** | human, authenticated | Searches doctors, views free slots, books and cancels appointments, sees own history. |
| **Doctor** | human, authenticated | Maintains a public profile, defines weekly working hours and days off, sees who booked what. |
| **Admin** | human, staff | Uses Django's built-in admin to manage users, doctors, schedules and appointments. No dedicated UI is built for this role. |

There is exactly one clinic in scope, so no clinic/organisation entity exists yet.

## 3. Scope

### 3.1 In scope

- Single-clinic directory of doctors with specialty, bio, clinic address, visit fee.
- Weekly recurring availability per doctor (weekday + start + end).
- One-off days off that override the weekly pattern.
- Slot search by doctor name and specialty.
- Booking, viewing and cancelling appointments, with a status lifecycle.
- Email confirmation (printed to console in development) and the data needed for reminders.
- Bonus items implemented only if time allows: reviews + average rating, clinic map link.

### 3.2 Explicitly out of scope

Listed so the report can defend the boundaries instead of looking incomplete:

- Online payments, invoices, insurance.
- Video consultations, chat, prescriptions, medical records.
- Multiple clinics/branches, staff accounts, per-clinic isolation.
- Native mobile app; the UI is responsive web only.
- Patient self-service rescheduling (cancel + rebook covers it).
- Multi-language UI and multi-timezone scheduling (clinic timezone only).
- HIPAA/GDPR compliance work; this is a coursework prototype.

## 4. Functional requirements

Every requirement has an ID used by the process diagrams and the traceability
matrix in `02-processes.md`.

### 4.1 Public (no login)

| ID | Requirement |
| --- | --- |
| FR-01 | A visitor can browse a list of doctors. |
| FR-02 | A visitor can search doctors by name and/or specialty. |
| FR-03 | A visitor can open a doctor's profile: specialty, bio, clinic address, visit fee, rating, available days. |

### 4.2 Authentication (both roles)

| ID | Requirement |
| --- | --- |
| FR-04 | A visitor can sign up as either a patient or a doctor; the chosen role is stored on the user. |
| FR-05 | A registered user can log in and log out. |
| FR-06 | After login the user is sent to a role-appropriate landing page. |

### 4.3 Doctor

| ID | Requirement |
| --- | --- |
| FR-07 | A doctor can view and edit their profile: specialty, bio, clinic name/address, visit fee. |
| FR-08 | A doctor can add, edit and delete weekly working hours (weekday, start, end). |
| FR-09 | A doctor can mark a single date as a day off with an optional reason. |
| FR-10 | A doctor can view all appointments booked with them, ordered by date and time. |
| FR-11 | A doctor can see the patient's name, phone and note for each appointment. |
| FR-12 | A doctor can mark a past appointment as completed. |

### 4.4 Patient

| ID | Requirement |
| --- | --- |
| FR-13 | A logged-in patient can see the free slots for a doctor on a given date, computed from working hours minus days off minus active bookings. |
| FR-14 | A patient can book one free slot, optionally with a note; the slot becomes unavailable immediately. |
| FR-15 | A patient can cancel their own appointment, which frees the slot for others. |
| FR-16 | A patient can view upcoming and past appointments. |

### 4.5 Bonus

| ID | Requirement |
| --- | --- |
| FR-17 | Booking sends a confirmation email to the patient and the doctor (console backend in dev). |
| FR-18 | The system can list appointments starting within the next 24 hours for a reminder job. |
| FR-19 | The doctor profile shows the clinic location (coordinates stored, map link rendered). |
| FR-20 | A patient can rate a completed appointment from 1 to 5 with an optional comment; the doctor's average rating is derived, never stored. |

## 5. Non-functional requirements

| ID | Requirement | How it is met |
| --- | --- | --- |
| NFR-01 | Every write action and every patient-specific page requires authentication. | Django auth + `LoginRequiredMixin` in Phase Two. |
| NFR-02 | The same doctor cannot have two active appointments in the same slot, even under concurrent requests. | PostgreSQL partial unique constraint `unique_active_slot_per_doctor` (verified, see report). |
| NFR-03 | Offered slots must match the doctor's schedule and exceptions. | Slots computed per request from `WorkingHours` − `TimeOff` − active `Appointment`s. |
| NFR-04 | All input is validated server-side. | Django forms + model constraints; the DB is the last line of defence. |
| NFR-05 | Passwords are never stored in plain text. | Django's default PBKDF2 hasher and validators. |
| NFR-06 | UI is simple, keyboard-navigable and readable on a phone. | Server-rendered templates in Phase Two, single stylesheet. |
| NFR-07 | A page responds in under ~2 seconds locally with the demo dataset. | Indexed queries on `(doctor, date)` and `(patient, date)`. |
| NFR-08 | No credentials in source control. | `.env` (git-ignored) + `.env.example`; settings read `os.environ`. |

## 6. Assumptions and constraints

1. One clinic, one physical address, one timezone (`UTC` in settings).
2. Appointments are exactly `SLOT_MINUTES = 30` minutes long; the value is one setting, not a per-doctor field.
3. Slots start on the hour or half hour, generated from a shift's start time.
4. A doctor's weekly hours are entered as start/end times, not as pre-built slots.
5. Cancellation is unrestricted: a patient may cancel any `booked` appointment at any time (no cutoff).
6. Doctor accounts are self-registered (open signup), matching the coursework brief.
7. Email is mocked by Django's console backend; SMS is out of scope.
8. Coursework environment: single developer, local PostgreSQL, no deployment pipeline.

## 7. Acceptance criteria

Written so they can be copied into tests in Phase Two.

| ID | Criterion |
| --- | --- |
| AC-01 | Logging in as a patient lands on the doctor list; as a doctor, on the doctor dashboard. |
| AC-02 | A doctor with Monday 09:00–12:00 shows six free slots on the next Monday. |
| AC-03 | Marking a date as a day off removes every slot for that date. |
| AC-04 | Booking 09:00 removes it from the free list and it cannot be booked by a second patient. |
| AC-05 | Cancelling an appointment makes the slot bookable again. |
| AC-06 | A patient cannot open or cancel another patient's appointment (404/403). |
| AC-07 | A doctor cannot view another doctor's appointment list. |
| AC-08 | Searching "cardio" returns cardiologists; searching a doctor's last name returns that doctor. |
| AC-09 | An appointment with `end_time <= start_time` is rejected. |
| AC-10 | A review can exist only once per appointment and only for a `completed` one (enforced in Phase Two forms). |

## 8. Glossary

| Term | Meaning |
| --- | --- |
| **Slot** | A 30-minute bookable interval, derived at request time; never a database row. |
| **Working hours** | A recurring weekly shift: weekday + start + end. `(doctor, weekday, start_time)` is unique. |
| **Time off** | A single date on which a doctor is unavailable, overriding the weekly pattern. |
| **Active appointment** | An appointment whose status is `booked` (not cancelled, not completed). |
| **Free slot** | A generated slot with no active appointment and not covered by time off. |
| **Role** | `doctor` or `patient`, stored on the single `User` model. |
