# CSV refresh lifecycle audit and rules

## Inspected baseline (176 passing tests)

- Product identity is `(DataSource, SourceProduct.external_id)`, mapped one-to-one
  to a catalog Product. Names/brands/prices never merge records across sources.
- Offer identity is `(DataSource, SourceOffer.external_id)`, mapped one-to-one to
  Offer. An existing ID cannot change product, marketplace or demonstration mode;
  such a batch fails atomically. The existing seller/product uniqueness rule also applies.
- A known offer's changed listed price replaced its current value, **without**
  creating a PriceObservation. Unchanged files refreshed import timestamps only.
- Brand, delivery and discount blanks preserved existing values; unknown amounts
  stayed NULL on creation. Explicit zero meant a known amount. Required name,
  category, seller, price and URL were always supplied. A retained discount that
  exceeds a reduced price caused the whole batch to fail.
- Missing offers were neither removed nor deactivated. No stale threshold existed.
- History was created only by explicit demo capture/illustrative seed commands or
  validated custom writers. No CSV history or inferred older prices existed.
- Price/charge changes preserved manual review; product name/brand/category or
  seller/reference URL changes invalidated it with a generic explanation.
- Preview exercised the same writes inside a rollback transaction. Applied
  failures rolled back catalog writes but retained a safe source error/attempt time.

## Rules after this iteration

The above identity, blank-field, deletion and atomicity rules remain in force.
Supplied managed metadata can replace manual edits on explicit apply; descriptions,
other sources, unrelated records and source identities are not overwritten.

Only a **changed price on an existing imported offer** creates an observation,
using the actual import time and the source's demonstration flag. First import
does not infer a prior price or create a baseline; unchanged prices and changes
only to delivery/discount create no observations. A → B → A creates two new
observations of B and A, never an invented old A. Existing history is retained.
Preview includes planned observation/review-reset counts but saves nothing.

Identity metadata changes invalidate affected reviews and record the changed
field names in the explanation. Price-only changes preserve status, explanation,
reviewer and review time. A source ID reassignment fails instead of silently
moving even an unreviewed association. No automatic cross-source matching occurs.

CLI counts distinguish created/updated/unchanged unique offers, identical duplicate
input rows skipped, observations created, and previous decisions invalidated.
Successful batches reject zero rows. Invalid batches reject **the entire batch**
and apply zero rows; where the input row count cannot be determined (e.g. malformed
CSV/file access), rejected count is reported as unknown rather than invented.
An unchanged offer can still receive a new `SourceOffer.imported_at`; this is a
successful reread, not a price change or marketplace-provided update.

## Conservative freshness information

`DataSource.stale_after_hours` is optional, positive and set by authorized staff in
Django admin. NULL means no age assessment. At or beyond the configured interval
since last success, the UI says the configured interval was exceeded; within it,
the UI does not claim that prices are current or verified. No universal default,
background refresh, automatic deletion, or availability inference exists.

Last attempted import, last successful import, and each offer's last-seen import
time are distinct. A failed attempt preserves the last success. Missing offers
keep their old last-seen time even after a successful partial file. Source age
does not establish every offer's freshness. The CSV schema has no marketplace
update timestamp; it remains explicitly unavailable, never copied from import time.

Imports are sequential local operations. Serialize writers and preview the exact
file immediately before `--apply`; preview is not a locked approval token, so
changed files/database state are revalidated on apply. No live Kaspi access,
marketplace authorization or authenticity of operator-supplied data is established.
