# Automated competitor monitoring: implementation and access gate

AnalyMark's intended main workflow is automated B2B competitor-price monitoring
for sellers in Kazakhstan, starting with Kaspi.kz. CSV is a fallback/test tool,
not the intended data-acquisition product. This distinction does not make the
current prototype a working Kaspi monitor.

## Repository audit before changes

Baseline: 195 passing tests. `OfferProvider.fetch()` returned validated bounded
records. Only `csv` was allowed by `run_import`; no network acquisition existed.
Stable `(source, external_id)` product/offer mappings controlled updates. Price
changes on existing offers created actual-time observations, atomically with
metadata/review updates. Blank optional values preserved known values, ID moves
were rejected, missing rows were retained, and price-only updates retained reviews.
Source last-attempt/success/error and optional age threshold already existed.
There was no scheduler, queue, refresh control UI or automatic competitor feed.

## Access investigation — 2026-10-27

This was the initial documentation review. The expanded review below adds a
public-page inspection and the currently linked shop agreement, including an
explicit restriction that the initial review had not established.

Official material actually reviewed:

- [API overview](https://guide.kaspi.kz/partner/ru/shop/api/general/q3192):
  adding products, processing orders, accounting integration for sellers.
- [Goods API index](https://guide.kaspi.kz/partner/ru/shop/api/goods):
  categories/attributes, product submission and submission results. A product card
  is not an individual seller offer or a public competitor-price feed.
- [List my orders](https://guide.kaspi.kz/partner/ru/shop/api/orders/q3201):
  seller's own orders, requiring an authentication token. Order prices/customer
  data are not suitable competitor listing data and are not imported here.
- [Price-list loading](https://guide.kaspi.kz/partner/ru/shop/goods/price_list/q2962):
  seller-hosted XML is consumed by Kaspi to update that seller's listings. This is
  the reverse direction and is not an endpoint for reading competitors' prices.

The previously referenced token page `general/q3196` timed out on this review;
its earlier summary was not treated as new verification. Targeted searches of
official documentation did not establish a documented, permitted public
competitor search/offers API. This does not prove that a commercial agreement
cannot exist. Public visibility alone does not establish permission for automated
collection. No undocumented website endpoint, CAPTCHA/access-control bypass,
seller credentials, scraping, or third-party marketing claim is used.

## Exact blocker

The Kaspi adapter is intentionally blocked and makes **no network request**.
Completing it requires a written approved access scope or licensed feed, endpoint
and authentication documentation, request/response samples, stable product/variant
and individual seller-offer identifiers, city/payment/discount/delivery semantics,
pagination/completeness rules, rate limits and permitted retention/use. Credentials
must be provided to the runtime through environment variables after that contract
is verified, never entered into the current forms or committed.

Until then, a scheduled Kaspi attempt can finish **blocked**, never succeeded,
and cannot add offers, observations, freshness or a last-success timestamp.

AlgaTop is a relevant competitor, not an available AnalyMark data source. Its
[bot FAQ](https://algatop.kz/bot) describes opening pages/changing prices like a
human, while its [analytics description](https://algatop.kz/kaspi-analytics)
mentions indirect data/model estimates. The exact competitor-offer acquisition
protocol and authorization are not disclosed in those descriptions. Its
[terms](https://algatop.kz/privacy), notably section 5.1.5, restrict using other
software to access its service. No public reusable AlgaTop feed was verified.
This supports technical feasibility of the product category, not access rights
or an integration for this project. No AlgaTop account was accessed or contacted.

## Practical acquisition review — 2026-10-27

**Outcome: real competitor-price acquisition into AnalyMark is NOT working.**
The investigation confirmed visible public offers, but no source meeting both
the technical and permission requirements is available to this team. No new
adapter, collection loop, database record, migration, or dependency was added.
This is a blocker report, not a completed integration.

Status terminology: **VERIFIED** means the stated observation or documentation
was checked, not that the vendor has been certified. **UNVERIFIED** means the
necessary capability, access, rights or reliability has not been established.
**UNAVAILABLE** means the route cannot currently supply the required permitted
competitor offers to AnalyMark; it does not assert technical impossibility.

### Existing implementation rechecked

Read `core/models.py`, `providers.py`, `importing.py`, `refreshing.py`, the refresh
command, source views/template, settings, tests and README before editing docs.
The baseline suite passed all 217 tests. Existing Git changes were retained.

- `OfferProvider.fetch()` returns bounded normalized `OfferRecord` batches;
  only CSV and the blocked Kaspi provider are registered. The latter raises
  `SourceBlocked` without making a network request.
- Product identity is `(DataSource, external_id)` through `SourceProduct`;
  offer identity uses the same pair through `SourceOffer`. Each mapping owns
  one local object. Similar names do not merge products across sources.
- Supplied prices update existing offers; blank brand/delivery/discount preserve
  existing values. Blank charges on new offers remain unknown. Missing rows
  remain stored. Product/marketplace/provenance moves of an existing offer ID
  fail; metadata identity changes reset reviews with a reason. Price-only
  changes preserve manual review.
- Only a changed existing listed price creates a new actual-import-time
  observation. Initial import and unchanged prices do not create history.
  Catalog, observations and successful refresh ledger commit atomically.
- Staff plus model permissions protect source configuration; refresh is POST
  with CSRF. One active job per source, due scheduling, safe failures and
  explicit stuck-job recovery already exist. They do not acquire data themselves.
- Original database: 14 products, 30 demo offers, 2 marketplaces, 12 observations,
  zero DataSource and RefreshRun records. No research observations were inserted.

### A. Public pages: actual browser inspection

An unauthenticated, ordinary browser search for `iPhone 16 128` in the shop's
displayed **Almaty** context opened this
[product card](https://kaspi.kz/shop/p/apple-iphone-16-128gb-nanosim-esim-chernyi-123713453/?c=750000000).
Evidence capture time: **2026-10-27T15:38:41.057Z** (20:38:41 UTC+05:00).
This is our inspection time, not a marketplace update timestamp. These are
transient, actually displayed values, not demo fixtures or promises of current
availability. The page was inspected once; longitudinal ID stability was not tested.

| Visible example | Listed price | Identity visible in seller link | Delivery displayed |
| --- | ---: | --- | --- |
| QazSeller | 409,999 KZT | merchant `2423002`, merchantSku `123728177_971238381` | Standard delivery free; October 31 |
| KBT Bars | 410,000 KZT | merchant `12261014`, merchantSku `123713453_647172380` | Standard delivery free; express 995 KZT |
| ALPHA | 412,997 KZT | merchant `234005`, merchantSku `123713453` | Standard delivery free; express 995 KZT |

The product code `123713453` appears in both the visible card and URL. Model,
128 GB storage, black colour and NanoSIM+eSIM variant are explicit. Five seller
rows and pagination were visible; this inspection did not enumerate all pages.
Seller links expose merchant and merchant-SKU identifiers, but they are candidate
keys, not a documented immutable offer-ID contract. Review counts were readable;
a numeric seller rating and stock quantity were not independently established.
Delivery alternatives depend on context; no discount amount or authoritative
last-update timestamp was established. A percentage promotion badge must not
be converted into a discount without its meaning being verified.

**VERIFIED:** the rendered DOM contains product JSON-LD with productID, brand,
category, name and a KZT price/availability entry. That entry has no seller
identity; it is not a full competitor-offer feed. The seller table and prices
appeared after the initial browser accessibility snapshot, establishing dynamic
page population. **UNVERIFIED:** whether the initial HTTP HTML already contains
all/part of that data, the network response contract, and long-term selector/ID
stability. The browser tool rejected `view-source:` navigation; no alternate
protocol, private endpoint or network-replay workaround was used. No login,
CAPTCHA, purchase, seller-account access or rate-limit bypass occurred.

### Policy evidence that changes the implementation decision

The shop footer links to this [agreement landing page](https://guide.kaspi.kz/client/ru/shop/documents/polzovatelskoye-soglasheniye-magazin-na-kaspi.kz).
Its embedded document is the
[current linked PDF](https://guide.kaspi.kz/cdn/content/kkz/files/Document/polzovatelskoye-soglasheniye-magazin-na-kaspi.kz.pdf?ri=ad945a4e-ddd5-4eae-8f83-2a664a4584da).
**VERIFIED:** section 13.1 prohibits automated collection of product, price and
seller information; 13.2 prohibits interfering with access protections. Section
14 describes access restrictions. The older
[legacy PDF](https://kaspi.kz/shop/legal/user_agreement.pdf) lacks section 13;
its silence is not permission. The embedded viewer was blank in this browser,
but the official PDF text was retrievable through web research.

[robots.txt](https://kaspi.kz/robots.txt) contains crawler directives, including
`Crawl-delay: 10` and `Visit-time: 0400-0845`. These are not a commercial reuse
license or an exception to the agreement. No scraper was implemented. Further
automated acquisition requires an applicable written exception or approved feed.

### B–D. Comparison of access routes

Cost/freshness/reliability judgments below are planning assessments, not measured
service levels. Advertised end-user prices are **not** data-feed quotations.

| Route and primary evidence | Verified capability | Competitor access / permission status | Practical cost, freshness, reliability and setup |
| --- | --- | --- | --- |
| Public Kaspi card, inspected above | Real seller rows, prices, URLs and some delivery details visible | **UNAVAILABLE** for an unapproved automated adapter under section 13.1 | No feed fee established; DOM maintenance/context handling would be substantial; no freshness SLA; written exception required |
| Official [API overview](https://guide.kaspi.kz/partner/ru/shop/api/general/q3192), [goods index](https://guide.kaspi.kz/partner/ru/shop/api/goods), [my orders](https://guide.kaspi.kz/partner/ru/shop/api/orders/q3201) | Seller product submission/taxonomy and authenticated own-order/accounting operations | **UNVERIFIED** competitor read API; **UNAVAILABLE** as the documented competitor source | Seller access does not grant competitor scope; no competitor-feed tariff, schema or SLA verified |
| Official [XML price-list workflow](https://guide.kaspi.kz/partner/ru/shop/goods/price_list/q2962) | Kaspi consumes the seller's own price/stock feed | **UNAVAILABLE** for reading competitors | Wrong data direction; automating this would not solve monitoring and could modify seller prices |
| AlgaTop [bot](https://algatop.kz/bot), [settings guide](https://algatop.kz/guide/obshchie-nastroiki-magazina), [partnership contact](https://algatop.kz/contacts) | Vendor advertises monitoring, Excel integration and partnership enquiries; guide assigns API token to stock/order operations | **UNVERIFIED** reusable competitor API/feed and upstream rights | [Retail tariff](https://algatop.kz/tariffs): 22,800 KZT for up to 50 products; external-feed price/SLA unknown. Published speed claims are not an independently tested feed guarantee |
| [ONELAB](https://onelab.kz/services/kaspi/) | Vendor advertises minimum competitor price, seller, check date/status and Excel/Google Sheets/XML output | **UNVERIFIED** licensed server-to-server feed, full seller-list coverage and permitted upstream collection | Custom quote by scope/frequency; published changes rate 20,000 KZT/hour is not a subscription quote. Concrete integration-enquiry candidate; sample and contract required |
| [SPYON](https://spyon.kz/) | Vendor advertises scheduled Kaspi monitoring; examples explicitly include demo content | **UNVERIFIED** public export/API contract and rights for another SaaS | Retail Start advertises 14,900 KZT/month, 100 positions, five runs/day; not a feed license or measured SLA |
| [AWW public API](https://aww.kz/api/) | Documented open licensed static reference data | **UNAVAILABLE** for competitor offers: documentation explicitly excludes live Kaspi product prices | Free reference data cannot substitute for listings; no offer integration added |
| [OWWA API](https://owwa.ru/api/) and [supported sites](https://owwa.ru/) | Documented price-monitoring API | **UNVERIFIED** Kaspi support; published scope lists Russian sites and Moscow region | Custom-site request needed; no Kaspi access test or subscription purchase justified |
| [ProAnalytics API](https://proanalytics.net/documentacia.html) / [uXprice](https://uxprice.com/ru) | Documented/advertised competitor-price API capabilities | **UNVERIFIED** Kaspi-specific all-seller offers and reuse permission | ProAnalytics says its standard API is not for external-service backends; bespoke contract needed. uXprice lists Kazakhstan but this does not prove Kaspi coverage. Relevant costs/SLA require quotations |
| Direct written agreement with Kaspi or licensed commercial feed | A concrete permission route to request, not an existing service entitlement | **UNVERIFIED**, currently **UNAVAILABLE** to this team | Negotiation/access lead time and price unknown; preferable technical contract and explicit rights if granted |

AlgaTop's FAQ describes browser-like actions; it does not document the acquisition
protocol. Its [terms, section 5.1.5](https://algatop.kz/privacy) restrict external
software accessing its service, and section 2.5 qualifies calculated analytics.
Neither a paid subscription nor a partnership invitation establishes permission
to extract/relicense its data. No private service was reverse engineered, no
provider account was created, and nobody was contacted on the user's behalf.

Some Guide pages timed out in the research fetcher. The API overview was then
read successfully in the ordinary browser, the goods index through search, and
the orders/XML pages through the research tool. An unsuccessful fetch is not
evidence that an API or permission does not exist.

### Recommended next step and exact access request

**Choose a licensed read-only feed as the acquisition approach, conditional on
verified rights and a real sample. No currently investigated route qualifies as
a ready, permitted provider.** Do not build another queue or substitute minimum
product-card prices for identified seller offers.

First request a small data-supply pilot from ONELAB because it explicitly offers
machine-readable monitoring output; ask AlgaTop through its partnership channel
as an alternative. This is a qualification recommendation, not an endorsement
of either provider's authorization. In parallel, ask Kaspi partner support
([official Guide](https://guide.kaspi.kz/partner/ru/shop/api/general/q3192), which
links its support chat) for an approved competitor feed or written exception.
Do not buy a retail bot plan expecting it to include a redistribution license.

Suggested request, prepared but **not sent**:

> Мы разрабатываем AnalyMark — B2B-сервис анализа цен для продавцов Казахстана.
> Нужен разрешённый канал чтения предложений конкурентов Kaspi, без изменения
> цен и без доступа к заказам покупателей. Предлагаем пилот: 10 карточек товаров,
> один согласованный город, обновление один раз в сутки. Это запрос на условия,
> а не уже согласованный лимит. Можете ли вы предоставить API или автоматически
> обновляемый фид с правом хранения истории и показа данных клиентам AnalyMark?
> Просим документацию, пример реальных данных, подтверждение основания для
> получения и передачи этих данных, ограничения использования и стоимость.

Obtain answers before implementation:

1. **Rights:** who authorizes upstream collection; does the agreement cover the
   current Kaspi restriction, our automated access, retention, derived analytics
   and display to multiple seller customers? Any attribution or deletion duties?
2. **Scope:** all competing seller offers or only the lowest price/our own store?
   Exact product variant/bundle, merchant ID, merchant SKU, stable offer ID, city,
   product URL, availability, delivery options and currency semantics?
3. **Amounts:** already discounted listed price versus an additional discount;
   cashback versus discount; delivery method/city; unknown versus zero. No
   customer details, credentials or write/repricing rights are required.
4. **Time and completeness:** actual source capture timestamp with timezone,
   marketplace timestamp only if supplied, cache age, coverage, missing/removed
   offers, pagination, partial-result flags and historical retention?
5. **Access and operation:** documented endpoint/file format, authentication,
   sandbox/real pilot records, timeouts, quotas, minimum interval, Retry-After,
   availability guarantees, support, versioning and outage notification?
6. **Commercial terms:** pilot and monthly fee, charge per product/offer/city/run,
   API/export add-on, taxes, overages, setup, cancellation and redistribution
   license. End-user bot tariffs do not answer these questions.

### Integration acceptance gate after access is granted

Use the existing provider → validation → transactional importer → refresh-run
path. First verify a few actual records against their supplied source links and
the agreed city; never infer identity from names or prices. A successful pilot
must show those records in product analytics with actual retrieval provenance,
then survive an unchanged refresh without duplicate offers/observations. A real
later price change must append history; if none occurs, do not fabricate one
to claim the live price-change path was exercised. Use isolated tests for that
branch until a real change occurs.

Current schema limits that an approved sample must resolve: no explicit city,
payment or delivery-method dimension; source URLs reject query parameters;
seller display name is also part of an Offer uniqueness constraint; no field for
upstream capture/update time; batches require 1–1000 rows. A city query cannot
simply be discarded, a seller name cannot replace a stable ID, and an empty feed
cannot be treated as deletion. Plan the smallest evidence-led extension only
after the feed contract is known. Do not silently flatten these distinctions.

### Verification for this research-only change

Only README and this existing document were edited. No runtime code, tests,
translations or migrations were changed. Browser verification covered public
search, one real product and its seller rows, rendered structured data, the
shop's agreement link and the official API overview. It did not test an
authorized machine feed, repeat-price acquisition, a third-party API account,
or real records displayed inside AnalyMark. The end-to-end criterion remains unmet.

Executed after the documentation changes: `manage.py test` — 217 passed
(10.556 seconds); `manage.py check` — no issues;
`manage.py makemigrations --check --dry-run` — no changes;
`python -m pip check` — no broken requirements;
`python tools/compile_translations.py --check` — `Checked ru/django`;
`git diff --check` — passed (existing line-ending notices only).
File-hash comparison confirmed that the database, reports, migrations and all
pre-existing runtime changes remained unchanged. Only README and this document
differ from this request's starting files. No commit or push was performed.

## Running the implemented architecture

1. Apply migrations and create a local administrator if needed.
2. Open Data Sources → Configure automated source (staff with
   `core.add_datasource`). Select the existing **Kaspi.kz** marketplace, a stable
   lowercase namespace, interval **5–10080 minutes**, and optional import-age
   threshold. Existing sources require `core.change_datasource`; non-staff users
   cannot configure/queue even with a model permission. Source identity/mode is
   immutable in the form. No URL, file path, credential or Python-class input exists.
3. Save disabled for an explicit attempt only, or enable periodic attempts.
   Queue refresh attempt uses POST/CSRF and returns immediately. It does not
   fetch anything inside the HTTP request. Repeated clicks reuse the active job.
4. Run `python manage.py refresh_sources` separately from `runserver`.
   The command polls every 15 seconds; `--poll-seconds 1..300` changes polling,
   not the source interval. `--once` executes one bounded pass and exits; it is
   also suitable for an external OS scheduler. No OS task is installed automatically.
5. Reload source management to inspect queued/running/succeeded/failed/blocked/
   cancelled state, actual start/finish times and safe counts/error. The latest
   ten operations are shown. Last attempt/success and import age stay distinct;
   a source with no success does not gain freshness from attempts.

Only one active queued/running job per source is allowed by a partial unique
database constraint. Workers claim a job using a conditional update. Each pass
queues up to 100 due sources and handles up to 50 queued jobs. A late schedule
queues one current attempt, never a backlog of fabricated past captures. Next
attempt is measured from enqueue time; a running job excludes overlapping work.
Disabling a schedule cancels queued scheduled work when claimed; manual attempts
remain possible. An already running operation is not interrupted by disabling.
There is no automatic retry loop beyond the configured interval. Interval
configuration is not a promise of acquisition frequency, particularly while blocked.

Use a single sequential worker for this SQLite MVP. There is no Celery, Redis,
network adapter, worker heartbeat, push progress, or production supervisor.
If no worker is running, jobs remain visibly queued. On interruption during a
provider operation a job can remain running. Inspect/stop the old worker, then
explicitly run `refresh_sources --once --recover-stuck-minutes 15`. Recovery fails
running jobs older than that limit. A conditional write fence prevents a recovered
late worker committing catalog changes. Recovery is never automatic or evidence
that a source was fetched. Start/finish timestamps use the real clock.

## Provider integration contract

`provider_for(source)` constructs a reviewed adapter from an allowlist.
`KaspiPendingProvider` raises `SourceBlocked`; CSV continues through its explicit
existing command, not the scheduler. No dummy/demo adapter is registered in the
runtime. Test fixtures patch the factory **only in isolated software tests**.

The worker uses the existing `run_import` normalization/transaction path, with
provider-specific namespaces. It preserves blank optional values, source IDs,
review invalidation rules, missing rows and existing records. Changed listed
prices create actual-time observations linked to their RefreshRun; unchanged
prices/initial imports do not infer history. CSV's existing marker is retained
only for CSV, not relabeled as automatic provider acquisition. Import writes,
new observations and successful job counts commit together. Failure rolls them
back and retains a safe failed/blocked operation outside that transaction. Current
provenance is unverified; no future adapter may claim live/verified data without
evidence. Runtime credentials for a future adapter belong in environment variables.

Before replacing the access gate, verify the permission/contract and implement
bounded timeouts, payload limits, rate limits and pagination with an atomic batch
policy. Current normalized batches retain the 1000-row/Decimal/KZT restrictions.
No externally supplied marketplace-update timestamp is modeled yet. Large feeds,
city/payment-specific comparability, conditional HTTP fetching and incremental
checkpoints need an explicit schema and tests against an approved sample.

## What works and what does not

The real UI → persisted queue → worker → **blocked result** works without preparing
a CSV file. Scheduling, permissions, deduplication and status/error handling are
operational. Real Kaspi public competitor listings/prices **cannot be obtained by
this implementation**. Success/price-change/rollback paths are software-tested with
fictional fixtures, not evidence of a live integration. The end-to-end product
goal remains incomplete until approved access is supplied and actual records are
retrieved with checked provenance. CSV remains an honest manual fallback.
## Five-marketplace scope follow-up — 2026-10-27

Only Kaspi.kz, Halyk Market, Ozon, Wildberries and Teez are supported; see [MARKETPLACE_ACCESS.md](MARKETPLACE_ACCESS.md). Other labels/records are archived, never deleted or reassigned. Initialization disables their source schedules and cancels queued/running operations. Queueing, execution and import application check active scope, including a check after acquisition to reject stale in-flight batches. Stop the worker while applying scope migrations/initialization. Completed refresh history and all price observations remain preserved.

No new real adapter was added. The `demo` provider classification identifies local fixtures and is rejected by the refresh queue. CSV remains a fallback and the pending Kaspi provider still reports blocked access. Seller APIs are not evidence of permitted competitor feeds. Old wider-marketplace research is not a list of current integrations.
