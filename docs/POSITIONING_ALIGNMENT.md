> Current scope update (2026-10-27): only Kaspi.kz, Halyk Market, Ozon, Wildberries and Teez are active in the MVP. Earlier counts and marketplace descriptions below are historical evidence, not current supported options. Excluded records are archived without deletion. See [current scope/access documentation](MARKETPLACE_ACCESS.md).

# AnalyMark business positioning and MVP alignment

Reviewed 27 October 2026 against the supplied **AnalyMark_Report (4).docx** (updated Assignment 4, SHA-256 prefix `41f02161ffa0`) and the official Assignment 5 brief. The latest Assignment 4 controls business positioning; the four files in local `Reports/` remain historical evidence. Goals in the report do not establish implemented capabilities or validated competitive advantage.

AnalyMark targets **small and medium-sized marketplace sellers in Kazakhstan**, initially Kaspi.kz. Differentiation is intended to come from equivalent-product comparison within the selected marketplace, understandable final buyer prices, data reliability, and seller control. Additional marketplaces are staged future work.

## Requirement and assumption matrix

**Table 1. Assignment 4 and Assignment 5 compared with the actual MVP**

| Requirement or assumption | Assignment evidence | Current implementation status and code evidence | Gap or inconsistency | Recommended action |
| --- | --- | --- | --- | --- |
| B2B workflow for small and medium sellers | A4 §§1, 5.1, 5.3 | Functional seller comparison/Watchlist; shared shell, dashboard and README now name the SME audience | No evidence of usefulness across business sizes | Test the initial small-seller cohort; record business-size context and validate medium-seller applicability separately |
| Kaspi first, compare within a selected marketplace | A4 §§1, 4, 5.3 | Functional on demo records: `ProductSearchForm` and `product_search` filter by marketplace; no integration | Search defaults to all labels; product analytics includes all labels for its exact product ID | Use the existing Search marketplace filter; disclose analytics scope. Test whether preserving selection on analytics is needed later |
| Match identical products/variants | A4 §4 “Matching identical products”; §§5.1–5.2 | Partial demonstration: `Offer.product` associates curated examples; names distinguish variants/bundles and exact-ID queries prevent similar-name leakage | No automated matching, card verification, structured variant review, confidence score, or measured accuracy | Keep associations unverified; after initial tests define variant attributes, review rules and a labeled evaluation set |
| Listed price and final buyer price where inputs exist | A4 §4 “Delivery and discounts”; §5.2 | Functional Decimal calculations in `Offer.total_buyer_cost`; negative/bounded amounts validated; unknown delivery/discount remains unknown | Inputs are fictional/manual, not a reliable marketplace feed | Retain explicit unknown/zero handling; evaluate interpretation with sellers before adding data adapters |
| Transparent benchmarks | A4 §4 “Price analysis within a marketplace” | Functional min/max/average/median listed prices via `listed_price_summary`; Search scopes them to its filters | Product analytics groups by product, not marketplace; mixed label statistics are not a verified market benchmark | Preserve existing results but state the scope and link to same-product Search filtering; do not mix buyer totals into these statistics |
| Data source and last update where available | A4 §§1, 4, 5.2 | Partial: demo/manual flags, marketplace, seller, optional URL, stored observation capture times | CSV offers now have source IDs, reference URLs and actual import times; older records still lack import times. No marketplace refresh timestamp or verified provenance | Distinguish manual import times from unknown marketplace update times; see README for the CSV workflow and official API research |
| Seller retains pricing control | A4 §4 “Recommendations confirmed by the seller”; §§5.1–5.3 | Functional decision-support UI; saving/removing does not change prices | No recommendation engine, seller cost/margin inputs, or evidence that recommendations are useful | Keep the decision with the seller; test cost/margin needs after initial usability work; advanced recommendations remain future work |
| More marketplaces/cross-market matching | A4 §§1, 4, 5.3 | Demonstration schema supports two labels; 18 Kaspi-labeled and 12 fictional Practice Market offers | This is not two working integrations or cross-market matching | Keep every record and label; add real coverage only in stages after source/identity feasibility is established |
| Scraping and automated card verification | A4 §§1, 5.2 describe the intended foundation | Not implemented: loader/capture commands use local records and make no live requests | Some report wording reads as current capability | Present it as planned; do not add scraping/APIs or bypass systems in this iteration |
| Trustworthy history and update reliability | A4 §5.4; A5 prototype quality | Functional stored observations and SVG/table; explicit capture command skips unchanged prices | Illustrative price changes are not real market history; no continuous monitoring, freshness SLA, or retention measurements | Keep actual capture times and demo labels; test understanding now and source reliability in a future permitted-data pilot |
| User journey, priorities, scope and development method | A5 Step 1, Steps 5–8 | Documented in this matrix and `MVP_EVALUATION.md`; Lean/HADI with Kanban selected | Formal prior board use and seller validation are not established | Operate the proposed method and revise priorities from observations |
| Alpha/beta testing | A5 Step 1, Step 9 | Partial alpha evidence: automated functional tests; beta protocol exists | No recorded team usability session or seller beta results in supplied materials | Execute the checklist and consented tasks; record actual completion/time/errors/usefulness |
| Working prototype | A5 Step 2 | Satisfied for a local demo: search, analytics, authentication, private persistent saves, recorded history | Not a live-market pilot; system record counts are not customer metrics | Demonstrate the real workflow and limits; collect user evidence for greater maturity |
| HADI before and after MVP | A5 Step 3 | Previous Customer Development supports retrospective hypothesis review; new experiments are planned | No completed post-MVP HADI Data/Insight | Separate old research from software tests and new experiments; complete the latter with real observations |
| Report and presentation | A5 submission instructions and assessment | Operational guides exist | No completed Assignment 5 report/deck or delivery evidence supplied | Prepare 500–1000 words with all members, required sections, literature review/APA, titled tables/graphs, PDF; rehearse slides/demo/Q&A |

