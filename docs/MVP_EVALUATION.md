> Current scope update (2026-10-27): only Kaspi.kz, Halyk Market, Ozon, Wildberries and Teez are active in the MVP. Earlier counts and marketplace descriptions below are historical evidence, not current supported options. Excluded records are archived without deletion. See [current scope/access documentation](MARKETPLACE_ACCESS.md).

# AnalyMark MVP evaluation and Assignment 5 audit

Audit date: 27 October 2026. Baseline revision: `a79b9c6`.

Business positioning now follows the latest supplied Assignment 4, `AnalyMark_Report (4).docx`. See the [business-positioning alignment matrix](POSITIONING_ALIGNMENT.md) for report evidence, implementation gaps and current priorities. The earlier audit evidence and uncommitted wording correction below are retained; this update adds no human study results.

The working demo is ready for internal review and a small seller usability study. This operational guide is **not the required 500–1000-word submission report**. Human alpha/beta sessions and post-MVP HADI results are not documented in the supplied project.

## Evidence and assignment coverage

The supplied university brief requires a journey map, prioritized features, scope, a development method, alpha/beta testing, a prototype, and HADI before and after the MVP. It also requires a report, presentation, and product demonstration (Astana IT University, n.d.).

**Table 1. Requirement matrix before and after this audit**

| Requirement | Existing evidence at the start | Status before → now | Next action |
| --- | --- | --- | --- |
| User Journey Map | README describes navigation; templates connect the screens | Partially satisfied → satisfied | Use Table 3; validate its assumed friction with sellers |
| Prioritized features | README lists scope and future directions without explicit priority classes | Partially satisfied → satisfied | Review Table 2 after beta |
| MVP scope | README states implemented functions and exclusions | Satisfied → satisfied | Keep claims within the demo scope below |
| Management/development method | Incremental Git changes, but no explicit method or board record | Missing → satisfied | Method selected below; team must operate it going forward |
| Alpha testing | Automated tests and technical workflow coverage; no team session log | Partially satisfied → partially satisfied | Execute the internal checklist and record reviewer findings |
| Beta testing | Customer Development research concerns existing seller behavior, not use of this MVP | Missing → missing | Run the consented seller sessions below; a protocol is not a completed test |
| Working prototype | Models, calculations, views, templates, persistence, and passing workflow tests | Satisfied → satisfied | Rehearse the local demo; real users/metrics are still needed for stronger maturity evidence |
| HADI before and after MVP | Assignment 3 contains hypotheses, research, and implications; no completed post-MVP experiment | Partially satisfied → partially satisfied | Use retrospective research rows and run the planned experiments in Table 5 |
| 500–1000-word report and literature review | Earlier assignments and the new task brief; no Assignment 5 submission report found | Missing → missing | Write the specified sections, confirm all group members, cite evidence in APA, export PDF |
| Presentation, speech, Q&A | No Assignment 5 deck or delivery evidence found | Missing → missing | Prepare slides from the report and rehearse the actual prototype |

Evidence: models, calculations, forms, views, URLs, templates, commands, tests, README, four local reports, and the latest supplied Assignment 4. No raw survey CSV or MVP session log was found. Assignment 3 includes charts and an interview transcript; its referenced original export/recording were not independently verified here.

Technical verification on the audit date: **112 tests passed both before and after the wording fix**; `manage.py check`, `makemigrations --check --dry-run`, and `pip check` passed. A CSRF-enforcing Django-client walkthrough on an isolated database copy checked the full journey, calculations, private/idempotent saving, removal, login return, stored history, empty history, and 404s. The copied catalog had 14 products, 30 demo offers, 2 marketplace labels, and 12 demo observations. These are system records, not user-study results. No new browser or human alpha/beta session was performed in this audit.

Usability fix: public comparison/filter messages no longer call the product “saved.” Selection does not imply Watchlist membership; existing regression assertions were updated.

## Scope and priorities

Business audience: small and medium-sized marketplace sellers in Kazakhstan, following updated Assignment 4. The first evaluation persona remains a small seller using manual checks/spreadsheets; applicability to medium-sized sellers is not validated by the earlier research. Kaspi.kz is the initial target; Practice Market is fictional, not an integration.

