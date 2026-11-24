import json
from pathlib import Path

import pytest

from demo.record_event_workflow import record_review_cases
from features.event_reviewer import review_event


CLEAN_DRAFT = {
    "name": "Desert Rookie 3v3",
    "date": "2026-12-12",
    "start_time": "10:00",
    "end_time": "14:00",
    "city": "Phoenix",
    "venue_id": "VEN-001",
    "format": "3v3",
    "skill_level": "Beginner",
    "players": 12,
    "description": "A 12-player beginner 3v3 basketball tournament in Phoenix.",
    "rules": [
        "Beginners are welcome.",
        "Follow the referee's decisions.",
        "Take water breaks between games.",
    ],
    "promotional_text": "Bring your team to Desert Rookie 3v3!",
}


@pytest.mark.parametrize(
    ("changes", "expected_category"),
    [
        pytest.param({}, None, id="clean"),
        pytest.param({"date": ""}, "missing_information", id="missing-date"),
        pytest.param({"rules": ["Advanced players only."]},
                     "contradiction", id="advanced-only"),
        pytest.param({"rules": ["No water breaks."]},
                     "safety", id="unsafe-rule"),
    ],
)
def test_review_event(changes, expected_category):
    draft = {**CLEAN_DRAFT, **changes}
    result = review_event(draft)

    if expected_category is None:
        assert result["verdict"] == "pass", result
        assert result["issues"] == [], result
    else:
        assert result["verdict"] == "needs_revision", result
        assert any(
            issue["category"] == expected_category
            for issue in result["issues"]
        ), result


def test_advanced_only_demo_case():
    path = Path(__file__).resolve().parents[1] / "demo" / "event_workflow.json"
    workflow = json.loads(path.read_text(encoding="utf-8"))
    case = record_review_cases(workflow, live=False)["advanced_only_rule"]

    saved_case = workflow["review_cases"]["advanced_only_rule"]
    if saved_case["mode"] == "mock":
        assert case == saved_case
    assert case["reviewed_listing"]["skill_level"] == "Beginner"
    assert "Advanced players only." in case["reviewed_listing"]["rules"]
    assert case["review_result"]["verdict"] == "needs_revision"
    assert any(
        issue["category"] == "contradiction"
        and issue["evidence"] == "Advanced players only."
        for issue in case["review_result"]["issues"]
    )
