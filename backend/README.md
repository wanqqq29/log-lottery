# Lottery Backend (Django + PostgreSQL)

## Quick Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations accounts lottery
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

## Env Keys

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

`settings.py` also keeps backward compatibility with `POSTGRES_*`.

## API Prefix

- Auth: `/api/auth/*`
- Business: `/api/*`

## Key Endpoints

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET/POST /api/auth/departments/`
- `GET/POST /api/projects/`
- `GET/POST /api/project-members/`
- `POST /api/project-members/bulk-upsert/`
- `GET/POST /api/prizes/`
- `GET/POST /api/exclusion-rules/`
- `POST /api/draw-batches/preview/`
- `POST /api/draw-batches/{id}/confirm/`
- `POST /api/draw-batches/{id}/void/`
- `POST /api/export-jobs/`
- `GET /api/export-jobs/{id}/download/`

## Core Flow

1. `POST /api/draw-batches/preview/` -> create `PENDING` batch + pending winners
2. `POST /api/draw-batches/{id}/confirm/` -> confirm winners and increase `prize.used_count`
3. `POST /api/draw-batches/{id}/void/` -> void pending winners and keep audit history

## Data Principles

- Phone is globally unique natural-person key.
- Project members keep snapshots (`uid/name/phone`) for draw history.
- Winner records are immutable in meaning: status changes from `PENDING` to `CONFIRMED` or `VOID`.
- Cross-project exclusion is rule-driven by source/target project and optional prize.
