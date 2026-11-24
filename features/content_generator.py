import json

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

class EventCopy(BaseModel):
    description: str
    rules: list[str]
    promotional_text: str

#Code written with assistance of CODEX
def generate_event(event_details: dict) -> dict:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    client = OpenAI()

    response = client.responses.parse(
        model="gpt-4o-mini",
        instructions=(
            "Write a draft listing for a fictional basketball tournament. "
            "Use the supplied tournament details as facts. "
            "Write a short description, a list of rules, and promotional text. "
            "Match the tournament format and skill level. "
            "Do not invent prizes, registration links, or confirmed reservations."
        ),
        input=json.dumps(event_details),
        text_format=EventCopy,
    )

    copy = response.output_parsed
    if copy is None:
        raise RuntimeError("OpenAI did not return a complete event draft.")

    return {**event_details, **copy.model_dump()}


#Code used for testing purposes
if __name__ == "__main__":
    from pprint import pprint
    from features.event_reviewer import review_event

    sample_event = {
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

    draft = generate_event(sample_event)
    conflicting_draft = {
        **draft,
        "skill_level": "Beginner",
        "rules": ["Advanced players only."],
    }

    pprint(review_event(conflicting_draft))
    pprint(draft)

    pprint(review_event(draft))

    draft_without_date = draft.copy()
    draft_without_date.pop("date")
    pprint(review_event(draft_without_date))

    
