"""Create and confirm fictional booking proposals without external side effects.

Confirmed bookings are returned to the caller and are not persisted. Approval of
an availability search is separate from approval of a booking proposal.
"""
from copy import deepcopy
from uuid import uuid4

from scheduling_agent import _find_facilities, _find_slots, create_plan


def _response(proposal, trace, status, error=None):
    return {"proposal": proposal, "trace": trace, "status": status, "error": error}


def _check_availability(proposal):
    facilities = _find_facilities("", proposal["venue_id"])
    if not facilities:
        return False
    slots = _find_slots([proposal["venue_id"]], proposal["date"],
                        proposal["start_time"], proposal["end_time"])
    return any(slot["slot_id"] == proposal["slot_id"] for slot in slots)


def propose_booking(request: dict) -> dict:
    """Validate a selected fictional slot and prepare a proposal for review."""
    trace = []
    try:
        if not isinstance(request, dict):
            raise ValueError("Request must be a dictionary.")
        for field in ("event_id", "slot_id", "venue_id", "date", "start_time", "end_time"):
            if not isinstance(request.get(field), str) or not request[field].strip():
                raise ValueError(f"{field} is required.")
        filters = create_plan(request)["filters"]
        proposal = {"booking_id": "BOOK-" + uuid4().hex.upper(),
                    "event_id": request["event_id"].strip(),
                    "slot_id": request["slot_id"].strip(),
                    "venue_id": filters["venue_id"], "date": filters["date"],
                    "start_time": filters["start_time"], "end_time": filters["end_time"],
                    "status": "pending_approval"}
        trace.append({"action": "validate_request", "result": "valid"})
        available = _check_availability(proposal)
        trace.append({"action": "check_availability", "slot_id": proposal["slot_id"],
                      "result": "available" if available else "unavailable"})
        if not available:
            raise ValueError("The selected fictional slot is not available for that time.")
        trace.append({"action": "request_human_approval", "result": "pending"})
        return _response(proposal, trace, "pending_approval")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        trace.append({"action": "error", "result": str(exc)})
        return _response(None, trace, "error", str(exc))


def confirm_booking(booking: dict, *, approved: bool = False) -> dict:
    """Confirm the reviewed proposal in memory only after explicit approval."""
    if approved is not True:
        raise PermissionError("Human approval of the booking proposal is required.")
    if not isinstance(booking, dict) or booking.get("status") != "pending_approval":
        raise ValueError("A pending booking proposal is required.")
    proposal = booking.get("proposal")
    if not isinstance(proposal, dict) or proposal.get("status") != "pending_approval":
        raise ValueError("A pending booking proposal is required.")
    # Revalidate the exact reviewed details and current mock availability.
    verified = propose_booking(proposal)
    trace = deepcopy(booking.get("trace", []))
    trace.append({"action": "human_approval", "result": "approved"})
    trace.extend(verified["trace"][:2])
    if verified["status"] != "pending_approval":
        trace.append({"action": "confirmation", "result": "not confirmed"})
        return _response(deepcopy(proposal), trace, "error", verified["error"])
    confirmed = deepcopy(proposal)
    confirmed["status"] = "approved"
    trace.append({"action": "confirm_mock_booking", "result": "approved in memory"})
    return _response(confirmed, trace, "approved")


def reject_booking(booking: dict) -> dict:
    """Reject a proposal without confirming it."""
    if not isinstance(booking, dict) or booking.get("status") != "pending_approval" or not isinstance(booking.get("proposal"), dict) or booking["proposal"].get("status") != "pending_approval":
        raise ValueError("A pending booking proposal is required.")
    proposal = deepcopy(booking["proposal"])
    proposal["status"] = "rejected"
    return _response(proposal, deepcopy(booking.get("trace", [])) +
                     [{"action": "human_approval", "result": "rejected"}], "rejected")
