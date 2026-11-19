# PulseNotify

PulseNotify is a Django REST API for monitoring mock flight prices. Users create a threshold alert; Celery Beat checks active routes every minute and enqueues a notification when a price matches the threshold.

## Setup

1. Copy `.env.example` to `.env`. Local development uses SQLite by default; production uses the PostgreSQL values in `.env`.
2. Install dependencies: `python3 -m pip install -r requirements.txt`
3. Start infrastructure: `docker compose up -d db redis`
4. Run migrations: `python manage.py migrate`

## Run the three application processes

In separate terminals, run:

```bash
python manage.py runserver
celery -A pulsenotify worker --loglevel=info
celery -A pulsenotify beat --loglevel=info
```

## API

- `POST /api/auth/register/` and `POST /api/auth/login/` are public.
- `POST, GET /api/alerts/` and `DELETE /api/alerts/<id>/` require a JWT `Bearer` token.
- `GET /api/flights/price/?route=DEL-BOM` is the public internal mock price feed.
- `GET /api/admin/summary/` requires a user whose `UserProfile.role` is `admin`.

Run tests with `python manage.py test`.
