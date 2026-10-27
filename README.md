# AnalyMark

AnalyMark is a university Technology Entrepreneurship project intended to become an **automated B2B competitor price-monitoring platform** for small and medium-sized sellers in Kazakhstan. Kaspi.kz is the initial target; other marketplaces may be added in stages. CSV import is a fallback/testing tool, not the main intended workflow.

## Five-marketplace MVP scope

Exactly **Kaspi.kz, Halyk Market, Ozon, Wildberries and Teez** are supported. Kaspi remains the initial target. All supplied demonstration prices/sellers are fictional; no verified LIVE competitor source is connected. The [scope and access review](docs/MARKETPLACE_ACCESS.md) separates seller API access from competitor-feed permission.

### Dashboard interface

The shared Django-template workspace uses a navy sidebar, a light canvas, consistent cards/forms, local system fonts and inline SVG symbols. Marketplace logos are unmodified local assets from official sites or publisher app listings; see [brand sources and usage limitations](docs/BRAND_ASSETS.md). Their presence does not imply affiliation or a live integration. There are no external image/font requests, frontend dependencies or build steps. Desktop marketplace shortcuts and the header product/brand search use the existing search route; mobile navigation remains compact and usable without JavaScript.

Data Sources shows five coverage cards using actual counts: distinct products with offers on that marketplace and total stored offers, including unreviewed/rejected associations (coverage is not a price benchmark). Cards distinguish DEMO, supplied, mixed and empty datasets; marketplace labels never imply a connected feed. Detailed source timestamps, staff-only errors, configuration links and the CLI-only CSV instructions remain below the cards. Initializing labels alone does not claim demo offers exist.

Watchlist cards preview at most three active stored offers per product, ordered by marketplace/seller, with listed prices, provenance and match-review labels. These are individual records, not a best-price recommendation or a cross-marketplace benchmark. Buyer charges/totals remain in the existing comparison views. The preview is bounded in the database; saved-entry ownership and POST/CSRF behavior are unchanged. EN/RU switching retains the current path and query filters.

Previous redesign verification: 254 baseline tests and 262 final tests passed. Django checks, migration consistency, dependency and translation checks passed. Browser rehearsal used a disposable database copy at 1280px and 390px widths, covering sources, search/filter/sort, language switching, product analytics/chart/history, login errors and redirects, Watchlist add/remove, dashboard and analytics. Wide history tables/charts retain internal horizontal scrolling on mobile. No schema/data migration or live integration was added by this redesign.

Final logo/polish pass (27–28 October 2026): 262 baseline tests and 265 final tests passed. The five authentic local assets replace generated marketplace symbols throughout navigation, cards, comparisons, Watchlist previews and history identity labels. Source/license uncertainty is documented in `docs/BRAND_ASSETS.md`; no affiliation or live-data claim is added. Browser checks at 1440px and 390px verified EN/RU Data Sources, local logo loading, search/offer rows, product analytics/history and responsive overflow; login/Watchlist add/remove/logout were exercised on a disposable database copy. This pass adds no dependencies, schema changes or catalog writes.

Follow-up consistency polish (28 October 2026): 265 baseline tests and 268 final
tests passed. Logo containers now have consistent bounds, preserve original
artwork, and prevent square icons from overflowing their rows. Coverage cards
use tighter spacing with aligned counts/actions. Russian demo counts use plural
forms; CSV copy instructions and the dashboard's imported-observation label are
corrected. Django, migration, dependency, compiled-translation, static discovery,
collectstatic dry-run and diff whitespace checks passed. Browser checks included
1440/1280/390 px layouts, EN/RU switching with a retained marketplace filter,
stored history and login/Watchlist operations on a disposable database copy.
Running initialization and both demo loaders twice on a separate copy changed
no table contents: 28 products / 51 offers / 12 observations physically retained;
21 products / 30 offers / 9 observations across the five active marketplaces.
These are audit snapshot counts, not hardcoded dashboard values. Original database,
four reports and five logo files remained byte-identical. No migration or data
rewrite was needed. Wide history charts/tables scroll internally on phones;
stored product names and operator-provided text are not automatically translated.

```powershell
cd C:\AnalyMark
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py init_marketplaces
.\.venv\Scripts\python.exe manage.py load_demo_data
.\.venv\Scripts\python.exe manage.py load_marketplace_demo
.\.venv\Scripts\python.exe manage.py runserver
```

`init_marketplaces` maintains the five canonical labels. Migration `0009` and the command archive all other marketplace labels without deleting products, offers, observations, source IDs or Watchlist entries. Ozon Kazakhstan is renamed **Ozon** in place if no Ozon row already exists; if both exist, the alias is archived without merging records. Existing website URLs are preserved. Archived source schedules are disabled and queued/running jobs cancelled; completed operation history is retained. Run scope changes with the worker stopped. A stale fetched batch is also checked again before it can write catalog records.

`load_demo_data` seeds **13 Kaspi products / 18 offers**. `load_marketplace_demo` adds **8 products / 12 offers** across Halyk Market, Ozon, Wildberries and Teez, using four stable demo source namespaces and reserved `.example` links. A fresh combined load has **21 products, 30 offers, five marketplaces** and zero observations unless capture is explicitly requested. Both loaders are repeatable and never recreate excluded fixtures. No additional catalog/history is invented just to retain the old scale.

