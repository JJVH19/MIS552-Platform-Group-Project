
"""MeetFlow AI — Shared Streamlit Application.

Person 1: Platform integration and Event Discovery
Person 2: Event Creator and Event Reviewer
Person 3: Booking Assistant (pending integration)
Person 4: Multi-Agent Event Coordination

Academic prototype using synthetic data and mock bookings only.
"""

import json
from pathlib import Path

import streamlit as st

from features.retrieval import search
from features.coordination_ui import render_coordination


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
WORKFLOW_PATH = BASE_DIR / "demo" / "event_workflow.json"

st.set_page_config(
    page_title="MeetFlow AI",
    page_icon="🏀",
    layout="wide",
)


# --------------------------------------------------
# Person 2: Event Creator / Reviewer Helpers
# --------------------------------------------------

def load_workflow():
    """Load recorded event generation and review examples."""
    with WORKFLOW_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def load_generated_events():
    """Return generated event drafts from cached examples."""
    workflow = load_workflow()

    generated_events = [workflow["generated_draft"]]

    generated_events.extend(
        case["generated_draft"]
        for case in workflow.get("additional_cases", {}).values()
        if "generated_draft" in case
    )

    return generated_events


def display_generated_event(event):
    """Render an event as readable Streamlit content."""

    st.markdown(
        f"### {event.get('name', 'Untitled Event')}"
    )

    date_col, time_col, city_col = st.columns(3)

    date_col.metric(
        "Date",
        event.get("date", "Not provided"),
    )

    time_col.metric(
        "Time",
        (
            f"{event.get('start_time', 'TBD')} – "
            f"{event.get('end_time', 'TBD')}"
        ),
    )

    city_col.metric(
        "City",
        event.get("city", "Not provided"),
    )

    format_col, skill_col, players_col, venue_col = st.columns(4)

    format_col.metric(
        "Format",
        event.get("format", "Not provided"),
    )

    skill_col.metric(
        "Skill level",
        event.get("skill_level", "Not provided"),
    )

    players_col.metric(
        "Players",
        event.get("players", "Not provided"),
    )

    venue_col.metric(
        "Venue",
        event.get("venue_id", "Not provided"),
    )

    st.markdown("#### Description")
    st.write(
        event.get(
            "description",
            "No description generated.",
        )
    )

    st.markdown("#### Rules")

    rules = event.get("rules", [])

    if rules:
        for rule in rules:
            st.markdown(f"- {rule}")
    else:
        st.info("No rules provided.")

    st.markdown("#### Promotional text")

    st.info(
        event.get(
            "promotional_text",
            "No promotional text generated.",
        )
    )


def load_event_reviews():
    """Load recorded Event Reviewer examples."""
    workflow = load_workflow()

    return list(
        workflow.get("review_cases", {}).values()
    )


def display_event_review(review_case):
    """Render a reviewed event and its assessment."""

    reviewed_event = review_case.get(
        "reviewed_listing", {}
    )

    review_result = review_case.get(
        "review_result", {}
    )

    display_generated_event(reviewed_event)

    st.divider()
    st.markdown("### Review result")

    verdict = review_result.get(
        "verdict", "unknown"
    )

    if verdict == "pass":
        st.success("Verdict: Pass")

    elif verdict == "needs_revision":
        st.warning("Verdict: Needs revision")

    else:
        st.info(
            f"Verdict: {verdict.replace('_', ' ').title()}"
        )

    issues = review_result.get("issues", [])

    if not issues:
        st.write("No issues found.")
        return

    st.markdown("#### Issues identified")

    for issue_number, issue in enumerate(
        issues, start=1
    ):
        category = (
            issue.get("category", "Uncategorized")
            .replace("_", " ")
            .title()
        )

        with st.container(border=True):
            st.markdown(
                f"**Issue {issue_number}: {category}**"
            )

            st.write(
                "Evidence:",
                issue.get("evidence", "Not provided"),
            )

            st.write(
                "Suggested correction:",
                issue.get("suggestion", "Not provided"),
            )


# --------------------------------------------------
# Main Application
# --------------------------------------------------

st.title("🏀 MeetFlow AI")

st.caption(
    "AI-powered basketball event and facility platform "
    "• Synthetic data • Mock bookings only"
)

tabs = st.tabs(
    [
        "Event Creator",
        "Event Reviewer",
        "Event Discovery",
        "Booking Assistant",
        "Event Coordination",
    ]
)


# --------------------------------------------------
# Tab 1: Event Creator (Person 2)
# --------------------------------------------------

with tabs[0]:

    st.subheader("Event Creator — Chapter 2")

    st.write(
        "Explore basketball tournament listings generated "
        "using the AI Event Creator."
    )

    st.caption(
        "Cached demonstration: previously generated "
        "event examples."
    )

    try:
        generated_events = load_generated_events()

        if not generated_events:
            st.info("No generated events available.")

        else:
            selected_index = st.selectbox(
                "Select a generated event",
                options=range(len(generated_events)),
                format_func=lambda index: (
                    generated_events[index].get(
                        "name", "Untitled Event"
                    )
                ),
                key="creator_event_select",
            )

            selected_event = generated_events[
                selected_index
            ]

            display_generated_event(selected_event)

    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(
            f"Unable to load generated events: {error}"
        )


