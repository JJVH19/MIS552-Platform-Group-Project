
"""MeetFlow AI - Chapter 6 multi-agent coordination.
Owner: Member 4
"""

from copy import deepcopy

from features.coordination_validation import (
    initialize_shared_state
)

from features.coordination_agents import run_agent


# Bounded communication protocol
# The Athlete Advisor receives a final opportunity
# to respond to the Facility Coordinator.

PROTOCOL = [
    ("Athlete Advisor", "Event Planner"),
    ("Event Planner", "Facility Coordinator"),
    ("Facility Coordinator", "Athlete Advisor"),
    ("Athlete Advisor", "Coordination Controller")
]


def finalize_coordination(state):
    """Apply deterministic decision and safety rules."""

    validation = state["validation"]
    messages = state["messages"]

    decisions = [
        message["decision"]
        for message in messages
    ]

    # Rule 1: Deterministic validation takes priority.
    if not validation["valid"]:

        status = "blocked"

        reason = (
            "Booking failed marketplace validation."
        )

    # Rule 2: An incomplete run cannot receive approval.
    elif len(messages) != len(PROTOCOL):

        status = "execution_failed"

        reason = (
            "The required agent protocol "
            "did not complete."
        )

    # Rule 3: Respect unresolved agent objections.
    elif "block" in decisions:

        status = "blocked"

        reason = (
            "At least one agent raised "
            "a blocking objection."
        )

    # Rule 4: Uncertainty requires further review.
    elif (
        "review" in decisions
        or validation["warnings"]
    ):

        status = "needs_review"

        reason = (
            "Outstanding concerns require "
            "human review or proposal revision."
        )

    # Rule 5: Consensus permits human approval,
    # but never automatically confirms a booking.
    elif all(
        decision == "support"
        for decision in decisions
    ):

        status = "pending_approval"

        reason = (
            "All agents support the proposal. "
            "Explicit human approval is required."
        )

    else:

        status = "execution_failed"

        reason = "Unexpected decision state."

    return {
        "messages": deepcopy(messages),
        "proposal": deepcopy(state["proposal"]),
        "approval_required": True,
        "status": status,
        "reason": reason,
        "validation": deepcopy(validation),
        "step_count": state["step_count"],
        "max_steps": state["max_steps"],
        "human_approved": False,
        "can_approve": status == "pending_approval",
        "booking_executed": False
    }


def coordinate_booking(proposal: dict, *, client=None) -> dict:
    """Coordinate a proposed court booking safely."""

    state = initialize_shared_state(proposal)

    # Stop invalid proposals before any paid LLM call.
    if not state["validation"]["valid"]:
        return finalize_coordination(state)

    # Ensure the protocol respects the hard cap.
    if len(PROTOCOL) > state["max_steps"]:
        raise RuntimeError(
            "Protocol exceeds maximum allowed steps."
        )

    # Run the agents over shared state.
    for role, recipient in PROTOCOL:

        try:

            message = run_agent(
                role=role,
                shared_state=state,
                client=client
            )

            # The controller assigns message routing.
            message["recipient"] = recipient

        except Exception as exc:

            # Fail closed without exposing credentials
            # or private connection details.
            result = finalize_coordination(state)

            result["status"] = "execution_failed"
            result["can_approve"] = False

            result["reason"] = (
                "Agent execution failed: "
                + type(exc).__name__
            )

            return result

    # Produce the final recommendation.
    # No booking records are modified here.
    return finalize_coordination(state)