On the existing database, all **28 products, 51 offers and 12 observations remain stored**. The active catalog has **21 products, 30 offers and nine observations**. Seven archive-only products, 21 excluded offers and three archived observations remain recoverable through administration/old history links. Eleven shared products remain active through their approved-marketplace offers; no relationships are reassigned. ForteMarket, Satu.kz, Flip.kz and Practice Market are archived, not supported options.

Dashboard counts, catalog/search, filters, product benchmarks/charts and source lists use active scope. Product/offer IDs and source namespaces remain stable. Archive-only saved products remain in the owner's private Watchlist with an archive warning and removal control. Old offer-history URLs remain read-only and explicitly labelled archived; this does not reactivate those offers. Archived or unsupported markets are rejected by CSV import and the refresh queue. `record_demo_observations` captures active demo offers only and never backfills timestamps.

Search and product analytics accept `marketplace=<id>` and `data_kind=demo|non_demo` (blank: all types), retained through pagination. Benchmarks/charts are separated by marketplace and provenance; no combined average mixes fictional and supplied prices. `non_demo` does not mean verified LIVE. Existing matching-review, authentication, CSRF and price-history rules are unchanged.

The current version provides a dashboard with real database counts, product search/comparison, per-product analytics, private persistent Watchlists using Django accounts, and charts/tables based only on recorded observations. It has a staff source-configuration UI and database-backed background refresh queue. **Kaspi competitor acquisition remains blocked: no verified permitted source is connected and no real Kaspi prices have been fetched.** Queue/scheduler functionality is not a completed live integration. Validated operator-supplied CSV remains available as a fallback; existing sample records remain demonstration data.

See [automated refresh and access investigation](docs/AUTOMATED_REFRESH.md) for verified official evidence, the exact external blocker, permissions, operational limits, and the provider contract. The team confirmed that it currently has no approved competitor source. Automated monitoring is technically plausible; absent a public API does not itself prove impossibility. This project has not established a permitted acquisition route.

