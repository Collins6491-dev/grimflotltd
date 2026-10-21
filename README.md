# GRIMFLOT LTD platform

GRIMFLOT LTD is being built as a production-oriented Django platform for smart
technology, energy, electrical installations, services, and e-commerce. This
repository includes public content, customer accounts, catalogue, checkout,
payment verification, orders, and staff operations.

## Architecture

The project separates environment configuration from business domains:

- `config/settings/` holds shared, development, and strict production settings.
- `apps/` isolates bounded domains: core, accounts, catalogue, cart, orders,
  payments, services, projects, enquiries, bookings, reviews, and dashboard.
- `apps/accounts` provides the custom email-first user model from the outset;
  this avoids a dangerous user-model migration later.
- `templates/`, `static/`, and `media/` provide the presentation and upload
  boundaries. Development uploads are local; production requires S3-compatible
  object storage.
- `requirements/` separates shared, development, and production dependencies.
- `render.yaml` defines a Render-ready build, migration, Gunicorn, health, and
  PostgreSQL foundation.

The public foundation now provides centralized design tokens, a shared template,
responsive two-tier navigation, an accessible mobile menu, footer, branded
loader, GSAP enhancement foundation, a cinematic responsive homepage, and
branded 400/403/404/500 pages. Homepage copy, slides, capabilities, delivery
steps, FAQs, feature-panel images, social links, logo, and favicon pass through
validated, database-backed content records without a template redesign. The
restricted Django admin remains available for maintenance, while the custom
business dashboard manages staff operations and key homepage editorial records.

## Local setup

Use Python 3.12+ and create an isolated environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\development.txt
python manage.py migrate
python manage.py runserver
```

The local health endpoint is available at `http://127.0.0.1:8000/health/`.
Development uses SQLite and an in-memory email backend. Do not use development
settings or the included development secret in a deployment.

## Verification commands

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Production foundation

Use `config.settings.production` only after supplying every required variable
in `.env.example` through the host's secrets dashboard. In particular:

- `DATABASE_URL` must be a managed PostgreSQL connection string.
- `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `SITE_URL` must
  describe the real deployment.
- `MEDIA_STORAGE_PROVIDER=s3` plus object-storage credentials is mandatory;
  production deliberately refuses local, ephemeral media storage.
- SMTP values are configured, but transactional email flows are implemented in
  later stages. Do not enable customer email promises before those flows exist.
- Redis is documented now; it becomes required when shared caching and
  production rate limiting are implemented in the security stage.

Render deployment uses the commands in `render.yaml`: install production
requirements and collect static assets, run migrations in the pre-deploy step,
then start Gunicorn. It never resets a database or runs tests at startup.

### Backup and recovery

Configure scheduled PostgreSQL backups with the production database provider
before launch. Periodically restore a backup into an isolated database and run
`python manage.py migrate --settings=config.settings.production` against that
copy to verify recoverability. Enable versioning and a retention policy on the
media object-storage bucket; database backups do not include uploaded images.

## Delivery status

Implemented and verified locally: project structure, split settings, custom
user model and migration, static/media boundaries, logging, health endpoint,
starter automated tests, dependency definitions, Render configuration, the
Stage 2 shared public-site foundation, the Stage 3 responsive editorial homepage
with an accessible hero carousel, and the Stage 4 content models, migrations,
admin maintenance interface, image validation, company/brand settings, services,
projects, gallery, testimonials, FAQs, homepage content, social links, and SEO
settings.

Configured in code but requiring external credentials before verification:
PostgreSQL, S3-compatible storage, SMTP, Redis, and Render deployment.

Development imagery and editorial content are intentionally marked as temporary
and credited in `static/images/demo/CREDITS.md`; they must be replaced or
approved before public launch.

Before launch, replace the demonstration imagery and editorial copy, configure
the external production services, and complete a production deployment rehearsal.
