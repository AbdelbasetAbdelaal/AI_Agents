from .models import FlightOffer


def rank_offers(offers: list[FlightOffer]) -> list[FlightOffer]:
    """Sort real provider offers by total price, then duration, then stops."""
    return sorted(
        offers,
        key=lambda offer: (offer.price, offer.duration_minutes, offer.stops),
    )