# --------------------------------------------------
# Tab 2: Event Reviewer (Person 2)
# --------------------------------------------------

with tabs[1]:

    st.subheader("Event Reviewer — Chapter 3")

    st.write(
        "Inspect AI reviews of basketball events for "
        "missing information, contradictory rules, "
        "and safety concerns."
    )

    st.caption(
        "Cached demonstration: saved review results."
    )

    try:
        event_reviews = load_event_reviews()

        if not event_reviews:
            st.info("No event reviews available.")

        else:
            review_labels = []

            for review in event_reviews:

                event_name = review.get(
                    "reviewed_listing", {}
                ).get(
                    "name", "Untitled Event"
                )

                review_result = review.get(
                    "review_result", {}
                )

                verdict = review_result.get(
                    "verdict", "unknown"
                ).replace("_", " ").title()

                issues = review_result.get(
                    "issues", []
                )

                category = (
                    issues[0].get("category", "")
                    .replace("_", " ")
                    .title()
                    if issues
                    else "No issues"
                )

                review_labels.append(
                    f"{event_name} — {verdict} ({category})"
                )

            selected_review_index = st.selectbox(
                "Select a reviewed event",
                options=range(len(event_reviews)),
                format_func=lambda index: (
                    review_labels[index]
                ),
                key="reviewer_event_select",
            )

            display_event_review(
                event_reviews[selected_review_index]
            )

    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(
            f"Unable to load event reviews: {error}"
        )


# --------------------------------------------------
# Tab 3: Event Discovery (Person 1)
# --------------------------------------------------

with tabs[2]:

    st.subheader("Event Discovery — Chapter 4")

    st.write(
        "Discover synthetic basketball courts and "
        "events using keyword, semantic, or hybrid retrieval."
    )

    kind = st.radio(
        "Search category",
        ["courts", "events"],
        horizontal=True,
        key="discovery_kind",
    )

    query = st.text_input(
        "Describe what you need",
        value="indoor competitive basketball court in Tempe",
        key="discovery_query",
    )

    col_method, col_results = st.columns(2)

    with col_method:
        method = st.selectbox(
            "Retrieval method",
            ["hybrid", "keyword", "semantic"],
            key="discovery_method",
        )

    with col_results:
        k = st.slider(
            "Number of results",
            min_value=1,
            max_value=10,
            value=5,
            key="discovery_k",
        )

    if query.strip():

        try:
            with st.spinner(
                "Ranking synthetic listings..."
            ):
                output = search(
                    query,
                    kind,
                    method,
                    k,
                )

            st.caption(
                "Retrieval engine: "
                + str(output.get("mode", method))
            )

            if output.get("warning"):
                st.warning(output["warning"])

            results = output.get("results", [])

            if not results:
                st.info(
                    "No matching listings found. "
                    "Try a different search."
                )

            for item in results:

                with st.container(border=True):

                    st.markdown(
                        "**"
                        + str(item.get("name", "Unnamed"))
                        + "**"
                    )

                    listing_id = item.get(
                        "venue_id",
                        item.get("event_id", ""),
                    )

                    st.caption(
                        f"ID: {listing_id} | "
                        f"City: {item.get('city', 'Unknown')} | "
                        f"Score: {item.get('score', 'N/A')}"
                    )

                    st.write(
                        item.get("description", "")
                    )

                    st.caption(
                        "Why matched: "
                        + str(
                            item.get(
                                "why_match",
                                "No explanation available",
                            )
                        )
                    )

        except (ValueError, OSError, KeyError) as error:
            st.error(
                f"Event Discovery failed: {error}"
            )

    else:
        st.info(
            "Enter a search query to discover listings."
        )


# --------------------------------------------------
# Tab 4: Booking Assistant (Person 3)
# --------------------------------------------------

with tabs[3]:

    st.subheader("Booking Assistant — Chapter 5")

    st.info(
        "Person 3's Booking Assistant is awaiting "
        "integration. This feature will generate "
        "booking proposals using tools, an agent trace, "
        "and human approval controls."
    )

    st.caption(
        "The booking proposal will eventually connect "
        "directly to the Event Coordination workflow."
    )


# --------------------------------------------------
# Tab 5: Event Coordination (Person 4)
# --------------------------------------------------

with tabs[4]:

    # Person 4's complete interface.
    # Supports cached recorded LLM runs and live execution.
    # Human approval is required for booking authorization.
    #
    # When Person 3's Booking Assistant is ready,
    # this can become:
    #
    # render_coordination(proposal=booking_proposal)

    render_coordination()


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()

st.caption(
    "MeetFlow AI | MIS 552 Group Project | "
    "Persons 1, 2, and 4 integrated | "
    "Person 3 pending | "
    "Synthetic marketplace — no real reservations"
)
