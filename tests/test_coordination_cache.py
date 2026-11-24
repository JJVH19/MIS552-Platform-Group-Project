
"""Standalone cached-mode tests for Member 4."""

import os
import unittest

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from features.coordination_cache import (
    coordinate_booking_mode,
    get_cached_proposal,
    load_recorded_run
)

from governance.coordination_controls import (
    apply_human_decision
)


class TestCoordinationCache(unittest.TestCase):

    def setUp(self):

        self.proposal = get_cached_proposal()

        self.bookings_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "bookings.json"
        )

        self.bookings_before = (
            self.bookings_path.read_bytes()
        )

        # Block any attempted live agent execution.

        self.agent_guard = patch(
            "features.coordination.run_agent",
            side_effect=AssertionError(
                "Live agent called during cached mode."
            )
        )

        self.client_guard = patch(
            "features.coordination_agents.OpenAI",
            side_effect=AssertionError(
                "OpenAI client created in cached mode."
            )
        )

        self.mock_agent = self.agent_guard.start()

        self.mock_client = self.client_guard.start()

        self.addCleanup(self.agent_guard.stop)

        self.addCleanup(self.client_guard.stop)


    def replay(self):

        return coordinate_booking_mode(
            self.proposal,
            mode="cached"
        )


    def tearDown(self):

        self.assertEqual(
            self.bookings_path.read_bytes(),
            self.bookings_before
        )

        self.mock_agent.assert_not_called()

        self.mock_client.assert_not_called()


    def test_01_no_api_key(self):

        self.assertFalse(
            os.environ.get("OPENAI_API_KEY")
        )

        result = self.replay()

        self.assertEqual(
            result["execution_mode"],
            "cached"
        )


    def test_02_original_agent_messages(self):

        result = self.replay()

        record = load_recorded_run()

        self.assertEqual(
            result["messages"],
            record["output"]["messages"]
        )

        self.assertEqual(
            len(result["messages"]),
            4
        )


    def test_03_decision_consistency(self):

        result = self.replay()

        record = load_recorded_run()

        self.assertEqual(
            result["status"],
            record["output"]["status"]
        )

        self.assertFalse(
            result["human_approved"]
        )


    def test_04_zero_api_calls(self):

        result = self.replay()

        self.assertEqual(
            result["api_calls_this_run"],
            0
        )


    def test_05_unrelated_proposal_rejected(self):

        changed = deepcopy(self.proposal)

        changed["venue_id"] = "VEN-999"

        with self.assertRaises(ValueError):

            coordinate_booking_mode(
                changed,
                mode="cached"
            )


    def test_06_unresolved_approval_denied(self):

        result = self.replay()

        self.assertEqual(
            result["status"],
            "needs_review"
        )

        with self.assertRaises(ValueError):

            apply_human_decision(
                result,
                "approve",
                acknowledged=True
            )


    def test_07_review_resolution(self):

        result = self.replay()

        resolved = apply_human_decision(
            result,
            "resolve_review",
            acknowledged=True,
            notes=(
                "UNIT TEST ONLY: simulate "
                "resolution of review concerns."
            )
        )

        self.assertEqual(
            resolved["status"],
            "pending_approval"
        )

        self.assertFalse(
            resolved["human_approved"]
        )


    def test_08_explicit_approval(self):

        result = self.replay()

        resolved = apply_human_decision(
            result,
            "resolve_review",
            acknowledged=True,
            notes="UNIT TEST ONLY: resolved concerns."
        )

        approved = apply_human_decision(
            resolved,
            "approve",
            acknowledged=True,
            notes="UNIT TEST ONLY: human approval."
        )

        self.assertTrue(
            approved["human_approved"]
        )

        self.assertEqual(
            approved["status"],
            "approved"
        )

        self.assertFalse(
            approved["booking_executed"]
        )


    def test_09_rejection(self):

        result = self.replay()

        rejected = apply_human_decision(
            result,
            "reject",
            acknowledged=True,
            notes="UNIT TEST ONLY: rejected."
        )

        self.assertEqual(
            rejected["status"],
            "rejected"
        )

        self.assertFalse(
            rejected["human_approved"]
        )


    def test_10_fresh_replay_resets_approval(self):

        first = self.replay()

        apply_human_decision(
            first,
            "reject",
            acknowledged=True
        )

        second = self.replay()

        self.assertFalse(
            second["human_approved"]
        )

        self.assertEqual(
            second["status"],
            "needs_review"
        )


    def test_11_stale_record_detected(self):

        record = load_recorded_run()

        record["output"]["validation"][
            "estimated_cost"
        ] += 100

        with patch(
            "features.coordination_cache.load_recorded_run",
            return_value=record
        ):

            with self.assertRaisesRegex(
                ValueError,
                "stale"
            ):

                self.replay()


    def test_12_incomplete_trace_detected(self):

        record = load_recorded_run()

        record["output"]["messages"].pop()

        with patch(
            "features.coordination_cache.load_recorded_run",
            return_value=record
        ):

            with self.assertRaises(ValueError):

                self.replay()


if __name__ == "__main__":

    unittest.main(verbosity=2)
