# MeetFlow AI — Basketball Event & Court Booking (MIS 552)

A **synthetic, mock-only** group platform prototype. **This starter implements Person 1's shared foundation and retrieval/search feature only.** The other four tabs are clearly labeled placeholders until teammates submit PRs.

## Getting started (macOS / Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```
Windows PowerShell: `.venv\Scripts\Activate.ps1` instead of `source ...`.

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
- `app.py`: five-tab Streamlit shell; currently only Discovery is wired.
- `build_index.py`: save vectors for the semantic corpus.

## Grading readiness
This is a **development starter, not a complete group submission**. Remaining work includes Chapters 2,3,5,6,7, real integration, 3 distinct LLM agents, safeguards, full cached replay, report, and video. No real booking/payment or unauthorized external operation.
