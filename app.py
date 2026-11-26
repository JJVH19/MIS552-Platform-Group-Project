"""MeetFlow AI — Shared Streamlit application.

Person 1: Platform integration and Event Discovery
Person 2: Event Creator and Event Reviewer
Person 3: Booking Assistant
Person 4: Multi-Agent Event Coordination

Academic prototype with fictional marketplace data and mock-only bookings.
"""

import json
import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from booking_tools import confirm_booking, propose_booking, reject_booking
from features.coordination_ui import render_coordination
from features.coordination_validation import validate_booking
from features.retrieval import documents, search
from scheduling_agent import create_plan, execute_plan


BASE_DIR = Path(__file__).resolve().parent
WORKFLOW_PATH = BASE_DIR / "demo" / "event_workflow.json"

st.set_page_config(page_title="MeetFlow AI", page_icon="🏀", layout="wide")


# --------------------------------------------------
# Person 2: Event Creator and Reviewer helpers
# --------------------------------------------------

def load_workflow():
    """Load previously recorded event generation and review examples."""
    with WORKFLOW_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def load_generated_events():
    """Get generated event drafts from the cached workflow."""
    workflow = load_workflow()
    generated_events = [workflow["generated_draft"]]
    generated_events.extend(
        case["generated_draft"]
        for case in workflow.get("additional_cases", {}).values()
        if "generated_draft" in case
    )
    return generated_events


def display_generated_event(event):
    """Display an event listing without modifying it."""
    st.markdown(f"### {event.get('name', 'Untitled Event')}")

    date_col, time_col, city_col = st.columns(3)
    date_col.metric("Date", event.get("date", "Not provided"))
    time_col.metric(
        "Time",
        f"{event.get('start_time', 'TBD')} – {event.get('end_time', 'TBD')}",
    )
    city_col.metric("City", event.get("city", "Not provided"))

    format_col, skill_col, players_col, venue_col = st.columns(4)
    format_col.metric("Format", event.get("format", "Not provided"))
    skill_col.metric("Skill level", event.get("skill_level", "Not provided"))
    players_col.metric("Players", event.get("players", "Not provided"))
    venue_col.metric("Venue", event.get("venue_id", "Not provided"))

    st.markdown("#### Description")
    st.write(event.get("description", "No description generated."))

    st.markdown("#### Rules")
    rules = event.get("rules", [])
    if rules:
        for rule in rules:
            st.markdown(f"- {rule}")
    else:
        st.info("No rules provided.")

    st.markdown("#### Promotional text")
    st.info(event.get("promotional_text", "No promotional text generated."))


def load_event_reviews():
    """Get recorded Event Reviewer cases."""
    return list(load_workflow().get("review_cases", {}).values())


def display_event_review(review_case):
    """Show an event and the saved AI review outcome."""
    reviewed_event = review_case.get("reviewed_listing", {})
    review_result = review_case.get("review_result", {})
    display_generated_event(reviewed_event)

    st.divider()
    st.markdown("### Review result")
    verdict = review_result.get("verdict", "unknown")
    if verdict == "pass":
        st.success("Verdict: Pass")
    elif verdict == "needs_revision":
        st.warning("Verdict: Needs revision")
    else:
        st.info(f"Verdict: {verdict.replace('_', ' ').title()}")

    issues = review_result.get("issues", [])
    if not issues:
        st.write("No issues found.")
        return

    st.markdown("#### Issues identified")
    for number, issue in enumerate(issues, start=1):
        category = issue.get("category", "Uncategorized").replace("_", " ").title()
        with st.container(border=True):
            st.markdown(f"**Issue {number}: {category}**")
            st.write("Evidence:", issue.get("evidence", "Not provided"))
            st.write("Suggested correction:", issue.get("suggestion", "Not provided"))


def clear_booking_workflow():
    """Discard old booking steps and any stale coordination approval."""
    for key in (
        "scheduling_plan", "scheduling_result", "booking_result",
        "m4_result", "m4_signature",
    ):
        st.session_state.pop(key, None)


