# AnalyMark

AnalyMark is a university Technology Entrepreneurship project: a pricing decision-support tool for small marketplace sellers in Kazakhstan. The initial MVP focuses on Kaspi.kz.

The current version provides a dashboard with real database counts, demonstration product search/comparison, per-product analytics, private persistent Watchlists using Django accounts, and charts/tables based only on recorded observations. It has no marketplace integration or live prices.

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
.\.venv\Scripts\python.exe manage.py load_demo_data
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py runserver
```

If `.venv` already exists and dependencies have been installed, only run migrations after relevant changes, then start the server. Open <http://127.0.0.1:8000/>. Stop the server with Ctrl+C.

Loading demo data is optional; Product Search shows an empty state until offers are added. For the existing environment, run `migrate`, `load_demo_data`, and `runserver` using the virtual environment's Python.

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

### Before deployment

This is a local demonstration configuration, not a deployment configuration. `manage.py check --deploy` against the default local settings reports six warnings: debug enabled, the public development secret, missing HTTPS redirect/HSTS, and session/CSRF cookies without the Secure flag. These defaults support loopback HTTP development; a clean `manage.py check` does not certify deployment readiness.

Before exposing the app, provide a separate deployment settings module with debug disabled, a private random secret, explicit allowed hosts, and HTTPS with secure session/CSRF cookies. Configure redirects and HSTS only for the actual HTTPS/proxy arrangement. Use a suitable WSGI/ASGI server and serve collected static assets separately; never publish the project root, reports, environment files, or SQLite database as static files. Protect and back up the database. Follow the [Django 5.2 deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) and rerun `check --deploy` with the intended settings. Production hosting, login rate limiting, dependency vulnerability scanning, and an external security assessment are not provided by this iteration.

## Structure

```text
AnalyMark/
├── Reports/                      Local university reports, excluded from Git
├── config/
│   ├── settings/{base,local}.py  Shared and local settings
│   ├── urls.py                  Project routes, including Django admin
│   ├── asgi.py
│   └── wsgi.py
├── core/
│   ├── migrations/              Catalog, Watchlist, and observation schema
│   ├── management/commands/     Demo loader and explicit observation capture
│   ├── templates/core/          Dashboard, search, analytics, Watchlist, history, shared includes
│   ├── tests/                   Models, auth, Watchlist, observations, search, and routing
│   ├── apps.py
│   ├── admin.py
│   ├── models.py
│   ├── comparison.py            Decimal statistics and sorting
│   ├── history.py               SVG coordinates for stored observation points
│   ├── forms.py                 Validated GET filters
│   ├── urls.py
│   └── views.py
├── static/core/css/app.css       Responsive local stylesheet
├── templates/                   Shared shell and registration/login.html
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
| `/` | Database counts, demo/unverified breakdowns, latest recording time, and product links |
| `/products/` | Product/brand search, marketplace filter, sorting, offer details, and listed-price benchmarks |
| `/products/<product_id>/` | Public product analytics: exact-product offers, benchmarks, stored history, Watchlist control |
| `/watchlist/` | Private saved products belonging to the signed-in user |
| `/watchlist/add/<product_id>/` | Authenticated, CSRF-protected POST; save to your own list |
| `/watchlist/remove/<product_id>/` | Authenticated, CSRF-protected POST; remove from your own list |
| `/accounts/login/` | Django username/password login, with safe return URL handling |
| `/accounts/logout/` | CSRF-protected POST logout |
| `/offers/<offer_id>/history/` | Public table of actual stored listed-price observations for one offer |
| `/analytics/` | Product catalog linking to individual product analytics; no cross-product price benchmark |
| `/admin/` | Standard Django admin; optional local superuser required |

The shell uses Django templates, HTML, and local CSS with responsive navigation and visible keyboard focus. JavaScript is not needed at this stage. `migrate` creates the catalog tables as well as Django's standard authentication/session tables. Marketplace, Product, and Offer are registered in Django admin. Optionally create a local admin account with `.\.venv\Scripts\python.exe manage.py createsuperuser`. No account is created automatically.

The presentation layout uses shared type, spacing, button, card, and feedback styles across the workspace. The dashboard starts with a direct **Search offers** action. Product analytics puts current offer comparison before recorded history, with section links for benchmarks, offers, and history. **Buyer total** consistently means listed price minus discount plus buyer delivery; unavailable totals use an explicit warning treatment and never stand in for zero. Login also offers a return to public Product Search without signing in.

