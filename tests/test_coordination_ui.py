
"""Streamlit application tests for Member 4."""

import unittest

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class TestCoordinationUI(unittest.TestCase):

    def setUp(self):

        self.bookings_path = (
            PROJECT_DIR
            / "data"
            / "bookings.json"
        )

        self.bookings_before = (
            self.bookings_path.read_bytes()
        )

        # Prevent paid calls during UI tests.

        self.agent_guard = patch(
            "features.coordination.run_agent",
            side_effect=AssertionError(
                "Unexpected live agent call."
            )
        )

        self.mock_agent = self.agent_guard.start()

        self.addCleanup(
            self.agent_guard.stop
        )

        self.app = AppTest.from_file(
            str(PROJECT_DIR / "member4_preview.py"),
            default_timeout=30
        )

        self.app.run()

        self.assertFalse(self.app.exception)


    def tearDown(self):

        self.assertEqual(
            self.bookings_before,
            self.bookings_path.read_bytes()
        )

        self.mock_agent.assert_not_called()


    def run_coordination(self):

        self.app.button(
            key="m4_run"
        ).click().run()

        self.assertFalse(self.app.exception)

        return self.app.session_state["m4_result"]


    def test_01_application_launch(self):

        self.assertEqual(
            self.app.radio(
                key="m4_mode"
            ).value,
            "cached"
        )

        self.assertNotIn(
            "m4_result",
            self.app.session_state
        )


    def test_02_run_cached_coordination(self):

        result = self.run_coordination()

        self.assertEqual(
            result["execution_mode"],
            "cached"
        )

        self.assertEqual(
            len(result["messages"]),
            4
        )

        self.assertEqual(
            result["api_calls_this_run"],
            0
        )


    def test_03_unresolved_approval_disabled(self):

        self.run_coordination()

        self.assertTrue(
            self.app.button(
                key="m4_approve_disabled"
            ).disabled
        )

        self.assertTrue(
            self.app.button(
                key="m4_resolve"
            ).disabled
        )


    def test_04_interactive_approval(self):

        self.run_coordination()

        self.app.text_area(
            key="m4_review_notes"
        ).set_value(
            "UI TEST ONLY: simulate resolution "
            "of outstanding concerns."
        ).run()

        self.app.checkbox(
            key="m4_review_ack"
        ).set_value(True).run()

        self.assertFalse(
            self.app.button(
                key="m4_resolve"
            ).disabled
        )

        self.app.button(
            key="m4_resolve"
        ).click().run()

        self.assertFalse(self.app.exception)

        result = self.app.session_state["m4_result"]

        self.assertEqual(
            result["status"],
            "pending_approval"
        )

        self.assertTrue(
            self.app.button(
                key="m4_approve"
            ).disabled
        )

        self.app.checkbox(
            key="m4_approval_ack"
        ).set_value(True).run()

        self.app.button(
            key="m4_approve"
        ).click().run()

        self.assertFalse(self.app.exception)

        result = self.app.session_state["m4_result"]

        self.assertEqual(
            result["status"],
            "approved"
        )

        self.assertTrue(result["human_approved"])

        self.assertFalse(result["booking_executed"])

        self.assertEqual(
            len(result["human_actions"]),
            2
        )


    def test_05_interactive_rejection(self):

        self.run_coordination()

        self.app.button(
            key="m4_reject"
        ).click().run()

        self.assertFalse(self.app.exception)

        result = self.app.session_state["m4_result"]

        self.assertEqual(
            result["status"],
            "rejected"
        )

        self.assertFalse(result["human_approved"])

        self.assertFalse(result["booking_executed"])


    def test_06_mode_change_clears_old_result(self):

        self.run_coordination()

        self.app.radio(
            key="m4_mode"
        ).set_value("live").run()

        self.assertFalse(self.app.exception)

        self.assertNotIn(
            "m4_result",
            self.app.session_state
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
