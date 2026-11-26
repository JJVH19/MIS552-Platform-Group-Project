# MeetFlow AI — Basketball Event & Court Booking (MIS 552)

MeetFlow AI is a five-tab **academic prototype** for discovering fictional basketball courts and events, drafting and reviewing event listings with AI, searching fictional court availability, and coordinating proposed bookings with human approval. All marketplace records are synthetic. **No actual reservations, payments, or persistent booking confirmations are made.**

## Features

| Tab | Owner | Functionality |
| --- | --- | --- |
| **Event Creator (Chapter 2)** | Person 2 | View recorded drafts or generate a fictional tournament listing with OpenAI from structured form inputs. |
| **Event Reviewer (Chapter 3)** | Person 2 | View recorded review results or run an AI review of an editable listing for missing information, contradictory rules, and safety concerns. A freshly generated draft can be selected for review within the same Streamlit session. |
| **Event Discovery (Chapter 4)** | Person 1 | Search fictional courts/events using BM25 keyword ranking, MiniLM embeddings, or reciprocal-rank-fusion hybrid ranking. Apply structured filters: city, court type, amenities and maximum hourly rate for courts; city, skill level and format for events. |
| **Booking Assistant (Chapter 5)** | Person 3 | Build and approve a search plan, inspect a bounded three-tool execution trace, select an available fictional slot, and create a mock booking proposal. |
| **Event Coordination (Chapter 6)** | Person 4 | Validate the proposed booking against synthetic marketplace data, replay a recorded agent exchange or run live LLM agents, show stakeholder messages and evidence, and require an explicit human decision before mock confirmation. |

The integration in `app.py` passes a Chapter 5 proposal to Chapter 6 through the Streamlit session. **A cached replay of the recorded `BOOK-002` demo cannot approve an unrelated Chapter 5 proposal.** New Chapter 5 proposals require **Live** coordination for the final mock-confirmation handoff.

## Getting started

Requirements: Python, pip, and an internet connection for the initial sentence-transformer model download. The application has been exercised on macOS with Python 3.14.8; dependency compatibility can vary by operating system and Python version.

```bash
# Run in the repository root
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

Open the local Streamlit URL printed in the terminal (usually `http://localhost:8501`). Stop the server with **Control + C** in its terminal.

### Cached mode vs. live AI

- **No API key needed:** Event Creator and Event Reviewer cached examples; Event Discovery; Booking Assistant; and the specific recorded demonstration in Event Coordination.
- **OpenAI API key required:** Live event generation, live event review, and live multi-agent coordination. These features only invoke the models when their respective action button is clicked; usage may incur API charges.
- To enable live calls, set `OPENAI_API_KEY` in your environment or a local `.env` file. **Never add API keys or your `.env` file to Git.** The Event Creator/Reviewer use Person 2's OpenAI implementation; Event Coordination uses Person 4's agent implementation.

If the MiniLM model is unavailable, Event Discovery displays an explicitly labeled **lexical TF-IDF fallback** instead of representing it as semantic embeddings. The optional `python build_index.py` command can generate reusable vector indexes for the synthetic corpus.

## Suggested demonstration workflow

1. **Event Creator:** Open **Cached examples** and inspect a generated tournament listing. Alternatively, use **Live generation** with an API key and click **Generate event with AI**.
2. **Event Reviewer:** Inspect a cached passed/revision example. In **Live review**, choose a saved or newly generated listing, optionally edit its rules, and click **Review with AI** (API key required).
3. **Event Discovery:** Search **courts** using hybrid retrieval and try **Tucson + Indoor + scoreboard**. Switch to **events** and try **Phoenix + Beginner + 3v3**. Results are ranked **after applying the selected structured filters**.
4. **Booking Assistant:** Create a search plan for fictional venue `VEN-005`, date `2026-12-16`, time `09:00`–`12:00`; approve the search and inspect matching availability. Select fictional slot `SLOT-0021`, enter event `EVT-029`, and create a **pending_approval** booking proposal.
5. **Event Coordination:** Choose **Chapter 5 Booking Assistant** as the proposal source. Inspect deterministic preflight validation. Live coordination is needed for a newly generated proposal; after agent review, appropriate human resolution/approval, and a separate **Confirm mock booking** click, the app returns a simulated in-memory confirmation. **No real court is reserved.**

For a completely offline Chapter 6 demonstration, select the **Recorded demo proposal** and **Cached** mode. That recorded example cannot authorize the newly generated Chapter 5 proposal.

**Important limitations:** Event Discovery search results do not automatically select a Booking Assistant form; venue IDs can be carried over manually. A live-generated listing is held in Streamlit session state and is not inserted into `data/events.json`. Booking proposals and mock confirmations are not persisted to `data/bookings.json`. The Chapter 5 scheduler is a **deterministic, bounded tool-driven agent**, not an OpenAI tool-calling agent. A full paid live API run has not been verified by the offline test suite.

## Testing

The combined **offline** verification used for the integrated branch is:

```bash
env -u OPENAI_API_KEY python -m pytest \
  tests/test_retrieval.py \
  tests/test_event_reviewer.py \
  tests/test_booking_tools.py \
  tests/test_scheduling_agent.py \
  tests/test_coordination_cache.py \
  tests/test_coordination_ui.py \
  tests/test_integration_workflow.py \
  -k "not test_review_event" -q
```

Latest locally reported result: **46 passed, 4 deselected** (the four tests requiring live OpenAI access were intentionally excluded).

`tests/test_integration_workflow.py` verifies the actual booking search/proposal flow, coordination control flow with **mocked** agent responses, the Streamlit human-approval gate, booking identity matching, cached-demo isolation, and non-persistence of booking records. **Mocked live-agent responses do not demonstrate real LLM reasoning or actual API calls.**

The `env -u` form above is for macOS/Linux. To run with real AI features, configure credentials appropriately, understand API costs, and test separately.

## Project structure

```text
app.py                        # Integrated five-tab Streamlit interface
features/content_generator.py # Person 2 event copy generation
features/event_reviewer.py    # Person 2 AI review
features/retrieval.py         # Person 1 keyword / semantic / hybrid retrieval and filters
scheduling_agent.py           # Person 3 bounded search planning and tool execution
booking_tools.py              # Person 3 mock proposal / confirm / reject
features/coordination*.py     # Person 4 coordination, validation, UI and cached replay
governance/                    # Human-approval and safety controls
contracts.py                  # Shared team contracts
data/                          # Synthetic facilities, events, availability and bookings
demo/                          # Recorded demo inputs and outputs
tests/                         # Component, UI and integration tests
docs/                          # Shared team contracts
```

## Safeguards and submission notes

- Uses fictional local records; no real facility integrations, payments, or reservations.
- Checks proposal fields, current mock availability, facility status and booking conflicts before coordination and mock confirmation.
- Requires explicit human acknowledgement; unresolved reviews and blocking agent objections cannot be silently approved.
- Prevents an approval of one proposal from automatically authorizing a different booking ID or changed details in the Streamlit handoff.
- Limits tool steps and agent interactions; the coordination agents never independently execute a booking.
- Keeps mock booking confirmations in memory, without changing persistent booking records.

**Scope:** This README describes the implemented software integration and offline test evidence. It does **not** claim completion of any separately required course report, presentation/video, Chapter 7 deliverable, or paid live-LLM evaluation. See `docs/TEAM_CONTRACTS.md` for the team's original interface conventions.
