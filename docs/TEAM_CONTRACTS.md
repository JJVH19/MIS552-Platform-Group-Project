# Team contracts — decide together before independent implementation

**Owner: Person 1.** Every member should confirm these field names and record changes in a PR.

## Base IDs and times
- `event_id` = `EVT-###`; `venue_id` = `VEN-###`; `booking_id` = `BOOK-###`.
- Date strings: `YYYY-MM-DD`. Times: local 24h `HH:MM`, interpreted in Arizona for this demo.
- No live APIs; all venues, events, bookings and slots are fictional.
- Shared data files live in `data/`; venue availability lives in `availability.json` (not inferred from venue text).

## Team function contracts
- Person 2: `generate_event(event_details: dict) -> dict` and `review_event(event: dict) -> dict`
- Person 1: `search_courts(query: str, method='hybrid', k=5) -> list[dict]`; same for `search_events`.
- Person 3: `propose_booking(request: dict) -> dict` — should return `proposal`, `trace`, `status`, `error` fields.
- Person 4: `coordinate_booking(proposal: dict) -> dict` — should return `messages`, `proposal`, `approval_required`, `status` fields.

## Proposed booking proposal structure
```json
{"booking_id":"BOOK-001","event_id":"EVT-001","venue_id":"VEN-001","date":"2026-12-12","start_time":"10:00","end_time":"14:00","status":"pending_approval"}
```

**No agent should write a confirmed booking before explicit human approval.** Person 3 and Person 4 must agree who owns the final mock-state mutation; avoid two different functions both confirming bookings.

## Required cross-feature connections
1. Generated event (Person 2) -> event reviewer (Person 2)
2. Retrieved court result (Person 1) -> scheduling agent (Person 3)
3. Booking proposal (Person 3) -> agent negotiation and approval (Person 4)

Keep the evidence/results trace observable in the final Streamlit app. Each member should provide a standalone test and a recorded cached-mode example.

## Cached mode
A complete cached demo must be able to demonstrate **every feature without an API key**. Each teammate provides their feature's recorded live examples as sanitized JSON. This starter does not yet implement full replay. Coordinate this early.
