# AnalyMark

AnalyMark is a university Technology Entrepreneurship project: a pricing decision-support tool for small marketplace sellers in Kazakhstan. The initial MVP focuses on Kaspi.kz.

The current version is a runnable Django application shell. It contains no marketplace integration, product records, live prices, or demonstration offer data. Product Search, Watchlist, and Analytics are clearly labeled placeholders.

## Requirements

- Python 3.12 (developed and checked with Python 3.12.3)
- Django 5.2 LTS, pinned with its required dependencies in `requirements.txt`
- SQLite, included with Python

No Node.js, frontend build, external database, API credentials, or Bootstrap/CDN access is needed.

## Local setup on Windows PowerShell

Run these commands from the project directory. Calling the virtual environment's Python directly avoids PowerShell activation policy issues.

```powershell
cd C:\AnalyMark
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py runserver
```

If `.venv` already exists and dependencies have been installed, only run migrations after relevant changes, then start the server. Open <http://127.0.0.1:8000/>. Stop the server with Ctrl+C.

On macOS/Linux, create the environment with `python3.12 -m venv .venv` and replace `.\.venv\Scripts\python.exe` with `.venv/bin/python` in the remaining commands.

## Configuration

`manage.py`, WSGI, and ASGI default to `config.settings.local`. Shared Django, SQLite, template, and static-file configuration lives in `config/settings/base.py`.

Local settings enable debug mode by default, allow only loopback hosts by default, and use an explicitly public development-only secret fallback. This configuration is for local development; production settings and deployment are not implemented.

Optional environment variables:

| Variable | Local behavior |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | Defaults to `config.settings.local` |
| `DJANGO_DEBUG` | Defaults to `true`; `true`, `1`, and `yes` enable debug |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts; defaults to `localhost,127.0.0.1,[::1]` |
| `DJANGO_SECRET_KEY` | Optional in local debug mode; required when debug is disabled |

`.env.example` documents these names. **Django does not automatically load `.env` files in this scaffold.** Set values in the shell before running commands, for example:

```powershell
$env:DJANGO_DEBUG = "true"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,[::1]"
```

Do not commit real secrets. `.env` files, virtual environments, local SQLite databases, and generated static files are ignored. The database is `db.sqlite3` at the project root. Times use `Asia/Qyzylorda` for display with Django timezone support enabled.

## Structure

```text
AnalyMark/
├── Reports/                      Existing university reports, preserved unchanged
├── config/
│   ├── settings/{base,local}.py  Shared and local settings
│   ├── urls.py                  Project routes, including Django admin
│   ├── asgi.py
│   └── wsgi.py
├── core/
│   ├── migrations/              No custom models or migrations yet
│   ├── templates/core/          Dashboard and placeholder pages
│   ├── tests/test_views.py      Main page, navigation, and routing tests
│   ├── apps.py
│   ├── admin.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── static/core/css/app.css       Responsive local stylesheet
├── templates/base.html          Shared branding, navigation, and data notice
├── .env.example
├── .gitattributes
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

## Routes and implementation status

| Route | Current behavior |
| --- | --- |
| `/` | Dashboard with branding, navigation, honest data status, and planned workflow |
| `/products/` | Product Search placeholder; no search or offers yet |
| `/watchlist/` | Watchlist placeholder; no saving or persistence yet |
| `/analytics/` | Analytics placeholder; no calculations or seller inputs yet |
| `/admin/` | Standard Django admin; optional local superuser required |

The shell uses Django templates, HTML, and local CSS with responsive navigation and visible keyboard focus. JavaScript is not needed at this stage. Django's standard authentication/session tables are created by `migrate`; there are no core business models yet. Optionally create a local admin account with `.\.venv\Scripts\python.exe manage.py createsuperuser`. No account is created automatically.

## Checks and tests

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --verbosity 2
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m pip check
```

The initial eight tests cover dashboard rendering, named routes, navigation, active-page marking, unavailable-data notices, placeholder disclosures, GET/HEAD versus POST behavior, missing routes, and static stylesheet discovery. They use `SimpleTestCase` and do not require a test database.

## MVP development direction

1. Define product, variant/bundle, offer, observation/source, seller-input, and watchlist records.
2. Add clearly labeled demonstration data or manual imports for a limited product category, then search and comparison.
3. Show timestamps, missing information, and uncertain matches explicitly.
4. Calculate minimum, average, and median benchmarks on a clearly defined comparable set. Show buyer totals only when the required data is known; unknown delivery is not zero.
5. Add seller product cost and desired minimum profit margin, with the margin definition explicit and buyer delivery separate.
6. Persist a basic watchlist; investigate real data access independently before adding a marketplace integration.

No marketplace scraping or external API integration exists. Demonstration prices must never be presented as verified live observations. Automatic repricing is outside scope. History, alerts, subscriptions, and additional marketplaces are deferred.

## Git

The local branch is `main`; the configured remote is <https://github.com/Light035/AnalyMark>. An initial commit can be made with a configured Git identity. No automatic push is part of setup. Inspect remote content before any future push and preserve any existing remote work.

The assignment documents in `Reports/` are retained as project history. They describe research and proposals, not evidence of implemented integrations.
