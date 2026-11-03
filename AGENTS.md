# AGENTS.md

## Project: Doctor Appointment Booking System

### Overview
Web app for booking doctor appointments with doctor and patient roles.

### Tech Stack
- **Backend:** Django (Python)
- **Database:** PostgreSQL
- Use Django ORM for all DB access; no raw SQL unless necessary
- Store DB credentials via environment variables (`.env`), never hardcode
- Use `psycopg2` (or `psycopg`) as the PostgreSQL driver

### Features

**Doctor**
- Login/signup
- Define specialty and profile
- Define working days and hours
- View booked appointments
- View patient info

**Patient**
- Login/signup
- View doctors
- Search doctors by name and specialty
- View available time slots
- Book and cancel appointments

**Bonus**
- Send confirmation via email/SMS
- Send appointment reminders
- Show clinic location on map
- Doctor can set visit fee and accept reviews
- Show calendar of available times

### Tech Notes
- Two roles: `doctor`, `patient`
- Auth required for all actions
- Time slots must reflect doctor's defined schedule
- Prevent double-booking of the same slot
- Use Django's built-in auth and custom user model with a `role` field

### Conventions
- Minimal, readable code
- Validate inputs server-side (Django forms/serializers)
- Keep UI simple and functional
- Write migrations for every model change
