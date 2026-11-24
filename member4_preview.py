
"""Standalone preview for Member 4 integration testing."""

import streamlit as st

from features.coordination_ui import (
    render_coordination
)

st.set_page_config(
    page_title="MeetFlow AI - Event Coordination",
    page_icon="🏀",
    layout="wide"
)

st.title("🏀 MeetFlow AI")

st.caption(
    "Basketball Event & Court Booking"
)

render_coordination()