On small screens, navigation stays visible in a two-column layout, forms stack, and wide history tables/charts scroll inside keyboard-focusable, labeled regions. Error summaries link to invalid visible search fields; hidden product-filter errors offer Reset filters instead. Long names wrap, price figures use aligned numerals, and demo/unknown/unverified labels remain readable. These presentation changes do not change calculations, capture observations, or alter authentication/CSRF rules. No frontend framework, external fonts, or new dependency is required.

## Dashboard and product analytics

The dashboard counts Product, Offer, Marketplace, and PriceObservation records directly from SQLite. Offers and observations show their demo/non-demo breakdowns; non-demo entries remain manually entered/recorded and unverified. Products have no independent demo or verification flag, so product counts are labeled catalog records. Marketplace counts are named database entries, not working integrations. Authenticated users see only their own Watchlist count; anonymous users see a login link instead of a private metric. Empty databases show zero counts, no-product guidance, and unavailable observation times.

Open **Analytics** to choose a product, select a product name in Search, or follow **Compare this product** from Watchlist. All link to `/products/<product_id>/`. This stable database ID selects offers and observations by their foreign keys, so similarly named products, variants, and bundles never enter another product's statistics. The optional older `/products/?product=<id>` search route still works.

Each product page shows brand/category, marketplace and seller labels, known delivery/discount amounts, honest buyer totals, and minimum/maximum/average/median listed prices using the same calculation helper as Search. Offer cards and benchmark markup are shared templates. The page also links to each offer's existing history and supports the existing CSRF-protected Watchlist save/remove routes. Product links do not establish verified identity or a marketplace match.

The product chart is a server-rendered SVG **scatter plot**, requiring no JavaScript or new dependencies. Each circle is exactly one stored observation, ordered by timestamp then record ID. Colors identify offers; filled circles mean demo observations and open circles mean manually recorded, unverified observations. Single timestamps and flat prices are supported. There are no price lines, interpolated values, inferred points, or claims of continuous monitoring. Axis limits use recorded dates and prices; point coordinates are only a visual scaling of those values. Overlapping points are possible and are explicitly disclosed.

An accompanying table lists every stored timestamp, marketplace/seller, source label, and listed price oldest first. It is the complete textual alternative to the chart. SVG title/description and focusable horizontal scroll containers keep chart/table content accessible on small screens. With no stored observations, the chart is omitted and the page shows an empty state. Viewing analytics never captures prices, refreshes a marketplace, or changes saved records.

## Login and Watchlist

Create your local development account interactively (no default username or password is supplied):

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Open `/accounts/login/` or select **Log in**, then use that username and password. The superuser account is convenient for local development; ordinary Django users also work, and an administrator can create them in `/admin/`. Email verification, self-registration, password reset, and third-party authentication are not implemented. No account or credential is created automatically.

Product Search remains public. Once signed in, choose **Save product** on an offer, then open Watchlist. Entries are stored in SQLite for the authenticated user, persist across logout/restart, and have a database uniqueness constraint on user/product. Repeat saving shows an informational message rather than creating a duplicate. **Remove product** only removes the current user's saved entry. Requests never accept an owner ID. The list is private and is not registered in the general Django admin interface.

Save, remove, and logout use POST forms with CSRF tokens. Anonymous visits to Watchlist or attempts to modify it redirect to login. Comparison links use the exact product ID (`/products/<id>/`) so similarly named variants and bundles are not accidentally included. Saving does not confirm a product match, fetch prices, or record history.

If a session expires while a save/remove form is open, login returns to the product page for saving or to Watchlist for removing. A message asks you to retry the action; login never replays a modification through a GET request. GET requests to save/remove/logout endpoints are rejected.

## Recorded price observations

Applying migrations does not create history. The plain `load_demo_data` command, normal page views, saving products, and offer edits do not create observations. The optional illustrative-history loader flag described below is a separate, explicit simulation. To capture the current listed price of every eligible demo offer at actual command execution time:

```powershell
.\.venv\Scripts\python.exe manage.py record_demo_observations
```

The command processes demo offers only (`is_demo=True`), validates the recorded listed price, labels every new observation as demonstration data, and reports recorded, unchanged, and invalid counts. Missing buyer delivery or discount does not disqualify an observation because it records only the listed price. There are no date arguments, historical backfills, live requests, or scheduled runs.

**Duplicate rule:** compare each offer's current listed price with its latest demonstration observation. Capture the first price; skip an unchanged price even if the command is run on another day; record a new snapshot only after a listed-price change. A sequence A → B → A records all three states. Delivery/discount changes do not add listed-price history. This is a sequential local command; it is not a concurrent ingestion service. Distinct changes may share the same actual timestamp because of clock resolution. They are ordered by record ID for ties; no synthetic time offsets are introduced. Migration `0003` removes the former offer/timestamp uniqueness restriction, which could cause rapid legitimate captures to fail, while preserving all stored observations.