The MVP tests an understandable comparison workflow using fictional offers. Buyer total = listed price − known discount + known buyer delivery; either unknown input makes it unavailable. Benchmarks use current listed prices only. Exact IDs separate variants/bundles; associations remain unverified. Product analytics includes all linked marketplace labels: use Search's marketplace filter for within-marketplace comparison. CSV offers now show actual import times; demo/manual records have unknown current-offer update times. Import and observation times are not marketplace refreshes.

**Table 2. Prioritized scope aligned with Assignment 4**

| Priority | Features or activities | State |
| --- | --- | --- |
| Must have for current MVP | Seller search/filter/sort, exact-product grouping, listed-price benchmarks, honest buyer totals/unknowns, demo/match/source/time limitations, private saves; retain the dashboard and recorded history | Functional with demo/manual data; no verified matching or freshness |
| Must have for evaluation | Internal alpha evidence, seller beta sessions, completed HADI decisions, report and presentation | Planned, not completed |
| Should have after initial testing | Correct observed seller friction; evaluate structured variant/review metadata, trustworthy provenance/update times and seller cost/minimum margin separate from buyer delivery | Not implemented; select from initial findings |
| Future work | Permitted real-data access, staged marketplaces, cross-market matching, validated advanced recommendations | Not implemented. Scraping/APIs are excluded from this iteration; automatic repricing remains outside scope |

Seller cost/margin is a research-backed gap. Demo snapshots do not validate freshness or outcomes; a single illustrative run is not a historical market trend.

## User journey

Scenario: find a specific white Luma lamp, compare offers, save it, and revisit evidence. Friction/thoughts below are **design hypotheses**, not observed participant quotes.

**Table 3. User Journey Map**

| Stage and goal | Action and touchpoint | Anticipated thought/friction | Response and measurement |
| --- | --- | --- | --- |
| Start with context | Dashboard → Search offers | “Are these live prices?” | Visible demo notice; ask the user to explain the source |
| Find the right item | Product Search → filters/results | Similar color, model, or bundle may be mistaken for an equivalent | Names/descriptions and marketplace labels; record variant errors and time |
| Compare prices | Product link → analytics → Compare offers | Lowest listed price may not be cheapest to the buyer | Separate listed figures, totals, unknowns, scoped benchmarks; score the user's explanation |
| Keep a product | Save → login if necessary → Watchlist | Concern about losing the product after login | Safe return and explicit save feedback; check completion without hints |
| Revisit evidence | Watchlist → Compare this product → Recorded history → offer history | “Did these prices really change over previous days?” | Actual recording times, demo labels, empty states; score source/history understanding |
| Finish safely | Remove product → Log out | Unclear whether saving changes a price | POST feedback and private ownership; verify only the user's entry changes |

## Development and management method

Choose Lean build–measure–learn with HADI and a Kanban board: **Backlog → Ready → Doing → Verify → Done**. This method is selected now; prior formal board use is not established.

Keep one implementation item active. Each card names a hypothesis, evidence, owner, acceptance check, and decision. This fits a small Django/SQLite project without extra infrastructure. “Done” requires relevant tests, honest labels, a journey check, and findings. An experiment additionally needs actual consented observations and an insight; writing its protocol is a separate card.

## Alpha protocol for the team

Use disposable data/accounts. The loader preserves edits; the illustrative flag records three deliberate changes at real capture times and skips edited samples/existing history. Never backdate observations or reset the original database for an empty state.

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