The reviewed dataset contains **14 fictional products, 30 demo offers and 12 demo observations**, using **Kaspi.kz** and **Practice Market (fictional)**. Counts describe stored records only. No records were removed, renamed, reset, or relabeled to manufacture alignment.

## Feature priorities

**Table 2. Must have, Should have after initial testing, and Future work**

| Priority | Scope and reason | State |
| --- | --- | --- |
| Must have for the current MVP | Seller search with an explicit marketplace filter; exact-product grouping and variant descriptions; known/unknown buyer totals; scoped listed-price statistics; source/match/freshness limitations; private saves; existing dashboard/history kept usable. These test the core comparison workflow without unsafe data claims | Functional with demo/manual data; matching and freshness are limited, not verified |
| Must have for evaluation | Team alpha record, consented seller beta, an actual HADI decision, report and presentation | Plans exist; human execution remains outstanding |
| Should have after initial testing | Fix observed seller friction; evaluate selection continuity, structured variants/review status, reliable provenance/update metadata, and separate seller cost/minimum-margin inputs. Prioritize matching quality and reliability before breadth | Not implemented by this pass; select from observed needs |
| Future work | Permitted real-data access after availability/reliability checks; staged marketplaces; cross-market matching after identity validation; advanced recommendations only after evaluating inputs and seller approval | Not implemented. Automatic repricing remains outside scope |

Existing curated associations are not a matching algorithm. Local seed/capture commands are not scraping. Min/median values are descriptive statistics, not recommended or “optimal” selling prices. Fictional cross-label examples demonstrate the data model, not supported marketplace coverage.

## Assignment 5 evaluation connection

Journey: **Dashboard → Search/filter by marketplace → exact product analytics → login/save → Watchlist → Compare this product → Recorded history/offer history**. Product analytics explicitly includes all linked labels; return to its Search link for a single-marketplace benchmark.

Use the [evaluation guide](MVP_EVALUATION.md) for the journey map, task answer checks, consent, alpha checklist, beta questionnaire, recording schema, proposed decision gates, and HADI. Previous Assignment 3 research reports 32 consented responses and one interview; its buyer-cost/same-platform/matching priorities motivate this focus. It is not a beta test of this app. Automated test results establish software behavior, not seller demand. No post-MVP study results were supplied; planned participant counts, completion metrics and pilot outcomes must not be presented as observations.

## Verification in this alignment pass

Baseline and final suites both passed **112 tests**. Django checks, the migration dry-run, dependency consistency and Git whitespace checks passed. A read-only Django-client check rendered the current catalog: the white Luma example has three offers in Kaspi-filtered Search and four across all labels in product analytics. The scope/freshness notices and earlier public-comparison wording fix were verified. No new browser or human study was performed. Models, calculations, views, routes and loader behavior were not changed; only narrative/disclosures, regression assertions and documentation were updated.

## Clarifications still needed in the written business report

The report file is preserved. When preparing the next written version:

- In §5.1, the row saying variants are matched “across marketplaces” conflicts with the selected-marketplace launch scope in §§1 and 5.2. Mark cross-market matching as future work.
- Statements about scraping, automated verification, recommendations, update monitoring, and anti-detection describe intended systems, not this codebase. Use planned/conditional wording; source/update information is shown only where actually available.
- “Every data point” having a source/update time is an aspiration; existing demo/manual offers lack update times; CSV offers now record actual import times. Do not equate import or observation capture with marketplace refresh.
- Differentiation, willingness to pay, matching accuracy, freshness and weekly retention are hypotheses. Competitor figures/prices in the report were not independently re-verified in this audit and are not application data.

Local source locators: supplied `AnalyMark_Report (4).docx`, especially §§1, 4, 5.1–5.4 and 6; supplied `Assignment 5. MVP (1).docx`, required tasks, assessment and submission instructions; `Reports/AnalyMark_Assignment3.docx` for reported Customer Development. Source documents are not copied into Git or overwritten.
## Implementation update — 2026-10-27

The preceding alignment assessment is retained as a historical review. The later [marketplace expansion](MARKETPLACE_ACCESS.md) adds clearly fictional source-isolated examples. Search and product analytics now separate benchmarks and charts by marketplace and demo/non-demo provenance, with filters on both pages. The older mixed-label benchmark gap is addressed; real permitted competitor acquisition and real-seller validation remain incomplete. The original four assignment documents are unchanged.
