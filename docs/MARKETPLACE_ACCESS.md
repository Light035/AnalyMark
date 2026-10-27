# Five-marketplace MVP: scope, access and preservation

Scope decision and technical review: **2026-10-27**. This supersedes the earlier nine-label demonstration. The supported marketplaces are exactly **Kaspi.kz, Halyk Market, Ozon, Wildberries and Teez**. Kaspi remains the first target. Marketplace names do not establish a live integration.

## Data access remains unchanged

The earlier official-source investigation found seller access with restrictions, not an approved competitor-offer feed available to the team. No new access investigation, credentials, integrations, paid services, scraping or marketplace requests were added in this scope-cleanup iteration.

| Approved marketplace | Official evidence from the access investigation | Current competitor access / application mode |
| --- | --- | --- |
| Kaspi.kz | [Seller API scope](https://guide.kaspi.kz/partner/ru/shop/api/general/q3192) covers own catalog/orders. [Shop agreement](https://guide.kaspi.kz/cdn/content/kkz/files/Document/polzovatelskoye-soglasheniye-magazin-na-kaspi.kz.pdf) restricts automated collection. | No approved public competitor feed; pending provider reports blocked. DEMO, optional supplied CSV only. |
| Halyk Market | [Official seller product API guide](https://halyk-market.gitbook.io/anyqtama/zagruzka-tovarov-po-api/zagruzka-tovarov-bez-prais-lista-po-api), linked through [partner rules](https://halykmarket.kz/info/join_rules). Own listing/card attachment is not all competitors' offers. | No permitted public competitor feed verified. DEMO, optional supplied CSV only. |
| Ozon | [Official Seller API introduction](https://dev.ozon.ru/start/40-Seller-API-API-prodavtsa-dlia-raboty-s-marketpleisom). Authenticated seller tools/benchmarks do not establish an unrestricted competitor-offer export. | No eligible competitor feed verified. DEMO, optional supplied CSV only. |
| Wildberries | [Official API authentication](https://github.com/wildberries-tech/api), [Kazakhstan own-price instructions](https://seller.wildberries.ru/instructions/ru/kz/material/how-to-set-price-and-discount). Seller credentials are required. | No permitted public competitor feed verified. DEMO, optional supplied CSV only. |
| Teez | [Official integration/access requirements](https://docs.teez.kz/kk/seller/api/integration): confirmed seller account/client credentials. Test access must be requested; no public credentials supplied. | No permitted public competitor feed verified. DEMO, optional supplied CSV only. |

These seller methods were classified **VERIFIED WITH RESTRICTIONS** for their documented scope. Competitor acquisition in this MVP remains **DEMO ONLY**. Non-demo CSV/manual input is unverified, not automatically LIVE. See [AUTOMATED_REFRESH.md](AUTOMATED_REFRESH.md) for the existing blocked-provider evidence and worker contract. Public page visibility is not an automated-data reuse license. No prices were fabricated as real, and no historic timestamps were invented.

## Excluded marketplaces are archived, not supported

ForteMarket, Satu.kz, Flip.kz and Practice Market (fictional) are no longer active options. Jmart/Jusan and all other names are outside the allowlist; no new labels for them are initialized. Earlier investigation of these services is not current product support.

The inspected database contained only demo offers/observations, no users or Watchlist entries, and no manually confirmed matches. However, Practice Market had **three existing stored observations**, and eleven products had offers shared with Kaspi. Source identity links use PROTECT, as do observation-to-offer links. Blind marketplace/product deletion would either fail protected foreign keys or risk unrelated records and saved entries. The chosen cleanup therefore deletes **no records at all**, including currently unused fixtures.

| Existing excluded label | Offers retained outside active scope | Stored observations retained | Treatment |
| --- | ---: | ---: | --- |
| Practice Market (fictional) | 12 | 3 | Archived; shared products retain their Kaspi offers. |
| ForteMarket | 3 | 0 | Archived with both source-specific products and source mappings. |
| Satu.kz | 3 | 0 | Archived with both source-specific products and source mappings. |
| Flip.kz | 3 | 0 | Archived with both source-specific products and source mappings. |

Ozon Kazakhstan is normalized to **Ozon on the same database primary key**. Source keys, product/offer IDs, timestamps, seller names, descriptions and observations are unchanged. Existing text mentioning the old Ozon label is historical source content, not an additional supported option. If both aliases exist in another database, the initializer archives Ozon Kazakhstan without merging any products/offers or deleting either row. An operator must review that collision separately.

## Migration and initialization

Migration `0009_marketplace_is_active` adds an activation flag and a conservative data migration. It normalizes the Ozon alias when unambiguous, deactivates unsupported rows, disables their schedules and cancels only queued/running refresh jobs. Completed jobs, source success/error timestamps, catalogs, reviews and price histories are retained. It does not seed missing marketplaces; `init_marketplaces` maintains the five canonical rows afterward.

The active policy requires **both** the activation flag and an approved name; even a newly inserted unsupported row with a true raw flag is not exposed as supported. Administration cannot add/rename supported marketplace identities. The initializer preserves existing website URLs, is repeatable and does not delete records. Its alias/deactivation data changes are not automatically undone by reversing the schema migration; use a reviewed restoration/backup if the scope decision is reversed. A database backup is retained locally outside Git.

Stop the sequential refresh worker before applying scope changes. Initialization cancels existing queued/running jobs for excluded marketplaces, and enqueue/due/execution paths enforce active scope. The importer checks scope before fetching and again inside the application transaction; a batch fetched before deactivation cannot commit afterward. No archived source is silently moved to another marketplace.

## Active dataset and counts

| Count | Before cleanup (all active) | After: active | After: total retained |
| --- | ---: | ---: | ---: |
| Marketplace labels | 9 | 5 | 9 |
| Products | 28 | 21 | 28 |
| Offers | 51 | 30 | 51 |
| Price observations | 12 | 9 | 12 |
| Data sources | 7 | 4 | 7 |

Seven products are archive-only. Twenty-one offers and three observations are excluded from active comparisons. Products shared between approved and archived marketplaces remain active, but only approved-marketplace offers/history contribute to their current comparisons. These numbers describe the inspected local dataset; the UI calculates real database counts and does not hardcode them.

`load_demo_data` now seeds **13 Kaspi products / 18 offers**. It no longer contains Practice Market rows or the product that only had a Practice offer. `load_marketplace_demo` seeds **8 products / 12 offers** across four isolated demo sources for Halyk, Ozon, Wildberries and Teez. Stable source IDs remain unchanged; changing registry display order does not change fixture prices. Repeat loading preserves existing prices, reviews, timestamps and relationships. Neither loader recreates excluded demo fixtures or adds history by default.

A fresh combined load has **21 products / 30 offers / five marketplaces / zero observations**. Existing nine active observations are retained, not reseeded. The larger 28/51 active scale is intentionally not maintained with replacement fixtures. Optional illustrative capture behavior remains explicit: `load_demo_data --with-illustrative-history` records a labelled sample sequence at actual invocation times only when its existing safety conditions allow it. `record_demo_observations` records active demo offers only and skips unchanged prices. This cleanup did not invoke either history-generating option.

## UI and existing workflows

- Dashboard, search, marketplace filters, analytics catalog, source coverage and source management use the active five-marketplace scope. Invalid/archived marketplace query IDs return an empty invalid selection, never unfiltered archived data.
- Benchmarks and charts remain separated by marketplace/provenance and use exact product IDs. Rejected matches are excluded; unknown buyer charges remain unknown. Source URLs, actual local import times and demo labels remain visible.
- Archive-only products disappear from active catalog discovery, but old product links show an archive warning. Old individual offer-history links remain read-only with an archive notice and original observations.
- Existing private Watchlist entries remain owned by the original user. Archived saved products show a warning and retain the remove action; new saves to archive-only products are rejected. Active-product Watchlist behavior and CSRF protection are unchanged.
- CSV accepts only active approved marketplaces. Archived sources cannot be configured/refreshed through the active source page. Administration retains source/history records for inspection; new offer choices exclude archived marketplaces.
- Search/filter/sort pagination and EN/RU switching remain available. Empty active history never implies that archived records were deleted.

## Commands (Windows PowerShell)

```powershell
cd C:\AnalyMark
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py init_marketplaces
.\.venv\Scripts\python.exe manage.py load_demo_data
.\.venv\Scripts\python.exe manage.py load_marketplace_demo
.\.venv\Scripts\python.exe manage.py runserver
```

CSV fallback uses the same explicit preview/apply commands from the README, with an exact approved marketplace name (use `Ozon`, not the old alias). The existing worker remains `manage.py refresh_sources`; Kaspi acquisition still reports blocked until permitted access exists. No new dependencies, integrations or infrastructure are needed.

Reports, existing migrations, source identities, database records and unrelated uncommitted work are preserved. Automated software tests do not establish real-seller validation or a working marketplace integration.

## Verification of this cleanup

- Baseline: 235 tests passed. Final: 254 tests passed, including 19 scope/preservation regression tests.
- `manage.py check`, `manage.py makemigrations --check --dry-run`, `pip check`, `tools/compile_translations.py --check` and `git diff --check` passed.
- Migration 0009 was applied locally. Initialization and both loaders were each rerun twice; every run created zero records in the existing database.
- A before/after database comparison preserved all 243 existing rows checked, allowing only the intentional Ozon marketplace-name normalization and the new activation field. Hash checks confirmed all four reports and all nine existing migration files were unchanged.
- Browser checks used a disposable database copy at 1280 x 850 and 390 x 844: exactly five marketplace filter options, Halyk filtering to three offers, mobile product analytics, five-row source coverage, EN/RU switching and retained archived offer history with its warning. The checked mobile pages had no document-level horizontal overflow. No browser console errors were recorded. The temporary test server was stopped afterward.

These checks verify application scope and data preservation, not live acquisition, marketplace authorization or real-seller validation.
