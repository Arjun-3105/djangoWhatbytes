# Healthcare Backend (Django + DRF + PostgreSQL)

Backend for a healthcare application: user registration/login with JWT, and REST APIs for patients, doctors, and patient-doctor mappings.

## Stack

- **Django** + **Django REST Framework**
- **PostgreSQL** (configurable via `DATABASE_URL`; SQLite used if unset, e.g. for local/test)
- **JWT** via `djangorestframework-simplejwt`
- **django-environ** for environment-based config

## Setup

1. **Clone and create virtualenv**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment**

   Copy `.env.example` to `.env` and set:

   - `SECRET_KEY` – Django secret (required in production)
   - `DATABASE_URL` – e.g. `postgres://user:password@localhost:5432/healthcare_db`
   - Optionally: `DEBUG`, `ALLOWED_HOSTS`

   If `.env` is missing, the app can run with defaults (SQLite, insecure secret) for local use.

3. **Database**

   ```bash
   python manage.py migrate
   python manage.py createsuperuser   # optional, for admin
   ```

4. **Run server**

   ```bash
   python manage.py runserver
   ```

## API Overview

Base URL: `http://localhost:8000/api/`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/auth/register/` | Register (name, email, password, password_confirm) |
| POST   | `/api/auth/login/`    | Login (email, password) → returns `access`, `refresh`, `user` |

Use the `access` token in the header: `Authorization: Bearer <access>`.

### Patients (authenticated; users see only their own)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/patients/`      | Create patient |
| GET    | `/api/patients/`      | List current user's patients |
| GET    | `/api/patients/<id>/` | Get patient |
| PUT    | `/api/patients/<id>/` | Update patient |
| DELETE | `/api/patients/<id>/` | Delete patient |

Patient payload: `first_name`, `last_name` (optional), `age`, `gender` (male/female/other), `address` (optional).

### Doctors

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/doctors/`      | Create doctor (authenticated) |
| GET    | `/api/doctors/`      | List all doctors (public) |
| GET    | `/api/doctors/<id>/` | Get doctor (public) |
| PUT    | `/api/doctors/<id>/` | Update doctor (authenticated) |
| DELETE | `/api/doctors/<id>/` | Delete doctor (authenticated) |

Doctor payload: `first_name`, `last_name` (optional), `specialization`, `email`, `phone_number` (optional).

### Patient–Doctor Mappings (authenticated; only for current user's patients)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/mappings/`              | Assign doctor to patient (`patient_id`, `doctor_id`) |
| GET    | `/api/mappings/`              | List all mappings for current user's patients |
| GET    | `/api/mappings/patient/<patient_id>/` | Doctors assigned to a patient |
| DELETE | `/api/mappings/<id>/`        | Remove mapping (id = mapping pk) |

## Tests

Run the full test suite:

```bash
python manage.py test
```

This will execute unit tests for:

- `accounts` – registration and JWT login flows
- `patients` – authenticated CRUD and per-user scoping
- `doctors` – public list/retrieve and authenticated write operations
- `mappings` – assigning/removing doctors to/from patients with permission checks

Tests default to an in-memory SQLite database and do not require PostgreSQL to be running.

## Production notes

- Set `SECRET_KEY` and `DATABASE_URL` in the environment; do not rely on defaults.
- Set `DEBUG=False` and configure `ALLOWED_HOSTS`.
- Use a production WSGI/ASGI server (e.g. Gunicorn/uvicorn) and serve static files appropriately.
