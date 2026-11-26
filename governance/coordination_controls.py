
"""MeetFlow AI - Chapter 6 human approval controls.
Owner: Member 4
"""

from copy import deepcopy
from datetime import datetime, timezone

from features.coordination_validation import (
    validate_booking
)

from features.coordination import PROTOCOL


def record_human_action(result, action, notes=""):
    """Record a human decision for the audit trail."""

    result.setdefault("human_actions", [])

    result["human_actions"].append({
        "action": action,
        "actor": "human_reviewer",
        "booking_id": result["proposal"]["booking_id"],
        "notes": notes,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "resulting_status": result["status"]
    })


def revalidate_proposal(result):
    """Check current data before authorizing a proposal."""

    current_validation = validate_booking(
        result["proposal"]
    )

    if not current_validation["valid"]:
        raise ValueError(
            "Booking failed final validation: "
            + "; ".join(current_validation["errors"])
        )

    # Detect changes to the evidence reviewed
    # during the original coordination run.

    if current_validation != result["validation"]:
        raise ValueError(
            "Booking evidence has changed. "
            "Run coordination again."
        )

    return current_validation


def verify_agent_protocol(result):
    """Ensure all required agent exchanges completed."""

    messages = result["messages"]

    actual_protocol = [
        (message["agent"], message["recipient"])
        for message in messages
    ]

    if actual_protocol != PROTOCOL:
        raise ValueError(
            "Agent communication protocol is incomplete."
        )

    if any(
        message["decision"] not in {
            "support", "review", "block"
        }
        for message in messages
    ):
        raise ValueError("Invalid agent decision.")

    if any(
        message["decision"] == "block"
        for message in messages
    ):
        raise ValueError(
            "Blocking agent objections cannot be overridden."
        )

    if result["step_count"] != len(PROTOCOL):
        raise ValueError("Invalid execution step count.")

    if result["step_count"] > result["max_steps"]:
        raise ValueError("Agent execution limit exceeded.")


def apply_human_decision(
    coordination,
    action,
    *,
    acknowledged=False,
    notes=""
):
    """Apply an explicit human decision.

    This function authorizes or rejects a proposal.
    It does not execute a booking or write bookings.json.
    """

    result = deepcopy(coordination)

    result.setdefault(
        "coordination_status",
        result["status"]
    )

    result.setdefault("human_actions", [])

    status = result["status"]

    notes = notes.strip()

    # Prevent repeated decisions on completed reviews.

    if status in {"approved", "rejected"}:
        raise ValueError(
            "A final human decision already exists."
        )

    if result.get("booking_executed"):
        raise ValueError(
            "Booking has already been executed."
        )

    # ==========================================
    # ACTION 1: RESOLVE OUTSTANDING REVIEW
    # ==========================================

    if action == "resolve_review":

        if status != "needs_review":
            raise ValueError(
                "Only proposals requiring review "
                "can use this action."
            )

        if acknowledged is not True:
            raise ValueError(
                "Human acknowledgement is required."
            )

        if not notes:
            raise ValueError(
                "Document how all outstanding "
                "concerns were addressed."
            )

        verify_agent_protocol(result)
        revalidate_proposal(result)

        result["review_resolved"] = True
        result["review_notes"] = notes
        result["status"] = "pending_approval"
        result["can_approve"] = True
        result["human_approved"] = False

        result["reason"] = (
            "Human reviewer documented resolution "
            "of outstanding concerns. "
            "Final approval remains required."
        )

        record_human_action(
            result,
            action,
            notes
        )

    # ==========================================
    # ACTION 2: APPROVE
    # ==========================================

    elif action == "approve":

        if status != "pending_approval":
            raise ValueError(
                "Only eligible pending proposals "
                "can be approved."
            )

        if result.get("can_approve") is not True:
            raise ValueError(
                "Proposal is not eligible for approval."
            )

        if acknowledged is not True:
            raise ValueError(
                "Explicit human approval is required."
            )

        verify_agent_protocol(result)

        unresolved_review = (
            any(
                message["decision"] == "review"
                for message in result["messages"]
            )
            or result["validation"]["warnings"]
        )

        if unresolved_review and not (
            result.get("review_resolved") is True
            and result.get("review_notes")
            and any(
                item["action"] == "resolve_review"
                for item in result["human_actions"]
            )
        ):
            raise ValueError(
                "Outstanding review concerns "
                "have not been resolved."
            )

        revalidate_proposal(result)

        result["status"] = "approved"
        result["proposal"]["status"] = "approved"
        result["human_approved"] = True
        result["can_approve"] = False
        result["booking_executed"] = False

        result["reason"] = (
            "Human approved the proposal. "
            "Awaiting authorized mock booking handoff."
        )

        record_human_action(
            result,
            action,
            notes
        )

    # ==========================================
    # ACTION 3: REJECT
    # ==========================================

    elif action == "reject":

        if status not in {
            "pending_approval",
            "needs_review"
        }:
            raise ValueError(
                "This proposal cannot be rejected "
                "through the approval queue."
            )

        if acknowledged is not True:
            raise ValueError(
                "Explicit human rejection is required."
            )

        result["status"] = "rejected"
        result["proposal"]["status"] = "rejected"
        result["human_approved"] = False
        result["can_approve"] = False
        result["booking_executed"] = False

        result["reason"] = (
            "Human rejected the proposal."
        )

        record_human_action(
            result,
            action,
            notes
        )

    else:
        raise ValueError(
            f"Unknown human action: {action}"
        )

    return result