For a fresh expanded catalog with no observations, the first invocation creates 30 observations and subsequent unchanged invocations create none. If the optional three-point illustrative sequence was already loaded, this command skips its unchanged final price and captures the other 29 offers, leaving 32 observations in total. Existing databases can have different counts. Capturing every offer removes the empty-history examples, so demonstrate those first. Rerunning `load_demo_data` now preserves all existing offer values and observations; it no longer resets seed prices. Demo snapshots reflect application state, never real marketplace price history.

Select **View recorded listed-price history** on an offer. The public history table shows only stored prices, recording timestamps (in `Asia/Qyzylorda`, with UTC offsets), and demo/unverified labels. Empty offers show an honest empty state. Model validation rejects nonpositive/invalid prices, future or timezone-naive timestamps, and labeling a demo offer's observation as non-demo. Custom writers must call `full_clean()` before saving, as with other Django models. Recorded prices are independent of later offer-price edits. Offers with observations are protected against deletion.

This remains an observation foundation: no verification of sources/matches, automatic capture, or immutable audit system is provided. The current offer relation supplies the displayed product/seller metadata, so later metadata edits affect those labels. Manually recorded non-demo observations remain unverified. No historical buyer totals are calculated.

## Demonstration catalog

```powershell
.\.venv\Scripts\python.exe manage.py load_demo_data
```

The seed catalog contains **14 fictional products and 30 demonstration offers across the existing 2 marketplace labels**. The original four products and nine offers retain their identities; ten products and 21 offers extend the catalog. Existing unrelated records remain additional to these counts.

| Category | Fictional products | Demo offers |
| --- | ---: | ---: |
| Desk lighting: Luma, Focus, Orbit | 7 | 14 |
| Keyboards: Keyra layouts and sizes | 3 | 6 |
| USB hubs: Portiq models and bundle | 3 | 7 |
| Workspace accessories: Matra desk mat | 1 | 3 |

Kaspi.kz is a real marketplace name used only as a demonstration label. Practice Market, all seeded product brands/models, and sellers are fictional. New product names include `(demo)`, descriptions identify fictional examples, seller names include `Demo`, and offers/observations use `is_demo=True` with visible demo labels. Existing records and descriptions are preserved. All prices are invented KZT examples, not scraped, verified, or current marketplace prices. Example product links use reserved `.example` domains and may not resolve.

The catalog includes comparable sellers with different listed prices, known free and paid delivery, zero and positive discounts, missing delivery, missing discount, and both inputs missing. Three products have just one offer; others have two to four. Variants, layouts, hub models, and bundles have separate product IDs and are not presumed equivalent. Product associations are curated; no automatic matching, confidence scoring, or verified compatibility is implemented.

**Preservation and repeatability:** loading runs in a transaction and adds missing rows only. It reuses marketplace names, product name/brand pairs, and offer identities (product, marketplace, seller, demo status). Unlike the earlier reset behavior, it never overwrites existing prices, charges, URLs, product descriptions/categories, or marketplace metadata, even for demo records. Manual offers (`is_demo=False`), user accounts, Watchlists, and existing observations are preserved. Renaming an identity field makes a record distinct; a later load can add the original named seed again. This is a sequential local seed command, not a concurrent import service or marketplace refresh. It never deletes records or contacts websites.

### Optional illustrative price sequence

To prepare the catalog with one explicitly illustrative history example:

```powershell
.\.venv\Scripts\python.exe manage.py load_demo_data --with-illustrative-history
```

For **Keyra K1 — compact, EN layout (demo)**, the **Steppe Keys Demo — illustrative history** offer is deliberately changed to **23,500 → 21,900 → 22,500 KZT**, with each actual demo state immediately saved as a `PriceObservation`. The final current price is the seed price, 22,500 KZT. This is an illustrative sample scenario executed within one command run, **not prices observed over past days, an elapsed market trend, or continuous monitoring**. Timestamps come from the real clock at each capture; there are no past dates, artificial time offsets, sleeps, or historical backfills. Ties may display within the same second and use record ID order. The existing chart plots only these stored records and adds no inferred points.

The flag can be used on first load or after a plain load. It records the sequence only if that offer has **no observations at all** and its amounts/URL and product description still match the seed. Otherwise it reports why it skipped the scenario and preserves those records. Rerunning with the flag creates no additional observations. Later offer edits do not cause reseeding, and plain loading never records history. All other products stay without history on a fresh database, providing honest empty-state examples; pre-existing history is retained on an existing database.