def coordination_matches_booking(coordination, proposal):
    """Require Chapter 6 approval for precisely the current Chapter 5 proposal.

    The coordination controls change proposal.status from pending_approval to
    approved. Other fields, including the generated booking ID, must match.
    """
    if not isinstance(coordination, dict) or not isinstance(proposal, dict):
        return False
    if (
        coordination.get("execution_mode") != "live"
        or coordination.get("status") != "approved"
        or coordination.get("human_approved") is not True
        or coordination.get("booking_executed") is not False
    ):
        return False

    reviewed = coordination.get("proposal")
    if not isinstance(reviewed, dict) or reviewed.get("status") != "approved":
        return False
    reviewed = {**reviewed, "status": "pending_approval"}
    return reviewed == proposal


# --------------------------------------------------
# Main application
# --------------------------------------------------

st.title("🏀 MeetFlow AI")
st.caption(
    "AI-powered basketball event and facility platform "
    "• Synthetic data • Mock bookings only"
)

tabs = st.tabs([
    "Event Creator", "Event Reviewer", "Event Discovery",
    "Booking Assistant", "Event Coordination",
])


# --------------------------------------------------
# Tab 1: Event Creator (Person 2)
# --------------------------------------------------

with tabs[0]:
    st.subheader("Event Creator — Chapter 2")
    st.write("Generate a fictional basketball tournament listing using an AI model, or view saved examples.")

    creator_mode = st.radio(
        "Event Creator mode",
        ["Cached examples", "Live generation"],
        horizontal=True,
        key="creator_mode",
    )

    if creator_mode == "Cached examples":
        st.caption("Previously recorded drafts. No API key or new model call is needed.")
        try:
            generated_events = load_generated_events()
            if not generated_events:
                st.info("No generated events available.")
            else:
                selected_index = st.selectbox(
                    "Select a generated event",
                    options=range(len(generated_events)),
                    format_func=lambda index: generated_events[index].get("name", "Untitled Event"),
                    key="creator_event_select",
                )
                display_generated_event(generated_events[selected_index])
        except (OSError, ValueError, KeyError, TypeError) as error:
            st.error(f"Unable to load generated events: {error}")

    else:
        st.info(
            "Live generation calls OpenAI only when you click Generate event. "
            "An OPENAI_API_KEY is required; model usage may incur charges. "
            "Drafts remain in this browser session and are not added to the booking database."
        )
        with st.form("live_event_generator"):
            name = st.text_input("Tournament name", value="Arizona Community Hoops")
            city = st.text_input("City", value="Tucson")
            venue_id = st.text_input("Fictional venue ID", value="VEN-005")
            event_date = st.date_input("Tournament date", value=date.today() + timedelta(days=7))
            col_start, col_end = st.columns(2)
            with col_start:
                start_time = st.text_input("Start time (HH:MM)", value="09:00")
            with col_end:
                end_time = st.text_input("End time (HH:MM)", value="12:00")
            col_format, col_skill = st.columns(2)
            with col_format:
                event_format = st.selectbox("Tournament format", ["3v3", "5v5", "pickup", "training"])
            with col_skill:
                skill_level = st.selectbox(
                    "Skill level", ["Beginner", "Intermediate", "Advanced", "Competitive", "Recreational"]
                )
            players = st.number_input("Number of players", min_value=1, max_value=500, value=12)
            generate_clicked = st.form_submit_button("Generate event with AI")

        if generate_clicked:
            try:
                parsed_start = datetime.strptime(start_time.strip(), "%H:%M")
                parsed_end = datetime.strptime(end_time.strip(), "%H:%M")
                if parsed_start.strftime("%H:%M") != start_time.strip() or parsed_end.strftime("%H:%M") != end_time.strip():
                    raise ValueError("Times must use HH:MM.")
                if parsed_end <= parsed_start:
                    raise ValueError("End time must be after start time.")
                if not name.strip() or not city.strip() or not venue_id.strip():
                    raise ValueError("Name, city, and venue ID are required.")

                details = {
                    "name": name.strip(),
                    "city": city.strip(),
                    "venue_id": venue_id.strip().upper(),
                    "date": event_date.isoformat(),
                    "start_time": start_time.strip(),
                    "end_time": end_time.strip(),
                    "format": event_format,
                    "skill_level": skill_level,
                    "players": int(players),
                }

                # Keep the API feature authored by Person 2; no new prompt or client here.
                from features.content_generator import generate_event

                with st.spinner("Generating tournament listing with AI..."):
                    generated = generate_event(details)
                st.session_state["live_generated_event"] = generated
                st.session_state.pop("live_event_review", None)
                st.success("Draft generated. Open Event Reviewer to assess it.")
            except ValueError as error:
                st.error(str(error))
            except Exception as error:
                st.error(
                    "Live generation was unsuccessful "
                    f"({type(error).__name__}). Check OPENAI_API_KEY and your connection."
                )

        if st.session_state.get("live_generated_event"):
            st.caption("Most recently generated live draft (not saved to events.json)")
            display_generated_event(st.session_state["live_generated_event"])


