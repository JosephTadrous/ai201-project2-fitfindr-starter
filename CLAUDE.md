# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FitFindr is a Project 2 assignment starter kit (CodePath AI201). It is a single-user
agent that takes a natural-language clothing query, searches a mock secondhand-listings
dataset, suggests an outfit using the user's wardrobe, and produces a shareable "fit card"
caption. The repo ships as **scaffolding**: the data layer and UI wiring are complete, but
the three tools, the planning loop, and the Gradio query handler are stubbed with `TODO`s
and must be implemented.

## Setup & commands

```bash
# Environment (already created at .venv)
source .venv/bin/activate
pip install -r requirements.txt

# Requires a Groq API key in a .env file at the project root:
#   GROQ_API_KEY=your_key_here    (free key at console.groq.com)

python utils/data_loader.py   # sanity-check that data loads (run this first)
python agent.py               # run the planning loop's built-in CLI tests (happy path + no-results)
python app.py                 # launch the Gradio UI (localhost:7860, port may vary)
pytest                        # run tests (pytest is a dependency; no test files exist yet — add your own)
pytest path/to/test.py::test_name   # run a single test
```

There is no build or lint step. Tools should be tested in isolation (import and call the
function directly, or via `pytest`) **before** being wired into `agent.py`.

## Architecture

The data flows in one direction through a planning loop, with a single session dict
carrying all state:

```
app.py (handle_query)  →  agent.py (run_agent)  →  tools.py (3 tools)  →  Groq LLM
                              │
                              └── session dict = single source of truth
```

- **`utils/data_loader.py`** (complete) — the only data access layer. `load_listings()`
  returns 40 mock listings; `get_example_wardrobe()` / `get_empty_wardrobe()` return wardrobe
  dicts with an `items` list. Tools must load data through these helpers, not by re-reading
  the JSON in `data/`.

- **`tools.py`** (stubbed) — three standalone, independently-testable functions. Signatures
  are fixed and must not change (see contract below):
  - `search_listings(description, size=None, max_price=None) -> list[dict]` — filter +
    keyword-score listings; returns `[]` on no match (never raises).
  - `suggest_outfit(new_item, wardrobe) -> str` — LLM call; must handle an empty wardrobe by
    giving general styling advice rather than failing.
  - `create_fit_card(outfit, new_item) -> str` — LLM call (use higher temperature for variety);
    returns an error *string* if `outfit` is empty (never raises).
  - The Groq client is created lazily via `_get_groq_client()`, which raises if `GROQ_API_KEY`
    is unset.

- **`agent.py`** (stubbed) — `run_agent(query, wardrobe)` is the orchestrator. It builds a
  session dict via `_new_session()`, then: parse query → `search_listings` → (early-return if
  no results) → select top item → `suggest_outfit` → `create_fit_card`. **The session dict is
  the contract between steps** — every intermediate result is stored on it, and `session["error"]`
  is checked first by callers (when set, the other output fields are `None`).

- **`app.py`** (stubbed) — `handle_query()` is the Gradio glue. It guards empty input, picks
  the wardrobe from a radio choice, calls `run_agent()`, and maps the session into three output
  panels (listing / outfit / fit card). The Blocks layout and event wiring are already done.

## Project-specific contracts

- **Tool signatures in `tools.py` are graded against the README's documented interfaces.** Do
  not change parameter names, counts, or types — the README "Tool Inventory" must match the code
  exactly. If a spec needs to change, update `planning.md` and the README together.
- **`planning.md` is a graded deliverable, filled out before writing code**, and the README
  contains graded prose sections (Interaction Walkthrough, Error Handling table, Spec Reflection)
  with `<!-- ... -->` template comments to replace. These are templates, not finished docs — do
  not treat their placeholder structure as the intended final content, and do not invent content
  for them.
- Error handling is by **return value, not exceptions**: tools return `[]` / an error string and
  the planning loop sets `session["error"]` and returns early. Preserve this pattern rather than
  letting exceptions propagate to the UI.
