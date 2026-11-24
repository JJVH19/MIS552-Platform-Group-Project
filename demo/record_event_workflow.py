import argparse
import json
from pathlib import Path


def record_case(event_details, *, live):
    if live:
        from features.content_generator import generate_event
        from features.event_reviewer import review_event

        draft = generate_event(event_details)
        review = review_event(draft)
    else:
        name = event_details["name"]
        skill = event_details["skill_level"].lower()
        draft = {
            **event_details,
            "description": (
                f"{name} is a {event_details['format']} basketball tournament "
                f"for {event_details['players']} {skill} players in {event_details['city']}."
            ),
            "rules": [
                f"This division welcomes {skill} players.",
                "Follow referee decisions and avoid dangerous contact.",
                "Take water breaks between games.",
            ],
            "promotional_text": f"Bring your team to {name} and enjoy a day of basketball!",
        }
        review = {"verdict": "pass", "issues": []}

    return {
        "organizer_input": event_details,
        "generated_draft": draft,
        "review_result": review,
        "mode": "live" if live else "mock",
    }


def record_review_cases(recording, *, live):
    cases = {
        name: {
            "reviewed_listing": example["generated_draft"],
            "review_result": example["review_result"],
            "mode": example["mode"],
        }
        for name, example in recording["additional_cases"].items()
    }

    conflicting_rule = "Advanced players only."
    original_draft = recording["generated_draft"]
    conflicting_draft = {
        **original_draft,
        "rules": [*original_draft["rules"], conflicting_rule],
    }
    if live:
        from features.event_reviewer import review_event

        result = review_event(conflicting_draft)
    else:
        result = {
            "verdict": "needs_revision",
            "issues": [
                {
                    "category": "contradiction",
                    "evidence": conflicting_rule,
                    "suggestion": "Allow beginners to enter or change the advertised skill level.",
                }
            ],
        }
    cases["advanced_only_rule"] = {
        "reviewed_listing": conflicting_draft,
        "review_result": result,
        "mode": "live" if live else "mock",
    }
    return cases


def main():
    parser = argparse.ArgumentParser(description="Save three event workflow examples.")
    parser.add_argument("--live", action="store_true", help="Generate and review all cases through OpenAI.")
    args = parser.parse_args()

    event_details = {
        "name": "Desert Rookie 3v3",
        "date": "2026-12-12",
        "start_time": "10:00",
        "end_time": "14:00",
        "city": "Phoenix",
        "venue_id": "VEN-001",
        "format": "3v3",
        "skill_level": "Beginner",
        "players": 12,
    }

    event_details_1 = {
        "name": "Scottsdale Weekend Hoops",
        "date": "2026-12-13",
        "start_time": "09:00",
        "end_time": "13:00",
        "city": "Scottsdale",
        "venue_id": "VEN-004",
        "format": "5v5",
        "skill_level": "Intermediate",
        "players": 20,
    }
    event_details_2 = {
        "name": "Phoenix 3v3 Challenge",
        "date": "2026-12-19",
        "start_time": "11:00",
        "end_time": "15:00",
        "city": "Phoenix",
        "venue_id": "VEN-001",
        "format": "3v3",
        "skill_level": "Advanced",
        "players": 18,
    }

    output_path = Path(__file__).with_name("event_workflow.json")
    if not args.live and output_path.exists():
        recording = json.loads(output_path.read_text(encoding="utf-8"))
    else:
        recording = record_case(event_details, live=args.live)
    recording["additional_cases"] = {
        "event_details_1": record_case(event_details_1, live=args.live),
        "event_details_2": record_case(event_details_2, live=args.live),
    }
    recording["review_cases"] = record_review_cases(recording, live=args.live)
    output_path.write_text(
        json.dumps(recording, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
