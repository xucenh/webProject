# Doctor Appointment Booking System

Django + PostgreSQL web app where doctors publish their weekly availability and
patients book 30-minute appointments. Built as a university project.

**Status: Phase Two complete** — Persian (RTL) UI, authentication, doctor search and
profiles, weekly schedules and days off, derived 30-minute slots, booking,
cancellation, visit completion, reviews, demo data and acceptance tests.

## Docs

| File | Contents |
| --- | --- |
| [`docs/01-scope.md`](docs/01-scope.md) | Problem, actors, in/out of scope, FRs, NFRs, acceptance criteria |
| [`docs/02-processes.md`](docs/02-processes.md) | 4 swimlane process diagrams (book, cancel, publish availability, post-visit), state diagram, screen map, traceability |
| [`docs/03-data-model.md`](docs/03-data-model.md) | ERD, class diagram, field specs, constraints, integrity map |
| [`docs/PHASE-1-REPORT.md`](docs/PHASE-1-REPORT.md) | Every command, file and model/app connection from Phase One |
| [`docs/phase-one-plan.md`](docs/phase-one-plan.md) | The original plan |

## Quick start

Arch Linux (and most distros) block `pip install` into the system Python
(PEP 668 / `externally-managed-environment`). Always use a virtualenv;
`.venv/` is already git-ignored.

```bash
# 1. virtualenv + dependencies
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt   # first run downloads ~13 MB
# or, if uv is installed (faster, same result):
#   uv venv && uv pip install -r requirements.txt

# 2. config
cp .env.example .env            # set DB_PASSWORD and DJANGO_SECRET_KEY

# 3. database
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py seed_demo       # Persian demo clinic: doctors, patients, visits

# 4. run
python3 manage.py runserver       # http://127.0.0.1:8000/
```

Every later session only needs:

```bash
cd ~/Projects/UniWebProject
source .venv/bin/activate
python3 manage.py runserver
```

Without activating, use `.venv/bin/python manage.py ...` instead of `python3`.

## Demo accounts

`seed_demo` is idempotent; run it again to top up without duplicating bookings.
Use `python3 manage.py seed_demo --reset` to delete and recreate only the demo
accounts and their appointments.

| Role | Usernames | Password |
| --- | --- | --- |
| Doctor | `dr_ahmadi`, `dr_sadeghi`, `dr_karimi`, `dr_rahimi`, `dr_hosseini` | `Demo12345!` |
| Patient | `sara`, `reza`, `maryam`, `amir` | `Demo12345!` |

## Screens

| URL | Role | Purpose |
| --- | --- | --- |
| `/` | any | Persian landing page |
| `/accounts/signup/`, `/accounts/login/` | visitor | patient or doctor signup, login |
| `/doctors/` | any | doctor list and search by name/specialty |
| `/doctors/<id>/` | any | profile, weekly hours, date picker, free slots, booking |
| `/appointments/` | patient | upcoming/history, cancel, review completed visits |
| `/doctor/appointments/` | doctor | bookings, patient phone/note, complete a visit |
| `/doctor/schedule/` | doctor | add/edit/delete shifts, days off with booking warning |
| `/doctor/profile/` | doctor | specialty, clinic, fee, bio, map coordinates |
| `/admin/` | staff | Django admin |

All customer-facing pages are Persian and RTL. Dates are shown in the Jalali
calendar with Persian digits; date inputs accept `۱۴۰۵/۰۹/۰۷` (or ISO
`2026-11-28`). The clinic timezone is `Asia/Tehran`.

## Database setup (PostgreSQL)

```bash
sudo -u postgres psql -c "CREATE ROLE clinic WITH LOGIN PASSWORD 'devpass' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE clinic_db OWNER clinic;"
```

## Layout

```
config/         Django project (settings, urls)
core/           home view, Jalali helpers, Persian template filters, seed command
accounts/       User (role: doctor | patient), signup/login
doctors/        DoctorProfile, WorkingHours, TimeOff, slot service, doctor portal
appointments/   Appointment, Review, patient/doctor views, emails, reminders
docs/           Phase One design documents
templates/      Persian RTL pages
static/         stylesheet and small UI script
```

## Checks

```bash
python3 manage.py check
python3 manage.py test                  # 46 acceptance/behaviour tests
python3 manage.py send_reminders --dry-run   # next-24h reminder list
```