# --------------------------------------------------
# Tab 2: Event Reviewer (Person 2)
# --------------------------------------------------

with tabs[1]:
    st.subheader("Event Reviewer — Chapter 3")
    st.write(
        "Inspect potential missing information, contradictory rules, and safety concerns."
    )

    reviewer_mode = st.radio(
        "Event Reviewer mode",
        ["Cached examples", "Live review"],
        horizontal=True,
        key="reviewer_mode",
    )

    if reviewer_mode == "Cached examples":
        st.caption("Recorded review outcomes. No OpenAI API call is made.")
        try:
            event_reviews = load_event_reviews()
            if not event_reviews:
                st.info("No event reviews available.")
            else:
                review_labels = []
                for review in event_reviews:
                    event_name = review.get("reviewed_listing", {}).get("name", "Untitled Event")
                    review_result = review.get("review_result", {})
                    verdict = review_result.get("verdict", "unknown").replace("_", " ").title()
                    issues = review_result.get("issues", [])
                    category = (
                        issues[0].get("category", "").replace("_", " ").title()
                        if issues else "No issues"
                    )
                    review_labels.append(f"{event_name} — {verdict} ({category})")

                selected_index = st.selectbox(
                    "Select a reviewed event",
                    options=range(len(event_reviews)),
                    format_func=lambda index: review_labels[index],
                    key="reviewer_event_select",
                )
                display_event_review(event_reviews[selected_index])
        except (OSError, ValueError, KeyError, TypeError) as error:
            st.error(f"Unable to load event reviews: {error}")

    else:
        st.info(
            "Live review calls OpenAI only when you click Review with AI. "
            "An OPENAI_API_KEY is required; model usage may incur charges. "
            "You can edit the rules before running the reviewer."
        )

        review_options = []
        last_generated = st.session_state.get("live_generated_event")
        if isinstance(last_generated, dict):
            review_options.append(("Most recent live-generated draft", last_generated))
        try:
            review_options.extend(
                (f"Saved example: {event.get('name', 'Untitled Event')} ({index + 1})", event)
                for index, event in enumerate(load_generated_events())
            )
        except (OSError, ValueError, KeyError, TypeError):
            pass

        if not review_options:
            st.warning("No listing is available to review. Create a draft in Event Creator.")
        else:
            selected_source = st.selectbox(
                "Listing to review",
                options=range(len(review_options)),
                format_func=lambda index: review_options[index][0],
                key="reviewer_live_source",
            )
            source_event = review_options[selected_source][1]
            source_key = hashlib.sha256(
                json.dumps(source_event, sort_keys=True).encode("utf-8")
            ).hexdigest()[:12]

            st.markdown(
                f"**Event:** {source_event.get('name', 'Untitled Event')} "
                f"| **Skill:** {source_event.get('skill_level', 'Not supplied')}"
            )
            edited_description = st.text_area(
                "Description",
                value=source_event.get("description", ""),
                key=f"review_description_{source_key}",
            )
            edited_rules = st.text_area(
                "Rules — one rule per line",
                value="\n".join(source_event.get("rules", [])),
                height=175,
                key=f"review_rules_{source_key}",
                help='For example, add "Advanced players only." to a beginner event to test contradiction detection.',
            )
            event_to_review = {
                **source_event,
                "description": edited_description.strip(),
                "rules": [line.strip() for line in edited_rules.splitlines() if line.strip()],
            }
            current_signature = json.dumps(event_to_review, sort_keys=True)

            if st.button("Review with AI", key="run_live_reviewer", type="primary"):
                try:
                    from features.event_reviewer import review_event

                    with st.spinner("Reviewing tournament listing with AI..."):
                        review_result = review_event(event_to_review)

                    st.session_state["live_event_review"] = {
                        "signature": current_signature,
                        "case": {
                            "reviewed_listing": event_to_review,
                            "review_result": review_result,
                        },
                    }
                    st.success("Live review complete.")
                except Exception as error:
                    st.session_state.pop("live_event_review", None)
                    st.error(
                        "Live review was unsuccessful "
                        f"({type(error).__name__}). Check OPENAI_API_KEY and your connection."
                    )

            last_review = st.session_state.get("live_event_review")
            if isinstance(last_review, dict) and last_review.get("signature") == current_signature:
                display_event_review(last_review["case"])
            elif isinstance(last_review, dict):
                st.caption("The listing has changed. Run Review with AI to evaluate the latest edits.")