Suggested demonstration: search **Luma** for variants/bundles and incomplete totals; open **Keyra K1 — compact, EN layout (demo)** for three competing offers and the illustrative chart/table; open **Focus F2 — white** for a single offer with an unknown discount; open **Matra M1** for multiple offers with no history. For Keyra's three current listed prices, the seed benchmarks are minimum 21,900, maximum 23,000, average 22,466.67, and median 22,500 KZT. Historical sample prices and buyer charges are excluded from those benchmarks. Existing edits may change the results.

## Search and comparison rules

- Search is case-insensitive by product name or brand; surrounding query whitespace is ignored.
- Use `q`, `marketplace` (database ID), and `sort` as GET parameters. The selected filters remain visible and can be bookmarked. Example: `/products/?q=Luma&sort=total`.
- `product` is an optional exact product ID used by Watchlist/history comparison links; it combines with the other filters. Clear it using Reset filters or Show all products.
- Sort values: `name`, `name_desc`, `price`, `price_desc`, `total`, and `total_desc`. Unknown totals always appear last, including descending order.
- All amounts are KZT decimals with two places. Listed price must be positive; delivery and discount may be zero or unknown. Discount is a KZT amount, not a percentage, and cannot exceed listed price.
- **Buyer total = listed price − discount + buyer delivery.** A total is unavailable when either delivery or discount is unknown. An explicit zero is known information. The listed price is defined as the amount before this separate discount; already-discounted prices must not have that same discount subtracted again.
- Minimum, maximum, average, and median use valid positive listed prices from the currently filtered offers only. Discounts and delivery are excluded. Average and median round to two places using `ROUND_HALF_UP`. No results means unavailable statistics, not zero prices. There are no total-cost statistics.
- Broad results can contain different products, variants, and bundles. Their aggregate is descriptive, not an equivalent-product market benchmark. Narrow the query and review product details before comparison.
- Every generated offer is labeled demonstration data. Manually entered non-demo records are labeled unverified, never live.

The small catalog is rendered without pagination; sorting uses Decimal values in memory to keep monetary calculations consistent on SQLite. This approach is intended for a small MVP dataset. Revisit pagination and database-side processing if the catalog grows. Admin and the loader validate records; custom data-writing code should call `full_clean()` before saving. Database constraints also enforce positive prices, nonnegative charges, discount bounds, and one current offer per seller/product/marketplace/demo status.

Seller product costs, margin inputs, repricing, alerts, and advanced historical analytics remain outside this feature.

## Checks and tests

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --verbosity 2
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m pip check
```

The tests cover model validation and database constraints, decimal totals, missing amounts and known zeros, repeatable demo loading, private Watchlists/CSRF, dashboard metrics and empty states, product analytics by exact ID, listed-price summaries, source labels, chronological chart/table data, same-timestamp price transitions, responsive/accessibility markup, and read-only analytics behavior. Readiness regression tests also exercise the combined search/login/Watchlist/history workflow, expired-session returns, external redirect rejection, foreign-origin CSRF rejection, allowed hosts, private cache headers, and non-public configuration/database paths. Database tests use Django's isolated test database; pure calculations use `SimpleTestCase`. They do not add accounts or change the development catalog.

For a demonstration, load the optional catalog (with `--with-illustrative-history` for the sample sequence), create a local user, search/filter offers, save a product, and open product analytics. Explicitly capturing every demo offer is optional and will populate the empty-history examples. An unchanged capture adds no records. To rehearse an empty database, use a separate disposable SQLite database/settings module; do not delete the existing database or records. The seed tests cover the 14-product/30-offer scope, missing amounts, price benchmarks, preserved edits/accounts/Watchlists/history, opt-in sequence repeatability, actual recorded states/times, and visible illustrative-history disclosures.

## MVP development direction

1. Add explicit structured variants/bundles and match confidence if needed beyond the current descriptive product names.
2. Add verified source metadata and ingestion rules if real externally supplied observations become available; distinguish observation times from marketplace update times.
3. Add seller product cost and desired minimum profit margin, with the margin definition explicit and buyer delivery separate.
4. Investigate real data access independently before adding a marketplace integration.

No marketplace scraping or external API integration exists. Demonstration prices must never be presented as verified live observations. Automatic repricing is outside scope. Advanced history analytics, alerts, subscriptions, and additional marketplaces are deferred.

## Git

The local branch is `main`; the configured remote is <https://github.com/Light035/AnalyMark>. The scaffold has an initial local commit. Review feature changes before committing; no automatic commit or push is part of this feature. Inspect remote content before any future push and preserve any existing remote work.

The assignment documents in `Reports/` are kept locally and excluded from future commits. Earlier commits may still contain them; removing them from the current branch does not rewrite Git history. They describe research and proposals, not evidence of implemented integrations.
