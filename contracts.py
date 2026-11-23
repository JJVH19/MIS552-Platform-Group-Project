"""Shared contracts. Coordinate schema changes with every teammate."""
from typing import TypedDict, Literal

class BookingProposal(TypedDict):
    booking_id: str
    event_id: str
    venue_id: str
    date: str                    # YYYY-MM-DD
    start_time: str              # 24h HH:MM
    end_time: str                # 24h HH:MM
    status: Literal["pending_approval", "approved", "rejected"]

# Agreed integration entrypoints (implemented by assigned teammates):
# Person 2: generate_event(event_details: dict) -> dict
#           review_event(event: dict) -> dict
# Person 1: search_courts(query: str, method="hybrid", k=5) -> list[dict]
#           search_events(query: str, method="hybrid", k=5) -> list[dict]
# Person 3: propose_booking(request: dict) -> dict
# Person 4: coordinate_booking(proposal: dict) -> dict
# IMPORTANT: Return contracts for agent traces and errors should be finalized in docs/TEAM_CONTRACTS.md.