# --------------------------------------------------
# Tab 3: Event Discovery (Person 1)
# --------------------------------------------------

with tabs[2]:
    st.subheader("Event Discovery — Chapter 4")
    st.write(
        "Find fictional basketball courts and events using BM25, "
        "semantic search, or hybrid retrieval with structured filters."
    )

    kind = st.radio(
        "Search category", ["courts", "events"],
        horizontal=True, key="discovery_kind",
    )
    query = st.text_input(
        "Describe what you need",
        value="indoor competitive basketball court in Tempe",
        key="discovery_query",
    )

    method_col, results_col = st.columns(2)
    with method_col:
        method = st.selectbox(
            "Retrieval method", ["hybrid", "keyword", "semantic"],
            key="discovery_method",
        )
    with results_col:
        k = st.slider(
            "Number of results", min_value=1, max_value=10,
            value=5, key="discovery_k",
        )

    filters = {}
    try:
        listings = documents(kind)
        cities = sorted({item["city"] for item in listings})
        st.markdown("#### Refine results")
        city = st.selectbox(
            "City", ["Any city", *cities], key="discovery_city"
        )
        if city != "Any city":
            filters["city"] = city

        if kind == "events":
            skill_col, format_col = st.columns(2)
            with skill_col:
                skills = sorted({item["skill_level"] for item in listings})
                skill = st.selectbox(
                    "Skill level", ["Any level", *skills],
                    key="discovery_skill",
                )
                if skill != "Any level":
                    filters["skill_level"] = skill
            with format_col:
                formats = sorted({item["format"] for item in listings})
                event_format = st.selectbox(
                    "Event format", ["Any format", *formats],
                    key="discovery_event_format",
                )
                if event_format != "Any format":
                    filters["format"] = event_format
        else:
            indoor_col, rate_col = st.columns(2)
            with indoor_col:
                court_type = st.selectbox(
                    "Court type", ["Any", "Indoor", "Outdoor"],
                    key="discovery_court_type",
                )
                if court_type != "Any":
                    filters["indoor"] = court_type == "Indoor"
            with rate_col:
                highest_rate = int(max(item["hourly_rate"] for item in listings))
                max_rate = st.slider(
                    "Maximum hourly rate ($)", min_value=0,
                    max_value=highest_rate, value=highest_rate,
                    key="discovery_max_rate",
                )
                if max_rate < highest_rate:
                    filters["max_hourly_rate"] = max_rate

            amenities = sorted({
                amenity
                for item in listings
                for amenity in item.get("amenities", [])
            })
            selected_amenities = st.multiselect(
                "Required amenities (must include all selected)",
                options=amenities,
                key="discovery_amenities",
            )
            if selected_amenities:
                filters["amenities"] = selected_amenities

        if query.strip():
            with st.spinner("Ranking matching synthetic listings..."):
                output = search(query, kind, method, k, filters=filters)
            st.caption(
                f"Retrieval engine: {output.get('mode', method)} · "
                f"{output.get('total_candidates', 0)} listings match the filters"
            )
            if output.get("warning"):
                st.warning(output["warning"])

            results = output.get("results", [])
            if not results:
                st.info(
                    "No listings match those filters. Try another city, "
                    "court type, amenity, or skill level."
                )

            for item in results:
                with st.container(border=True):
                    st.markdown("**" + str(item.get("name", "Unnamed")) + "**")
                    listing_id = item.get(
    "event_id" if kind == "events" else "venue_id", ""
)
                    st.caption(
                        f"ID: {listing_id} | City: {item.get('city', 'Unknown')} "
                        f"| Score: {item.get('score', 'N/A')}"
                    )
                    if kind == "courts":
                        st.caption(
                            ("Indoor" if item.get("indoor") else "Outdoor")
                            + f" · ${item.get('hourly_rate', 'N/A')}/hour"
                            + " · Amenities: " + ", ".join(item.get("amenities", []))
                        )
                    else:
                        st.caption(
                            f"{item.get('format', 'Unknown format')} · "
                            f"{item.get('skill_level', 'Unknown skill')} · "
                            f"{item.get('date', 'Unknown date')}"
                        )
                    st.write(item.get("description", ""))
                    st.caption(
                        "Why matched: " + str(
                            item.get("why_match", "No explanation available")
                        )
                    )
        else:
            st.info("Enter a search query to discover listings.")

    except (ValueError, OSError, KeyError, TypeError) as error:
        st.error(f"Event Discovery failed: {error}")


