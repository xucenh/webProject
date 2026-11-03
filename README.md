# Doctor Appointment Booking System

Django + PostgreSQL web app where doctors publish their weekly availability and
patients book 30-minute appointments. Built as a university project.

**Status: Phase One complete** — scope, process design and data model are done and
migrated to PostgreSQL. Feature views and templates start in Phase Two.

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

# 4. run
python3 manage.py runserver     # http://127.0.0.1:8000/admin/
```

Every later session only needs:

```bash
cd ~/Projects/UniWebProject
source .venv/bin/activate
python3 manage.py runserver
```

Without activating, use `.venv/bin/python manage.py ...` instead of `python3`.

## Doors that are open right now

| URL | State |
| --- | --- |
| `/admin/` | works — log in and manage users, doctors, schedules, appointments |
| `/` | Django's default "install worked" page (no project URLs yet) |
| everything else | Phase Two |


Database setup (PostgreSQL):

```bash
sudo -u postgres psql -c "CREATE ROLE clinic WITH LOGIN PASSWORD 'devpass' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE clinic_db OWNER clinic;"
```

## Layout

```
config/         Django project (settings, urls)
accounts/       User (role: doctor | patient)
doctors/        DoctorProfile, WorkingHours, TimeOff
appointments/   Appointment, Review
docs/           Phase One documents
templates/      (empty — Phase Two)
static/         (empty — Phase Two)
```
