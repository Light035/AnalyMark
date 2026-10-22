"""Display coordinates for stored observations; no generated or interpolated prices."""
from decimal import Decimal


SERIES_COLORS = ("#087b68", "#6850a1", "#a14d18", "#245e9c", "#913d68", "#556327")


def observation_chart(observations):
    ordered = sorted(observations, key=lambda observation: (observation.observed_at, observation.pk))
    if not ordered:
        return None
    first_at, last_at = ordered[0].observed_at, ordered[-1].observed_at
    minimum = min(observation.price for observation in ordered)
    maximum = max(observation.price for observation in ordered)
    time_span = (last_at - first_at).total_seconds()
    price_span = maximum - minimum
    series = {}
    points = []
    for observation in ordered:
        if observation.offer_id not in series:
            series[observation.offer_id] = {
                "offer": observation.offer,
                "color": SERIES_COLORS[len(series) % len(SERIES_COLORS)],
            }
        # Coordinates are scaled; the underlying recorded times and prices are unchanged.
        x = 416 if not time_span else 112 + 608 * (observation.observed_at - first_at).total_seconds() / time_span
        y = Decimal("122") if not price_span else Decimal("24") + Decimal("196") * (maximum - observation.price) / price_span
        points.append({"observation": observation, "x": f"{x:.2f}", "y": f"{y:.2f}", "color": series[observation.offer_id]["color"]})
    return {
        "points": points, "series": list(series.values()),
        "minimum": minimum, "maximum": maximum,
        "first_at": first_at, "last_at": last_at,
        "single_time": not time_span, "single_price": not price_span,
    }