# --------------------------------------------------
# --------------------------------------------------
# Tab 4: Booking Assistant (Person 3)
# --------------------------------------------------

with tabs[3]:
    st.subheader("Booking Assistant — Chapter 5")
    st.caption(
        "Find fictional available courts, inspect each tool call, "
        "and create a proposal for multi-agent coordination. "
        "Times are local to Arizona."
    )

    with st.form("scheduling_request"):
        city = st.text_input("City (optional)", key="booking_city")
        venue_id = st.text_input("Venue ID (optional)", key="booking_venue")
        requested_date = st.text_input("Date (YYYY-MM-DD, optional)", key="booking_date")
        start_time = st.text_input("Start time (HH:MM, optional)", key="booking_start")
        end_time = st.text_input("End time (HH:MM, optional)", key="booking_end")
        submitted = st.form_submit_button("Create search plan")

    if submitted:
        clear_booking_workflow()
        try:
            st.session_state["scheduling_plan"] = create_plan({
                "city": city,
                "venue_id": venue_id,
                "date": requested_date,
                "start_time": start_time,
                "end_time": end_time,
            })
        except ValueError as error:
            st.error(str(error))

    if "scheduling_plan" in st.session_state:
        plan = st.session_state["scheduling_plan"]
        st.markdown("### Review the search plan")
        for step in plan["steps"]:
            st.write("- " + step)
        st.json(plan["filters"])

        approve_col, reject_col = st.columns(2)
        if approve_col.button("Approve and search", key="p3_approve_search"):
            try:
                st.session_state.pop("booking_result", None)
                st.session_state.pop("m4_result", None)
                st.session_state["scheduling_result"] = execute_plan(plan, approved=True)
            except (ValueError, OSError, PermissionError) as error:
                st.error(str(error))

        if reject_col.button("Reject search plan", key="p3_reject_search"):
            clear_booking_workflow()
            st.rerun()

    if "scheduling_result" in st.session_state:
        result = st.session_state["scheduling_result"]
        st.markdown("### Scheduling trace")
        st.write(" ".join(result.get("trace", [])))
        for entry in result.get("timeline", []):
            with st.expander(f"Step {entry['step']}: {entry['tool']}"):
                st.write(entry["decision"])
                st.write("Arguments")
                st.json(entry["arguments"])
                if "result" in entry:
                    st.write("Result")
                    st.json(entry["result"])
                else:
                    st.error(entry.get("error", "Tool execution failed."))

        if result["status"] != "completed":
            st.warning("Search status: " + result["status"])

        if result.get("results"):
            st.markdown("### Available fictional slots")
            st.dataframe(result["results"], hide_index=True)
            slots = {slot["slot_id"]: slot for slot in result["results"]}

            with st.form("booking_request"):
                selected_slot_id = st.selectbox(
                    "Choose an available slot",
                    options=list(slots),
                    format_func=lambda slot_id: (
                        f"{slot_id} | {slots[slot_id]['venue_name']} | "
                        f"{slots[slot_id]['date']} "
                        f"{slots[slot_id]['start_time']}–{slots[slot_id]['end_time']}"
                    ),
                    key="p3_selected_slot",
                )
                event_id = st.text_input(
                    "Existing fictional event ID",
                    value="EVT-001",
                    key="p3_event_id",
                    help="Chapter 6 validates that this event exists. "
                         "Differences in venue/date/time require human review.",
                )
                proposal_submitted = st.form_submit_button("Create booking proposal")

            if proposal_submitted:
                st.session_state.pop("m4_result", None)
                st.session_state.pop("m4_signature", None)
                st.session_state["booking_result"] = propose_booking({
                    **slots[selected_slot_id],
                    "event_id": event_id,
                })
        elif result["status"] == "completed":
            st.info("No matching available slots were found.")

    booking = st.session_state.get("booking_result")
    if isinstance(booking, dict):
        st.markdown("### Mock booking proposal")
        if booking.get("proposal"):
            st.json(booking["proposal"])
        if booking.get("error"):
            st.error(booking["error"])
        st.markdown("#### Booking tool trace")
        st.json(booking.get("trace", []))

        if booking.get("status") == "pending_approval":
            st.success("Proposal created. Next: open Event Coordination to review it.")
            st.info(
                "Do not confirm directly in Chapter 5. Chapter 6 must "
                "evaluate and approve this specific proposal first."
            )
            if st.button("Reject booking proposal", key="p3_reject_proposal"):
                try:
                    st.session_state["booking_result"] = reject_booking(booking)
                    st.session_state.pop("m4_result", None)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        elif booking.get("status") == "approved":
            st.success("Mock booking confirmed in this session; no actual slot was reserved.")
        elif booking.get("status") == "rejected":
            st.info("Mock booking proposal rejected.")