The [expanded acquisition review](docs/AUTOMATED_REFRESH.md#practical-acquisition-review--2026-10-27) verified competing offers on a public Kaspi product page, but also found an explicit automated-collection restriction in section 13.1 of the agreement currently linked from the shop. The older `/shop/legal/user_agreement.pdf` omits that section and must not be used as permission. No scraper was added and no browser-observed prices were imported. The practical next step is an approved read-only feed with documented reuse rights; the review compares providers and includes an access-request checklist. Real end-to-end competitor acquisition remains **unavailable**, not completed by the scheduler.

To run the implemented queue after `manage.py migrate`, keep the app in one terminal and start the worker in another:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
# In a separate terminal, from C:\AnalyMark:
.\.venv\Scripts\python.exe manage.py refresh_sources
# Or execute one pass (also suitable for a separately configured OS scheduler):
.\.venv\Scripts\python.exe manage.py refresh_sources --once
```

Sign in with an authorized staff account, open **Data Sources → Configure automated source**, and create an access-pending Kaspi source using the existing exact Kaspi.kz marketplace. Staff need `core.add_datasource` to create and `core.change_datasource` to configure/queue; a local superuser has these. Enable a 5–10080 minute schedule or queue an explicit attempt. Reload the management page for actual results: with the present adapter, the outcome is **blocked**, not successfully fetched. No credentials or arbitrary endpoint URLs are accepted. The pending source defaults to periodic refresh disabled; no automated sources or jobs are seeded automatically; optional demo loading creates local fixture sources only.

Migration `0007` adds RefreshRun, source schedule fields/constraints and an optional observation→refresh-run link. Existing sources stay disabled and their timestamps/catalog/history remain unchanged. Successful future provider writes and the run's success/counts share one transaction; late recovered jobs cannot commit. Optional recovery: stop/inspect an interrupted worker, then run `refresh_sources --once --recover-stuck-minutes 15`. This is a single sequential SQLite worker with no heartbeat/supervisor, not a production task service. No new dependencies or OS scheduled tasks are installed.

The latest supplied Assignment 4 defines the intended positioning: compare identical products/variants within a selected marketplace, show listed and known final buyer prices, expose source/update information where available, and keep pricing decisions with the seller. These are product goals. The current prototype uses curated demo associations rather than verified matching and does not generate price recommendations. See the [Assignment 4 and Assignment 5 alignment matrix](docs/POSITIONING_ALIGNMENT.md) for implemented capabilities and gaps; older reports remain historical proposals.

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
├── docs/MVP_EVALUATION.md        Assignment 5 audit, journey, alpha/beta and HADI plans
├── docs/POSITIONING_ALIGNMENT.md Assignment 4/5 evidence, gaps, and feature priorities
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
| `/data-sources/` | Public, read-only source status and command-line CSV preview/apply guide; error details are staff-only |
| `/admin/` | Standard Django admin; optional local superuser required |

The shell uses Django templates, HTML, and local CSS with responsive navigation and visible keyboard focus. JavaScript is not needed at this stage. `migrate` creates the catalog tables as well as Django's standard authentication/session tables. Marketplace, Product, and Offer are registered in Django admin. Optionally create a local admin account with `.\.venv\Scripts\python.exe manage.py createsuperuser`. No account is created automatically.

The presentation layout uses a restrained navy/blue palette, local system typography, and shared spacing, form, table, badge and feedback styles. The sidebar links directly to Dashboard, Product Search, Analytics, Watchlist and Data Sources. The dashboard starts with a direct **Search offers** action, real database metrics, a disjoint offer breakdown (demo / non-demo CSV imports / other manual entries), and source status before the catalog. Demonstration CSV offers count as demo rather than being counted twice. Failed latest imports and sources without any successful import are counted separately from their actual stored status/timestamps.

Search keeps the existing GET parameters and displays validated active filters. Search and product analytics share a semantic desktop comparison table; below 900 px the same rows become labeled cards with no duplicate content or duplicate forms. **Buyer total** has a distinct column and consistently means listed price minus discount plus buyer delivery; unknown inputs show an explicit warning rather than zero. Product descriptions and reference links remain available in native keyboard-accessible “Details & reference” disclosures. Product analytics retains benchmarks, section navigation, the existing stored-observation SVG and its complete history table. Watchlist cards show the real saved date and current offer count. Login offers a return to public Product Search without signing in.

On small screens, navigation stays visible, forms stack, and wide history/source tables and charts scroll inside keyboard-focusable labeled regions. Source workflow commands also scroll within their own focusable blocks. Error summaries link to invalid visible search fields; hidden product-filter errors offer Reset filters instead. Long names wrap, price figures use aligned numerals, and demo/unknown/unverified labels remain readable. Data Sources provides a discoverable local CSV guide; there is no upload form or new write endpoint. Import times remain separate from unknown marketplace update times. These changes do not change monetary calculations, capture observations, or alter authentication/CSRF rules. No frontend framework, external fonts, JavaScript, or new dependency is required.

## Dashboard and product analytics

The dashboard counts Product, Offer, Marketplace, and PriceObservation records directly from SQLite. Offers and observations show their demo/non-demo breakdowns; non-demo entries remain manually entered/imported/recorded and unverified. Products have no independent demo or verification flag, so product counts are labeled catalog records. Marketplace counts are named database entries, not working integrations. Authenticated users see only their own Watchlist count; anonymous users see a login link instead of a private metric. Empty databases show zero counts, no-product guidance, and unavailable observation times.

Open **Analytics** to choose a product, select a product name in Search, or follow **Compare this product** from Watchlist. Catalog counts and pagination show the full result total. All link to `/products/<product_id>/`. This stable database ID selects offers and observations by their foreign keys, so similarly named products, variants, and bundles never enter another product's statistics. The optional older `/products/?product=<id>` search route still works.

Each product page shows brand/category, marketplace and seller labels, known delivery/discount amounts, honest buyer totals, and minimum/maximum/average/median listed prices using the same calculation helper as Search. Benchmarks are separated by marketplace and demo/non-demo provenance, within the approved five-marketplace scope. The page's marketplace/provenance filters apply to offers and their recorded history. Offer cards and benchmark markup are shared templates. The page also links to each offer's existing history and supports the existing CSRF-protected Watchlist save/remove routes. Product links do not establish verified identity or a marketplace match.

CSV-managed and new multi-marketplace fixture offers have a source namespace, distinct source product/offer IDs, reference URL, and actual last-import/local-load timestamp through `SourceProduct`/`SourceOffer`. Legacy demo/manual offers have no recorded import or marketplace update time; none is backfilled. Local loading, CSV import and observation capture times do not certify marketplace freshness, verified matching, or live prices. A reliable marketplace update timestamp remains unavailable.

The product chart is a server-rendered SVG **scatter plot**, requiring no JavaScript or new dependencies. Each circle is exactly one stored observation, ordered by timestamp then record ID. Colors identify offers; filled circles mean demo observations and open circles mean manually recorded or CSV-imported, unverified observations. Single timestamps and flat prices are supported. There are no price lines, interpolated values, inferred points, or claims of continuous monitoring. Axis limits use recorded dates and prices; point coordinates are only a visual scaling of those values. Overlapping points are possible and are explicitly disclosed.

An accompanying table lists every observation on the current history page (up to 50), with timestamp, marketplace/seller, source label and listed price oldest first. Separate marketplace/provenance charts collectively plot exactly those same page records, with unique accessible titles. Independent offers_page and history_page parameters preserve the other section’s position. Rejected associations are excluded from product-level history and benchmarks; individual offer histories retain their original observations. The table is the complete textual alternative to the charts. SVG title/description and focusable horizontal scroll containers keep chart/table content accessible on small screens. With no stored observations, charts are omitted and the page shows an empty state. Viewing analytics never captures prices, refreshes a marketplace, or changes saved records.

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

This remains an observation foundation: no verification of sources/matches, scheduled capture, or immutable audit system is provided. Explicit CSV updates now capture changed existing listed prices as described below. The current offer relation supplies the displayed product/seller metadata, so later metadata edits affect those labels. Manually recorded and imported non-demo observations remain unverified. No historical buyer totals are calculated.

## Demonstration catalog

```powershell
.\.venv\Scripts\python.exe manage.py load_demo_data
```

This command seeds **13 fictional products and 18 demonstration offers on Kaspi.kz** and initializes the five approved marketplace labels. The four other platforms are populated by `load_marketplace_demo` (8 additional products / 12 offers). Existing unrelated and archived records remain stored but are not seeded or counted as active supported offers.

| Category | Fictional products | Demo offers |
| --- | ---: | ---: |
| Desk lighting: Luma, Focus, Orbit | 7 | 9 |
| Keyboards: Keyra compact layouts | 2 | 3 |
| USB hubs: Portiq models and bundle | 3 | 4 |
| Workspace accessories: Matra desk mat | 1 | 2 |

The five approved marketplace names are real, but all seeded product brands/models, seller identities and prices are fictional. No marketplace supplied these fixtures. New product names include `(demo)`, descriptions identify fictional examples, seller names include `Demo`, and offers/observations use `is_demo=True` with visible demo labels. Existing records and descriptions are preserved. All prices are invented KZT examples, not scraped, verified, or current marketplace prices. Example product links use reserved `.example` domains and may not resolve.

The catalog includes comparable sellers with different listed prices, known free and paid delivery, zero and positive discounts, missing delivery, missing discount, and both inputs missing. Nine Kaspi products have one offer; the others have two or three. Variants, layouts, hub models, and bundles have separate product IDs and are not presumed equivalent. Product associations are curated; no automatic matching, numerical confidence scoring, or verified compatibility is implemented. Offer associations now have explicit manual review states; seed loading never marks them confirmed.

**Preservation and repeatability:** loading runs in a transaction and adds missing rows only. It reuses marketplace names, product name/brand pairs, and offer identities (product, marketplace, seller, demo status). Unlike the earlier reset behavior, it never overwrites existing prices, charges, URLs, product descriptions/categories, or marketplace website URLs, even for demo records. Marketplace activation and the explicit Ozon alias normalization are the only scope updates. Manual offers (`is_demo=False`), user accounts, Watchlists, and existing observations are preserved. Renaming an identity field makes a record distinct; a later load can add the original named seed again. This is a sequential local seed command, not a concurrent import service or marketplace refresh. It never deletes records or contacts websites.

### Optional illustrative price sequence

To prepare the catalog with one explicitly illustrative history example:

```powershell
.\.venv\Scripts\python.exe manage.py load_demo_data --with-illustrative-history
```

For **Keyra K1 — compact, EN layout (demo)**, the **Steppe Keys Demo — illustrative history** offer is deliberately changed to **23,500 → 21,900 → 22,500 KZT**, with each actual demo state immediately saved as a `PriceObservation`. The final current price is the seed price, 22,500 KZT. This is an illustrative sample scenario executed within one command run, **not prices observed over past days, an elapsed market trend, or continuous monitoring**. Timestamps come from the real clock at each capture; there are no past dates, artificial time offsets, sleeps, or historical backfills. Ties may display within the same second and use record ID order. The existing chart plots only these stored records and adds no inferred points.

The flag can be used on first load or after a plain load. It records the sequence only if that offer has **no observations at all** and its amounts/URL and product description still match the seed. Otherwise it reports why it skipped the scenario and preserves those records. Rerunning with the flag creates no additional observations. Later offer edits do not cause reseeding, and plain loading never records history. All other products stay without history on a fresh database, providing honest empty-state examples; pre-existing history is retained on an existing database.

Suggested demonstration: search **Luma** for variants/bundles and incomplete totals; open **Keyra K1 — compact, EN layout (demo)** for two competing offers and the illustrative chart/table; open **Focus F2 — white** for a single offer with an unknown discount; open **Matra M1** for multiple offers with no history. For Keyra's two current Kaspi listed prices, the seed benchmarks are minimum 21,900, maximum 22,500, average 22,200, and median 22,200 KZT. Historical sample prices and buyer charges are excluded from those benchmarks. Existing edits may change the results.

## Search and comparison rules

- Search is case-insensitive by product name or brand; surrounding query whitespace is ignored.
- Use `q`, `marketplace` (database ID), and `sort` as GET parameters. The selected filters remain visible and can be bookmarked. Example: `/products/?q=Luma&sort=total`.
- `product` is an optional exact product ID used by analytics/Watchlist comparison links; it combines with the other filters. Selecting a product does not imply it is saved. Clear it using Reset filters or Show all products.
- Sort values: `name`, `name_desc`, `price`, `price_desc`, `total`, and `total_desc`. Unknown totals always appear last, including descending order.
- All amounts are KZT decimals with two places. Listed price must be positive; delivery and discount may be zero or unknown. Discount is a KZT amount, not a percentage, and cannot exceed listed price.
- **Buyer total = listed price − discount + buyer delivery.** A total is unavailable when either delivery or discount is unknown. An explicit zero is known information. The listed price is defined as the amount before this separate discount; already-discounted prices must not have that same discount subtracted again.
- Minimum, maximum, average, and median use valid positive listed prices from the currently filtered offers only. Discounts and delivery are excluded. Average and median round to two places using `ROUND_HALF_UP`. No results means unavailable statistics, not zero prices. There are no total-cost statistics.
- Broad results can contain different products, variants, and bundles. Their aggregate is descriptive, not an equivalent-product market benchmark. Narrow the query and review product details before comparison.
- Every generated demo offer is labeled demonstration data. Manually entered and CSV-imported non-demo records are labeled unverified, never live.

Search, per-product offers, the analytics catalog, Watchlist and Data Sources use server-side pagination (20 records per page). Histories use 50 observations per page. Filtering and sorting execute in SQLite before LIMIT/OFFSET; no full catalog is materialized in Python for pagination. Listed-price aggregates use integer cents in SQL, with Decimal half-up rounding; the median query reads at most two prices. Provisional benchmarks cover the complete filtered, non-rejected set across pages, not just visible rows. Unknown buyer totals sort last in both directions. Unicode casefolding registered on each SQLite connection supports Russian case-insensitive search and stable name sorting. Admin and the loader validate records; custom data-writing code should call `full_clean()` before saving. Database constraints also enforce positive prices, nonnegative charges, discount bounds, and one current offer per seller/product/marketplace/demo status.

Seller product costs, margin inputs, repricing, alerts, and advanced historical analytics remain outside this feature.

## Data access: verified scope and limitations

Reviewed official Kaspi documentation on **27 October 2026**:

| Path | What the documentation establishes | AnalyMark status |
| --- | --- | --- |
| Seller-account API | [API overview](https://guide.kaspi.kz/partner/ru/shop/api/general/q3192) describes adding products, managing orders, and accounting integration. [Token instructions](https://guide.kaspi.kz/partner/ru/shop/api/general/q3196) restrict token generation to the company head and describe access to that seller account's orders/products. [Order listing](https://guide.kaspi.kz/partner/ru/shop/api/orders/q3201) requires authentication and returns the seller's orders. | Not connected. No seller token supplied or operational request performed. Own order/product data is not a competitor-price feed. Order/customer data is outside this importer. |
| Product API | The [official goods documentation](https://guide.kaspi.kz/partner/ru/shop/api/goods) documents categories, attributes, product submission and submission status. | Not a verified public search/competitor-offers API. Product information alone does not identify an individual seller offer. No full-catalog export endpoint is assumed. |
| Public competitor offers | No documented, permitted public competitor search/offer API was found in the reviewed official material. This is a research limitation, not proof that no other agreement is possible. | Blocked pending documented access rights, scope and an authorized sample. Undocumented website endpoints and third-party claims are not used. |
| Operator CSV and reference URLs | The operator supplies lawfully obtained, non-confidential product/offer records and is responsible for their provenance and permission to use them. | Implemented. URLs are stored as references only, never fetched or scraped. This fallback does not grant rights to gather marketplace data. |

No real Kaspi prices were retrieved or verified during development. There is no automatic product matching, working network API adapter, scraper, anti-bot bypass, or automatic repricing. A background queue/scheduler now exists, but the Kaspi adapter is an explicit access gate that makes no request. An authorized seller API may help a future own-catalogue workflow; it must not be represented as access to competitors. Obtain documented permission/scope before adding a network provider. A future adapter must read credentials from environment variables, bound timeouts, and sanitize errors; no token or unused credential setting is required or stored by this implementation.

## Manual CSV offer import

`core/providers.py` defines immutable `OfferRecord` values and the `OfferProvider.fetch()` contract, independently of Django catalog writes. The local CSV provider performs bounded file acquisition; `core/importing.py` validates normalized records and applies a single catalog transaction. Typed timeout/unavailable/malformed-data failures are handled without displaying raw provider exceptions. No network provider or HTTP response parser is implemented, so network behavior has only simulated contract tests.

Create a local input from the **header-only** template, then fill it with records you are permitted to use. The template deliberately contains no invented non-demo records:

```powershell
cd C:\AnalyMark
.\.venv\Scripts\python.exe manage.py migrate
Copy-Item .\examples\offers_template.csv .\offers.local.csv
# Edit offers.local.csv and supply actual product/variant and seller-offer data.
.\.venv\Scripts\python.exe manage.py import_offers_csv .\offers.local.csv --source kaspi-manual --marketplace "Kaspi.kz" --dry-run
.\.venv\Scripts\python.exe manage.py import_offers_csv .\offers.local.csv --source kaspi-manual --marketplace "Kaspi.kz" --apply
```

Preview is also the default when neither flag is supplied. It runs the same validation and database constraints inside a transaction, then **rolls back all writes**, including observations, reviews and source/status changes. It reports products/offers created/updated/unchanged, rejected/skipped offer rows, observations and invalidated review decisions. Review those counts and the file before explicitly applying. A header-only or empty file is rejected. Applied failures return a nonzero exit code, retain a sanitized source error, and save no catalog changes or observations. The first applied failure may create an empty source status record. A later failure preserves the previous last-success time. Preview does not lock the file/database for later approval: apply revalidates the current file and records.

The marketplace must already exist under its exact name (`load_demo_data` creates the Kaspi.kz label; otherwise create a Marketplace in `/admin/`). Source keys are stable lowercase letters/digits/hyphens/underscores, max 80 characters. Reuse the **same key, marketplace, and demo mode** for later updates. Existing namespaces cannot be reassigned. `*.local.csv` is ignored by Git; avoid putting supplier files or credentials elsewhere in the repository.

### File contract

UTF-8 (optional BOM), comma-separated, quoted cells supported, at most 2 MiB and 1000 offer rows. Supply exactly these unique headers, in any order:

```text
product_id,product_name,brand,category,offer_id,seller_name,listed_price,currency,delivery_cost,discount,source_url
```

| Field | Rule |
| --- | --- |
| `product_id` | Required stable source identity for one exact product/variant/bundle; 1–160 ASCII letters/digits/dots/colons/underscores/hyphens, starting with a letter/digit. Never reuse a generic model ID for different variants. |
| `offer_id` | Separately required stable individual seller-offer identity, same format. A product card/URL alone is insufficient. IDs are scoped to the named source. |
| `product_name`, `category`, `seller_name` | Required, max 200 / 120 / 160 characters respectively; no control characters. Seller names must be supplied, never inferred. |
| `brand` | Optional, max 120 characters. |
| `listed_price`, `currency` | Positive KZT Decimal amount before the separately supplied discount; at most 12 digits / 2 decimal places. Currency must be exactly `KZT`; no conversion. Do not subtract an already-applied discount again. |
| `delivery_cost`, `discount` | Optional nonnegative KZT amounts; discount cannot exceed listed price. Blank means unknown; explicit `0` means known zero. Delivery is the buyer's charge, not the seller's cost. |
| `source_url` | Required public http(s) reference URL, max 200 characters, without embedded credentials, query parameters or fragments. Use a clean reference URL; URLs are not requested. A URL does not verify the seller, matching, permissions or price. |

Rows with the same source product ID must agree on name/brand/category within a file. Identical repeated offer rows collapse; conflicting duplicate offer IDs reject the whole file. Human-readable errors identify a logical CSV row and field without echoing cell values. The command reports the first error; correct it and preview again. Region, stock, tax, payment-specific and time-specific price eligibility are not modeled; review that comparability manually and leave uncertain delivery/discount amounts blank.

### Preservation and update rules

- Source/product-ID and source/offer-ID have database uniqueness constraints. Imported products are **never matched by name** to demo, manually created, or another source's products. This avoids accidental variants/bundle merging. It can create separate catalog entries for the same item across different sources; review/merging is future work.
- Only records already owned by that source's mappings are updated. Nonblank product name/category/brand, seller name, listed price and reference URL replace their previous managed values when applied. **Manual edits to these managed fields can be overwritten on the next explicit import**; inspect the preview/file first. Existing unrelated user/demo products, Watchlists, accounts and observations are untouched. Descriptions are not imported.
- Blank brand/delivery/discount values preserve existing known values on updates. New offers get unknown (`NULL`) charges. There is no implicit clear operation. If a retained discount would exceed a new lower price, the entire import fails; explicitly supply a valid known discount rather than assuming zero.
- A source offer ID cannot move to another product/marketplace/demo mode. The existing one-current-offer-per-seller/product/marketplace/demo constraint still applies; conflicting different IDs fail rather than overwrite another offer. Missing rows are not deleted or deactivated; stale offers can remain and are not live availability claims.
- Every successful applied batch records its actual import time, even when prices are unchanged. Repeating a file creates no duplicate catalog/mapping records. Source status reports last attempt, last success and current mapped product/offer counts. Error details are staff-only; catalog data and source summaries are public like Product Search. Do not import private seller costs, tokens, order records or customer information.
- A **listed-price change on an existing imported offer** creates a PriceObservation at actual import time in the same transaction, retaining the source's demo flag and explicit `recorded_by_import=True` provenance. First imports and unchanged prices do not create observations. A → B → A records B and A only: no invented earlier A is backfilled. Delivery/discount-only changes do not create listed-price observations. Prior history is preserved; a failed batch/preview retains no new history. The separate `record_demo_observations` command remains demo-only.
- For invented training inputs use a separate source key and add `--demo` on **every** invocation, including preview/apply. This flags all created offers and the source as demonstration data. Never import fictional inputs in the default non-demo mode.

The dashboard's Data sources section lists available paths and configured CSV sources, status, last successful import and current mapped counts. Offer cards distinguish CSV/demo/manual records and show actual import timestamps where present. Old records are deliberately not backfilled. This is a sequential operator workflow, not a concurrent ingestion service; serialize imports and keep local SQLite backups before applying external files. Uploaded-file UI, seller self-service import, historical import auditing, cross-source reconciliation and marketplace verification are not implemented.

Migration `0004` adds only `DataSource`, `SourceProduct` and `SourceOffer` tables/constraints. It does not change existing catalog rows or create history. No new dependencies or settings are needed.

### Repeat imports, history and import age

The [CSV lifecycle audit](docs/CSV_REFRESH.md) records the inspected baseline and exact refresh rules. Reuse the original source key and IDs, preview the updated file with `--dry-run`, then apply it with `--apply` using the commands above. Do not change IDs merely because a price changes. Product/seller/reference identity changes invalidate affected manual decisions with field-specific reasons; price-only updates retain the complete review. ID reassignment to another product fails atomically instead of moving the association.

Counts are per unique offer for created/updated/unchanged; identical duplicate input rows are **skipped**. Product-only metadata changes appear under products updated and invalidated reviews, even if an offer's own fields are unchanged. Successful batches report rejected=0. Invalid input rejects the whole batch (no partial acceptance); CLI reports all input rows as rejected when their count is known, otherwise `rejected=unknown`. These are import-validation counts, separate from rejected product-match decisions.

Migration `0006` adds an optional positive `DataSource.stale_after_hours` and a positive-or-NULL database constraint, plus `PriceObservation.recorded_by_import` defaulting to false. Existing observations are not relabeled as CSV captures; no records, dates or history are generated by migration. Run `manage.py migrate` before using the updated app.

Authorized staff with DataSource change permission can open `/admin/core/datasource/`, select a source, and set **Import age threshold (hours)**. Blank is the default and means no age assessment. At or beyond the configured interval since last success, the UI reports that the interval was exceeded; within it, prices still remain unverified. Existing source identity/mode and operational timestamps are read-only in admin. No universal stale threshold or background job is introduced.

Dashboard/Data Sources show **last attempt** separately from **last success**, safe latest status and the configured age assessment. Failed attempts preserve the last success. Each offer keeps its own last-seen import time; absence from a later partial CSV does not refresh, delete or mark it unavailable. A recent source import does not prove all offers are recent. The current CSV has no marketplace-provided update-time column, so that time is explicitly not supplied. Import times must never be represented as marketplace refresh times.

History tables and chart titles distinguish demo snapshots, CSV price-change observations, and other manually recorded unverified observations. The import marker is explicit rather than inferred from an offer having source metadata. All timestamps are actual recording times; all non-demo imports remain unverified operator-supplied data, not live Kaspi prices. Import operations remain sequential: serialize writers; concurrent ingestion is not supported or tested.

Import regression tests cover preview/default mode, complete rollback, stable IDs and uniqueness constraints, repeated/changed input, blank-versus-zero handling, preserved unrelated records, retained-discount validation, UTF-8/quoted CSV, file/row limits, malformed records, timeouts/unavailable sources, sanitized failures, actual import timestamps, source status/access, and rendered provenance. Their input records are fictional and use Django's isolated test database; they do not validate real marketplace access or permissions.

## Manual association review and comparison scope

Products are associated through the exact `Offer.product` foreign key. CSV products are scoped by `SourceProduct(source, external_id)` and retain a separate source product/variant ID and seller-offer ID. A product mapping belongs to one source; equal names, brands, prices or URLs do not merge products or establish cross-source identity. This iteration does not introduce cross-marketplace matching or cross-source reconciliation.

Migration `0005` adds an offer review status, explanation, reviewer and actual review timestamp, plus a database status constraint. Existing offers default to **unreviewed**, with no invented reviewer/time. No old relationship, price, source ID, observation or Watchlist is reassigned or deleted.

- **Unreviewed association:** no confirmed identity claim; included only in explicitly provisional benchmarks.
- **Manually confirmed match:** a staff reviewer checked the association to the current catalog product using model, variant and bundle evidence. This does not verify the marketplace, price, delivery, discount or cross-marketplace identity; demo labels remain demo.
- **Rejected association:** visible for transparency, excluded from listed-price benchmarks and product-level history/chart. Its individual offer history and stored observations remain available.

To review: create an authorized local administrator if needed (`manage.py createsuperuser`), open `/admin/core/offer/`, filter **Match review**, open an offer and inspect its product, marketplace, source IDs/reference/import time. Choose a status and provide a meaningful explanation when confirming or rejecting, then save. Admin permissions and CSRF protection apply; public pages cannot submit reviews. The actual reviewer/time are set by the server. Review notes appear publicly with offer details: never enter credentials, customer details or private costs.

Imported offers' product/marketplace/demo identity is read-only in admin; this workflow reviews existing associations rather than merging source products. Manual-offer reassignment requires confirmed review and an explanation. Product name/brand/category changes, or offer identity/reference changes through admin/CSV, invalidate the old review and return it to unreviewed; normal price/delivery/discount updates preserve it. CSV identity changes and review resets share the import transaction, including dry-run rollback. Custom writers must validate models and invalidate reviews when changing identity; direct SQL updates are outside this workflow.

Product pages select the exact product ID only. Search additionally supports `review=unreviewed|confirmed|rejected`; omitted/blank means all associations. An unknown review value is an invalid filter, never a fallback to unfiltered data. Unreviewed matches are always labeled; rejected prices never silently enter benchmarks. Buyer-total rules are unchanged: both buyer delivery and the separate discount must be known, including explicit zero values.

## Pagination

- Search/catalog/Watchlist/Data Sources: `page`, 20 records per page; individual offer history: `page`, 50 observations.
- Product analytics: `offers_page` (20 offers) and `history_page` (50 oldest-first observations), independently navigable.
- Page links preserve current GET filters, exact-product selection, review status, sorting and the other section’s page. Current page and total result count are shown. Sort ties use stable identifiers.
- Invalid, non-ASCII, zero, negative, fractional or excessively long page values use page 1. A valid positive page beyond the end selects the last page. Empty sets have page 1 of 1 with zero results and honest empty states.
- Product charts show only the explicitly identified history page, using actual stored observations without interpolation. No page view creates observations. The dashboard previews six products and at most five configured sources, linking to their complete paginated lists.

This bounds application memory, not every database operation: contains-search, exact aggregate/median computation and deep offset pages still require database work. SQLite remains appropriate for the MVP; this is not a claim of production-scale indexing or concurrent ingestion capacity.

## English and Russian / Английский и русский

Use **EN / RU** in the header to switch language. The POST form uses Django CSRF protection, retains the current path/query and saves a language cookie. Existing URLs remain unchanged; the browser language is used when there is no preference cookie. English remains the default fallback.

**Русский интерфейс:** нажмите **RU** в шапке. Переведены навигация, поиск и фильтры, ценовые показатели, статусы проверки, история, страницы источников, вход, уведомления и пагинация. Названия товаров, категории, описания, имена продавцов, ID источников и пользовательские заметки сохраняются на языке исходных данных. Команды, имена столбцов CSV и сохранённые сообщения оператора не переводятся автоматически. Русский язык не означает наличие интеграции с Kaspi.kz.

Translation source: `locale/ru/LC_MESSAGES/django.po`; compiled runtime catalog: `django.mo`. After changing translations:

```powershell
.\.venv\Scripts\python.exe tools/compile_translations.py
.\.venv\Scripts\python.exe tools/compile_translations.py --check
```

The compiler uses only Python's standard library; GNU gettext or another package is not required. Keep PO and MO together when committing later. Restart the development server after changing translations. Django handles Russian plural forms and local number formatting; timestamps retain their actual stored values and explicit UTC offsets.

## Checks and tests

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --verbosity 2
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe tools/compile_translations.py --check
.\.venv\Scripts\python.exe manage.py collectstatic --dry-run --noinput
git diff --check
```

The tests cover model validation and database constraints, decimal totals, missing amounts and known zeros, repeatable demo loading, private Watchlists/CSRF, dashboard metrics and empty states, product analytics by exact ID, listed-price summaries, source labels, chronological chart/table data, same-timestamp price transitions, responsive/accessibility markup, and read-only analytics behavior. Readiness regression tests also exercise the combined search/login/Watchlist/history workflow, expired-session returns, external redirect rejection, foreign-origin CSRF rejection, allowed hosts, private cache headers, and non-public configuration/database paths. Database tests use Django's isolated test database; pure calculations use `SimpleTestCase`. They do not add accounts or change the development catalog.

For a demonstration, load the optional catalog (with `--with-illustrative-history` for the sample sequence), create a local user, search/filter offers, save a product, and open product analytics. Explicitly capturing every demo offer is optional and will populate the empty-history examples. An unchanged capture adds no records. To rehearse an empty database, use a separate disposable SQLite database/settings module; do not delete the existing database or records. The seed tests cover the 13-product/18-offer Kaspi scope and the combined five-marketplace 21-product/30-offer scope, missing amounts, price benchmarks, preserved edits/accounts/Watchlists/history, opt-in sequence repeatability, actual recorded states/times, and visible illustrative-history disclosures.

## MVP evaluation and Assignment 5

See the [Assignment 4 and Assignment 5 alignment matrix](docs/POSITIONING_ALIGNMENT.md) for current business assumptions, evidence, gaps, and Must/Should/Future priorities. The [MVP evaluation and Assignment 5 audit](docs/MVP_EVALUATION.md) provides the user journey, chosen development method, internal alpha checklist, consented seller beta tasks/questionnaire, metrics, and HADI experiments. It distinguishes reported Customer Development evidence, automated technical checks, and experiments that have not been conducted.

The working demo and passing tests do not establish seller usefulness, real-market savings, live data access, or paid demand. Team alpha sessions, real seller beta sessions, post-MVP HADI results, and the separate 500–1000-word report/presentation still need to be completed. The evaluation guide is not the submission report. Local reports and the original database are preserved.

## MVP development direction

1. Add explicit structured variants/bundles and match confidence if needed beyond the current descriptive product names.
2. Add verified source metadata and ingestion rules if real externally supplied observations become available; distinguish observation times from marketplace update times.
3. Add seller product cost and desired minimum profit margin, with the margin definition explicit and buyer delivery separate.
4. Investigate real data access independently before adding a marketplace integration.

No marketplace scraping or external API integration exists. Demonstration prices must never be presented as verified live observations. Automatic repricing is outside scope. Advanced history analytics, alerts, subscriptions, and additional marketplaces are deferred.

## Git

The working branch is `main`; the intended remote is <https://github.com/Light035/AnalyMark>. Before saving changes, review tracked and untracked files, run the checks above, stage only intended source/assets/documentation, inspect the commit, and verify remote ancestry. Never force-push or include local databases, supplier files, secrets, reports, virtual environments or browser-test artifacts.

The assignment documents in `Reports/` are kept locally and excluded from future commits. Earlier commits may still contain them; removing them from the current branch does not rewrite Git history. They describe research and proposals, not evidence of implemented integrations.
