"""Offline scheduling agent for searching fictional court availability.

Planning validates the request without reading the data files. Execution requires
an explicit approval and only searches the local synthetic data; it makes no booking.
"""
from datetime import date, time
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def create_plan(request: dict) -> dict:
    """Prepare a reviewable search plan from structured user preferences."""
    if not isinstance(request, dict):
        raise ValueError("Request must be a dictionary.")
    city = str(request.get("city", "")).strip()
    venue_id = str(request.get("venue_id", "")).strip().upper()
    requested_date = str(request.get("date", "")).strip()
    start = str(request.get("start_time", "")).strip()
    end = str(request.get("end_time", "")).strip()
    if requested_date:
        try:
            if date.fromisoformat(requested_date).isoformat() != requested_date:
                raise ValueError
        except ValueError:
            raise ValueError("Date must use YYYY-MM-DD.") from None
    for value in (start, end):
        if value:
            try:
                if len(value) != 5 or time.fromisoformat(value).strftime("%H:%M") != value:
                    raise ValueError
            except ValueError:
                raise ValueError("Times must use 24-hour HH:MM.") from None
    if bool(start) != bool(end) or (start and start >= end):
        raise ValueError("Provide both times, with the end after the start.")
    filters = {"city": city, "venue_id": venue_id, "date": requested_date,
               "start_time": start, "end_time": end}
    return {"filters": filters, "steps": [
        "Find active fictional basketball facilities matching the preferences.",
        "If facilities match, search their fictional availability.",
        "If slots match, combine them with facility details; do not create a booking."
    ], "status": "pending_approval"}


MAX_AGENT_STEPS = 3


def _find_facilities(city: str, venue_id: str) -> list:
    with (DATA_DIR / "facilities.json").open(encoding="utf-8") as file:
        facilities = json.load(file)
    return [v for v in facilities if v.get("status") == "active"
            and v.get("sport", "").casefold() == "basketball"
            and (not city or v.get("city", "").casefold() == city.casefold())
            and (not venue_id or v["venue_id"] == venue_id)]


def _find_slots(venue_ids: list, date: str, start_time: str, end_time: str) -> list:
    with (DATA_DIR / "availability.json").open(encoding="utf-8") as file:
        slots = json.load(file)
    return [s for s in slots if s.get("venue_id") in venue_ids
            and s.get("available") is True and (not date or s.get("date") == date)
            and (not start_time or (s["start_time"] <= start_time and s["end_time"] >= end_time))]


def _format_results(facilities: list, slots: list) -> list:
    venues = {v["venue_id"]: v for v in facilities}
    results = [{**s, "venue_name": venues[s["venue_id"]]["name"],
                "city": venues[s["venue_id"]]["city"],
                "hourly_rate": venues[s["venue_id"]].get("hourly_rate")}
               for s in slots]
    return sorted(results, key=lambda x: (x["date"], x["start_time"], x["venue_name"]))


# Fixed allowlist and argument schemas for structured function calls. The agent
# cannot call arbitrary Python functions or modify files.
TOOLS = {
    "find_facilities": (_find_facilities, {"city": str, "venue_id": str}),
    "find_slots": (_find_slots, {"venue_ids": list, "date": str, "start_time": str, "end_time": str}),
    "format_results": (_format_results, {"facilities": list, "slots": list}),
}


def _call_tool(call: dict):
    name, arguments = call["name"], call["arguments"]
    if name not in TOOLS or not isinstance(arguments, dict):
        raise ValueError("Invalid tool call.")
    function, schema = TOOLS[name]
    if set(arguments) != set(schema) or any(not isinstance(arguments[k], t) for k, t in schema.items()):
        raise ValueError("Invalid tool arguments.")
    return function(**arguments)


def execute_plan(plan: dict, *, approved: bool = False, max_steps: int = MAX_AGENT_STEPS) -> dict:
    """Run a bounded, rule-driven ReAct loop after explicit human approval.

    Each iteration chooses one structured tool call based on prior observations.
    This local policy does not use an LLM and performs no booking.
    """
    if approved is not True:
        raise PermissionError("Human approval is required before executing the plan.")
    if not isinstance(plan, dict) or plan.get("status") != "pending_approval":
        raise ValueError("A pending plan is required.")
    validated = create_plan(plan.get("filters"))
    if plan != validated:
        raise ValueError("The plan was changed; create and review a new plan.")
    if type(max_steps) is not int or not 1 <= max_steps <= MAX_AGENT_STEPS:
        raise ValueError(f"max_steps must be between 1 and {MAX_AGENT_STEPS}.")
    filters = validated["filters"]
    observations = {}
    timeline = []
    for step in range(1, max_steps + 1):
        if "facilities" not in observations:
            decision = "Find facilities matching the requested location."
            call = {"name": "find_facilities", "arguments": {"city": filters["city"], "venue_id": filters["venue_id"]}}
            key = "facilities"
        elif not observations["facilities"]:
            break
        elif "slots" not in observations:
            decision = "Search availability for the facilities found."
            call = {"name": "find_slots", "arguments": {"venue_ids": [v["venue_id"] for v in observations["facilities"]],
                    "date": filters["date"], "start_time": filters["start_time"], "end_time": filters["end_time"]}}
            key = "slots"
        elif not observations["slots"]:
            break
        else:
            decision = "Combine matching slots with their facility details."
            call = {"name": "format_results", "arguments": {"facilities": observations["facilities"], "slots": observations["slots"]}}
            key = "results"
        try:
            result = _call_tool(call)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            timeline.append({"step": step, "decision": decision, "tool": call["name"],
                             "arguments": call["arguments"], "error": str(exc)})
            return {"status": "error", "results": [], "timeline": timeline,
                    "trace": ["Tool failed; search stopped.", "No booking was created."]}
        timeline.append({"step": step, "decision": decision, "tool": call["name"],
                         "arguments": call["arguments"], "result": result})
        observations[key] = result
        if key == "results":
            break
    complete = ("results" in observations or observations.get("facilities") == []
                or observations.get("slots") == [])
    results = observations.get("results", [])
    return {"status": "completed" if complete else "step_limit_reached", "results": results,
            "timeline": timeline, "trace": ["Human approved the search plan.",
                f"Found {len(results)} matching fictional availability slots." if complete
                else "Search stopped at the step limit before completion.",
                "No booking was created."]}
