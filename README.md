# MeetFlow AI — Basketball Event & Court Booking (MIS 552)

A **synthetic, mock-only** group platform prototype. Event Discovery and a human-approved fictional availability search are implemented. The other tabs are placeholders.

## Getting started (macOS / Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```
Windows PowerShell: `.venv\Scripts\Activate.ps1` instead of `source ...`.

In the Booking Assistant tab, enter optional search preferences and select **Create search plan**. Review the plan and select **Approve and search** to search the fictional data, or **Reject plan** to discard it. The search does not reserve a court. This offline agent uses deterministic rules, not a language model; a requested time range must fit entirely inside an available slot.

After approval, a rule-driven ReAct loop chooses structured calls to three local mock tools: find facilities, find available slots, and format results. It observes each result and stops early when no matches exist. The interface displays tool arguments and results in a timeline. A hard limit of three calls prevents unbounded execution; a lower limit can be supplied to `execute_plan` for testing.

Select an available slot and provide a fictional event ID to create a structured booking proposal. Review it and separately approve or reject the booking; approving the search alone never approves a booking. Availability is checked again on confirmation. The result and execution trace exist only in the current app session: no booking is saved, no slot is reserved, and event IDs are labels rather than validated event records.

On a connected computer, first-time use downloads the local `all-MiniLM-L6-v2` model (~tens of MB). To persist embeddings for the synthetic corpus, run `python build_index.py`. These vectors may be committed if you choose, after confirming sizes/licenses. If the embedding model is unavailable, the app labels its lexical TF-IDF fallback; **it is not a semantic equivalent**.

## Unit tests
```bash
python -m pytest -q
```

## Teamwork
Read `docs/TEAM_CONTRACTS.md` first. Each teammate uses a separate feature branch and PR. Do not commit API keys. The project uses invented events/courts and local mock tools only.

## Architecture
- `features/retrieval.py`: BM25, MiniLM vector search, RRF hybrid search.
- `data/`: 44 synthetic basketball events, 40 synthetic venues, 200 fictional availability slots, empty booking record.
- `contracts.py`: shared function signature proposals.
- `scheduling_agent.py`: creates a reviewable search plan and searches fictional availability after approval.
- `booking_tools.py`: creates, checks, approves, or rejects an in-memory mock booking proposal with a trace.
- `app.py`: five-tab Streamlit shell; Discovery and Booking Assistant are wired.
- `build_index.py`: save vectors for the semantic corpus.

## Grading readiness
This is a **development starter, not a complete group submission**. Remaining work includes Chapters 2,3,5,6,7, real integration, 3 distinct LLM agents, safeguards, full cached replay, report, and video. No real booking/payment or unauthorized external operation.