# --------------------------------------------------
# Tab 5: Event Coordination (Person 4)
# --------------------------------------------------

with tabs[4]:
    booking = st.session_state.get("booking_result")
    booking_proposal = (
        booking.get("proposal")
        if isinstance(booking, dict)
        and booking.get("status") == "pending_approval"
        and isinstance(booking.get("proposal"), dict)
        else None
    )

    if booking_proposal is not None:
        st.success("A Chapter 5 booking proposal is ready for coordination.")
        st.caption(
            "Select 'Chapter 5 Booking Assistant' as the proposal source. "
            "For a newly created proposal, use Live mode: cached mode "
            "only supports the previously recorded BOOK-002 example. "
            "Live mode requires an OpenAI API key and only calls the model "
            "when you click Run Event Coordination."
        )

        # Give immediate, free feedback before any live model call.
        try:
            preflight = validate_booking(booking_proposal)
            if not preflight["valid"]:
                for error in preflight["errors"]:
                    st.error("Proposal validation: " + error)
                st.warning("Correct the proposal before running live coordination.")
            for warning in preflight["warnings"]:
                st.warning("Proposal review: " + warning)
        except (OSError, KeyError, TypeError, ValueError) as error:
            st.error(f"Unable to validate proposal: {error}")

    elif isinstance(booking, dict) and booking.get("status") == "approved":
        st.success(
            "Chapter 5 mock booking confirmed in this session. "
            "No booking record was written and no reservation was made."
        )
    elif isinstance(booking, dict) and booking.get("status") == "rejected":
        st.info("Chapter 5 proposal was rejected. Cached coordination is still available.")

    # Person 4's existing UI includes the recorded demonstration, four-message
    # agent timeline, deterministic validation, and human approval controls.
    coordination_result = render_coordination(proposal=booking_proposal)

    # A cached replay has a different proposal from Chapter 5 and cannot
    # authorize it. Require actual Chapter 6 live approval of the exact proposal.
    if booking_proposal is not None and coordination_matches_booking(
        coordination_result, booking_proposal
    ):
        st.divider()
        st.subheader("Finalize the simulated booking")
        st.info(
            "This exact proposal received human approval in Chapter 6. "
            "Final mock confirmation remains a separate action."
        )
        if st.button("Confirm mock booking", key="p3_p4_confirm"):
            try:
                confirmed = confirm_booking(booking, approved=True)
                st.session_state["booking_result"] = confirmed
                if confirmed["status"] == "approved":
                    st.success(
                        "Mock booking confirmed in memory. No real reservation was made."
                    )
                else:
                    st.error(confirmed.get("error", "Confirmation failed."))
            except (PermissionError, ValueError, OSError) as error:
                st.error(str(error))


st.divider()
st.caption(
    "MeetFlow AI | MIS 552 Group Project | Persons 1–4 integrated | "
    "Synthetic marketplace — no real reservations"
)
