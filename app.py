"""Person 1 owns the shared app; teammates implement importable feature functions."""
import json
from pathlib import Path

import streamlit as st
from features.retrieval import search


WORKFLOW_PATH = Path(__file__).parent / "demo" / "event_workflow.json"


def load_generated_events():
    """Load the event-generator drafts recorded in the demo workflow."""
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    generated_events = [workflow["generated_draft"]]
    generated_events.extend(
        case["generated_draft"]
        for case in workflow.get("additional_cases", {}).values()
        if "generated_draft" in case
    )
    return generated_events


def display_generated_event(event):
    """Render a generated event as regular Streamlit content."""
    st.markdown(f"### {event.get('name', 'Untitled Event')}")

    date_column, time_column, location_column = st.columns(3)
    date_column.metric("Date", event.get("date", "Not provided"))
    time_column.metric(
        "Time",
        f"{event.get('start_time', 'TBD')}–{event.get('end_time', 'TBD')}",
    )
    location_column.metric("City", event.get("city", "Not provided"))

    format_column, skill_column, players_column, venue_column = st.columns(4)
    format_column.metric("Format", event.get("format", "Not provided"))
    skill_column.metric("Skill level", event.get("skill_level", "Not provided"))
    players_column.metric("Players", event.get("players", "Not provided"))
    venue_column.metric("Venue", event.get("venue_id", "Not provided"))

    st.markdown("#### Description")
    st.write(event.get("description", "No description generated."))

    st.markdown("#### Rules")
    rules = event.get("rules", [])
    if rules:
        for rule in rules:
            st.markdown(f"- {rule}")
    else:
        st.write("No rules generated.")

    st.markdown("#### Promotional text")
    st.info(event.get("promotional_text", "No promotional text generated."))


def load_event_reviews():
    """Load the event-reviewer cases recorded in the demo workflow."""
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return list(workflow.get("review_cases", {}).values())


def display_event_review(review_case):
    """Render a reviewed listing and its result as regular Streamlit content."""
    reviewed_event = review_case.get("reviewed_listing", {})
    review_result = review_case.get("review_result", {})

    display_generated_event(reviewed_event)

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

    st.markdown("#### Issues")
    for issue_number, issue in enumerate(issues, start=1):
        category = issue.get("category", "Uncategorized").replace("_", " ").title()
        with st.container(border=True):
            st.markdown(f"**Issue {issue_number}: {category}**")
            st.write(f"Evidence: {issue.get('evidence', 'Not provided')}")
            st.write(f"Suggestion: {issue.get('suggestion', 'Not provided')}")
st.set_page_config(page_title='MeetFlow AI',page_icon='🏀',layout='wide')
st.title('🏀 MeetFlow AI')
st.caption('Synthetic basketball event and facility platform • Course prototype • Mock bookings only')
tabs=st.tabs(['Event Creator','Event Reviewer','Event Discovery','Booking Assistant','Event Coordination'])
with tabs[0]:
    st.subheader('Event Creator — Chapter 2')
    try:
        generated_events = load_generated_events()
        selected_name = st.selectbox(
            "Generated event",
            [event.get("name", "Untitled Event") for event in generated_events],
        )
        selected_event = next(
            event
            for event in generated_events
            if event.get("name", "Untitled Event") == selected_name
        )
        display_generated_event(selected_event)
    except (OSError, json.JSONDecodeError, KeyError) as error:
        st.error(f"Unable to load generated events: {error}")
with tabs[1]:
    st.subheader('Event Reviewer — Chapter 3')
    try:
        event_reviews = load_event_reviews()
        if not event_reviews:
            st.info("No event reviews are available.")
        else:
            review_labels = []
            for review in event_reviews:
                event_name = review.get("reviewed_listing", {}).get(
                    "name", "Untitled Event"
                )
                review_result = review.get("review_result", {})
                verdict = review_result.get("verdict", "unknown").replace(
                    "_", " "
                ).title()
                issues = review_result.get("issues", [])
                category = (
                    issues[0].get("category", "").replace("_", " ").title()
                    if issues
                    else "No issues"
                )
                review_labels.append(f"{event_name} — {verdict} ({category})")

            selected_review_index = st.selectbox(
                "Reviewed event",
                range(len(event_reviews)),
                format_func=lambda index: review_labels[index],
            )
            display_event_review(event_reviews[selected_review_index])
    except (OSError, json.JSONDecodeError, KeyError) as error:
        st.error(f"Unable to load event reviews: {error}")
with tabs[2]:
    st.subheader('Event Discovery — Chapter 4')
    kind=st.radio('Search', ['courts','events'],horizontal=True)
    q=st.text_input('Describe what you need',value='indoor competitive basketball court in Tempe')
    method=st.selectbox('Retrieval', ['hybrid','keyword','semantic'])
    k=st.slider('Number of results',1,10,5)
    if q:
        with st.spinner('Ranking synthetic listings...'):
            output=search(q,kind,method,k)
        st.caption('Retrieval engine: '+output['mode'])
        if output['warning']:st.warning(output['warning'])
        for item in output['results']:
            with st.container(border=True):
                st.markdown('**'+item.get('name','Unnamed')+'**')
                st.caption('ID: '+item.get('venue_id',item.get('event_id',''))+' | '+item['city']+' | Score: '+str(item['score']))
                st.write(item.get('description',''))
                st.caption('Why matched: '+item['why_match'])
with tabs[3]:
    st.subheader('Booking Assistant — Chapter 5')
    st.info('Person 3 will integrate propose_booking(request), mock tool calls, trace and approval here.')
with tabs[4]:
    st.subheader('Event Coordination — Chapter 6')
    st.info('Person 4 will integrate coordinate_booking(proposal), multiple LLM agents, shared state and monitoring here.')
st.divider()
st.caption('Development note: Five page shells exist; only Event Discovery is implemented by this starter.')
