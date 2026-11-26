
"""MeetFlow AI - Chapter 6 Streamlit interface.
Owner: Member 4
"""

import json
from copy import deepcopy

import streamlit as st

from features.coordination_cache import (
    coordinate_booking_mode,
    get_cached_proposal
)

from governance.coordination_controls import (
    apply_human_decision
)


STATUS_LABELS = {
    "blocked": "Blocked",
    "needs_review": "Needs human review",
    "pending_approval": "Pending human approval",
    "approved": "Human approved",
    "rejected": "Rejected",
    "execution_failed": "Execution failed"
}


def render_coordination(proposal=None, mode=None):
    """Render Chapter 6 inside the shared Streamlit app.

    proposal:
        Booking proposal supplied by Member 3.

    mode:
        Optional shared application execution mode.
    """

    st.subheader("Multi-Agent Event Coordination")

    st.caption(
        "Chapter 6 • Athlete Advisor • Event Planner "
        "• Facility Coordinator"
    )

    st.info(
        "Academic simulation using synthetic data. "
        "No real reservations or payments are processed."
    )

    # ==========================================
    # EXECUTION MODE
    # ==========================================

    if mode is None:

        mode = st.radio(
            "Execution mode",
            ["cached", "live"],
            horizontal=True,
            format_func=lambda value: value.title(),
            key="m4_mode"
        )

    mode = mode.lower()

    if mode not in {"cached", "live"}:
        st.error("Unsupported execution mode.")
        return

    if mode == "cached":

        st.caption(
            "Replays genuine recorded model responses. "
            "No API key is required."
        )

    else:

        st.caption(
            "Generates new responses from "
            "three LLM agents."
        )

    # ==========================================
    # BOOKING PROPOSAL SOURCE
    # ==========================================

    sources = ["Recorded demo proposal"]

    if proposal is not None:

        sources.insert(
            0,
            "Chapter 5 Booking Assistant"
        )

    source = st.selectbox(
        "Booking proposal source",
        sources,
        key="m4_source"
    )

    try:

        if source == "Chapter 5 Booking Assistant":

            active_proposal = deepcopy(proposal)

        else:

            active_proposal = get_cached_proposal()

    except Exception as error:

        st.error(
            "Unable to load booking proposal: "
            + type(error).__name__
        )

        return

    # Clear stale results if the proposal or mode changes.

    signature = json.dumps(
        {
            "mode": mode,
            "proposal": active_proposal,
            "source": source
        },
        sort_keys=True
    )

    if st.session_state.get(
        "m4_signature"
    ) != signature:

        st.session_state["m4_signature"] = signature

        st.session_state.pop("m4_result", None)

        for key in [
            "m4_review_notes",
            "m4_review_ack",
            "m4_approval_ack"
        ]:
            st.session_state.pop(key, None)

    st.markdown("### Booking proposal")

    st.caption("Source: " + source)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Booking ID",
        active_proposal.get("booking_id", "Unknown")
    )

    col2.metric(
        "Event ID",
        active_proposal.get("event_id", "Unknown")
    )

    col3.metric(
        "Facility ID",
        active_proposal.get("venue_id", "Unknown")
    )

    st.write(
        "Date:",
        active_proposal.get("date")
    )

    st.write(
        "Requested time:",
        active_proposal.get("start_time"),
        "to",
        active_proposal.get("end_time"),
        "(Arizona local time)"
    )

    # ==========================================
    # USER-INITIATED AGENT EXECUTION
    # ==========================================

    if st.button(
        "Run Event Coordination",
        type="primary",
        key="m4_run"
    ):

        st.session_state.pop("m4_result", None)

        for key in [
            "m4_review_notes",
            "m4_review_ack",
            "m4_approval_ack"
        ]:
            st.session_state.pop(key, None)

        try:

            with st.spinner(
                "Coordinating stakeholder agents..."
            ):

                result = coordinate_booking_mode(
                    active_proposal,
                    mode=mode
                )

            st.session_state["m4_result"] = result

        except (ValueError, FileNotFoundError) as error:

            st.error(str(error))

        except Exception as error:

            st.error(
                "Coordination could not complete: "
                + type(error).__name__
            )

    result = st.session_state.get("m4_result")

    if result is None:

        st.caption(
            "Run coordination to view the agent decisions."
        )

        return

    # ==========================================
    # COORDINATION MONITOR
    # ==========================================

    st.divider()

    st.markdown("### Coordination monitor")

    validation = result["validation"]

    event = validation.get("event") or {}

    facility = validation.get("facility") or {}

    st.write(
        "**Event:**",
        event.get("name", "Unknown")
    )

    st.write(
        "**Facility:**",
        facility.get("name", "Unknown")
    )

    cost = validation.get("estimated_cost")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Agent steps",
        f"{result['step_count']}/{result['max_steps']}"
    )

    col2.metric(
        "Estimated rental",
        f"${cost:,.2f}" if cost is not None else "N/A"
    )

    col3.metric(
        "API calls this run"
        if mode == "cached"
        else "LLM responses",
        0 if mode == "cached"
        else len(result["messages"])
    )

    if mode == "cached":

        st.caption(
            "Recorded live execution: "
            + result.get("recorded_at", "Unknown")
        )

        st.caption(
            "Cache source: "
            + result.get("cache_source", "Unknown")
        )

    if validation["valid"]:

        st.success(
            "Marketplace validation passed."
        )

    else:

        st.error(
            "Marketplace validation failed."
        )

    for error in validation["errors"]:

        st.error(error)

    for warning in validation["warnings"]:

        st.warning(warning)

    if validation["matching_slots"]:

        st.markdown("**Verified availability evidence**")

        st.dataframe(
            validation["matching_slots"],
            hide_index=True
        )

    # ==========================================
    # MULTI-AGENT COMMUNICATION TIMELINE
    # ==========================================

    st.markdown("### Agent communication timeline")

    if not result["messages"]:

        st.caption(
            "No agent messages were generated."
        )

    for message in result["messages"]:

        with st.container(border=True):

            st.markdown(
                f"**Step {message['step']}: "
                f"{message['agent']}**"
            )

            st.caption(
                f"Recipient: {message['recipient']} | "
                f"Previous messages received: "
                f"{message['previous_messages_received']}"
            )

            decision = message["decision"]

            if decision == "support":

                st.success("SUPPORT")

            elif decision == "review":

                st.warning("REVIEW")

            else:

                st.error("BLOCK")

            st.write(message["message"])

            with st.expander(
                "Supporting evidence and concerns",
                expanded=True
            ):

                st.markdown("**Evidence**")

                for item in message["evidence"]:

                    st.write("-", item)

                st.markdown("**Concerns**")

                if message["concerns"]:

                    for item in message["concerns"]:

                        st.write("-", item)

                else:

                    st.caption("None reported.")

            st.caption(
                "Model: "
                + str(message["model"])
                + (
                    " • Recorded live response"
                    if mode == "cached"
                    else " • Live response"
                )
            )

    # ==========================================
    # FINAL DECISION AND GOVERNANCE
    # ==========================================

    st.divider()

    st.markdown("### Final coordination decision")

    status = result["status"]

    label = STATUS_LABELS.get(
        status,
        status
    )

    if status == "approved":

        st.success(label)

    elif status in {
        "needs_review",
        "pending_approval"
    }:

        st.warning(label)

    else:

        st.error(label)

    st.write(result["reason"])

    st.markdown("### Human approval and safeguards")

    st.write(
        "Human authorization required: Yes"
    )

    st.write(
        "Human approved:",
        "Yes" if result["human_approved"] else "No"
    )

    st.write(
        "Booking executed:",
        "Yes" if result["booking_executed"] else "No"
    )

    # Prevent blocked or failed proposals from
    # entering the approval controls.

    if status in {"blocked", "execution_failed"}:

        st.error(
            "Approval disabled. "
            "Revise the proposal before retrying."
        )

    elif status in {"needs_review", "pending_approval"}:

        notes = ""

        if status == "needs_review":

            notes = st.text_area(
                "Document how outstanding concerns "
                "have been resolved",
                key="m4_review_notes"
            )

        acknowledgement = st.checkbox(
            (
                "I have verified and addressed "
                "all outstanding concerns."
                if status == "needs_review"
                else "I explicitly authorize "
                "this simulated booking proposal."
            ),
            key=(
                "m4_review_ack"
                if status == "needs_review"
                else "m4_approval_ack"
            )
        )

        col1, col2 = st.columns(2)

        action = None

        if status == "needs_review":

            if col1.button(
                "Resolve Review",
                disabled=(
                    not acknowledgement
                    or not notes.strip()
                ),
                key="m4_resolve"
            ):

                action = "resolve_review"

            st.button(
                "Approve Booking",
                disabled=True,
                key="m4_approve_disabled"
            )

        else:

            if col1.button(
                "Approve Booking",
                type="primary",
                disabled=not acknowledgement,
                key="m4_approve"
            ):

                action = "approve"

        if col2.button(
            "Reject Proposal",
            key="m4_reject"
        ):

            action = "reject"

        if action:

            try:

                st.session_state["m4_result"] = (
                    apply_human_decision(
                        result,
                        action,
                        acknowledged=(
                            True
                            if action == "reject"
                            else acknowledgement
                        ),
                        notes=notes
                    )
                )

                st.rerun()

            except ValueError as error:

                st.error(str(error))

    elif status == "approved":

        st.success(
            "Human authorization recorded. "
            "Ready for authorized mock-booking handoff. "
            "No reservation has been executed."
        )

    elif status == "rejected":

        st.info(
            "Review closed. No booking authorized."
        )

    # ==========================================
    # HUMAN DECISION AUDIT TRAIL
    # ==========================================

    if result.get("human_actions"):

        st.markdown("### Human decision audit trail")

        st.dataframe(
            result["human_actions"],
            hide_index=True
        )

    st.caption(
        "MeetFlow AI • Chapter 6 • "
        "Member 4 • Human-controlled autonomy"
    )

    return result
