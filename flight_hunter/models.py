from datetime import date
from pydantic import BaseModel, Field, model_validator


class FlightSearchRequest(BaseModel):
    origin: str = Field(min_length=3, max_length=3, description="IATA airport code")
    destination: str = Field(min_length=3, max_length=3, description="IATA airport code")
    departure_date: date
    return_date: date | None = None
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=8)
    cabin_class: str = "ECONOMY"
    currency: str = "EGP"

    @model_validator(mode="after")
    def validate_route_and_dates(self):
        if self.origin.upper() == self.destination.upper():
            raise ValueError("Origin and destination must be different")
        if self.return_date and self.return_date < self.departure_date:
            raise ValueError("Return date cannot be before departure date")
        return self


class FlightOffer(BaseModel):
    provider: str
    airline: str
    origin: str
    destination: str
    departure_at: str
    arrival_at: str
    price: float = Field(gt=0)
    currency: str = "EGP"
    stops: int = Field(ge=0)
    duration_minutes: int = Field(gt=0)
    booking_url: str | None = None
    baggage_summary: str | None = None
    offer_id: str | None = None
    itinerary_details: list[dict] = Field(default_factory=list)
