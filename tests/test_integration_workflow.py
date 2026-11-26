"""Person 1 integration tests: booking search -> mock multi-agent coordination.

These tests are offline. Any 'live' agent output below is deliberately mocked,
NOT a real OpenAI call. All reservations stay in memory.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from booking_tools import confirm_booking, propose_booking
from features.coordination_cache import coordinate_booking_mode
from features.coordination_validation import validate_booking
from governance.coordination_controls import apply_human_decision
from scheduling_agent import create_plan, execute_plan

ROOT = Path(__file__).resolve().parents[1]
BOOKINGS_FILE = ROOT / "data" / "bookings.json"
DATE = "2026-12-16"
VENUE_ID = "VEN-005"
EVENT_ID = "EVT-029"
SLOT_ID = "SLOT-0021"


def mock_agent(*, role, shared_state, client=None):
    """Simulate a supporting agent, recording a genuine shared-state exchange.

    This exercises coordination control flow, not LLM reasoning quality.
    """
    step = shared_state["step_count"] + 1
    message = {
        "step": step,
        "agent": role,
        "recipient": "",  # coordination.py fills the actual recipient
        "decision": "support",
        "message": "Offline integration test: support, subject to human approval.",
        "evidence": ["Synthetic marketplace records used for this test."],
        "concerns": [],
        "previous_messages_received": len(shared_state["messages"]),
        "model": "mock-agent-no-api",
        "mode": "live",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }
    shared_state["messages"].append(message)
    shared_state["agent_decisions"][role] = "support"
    shared_state["step_count"] = step
    return message


@pytest.fixture
def no_live_api():
    """Mock all four coordination agent steps and fail if OpenAI is created."""
    with (
        patch("features.coordination.run_agent", side_effect=mock_agent) as agent,
        patch("features.coordination_agents.OpenAI", side_effect=AssertionError("Unexpected paid API call.")) as client,
    ):
        yield agent, client
        client.assert_not_called()


def make_booking():
    plan = create_plan({
        "city": "Tucson", "venue_id": VENUE_ID, "date": DATE,
        "start_time": "09:00", "end_time": "12:00",
    })
    result = execute_plan(plan, approved=True)
    assert result["status"] == "completed"
    slot = next((s for s in result["results"] if s["slot_id"] == SLOT_ID), None)
    assert slot is not None, "Synthetic SLOT-0021 fixture changed; inspect availability.json."
    booking = propose_booking({**slot, "event_id": EVENT_ID})
    assert booking["status"] == "pending_approval", booking.get("error")
    assert booking["proposal"]["status"] == "pending_approval"
    return booking


def resolve_if_needed(result):
    if result["status"] == "needs_review":
        result = apply_human_decision(
            result, "resolve_review", acknowledged=True,
            notes="TEST ONLY: documented simulated resolution; no real booking.",
        )
    assert result["status"] == "pending_approval"
    return result


def _button_with_label(app, label):
    matches = [button for button in app.button if button.label == label]
    assert len(matches) == 1, f"Expected one button labeled {label!r}, got {len(matches)}"
    return matches[0]


def _has_button(app, key):
    return any(button.key == key for button in app.button)


def _start_app_and_propose_booking():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    app.run()
    assert not app.exception, app.exception

    # Submit a real Streamlit form to invoke Person 3's search plan and tools.
    for key, value in {
        "booking_city": "Tucson", "booking_venue": VENUE_ID,
        "booking_date": DATE, "booking_start": "09:00",
        "booking_end": "12:00",
    }.items():
        app.text_input(key=key).set_value(value)
    _button_with_label(app, "Create search plan").click().run()
    assert not app.exception, app.exception

    app.button(key="p3_approve_search").click().run()
    assert not app.exception, app.exception
    assert app.session_state["scheduling_result"]["status"] == "completed"

    app.selectbox(key="p3_selected_slot").set_value(SLOT_ID)
    app.text_input(key="p3_event_id").set_value(EVENT_ID)
    _button_with_label(app, "Create booking proposal").click().run()
    assert not app.exception, app.exception

    booking = app.session_state["booking_result"]
    assert booking["status"] == "pending_approval"
    assert booking["proposal"]["slot_id"] == SLOT_ID

    # Explicitly select the newly created Chapter 5 proposal, not the demo.
    app.selectbox(key="m4_source").set_value("Chapter 5 Booking Assistant").run()
    assert not app.exception, app.exception
    return app


def _approve_in_ui(app):
    result = app.session_state["m4_result"]
    if result["status"] == "needs_review":
        app.text_area(key="m4_review_notes").set_value(
            "TEST ONLY: concerns documented and resolved in the synthetic scenario."
        ).run()
        app.checkbox(key="m4_review_ack").set_value(True).run()
        app.button(key="m4_resolve").click().run()
        assert not app.exception, app.exception

    assert app.session_state["m4_result"]["status"] == "pending_approval"
    assert app.button(key="m4_approve").disabled
    app.checkbox(key="m4_approval_ack").set_value(True).run()
    app.button(key="m4_approve").click().run()
    assert not app.exception, app.exception
    assert app.session_state["m4_result"]["status"] == "approved"
    assert app.session_state["m4_result"]["human_approved"] is True


def test_component_flow_requires_human_review_and_keeps_data_unchanged(no_live_api):
    before = BOOKINGS_FILE.read_bytes()
    booking = make_booking()
    proposal = booking["proposal"]
    assert validate_booking(proposal)["valid"]

    with pytest.raises(PermissionError):
        confirm_booking(booking)

    result = coordinate_booking_mode(proposal, mode="live")
    assert len(result["messages"]) == 4
    assert result["booking_executed"] is False
    assert result["human_approved"] is False
    assert result["execution_mode"] == "live"

    with pytest.raises(ValueError):
        apply_human_decision(result, "approve", acknowledged=False)

    result = resolve_if_needed(result)
    approved = apply_human_decision(result, "approve", acknowledged=True)
    assert approved["status"] == "approved"
    assert approved["proposal"]["booking_id"] == proposal["booking_id"]
    assert approved["booking_executed"] is False

    confirmed = confirm_booking(booking, approved=True)
    assert confirmed["status"] == "approved"
    assert booking["status"] == "pending_approval"
    assert BOOKINGS_FILE.read_bytes() == before
    assert no_live_api[0].call_count == 4


def test_streamlit_live_handoff_requires_approval_then_confirms_in_memory(no_live_api):
    before = BOOKINGS_FILE.read_bytes()
    app = _start_app_and_propose_booking()
    assert not _has_button(app, "p3_p4_confirm")

    app.radio(key="m4_mode").set_value("live").run()
    app.button(key="m4_run").click().run()
    assert not app.exception, app.exception
    assert app.session_state["m4_result"]["execution_mode"] == "live"
    assert not _has_button(app, "p3_p4_confirm")

    _approve_in_ui(app)
    assert _has_button(app, "p3_p4_confirm")
    app.button(key="p3_p4_confirm").click().run()
    assert not app.exception, app.exception
    assert app.session_state["booking_result"]["status"] == "approved"
    assert BOOKINGS_FILE.read_bytes() == before
    assert no_live_api[0].call_count == 4


def test_approval_for_different_booking_cannot_be_reused(no_live_api):
    app = _start_app_and_propose_booking()
    app.radio(key="m4_mode").set_value("live").run()
    app.button(key="m4_run").click().run()
    assert not app.exception, app.exception
    _approve_in_ui(app)
    assert _has_button(app, "p3_p4_confirm")

    result = deepcopy(app.session_state["m4_result"])
    result["proposal"]["booking_id"] = "BOOK-DIFFERENT"
    app.session_state["m4_result"] = result
    app.run()
    assert not app.exception, app.exception
    assert not _has_button(app, "p3_p4_confirm")
    assert app.session_state["booking_result"]["status"] == "pending_approval"


def test_approved_cached_demo_cannot_authorize_person3_booking(no_live_api):
    app = _start_app_and_propose_booking()
    # The saved BOOK-002 demonstration can be reviewed in cached mode, but it
    # must never authorize the separate BOOK-<random> proposal from Chapter 5.
    app.selectbox(key="m4_source").set_value("Recorded demo proposal").run()
    app.radio(key="m4_mode").set_value("cached").run()
    app.button(key="m4_run").click().run()
    assert not app.exception, app.exception
    assert app.session_state["m4_result"]["execution_mode"] == "cached"
    assert not _has_button(app, "p3_p4_confirm")

    _approve_in_ui(app)
    assert app.session_state["m4_result"]["status"] == "approved"
    assert not _has_button(app, "p3_p4_confirm")
    assert app.session_state["booking_result"]["status"] == "pending_approval"
