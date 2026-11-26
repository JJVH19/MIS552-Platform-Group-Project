
"""MeetFlow AI - Chapter 6 booking validation.
Owner: Member 4
"""

import json
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from contracts import BookingProposal

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_records(filename):
    """Read the existing synthetic marketplace data."""
    with open(DATA_DIR / filename, encoding="utf-8") as file:
        return json.load(file)


def validate_booking(proposal):
    """Evaluate a proposal without modifying booking records."""

    errors = []
    warnings = []

    result = {
        "valid": False,
        "errors": errors,
        "warnings": warnings,
        "event": None,
        "facility": None,
        "matching_slots": [],
        "estimated_cost": None
    }

    # 1. Validate the shared booking contract
    required_fields = set(BookingProposal.__annotations__)

    if not isinstance(proposal, dict):
        errors.append("Proposal must be a dictionary.")
        return result

    missing_fields = required_fields - set(proposal)

    if missing_fields:
        errors.append(
            f"Missing fields: {sorted(missing_fields)}"
        )
        return result

    if any(
        not isinstance(proposal[field], str)
        or not proposal[field].strip()
        for field in required_fields
    ):
        errors.append("Required fields must be non-empty strings.")
        return result

    if proposal["status"] != "pending_approval":
        errors.append("Proposal must be pending human approval.")

    # 2. Validate date and time
    try:
        start = datetime.strptime(
            proposal["date"] + " " + proposal["start_time"],
            "%Y-%m-%d %H:%M"
        )

        end = datetime.strptime(
            proposal["date"] + " " + proposal["end_time"],
            "%Y-%m-%d %H:%M"
        )

        if start.strftime("%Y-%m-%d") != proposal["date"]:
            raise ValueError("Invalid date format.")

        if start.strftime("%H:%M") != proposal["start_time"] or \
           end.strftime("%H:%M") != proposal["end_time"]:
            raise ValueError("Invalid time format.")

        if end <= start:
            errors.append("End time must be after start time.")

    except ValueError:
        errors.append("Invalid date or time format.")
        return result

    # 3. Load the current marketplace records
    events = load_records("events.json")
    facilities = load_records("facilities.json")
    availability = load_records("availability.json")
    bookings = load_records("bookings.json")

    # 4. Validate the event
    event = next(
        (
            record for record in events
            if record["event_id"] == proposal["event_id"]
        ),
        None
    )

    result["event"] = event

    if event is None:
        errors.append("Event does not exist.")

    # 5. Validate the facility
    facility = next(
        (
            record for record in facilities
            if record["venue_id"] == proposal["venue_id"]
        ),
        None
    )

    result["facility"] = facility

    if facility is None:
        errors.append("Facility does not exist.")

    elif facility["status"] != "active":
        errors.append("Facility is not active.")

    # 6. Identify changes to the original event
    if event:
        for field in [
            "venue_id", "date", "start_time", "end_time"
        ]:
            if event[field] != proposal[field]:
                warnings.append(
                    f"Proposed {field} differs from the event record."
                )

    # 7. Verify court availability
    matching_slots = [
        slot for slot in availability
        if slot["venue_id"] == proposal["venue_id"]
        and slot["date"] == proposal["date"]
        and slot["start_time"] <= proposal["start_time"]
        and slot["end_time"] >= proposal["end_time"]
        and slot["available"] is True
    ]

    result["matching_slots"] = matching_slots

    if not matching_slots:
        errors.append(
            "No available slot covers the requested time."
        )

    # 8. Detect duplicate and conflicting bookings
    for booking in bookings:

        if booking["booking_id"] == proposal["booking_id"]:
            errors.append("Booking ID already exists.")

        if booking.get("status") not in [
            "approved", "confirmed"
        ]:
            continue

        same_venue = (
            booking["venue_id"] == proposal["venue_id"]
        )

        same_date = (
            booking["date"] == proposal["date"]
        )

        overlaps = (
            proposal["start_time"] < booking["end_time"]
            and proposal["end_time"] > booking["start_time"]
        )

        if same_venue and same_date and overlaps:
            errors.append(
                f"Potential booking conflict: "
                f"{booking['booking_id']}"
            )

    # 9. Calculate estimated facility cost
    if facility and end > start:

        duration_hours = (
            end - start
        ).total_seconds() / 3600

        result["estimated_cost"] = round(
            duration_hours * facility["hourly_rate"],
            2
        )

    # 10. Return the validation decision
    result["valid"] = len(errors) == 0

    return result


def initialize_shared_state(proposal):
    """Create a shared workspace for the three agents."""

    validation = validate_booking(proposal)

    return {
        "proposal": deepcopy(proposal),
        "validation": validation,
        "messages": [],
        "agent_decisions": {},
        "step_count": 0,
        "max_steps": 6,
        "approval_required": True,
        "human_approved": False,
        "status": "pending_coordination"
    }
