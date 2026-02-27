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

## API Prefix

- Auth: `/api/auth/*`
- Business: `/api/*`

## Core Flow

1. `POST /api/draw-batches/preview/` -> create `PENDING` batch + pending winners
2. `POST /api/draw-batches/{id}/confirm/` -> confirm winners and increase `prize.used_count`
3. `POST /api/draw-batches/{id}/void/` -> void pending winners and keep audit history

## Data Principles

- Phone is globally unique natural-person key.
- Project members keep snapshots (`uid/name/phone`) for draw history.
- Winner records are immutable in meaning: status changes from `PENDING` to `CONFIRMED` or `VOID`.
- Cross-project exclusion is rule-driven by source/target project and optional prize.
