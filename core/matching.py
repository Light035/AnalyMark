"""Manual association review only. No identity inference or record merging."""
from .models import Offer


def reset_reviews(offers, reason="Product or offer identity changed; manual review is required again."):
    return offers.update(
        match_status=Offer.MatchStatus.UNREVIEWED,
        match_notes=reason,
        match_reviewed_at=None, match_reviewed_by=None,
    )
