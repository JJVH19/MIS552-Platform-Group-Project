
"""MeetFlow AI - Chapter 6 cached demonstration.
Owner: Member 4
"""

import json
from pathlib import Path
from copy import deepcopy

from features.coordination import (
    coordinate_booking,
    finalize_coordination,
    PROTOCOL
)

from features.coordination_validation import (
    initialize_shared_state
)


DEMO_DIR = Path(
    __file__
).resolve().parents[1] / "demo"

CACHE_FILE = (
    DEMO_DIR / "coordination_scenario2_live.json"
)


def load_recorded_run():
    """Load a genuine previously recorded live run."""

    if not CACHE_FILE.exists():

        raise FileNotFoundError(
            "Recorded coordination demonstration "
            "is unavailable."
        )

    with open(
        CACHE_FILE,
        encoding="utf-8"
    ) as file:

        record = json.load(file)

    if record.get("mode") != "live":

        raise ValueError(
            "Cache must originate from a live run."
        )

    return record


def get_cached_proposal():
    """Return the supported demonstration input."""

    record = load_recorded_run()

    return deepcopy(record["input"])


def replay_coordination(proposal):
    """Replay recorded agent decisions without API calls."""

    record = load_recorded_run()

    recorded_input = record["input"]
    recorded_output = record["output"]

    # Prevent unrelated requests from receiving
    # a misleading cached response.

    if proposal != recorded_input:

        raise ValueError(
            "No recorded demonstration matches "
            "this booking proposal."
        )

    if recorded_output["proposal"] != recorded_input:

        raise ValueError(
            "Recorded proposal is inconsistent."
        )

    # Revalidate using current marketplace data.

    state = initialize_shared_state(proposal)

    if not state["validation"]["valid"]:

        raise ValueError(
            "Cached proposal no longer passes "
            "marketplace validation."
        )

    # Detect stale marketplace evidence.

    if state["validation"] != recorded_output["validation"]:

        raise ValueError(
            "Marketplace evidence has changed. "
            "The recorded run is stale."
        )

    messages = deepcopy(
        recorded_output["messages"]
    )

    # Verify the recorded communication protocol.

    actual_protocol = [
        (message["agent"], message["recipient"])
        for message in messages
    ]

    if actual_protocol != PROTOCOL:

        raise ValueError(
            "Recorded agent protocol is incomplete."
        )

    if len(messages) > state["max_steps"]:

        raise ValueError(
            "Recorded run exceeds execution limit."
        )

    for index, message in enumerate(messages):

        if message["step"] != index + 1:

            raise ValueError(
                "Invalid recorded step sequence."
            )

        if message["previous_messages_received"] != index:

            raise ValueError(
                "Invalid shared-state message history."
            )

        if message["decision"] not in {
            "support", "review", "block"
        }:

            raise ValueError(
                "Invalid recorded agent decision."
            )

        if message.get("mode") != "live":

            raise ValueError(
                "Message does not originate "
                "from a recorded live run."
            )

    # Restore the observable agent state.

    state["messages"] = messages

    state["step_count"] = len(messages)

    state["agent_decisions"] = {
        message["agent"]: message["decision"]
        for message in messages
    }

    # Reapply the current deterministic decision rules.
    # Do not restore any historical human approval.

    result = finalize_coordination(state)

    if result != recorded_output:

        raise ValueError(
            "Replayed decision differs from "
            "the original recorded result."
        )

    result["execution_mode"] = "cached"

    result["recorded_at"] = record["recorded_at"]

    result["api_calls_this_run"] = 0

    result["cache_source"] = CACHE_FILE.name

    return result


def coordinate_booking_mode(
    proposal,
    mode="cached",
    *,
    client=None
):
    """Provide a common entry point for both modes."""

    if mode == "cached":

        return replay_coordination(proposal)

    if mode == "live":

        result = coordinate_booking(
            proposal,
            client=client
        )

        result["execution_mode"] = "live"

        return result

    raise ValueError(
        f"Unsupported execution mode: {mode}"
    )