For human sessions, use a separate project copy with its own `.venv` and SQLite database, following README setup. In that separate copy only:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py load_demo_data --with-illustrative-history
.\.venv\Scripts\python.exe manage.py runserver
```

Confirm SQLite's path points inside that separate copy. Use a local admin to create ordinary seller test accounts; do not share administrator credentials. The audit used a disposable copy and removed it afterward.

Team checklist, still to be recorded as a human session:

- [ ] Follow Table 3 with a mouse and keyboard, on desktop and a narrow screen.
- [ ] Try valid/invalid/empty filters; check a variant and bundle separately.
- [ ] Recalculate one known total; check unknown delivery, unknown discount, and explicit zeros.
- [ ] Verify two accounts cannot see/remove each other's saves; repeat a save.
- [ ] Check invalid login, return destination, logout, and expired-session retry.
- [ ] Check stored observations, illustrative disclosures, empty history, and unknown IDs.
- [ ] Repeat demo loading/capture on the disposable database; confirm duplicate rules.
- [ ] Log build/fixture, tester, date, steps, expected/actual result, severity, and retest outcome.

Block beta for cross-user exposure, wrong totals, or misleading live/verified claims. Automated checks do not replace the team session.

## Beta protocol with target sellers

**Planned, not conducted.** Recruit five consenting sellers who set prices, preferably through manual checks/spreadsheets. Note role, current tool and self-described business size without identifying the business. This first small-seller cohort cannot validate the whole SME audience; evaluate medium-sized sellers separately. Assign a moderator and note-taker.

Explain: “This student prototype has fictional prices and no marketplace connection. We test the product, not you. Participation is voluntary; skip questions or stop anytime.” Obtain consent for anonymous notes and separate consent for optional recording. Use participant codes and separate test accounts. Keep consent/contact details separate from notes in local ignored `Reports/MVP_Testing/`, outside Git. Do not request commercial costs or personal marketplace credentials.

**Table 4. Beta tasks and facilitator answer checks**

| Task given without a click-by-click tutorial | Success check for the unchanged seed dataset |
| --- | --- |
| T1 Find the white Luma L1 single lamp on Kaspi.kz and open its comparison | Exact single-lamp product, not black or cable bundle; correct filter. Recognize that analytics includes all demo labels and use filtered Search for a Kaspi-only benchmark |
| T2 Identify the lowest listed offer and cheapest offer whose buyer total can be calculated; explain the difference | Listed minimum 11,800 KZT has unknown delivery. Cedar Desk Demo has a known 12,300 total: 12,000 − 500 + 800. Unknown offers cannot be ranked as cheapest totals |
| T3 Explain whether the match/prices/update time are verified, and whether buyer delivery represents seller cost | Demo/unverified associations; no live prices; CSV import times and observation capture times are not marketplace refresh times; buyer delivery is not seller cost/margin |
| T4 Save the product, return through Watchlist after login, then remove it | Correct personal entry persists and is removed; no other user's entry changes |
| T5 Open Keyra compact EN history and Matra history; explain both | Keyra's stored illustrative changes were captured during a command run, not continuous monitoring. Matra has no stored observations |

Hide the answer column. Reset only the disposable fixture; these fictional answers change if it is edited. Allow three minutes per task. Record first unassisted success or timeout, then help and mark assisted separately. Never restart the timer silently. Ask:

1. How useful would this comparison workflow be? Rate 1 (not useful) to 5 (very useful), then explain.
2. What was confusing, missing, or difficult?
3. How did you interpret Unknown, the benchmark, and the recorded timestamp?
4. What would need to change before you could use it in your actual workflow? What would you use instead?

Use a blank log schema; do not populate example responses as if collected:

```text
session_code,date,build,fixture,task,outcome,seconds,hints,error_type,usefulness_1_to_5,notes
```

Outcomes: unassisted correct, assisted, failed/timeout. Classify matching, cost, source/history, navigation, and authentication errors. No beta results are available.

Metrics: unassisted correct / attempted **per task**, including failures/timeouts; median successful unassisted time, with assisted/failure counts and timeout durations separately; error types/counts; usefulness distribution with its response denominator. Proposed gates: ≥80% unassisted success per task, zero critical data/security misunderstandings, and ≥4/5 sellers rating usefulness ≥4. These are targets, not findings. Report actual denominators if recruitment falls short. Below a gate, revise and retest. Passing suggests sample usability, not savings, conversion, retention, or purchase intent.

## HADI experiments and evidence

Assignment 3 reports 32 consented responses, one excluded refusal, and one interview (AnalyMark project team, 2026). The figures below are convenience-sample self-reports, not new MVP results. Its 13/32 existing analytics payers do not establish willingness to buy AnalyMark; one interview cannot establish general demand.

**Table 5. HADI cycle before development and planned after the MVP**

| Stage / Hypothesis | Action | Data available or to collect | Insight / next decision |
| --- | --- | --- | --- |
| Before MVP: broad cross-market aggregation is the main value | Earlier proposal followed by reported Customer Development | 23/32 prioritize same-platform prices, 12/32 cross-platform; Kaspi named by 25/32 | Narrow to Kaspi-first comparison. This is a retrospective reconstruction, not proof of a preregistered HADI experiment |
| Before MVP: a useful comparison needs equivalent products and understandable costs | Reported survey/interview analysis | Buyer-cost priority 25/32; matching and cost-comparison difficulty 17/32 each; interview describes human checks | Preserve variants, unknowns, evidence labels, and human pricing control; real match accuracy remains untested |
| During MVP: the scoped workflow can work technically | Implemented Django prototype and this automated audit | 112 passing tests; isolated journey check; 14 products/30 demo offers | Technical feasibility with local data is supported; seller usefulness and live data feasibility are not |
| After MVP H1: sellers can compare/save without unsafe assumptions | **Planned:** run T1–T5 with consented sellers | Per-task completion/time, hints/errors, source understanding, usefulness; nothing collected yet | Apply proposed gates above; fix specific confusion and repeat, without claiming product-market fit |
| After MVP H2: the interface reduces comparison effort | **Planned:** paired comparison against a spreadsheet containing the same fictional offers; counterbalance order and use equivalent variants | Paired times and matching/cost errors; nothing collected yet | Proposed gate: median paired time reduction ≥20%, no extra critical errors. Otherwise revise scope. Equal static inputs test interface effort, not live marketplace savings |
| After MVP H3: equivalent offers and provenance can be trusted within one marketplace | **Planned, gated:** only after permitted real offer data becomes available, have sellers label same/different variants and review source/update metadata | False matches/splits, review disagreements, traceable-source and known-update-time coverage; nothing collected yet | Establish review/quality criteria before any verified-match or freshness claim; a demo dataset cannot supply these reliability metrics |

Log date, owner, hypothesis, preselected rule, actual participants/results, limitations, insight, and next action. Never fill future results from prior surveys or software test counts. Refresh needs, cost/margin inputs, paid demand, and real data access need separate experiments.

## Remaining submission work

The brief weights report 30%, presentation/speech/Q&A 30%, and MVP quality 40%; a working site does not automatically earn the advanced maturity grade (Astana IT University, n.d.). The team still needs:

- A 500–1000-word report with **Title, Introduction, Main Part (Steps 1–3), Conclusion, References**, every current group member, a relevant literature review, APA citations for statistical/financial claims, and titles for tables/graphs. Prepare the editable report and submit its PDF to Moodle as specified. This guide is not that report.
- Actual team alpha notes, consented seller beta evidence, and a completed post-MVP HADI insight/decision. Older Customer Development responses cannot substitute for new MVP tests.
- Slides based on the report, a rehearsed demo, and student delivery/Q&A. Explain data limitations and remaining gaps honestly. The supplied deadline field is blank; confirm it with the course rather than inventing a date.

## References and local source locators

AnalyMark project team. (n.d.). *Competitor analysis report: AnalyMark* [Updated Assignment 4 course report]. Current positioning source: supplied `AnalyMark_Report (4).docx` in Downloads/Telegram Desktop. Its intended capabilities do not establish implementation; older Assignment 1/2 proposals below remain historical.

Astana IT University. (n.d.). *Assignment 5: Creating your MVP* [Technological Entrepreneurship course assignment brief]. Supplied file: `Assignment 5. MVP (1).docx` in the user's Downloads folder.

AnalyMark project team. (n.d.). *Assignment 2: Creating a value proposition as part of the Business Model Canvas* [Unpublished course report]. Local source: `Reports/Assignment2_Report (3).docx`. This is an earlier proposal, not proof that its live-data claims were implemented.

AnalyMark project team. (2026). *Assignment 3 Customer Development* [Unpublished course report]. Local source: `Reports/AnalyMark_Assignment3.docx`, sections “Survey results,” “Hypothesis assessment,” “Research limitations,” and Appendix A Figures 7 and 9. Research dates/counts are reported by that document; the original raw export is absent here.

These references identify audit evidence. They do not replace the report's required external literature review. Verify external sources before citing them. Local report files remain ignored by Git and are not copied into this guide.
