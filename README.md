# Smart Service Marketplace — Backend

Django + DRF + PostgreSQL backend for the Smart Service Marketplace MVP: a two-sided
marketplace connecting customers with local service vendors (barbers, salons, spas).
Customers discover nearby vendors, book appointments, and rate them; vendors manage
profiles, services, schedules, and bookings; admins verify vendors and manage plans.

Implements SRS v1.0 MVP functional requirements FR-101 … FR-303.

## Tech stack

- **Django 5.1 + Django REST Framework** — REST API
- **PostgreSQL** — database (with `btree_gist` for the booking exclusion constraint)
- **SimpleJWT** — access/refresh auth with refresh-token blacklist
- **drf-spectacular** — OpenAPI schema + Swagger UI
- **Celery** — async seam (eager in MVP)

External integrations (SMS OTP, FCM push, real-time) are **stubbed** behind provider
interfaces (`apps/notifications/providers/`). Swapping in Twilio / Firebase / Channels
later is a settings-only change — see `SMS_PROVIDER` / `PUSH_PROVIDER` / `REALTIME_PROVIDER`.

## Project layout

```
config/            settings (base/dev/prod/test), urls, celery, wsgi/asgi
apps/
  common/          base UUID model, role permissions, pagination, exceptions
  accounts/        custom User, phone/email auth backend, OTP, JWT, profile
  notifications/   provider ABCs + console stubs + factory, NotificationLog, DeviceToken
  vendors/         Vendor, Category, WorkingHours, ScheduleBlock, open/closed, admin verify
  catalog/         Service CRUD
  subscriptions/   SubscriptionPlan, VendorSubscription (choose/upgrade/downgrade)
  search/          proximity/haversine + filter query layer
  bookings/        Booking + exclusion constraint, availability, state machine
  reviews/         Review + rating aggregation signal
  dashboard/       vendor analytics
```

## Local setup

Requires Python 3.13 and a PostgreSQL 17 server.

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements/dev.txt   # Windows
# source .venv/bin/activate && pip install -r requirements/dev.txt  # POSIX

cp .env.example .env        # then edit DATABASE_URL to point at your Postgres
```

Set `DATABASE_URL` in `.env`, e.g. `postgres://postgres:postgres@127.0.0.1:5432/service_marketplace`.
A quick disposable Postgres via Docker:

```bash
docker run -d --name ssm-postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=service_marketplace -p 5433:5432 postgres:17
# then set DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5433/service_marketplace
```

Migrate, seed, and run:

```bash
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_demo      # demo vendor, services, customer
.venv\Scripts\python manage.py runserver
```

- API base: `http://127.0.0.1:8000/api/v1/`
- Swagger UI: `http://127.0.0.1:8000/api/schema/swagger-ui/`
- Django admin: `http://127.0.0.1:8000/django-admin/` (`createsuperuser` first)

Demo credentials (after `seed_demo`):
- Vendor — `vendor@example.com` / `VendorPass123`
- Customer — `customer@example.com` / `CustomerPass123`

## Booking flow (the core loop)

`category → vendor → time → confirm` in ≤4 steps:

1. `GET /api/v1/categories/?top=true` (parent pillars + children) and
   `GET /api/v1/vendors/?lat=&lng=&order_by=distance`
2. `GET /api/v1/vendors/{id}/` — services (with discounts + images) + hours
3. `GET /api/v1/vendors/{id}/availability/?services={id},{id}&date=YYYY-MM-DD`
   — slot length = combined duration of the selected services
4. `POST /api/v1/bookings/` `{vendor, services: [...], scheduled_start, notes}`
   — returns line items + `subtotal` / `service_fee` (5%, configurable) / `total`

## Mobile-app support endpoints (Slotify)

- `GET/POST/DELETE /api/v1/favorites/` — server-synced favorite vendors (delete by vendor id)
- `POST /api/v1/customer-reviews/` — vendor rates a customer after a completed booking
- `GET /api/v1/customers/{id}/` — customer profile for vendors (rating, reviews, shared history)
- `PATCH /api/v1/notifications/{id}/read/`, `POST /api/v1/notifications/read-all/`
- `GET /api/v1/vendors/me/analytics/` — monthly income, weekly appointments, bookings by service
- `POST /api/v1/complaints/` (+ own list); admin resolves via `/api/v1/admin/complaints/{id}/resolve/`
- `POST /api/v1/vendors/me/services/{id}/images/` (multipart), `DELETE .../images/{image_id}/`
- Service discounts: `has_discount`, `discount_percent`, `discount_description`, `discounted_price`

**Double-booking is prevented at the database level** (FR-122) via a partial Postgres
exclusion constraint on overlapping time ranges per vendor; concurrent conflicting
requests get `409 Conflict`. See `apps/bookings/models.py` and `apps/bookings/services.py`.

## Tests

Run against PostgreSQL (the exclusion constraint cannot exist on SQLite):

```bash
.venv\Scripts\python -m pytest -q
```

Includes the critical concurrency test (`apps/bookings/tests/test_concurrency.py`):
two threads booking the same slot → exactly one success + one 409, DB row count == 1.

## Lint / format

```bash
.venv\Scripts\python -m ruff check apps config
.venv\Scripts\python -m black apps config
```

## Reminders (FR-125)

```bash
.venv\Scripts\python manage.py send_due_reminders --window-minutes 60   # cron now; celery-beat later
```

## Notes

- Custom `User` (`accounts.User`) with a `role` field (customer/vendor/admin); login by
  phone **or** email via `apps/accounts/backends.py`. Argon2 password hashing.
- Localization: `LANGUAGES = [en, am]`; user-facing strings wrapped in `gettext_lazy`.
  Generate Amharic catalog with `manage.py makemessages -l am` (needs GNU gettext).
- Search uses lat/lng + Haversine (no PostGIS) — right-sized for a single-city MVP.
