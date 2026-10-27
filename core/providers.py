"""Acquisition contract and bounded local CSV provider. No marketplace HTTP calls.

Providers return product identity AND individual seller-offer identity. A product
card alone must never be converted into a supposed competitor seller offer.
"""
import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


COLUMNS = (
    "product_id", "product_name", "brand", "category", "offer_id", "seller_name",
    "listed_price", "currency", "delivery_cost", "discount", "source_url",
)
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000


class SourceError(Exception):
    """Only safe, deliberately written messages may cross the UI/CLI boundary."""

    public_message = "Source unavailable. No catalog changes were saved."


class SourceUnavailable(SourceError):
    pass


class SourceTimeout(SourceError):
    public_message = "Source timed out. No catalog changes were saved; retry explicitly."


class SourceBlocked(SourceError):
    public_message = "Kaspi competitor access is not verified. Approved feed/API documentation and permission are required; no marketplace request was made."


class InvalidSourceData(SourceError):
    def __init__(self, safe_message):
        self.public_message = safe_message
        super().__init__(safe_message)


@dataclass(frozen=True)
class OfferRecord:
    product_id: str
    product_name: str
    brand: str
    category: str
    offer_id: str
    seller_name: str
    listed_price: Decimal
    currency: str
    delivery_cost: Decimal | None
    discount: Decimal | None
    source_url: str
    row_number: int = field(default=0, compare=False, repr=False)


class OfferProvider(Protocol):
    kind: str

    def fetch(self) -> list[OfferRecord]:
        """Return a bounded batch or raise SourceError; never save Django models."""
        ...


class ValidatedRecords(list):
    """Normalized rows plus duplicate accounting across repeated validation."""

    def __init__(self, records, skipped=0):
        super().__init__(records)
        self.skipped = skipped


def _invalid(row, field, explanation):
    # Never echo raw cell values, file paths, credentials, or provider exceptions.
    raise InvalidSourceData(f"Row {row}: {field}: {explanation}")


def _text(value, row, field, limit, required=True):
    if not isinstance(value, str):
        _invalid(row, field, "expected text.")
    value = value.strip()
    if (required and not value) or len(value) > limit or any(ord(c) < 32 for c in value):
        _invalid(row, field, f"use {'1' if required else '0'}–{limit} characters without control characters.")
    return value


def _money(value, row, field, optional=False):
    if optional and (value is None or value == ""):
        return None
    if not isinstance(value, (str, Decimal)):
        _invalid(row, field, "use a decimal amount with at most two fractional digits.")
    try:
        amount = Decimal(value)
        if (not amount.is_finite() or amount < 0 or amount > Decimal("9999999999.99")
                or amount.as_tuple().exponent < -2 or (not optional and amount == 0)):
            raise ValueError
    except (InvalidOperation, ValueError):
        _invalid(row, field, "use a positive listed price or nonnegative charge, at most two decimals and 12 digits.")
    return amount


def _validate_records(records):
    """Shared boundary validation also protects future providers, not just CSV."""
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_ROWS:
        raise InvalidSourceData(f"Supply 1–{MAX_ROWS} offer rows.")
    result, seen_offers, products = [], {}, {}
    skipped = getattr(records, "skipped", 0)
    for row, record in enumerate(records, start=2):
        if not isinstance(record, OfferRecord):
            _invalid(row, "record", "provider returned an unsupported record format.")
        if type(record.row_number) is not int or record.row_number < 0:
            _invalid(row, "record", "invalid source row number.")
        row = record.row_number or row
        values = {}
        for field, limit in (("product_id", 160), ("offer_id", 160), ("product_name", 200),
                             ("brand", 120), ("category", 120), ("seller_name", 160)):
            values[field] = _text(getattr(record, field), row, field, limit, required=field != "brand")
        for field in ("product_id", "offer_id"):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", values[field]):
                _invalid(row, field, "use a stable source ID with letters, digits, dots, colons, underscores or hyphens.")
        if record.currency != "KZT":
            _invalid(row, "currency", "only KZT is supported; no currency conversion is performed.")
        values["currency"] = "KZT"
        for field in ("listed_price", "delivery_cost", "discount"):
            values[field] = _money(getattr(record, field), row, field, optional=field != "listed_price")
        if values["discount"] is not None and values["discount"] > values["listed_price"]:
            _invalid(row, "discount", "cannot exceed the listed price.")
        url = _text(record.source_url, row, "source_url", 200)
        try:
            URLValidator(schemes=["http", "https"])(url)
            parts = urlsplit(url)
            if parts.username or parts.password or parts.query or parts.fragment:
                raise ValueError
        except (ValidationError, ValueError):
            _invalid(row, "source_url", "use a public http(s) reference URL without credentials, query parameters or fragments.")
        values["source_url"] = url
        normalized = OfferRecord(**values, row_number=row)
        identity = (normalized.product_name, normalized.brand, normalized.category)
        if normalized.product_id in products and products[normalized.product_id] != identity:
            _invalid(row, "product_id", "conflicting product/variant metadata in this file.")
        products[normalized.product_id] = identity
        if normalized.offer_id in seen_offers:
            if seen_offers[normalized.offer_id] != normalized:
                _invalid(row, "offer_id", "conflicting rows use the same offer ID.")
            skipped += 1
            continue  # Identical repeated rows are safely collapsed.
        seen_offers[normalized.offer_id] = normalized
        result.append(normalized)
    return ValidatedRecords(result, skipped=skipped)


def validate_records(records):
    try:
        return _validate_records(records)
    except InvalidSourceData as error:
        # Entire batch is rejected, not just the first invalid row. No raw cells.
        error.rejected_count = len(records) + getattr(records, "skipped", 0) if isinstance(records, list) else None
        raise


class CSVOfferProvider:
    kind = "csv"

    def __init__(self, path):
        self.path = Path(path)

    def fetch(self):
        try:
            with self.path.open("rb") as stream:
                data = stream.read(MAX_BYTES + 1)
        except (OSError, ValueError):
            raise SourceUnavailable from None
        if len(data) > MAX_BYTES:
            raise InvalidSourceData("CSV exceeds the 2 MiB limit.")
        try:
            reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
            if reader.fieldnames is None or len(reader.fieldnames) != len(COLUMNS) or set(reader.fieldnames) != set(COLUMNS):
                raise InvalidSourceData("CSV headers must contain exactly: " + ", ".join(COLUMNS))
            records = []
            for row, cells in enumerate(reader, start=2):
                if row > MAX_ROWS + 1:
                    raise InvalidSourceData(f"CSV exceeds the {MAX_ROWS} row limit.")
                if None in cells or any(value is None for value in cells.values()):
                    _invalid(row, "columns", "wrong number of cells.")
                values = {field: value.strip() for field, value in cells.items()}
                records.append(OfferRecord(**values, row_number=row))
        except (UnicodeDecodeError, csv.Error):
            raise InvalidSourceData("Use a valid UTF-8, comma-separated CSV file (quoted fields are supported).") from None
        return validate_records(records)


class KaspiPendingProvider:
    """An explicit access gate, not an implemented marketplace integration."""

    kind = "kaspi"

    def fetch(self):
        raise SourceBlocked()


SUPPORTED_PROVIDER_KINDS = frozenset({"csv", "kaspi"})


def provider_for(source):
    """No arbitrary URLs, file paths, credentials or importable classes from UI."""
    if source.provider == "kaspi":
        return KaspiPendingProvider()
    raise InvalidSourceData("This source has no automated provider. CSV remains an explicit fallback command.")
