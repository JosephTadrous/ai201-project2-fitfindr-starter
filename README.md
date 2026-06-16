# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

Your README submission must document each tool's name, inputs, and return value. **These must exactly match your actual function signatures in `tools.py`.** Your documented interfaces will be checked against your actual function signatures in `tools.py` — if the parameter count or types contradict what's in the code, you may not receive full credit for that tool.

### `search_listings(description, size=None, max_price=None)`

**Purpose:** Filters the 40-item mock dataset to listings that match the user's request and ranks them by relevance.

**Inputs:**
- `description` (`str`) — keywords describing the item (e.g. `"vintage graphic tee"`). Required. Drives relevance scoring by counting keyword hits across each listing's title, description, style tags, and category.
- `size` (`str | None`) — size string to filter by, matched case-insensitively as a substring (e.g. `"M"` matches `"S/M"` and `"M/L"`). `None` skips size filtering.
- `max_price` (`float | None`) — inclusive price ceiling in dollars. `None` skips price filtering.

**Returns:** `list[dict]` — matching listing dicts sorted best-match first, or `[]` if nothing matches. Each dict contains: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str or None), `platform` (str).

---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Uses the Groq LLM (`llama-3.3-70b-versatile`) to suggest 1–2 complete outfits pairing the thrifted item with the user's existing wardrobe. Falls back to general styling advice when the wardrobe is empty.

**Inputs:**
- `new_item` (`dict`) — a full listing dict (the top result from `search_listings`), used to describe the thrifted piece to the LLM.
- `wardrobe` (`dict`) — a wardrobe dict with an `items` key holding a list of wardrobe item dicts (each with `name`, `category`, `colors`, `style_tags`). May have an empty `items` list.

**Returns:** `str` — a non-empty string of outfit suggestions. If the wardrobe is populated, suggestions name specific wardrobe pieces by name. If the wardrobe is empty, suggestions describe general styling directions (what kinds of bottoms, shoes, and layers pair well).

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Uses the Groq LLM (`llama-3.1-8b-instant`, temperature 0.9) to generate a short, casual social-media caption for the outfit.

**Inputs:**
- `outfit` (`str`) — the outfit suggestion string from `suggest_outfit`. If empty or whitespace-only, the function returns an error string without calling the LLM.
- `new_item` (`dict`) — the listing dict for the thrifted item. The LLM is instructed to mention the item's `title`, `price`, and `platform` once each in the caption.

**Returns:** `str` — a 2–4 sentence Instagram/TikTok-style caption with a casual, authentic tone. Returns a descriptive error message string (not an exception) if `outfit` is empty.

---

## Interaction Walkthrough

**User query:** `"I'm looking for a vintage graphic tee under $30"`

**Step 1 — Tool called:** `search_listings`
- Input: `description="I'm looking for a vintage graphic tee"`, `size=None`, `max_price=30.0`
- Why this tool: The query contains a price ceiling (`under $30`) and descriptive keywords. The agent parses these with regex first, then calls `search_listings` to filter the dataset and rank results by keyword overlap.
- Output: 20 listing dicts sorted by relevance score. Top result: `{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'price': 18.0, 'platform': 'depop', ...}`

**Step 2 — Tool called:** `suggest_outfit`
- Input: `new_item={'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', ...}`, `wardrobe={'items': [{'name': 'Baggy straight-leg jeans, dark wash', ...}, ...]}`
- Why this tool: A top result was found, so the agent proceeds to styling. The wardrobe has 10 items, so the LLM receives the full wardrobe list and is prompted to name specific pieces in the outfit suggestions.
- Output: `"Pair the Y2K Baby Tee with the Baggy straight-leg jeans and the Chunky white sneakers... or combine with the Wide-leg khaki trousers and the Black combat boots for an edgy look."`

**Step 3 — Tool called:** `create_fit_card`
- Input: `outfit="Pair the Y2K Baby Tee with the Baggy straight-leg jeans..."`, `new_item={'title': 'Y2K Baby Tee — Butterfly Print', 'price': 18.0, 'platform': 'depop', ...}`
- Why this tool: The outfit suggestion is non-empty, so the agent proceeds to generate the shareable caption. The item's title, price, and platform are passed so the LLM can weave them into the caption naturally.
- Output: `"Just threw on this vintage butterfly tee for a chill day out - snagged it for $18 on Depop. Pairs perfectly with some comfy baggy jeans and chunky sneaks, gives off a totally '00s vibe."`

**Final output to user:** Three Gradio panels:
- **Top listing found:** Title, price, size, condition, platform, brand, style tags, and full description for the Y2K Baby Tee.
- **Outfit idea:** The full 1–2 outfit suggestions naming specific wardrobe pieces.
- **Your fit card:** The 2–3 sentence casual caption ready to share.

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | Returns `[]` when no listings match the filters | The planning loop checks `if not session["search_results"]` immediately after the call. It sets `session["error"] = "No listings found matching your search. Try broader keywords or remove the size/price filter."` and returns the session early — `suggest_outfit` and `create_fit_card` are never called. Confirmed in testing: `run_agent("designer ballgown size XXS under $5", wardrobe)` produced exactly this message with `fit_card` and `outfit_suggestion` both `None`. |
| `suggest_outfit` | `wardrobe["items"]` is an empty list | The tool itself handles this before calling the LLM. It checks `if not wardrobe.get("items")` and switches to a general-styling prompt that asks for advice on what kinds of pieces pair well with the item, rather than referencing specific wardrobe items. The planning loop does not special-case this — it stores whatever non-empty string the tool returns. Confirmed in testing: calling with `get_empty_wardrobe()` returned styling advice beginning `"The Y2K Baby Tee with a butterfly print is a adorable and nostalgic piece. Here are two complete outfit suggestions..."` with no wardrobe-item references. |
| `create_fit_card` | `outfit` is an empty or whitespace-only string | The tool guards at the top: `if not outfit or not outfit.strip()` returns `"Unable to generate fit card: outfit suggestion was missing."` immediately, without calling the LLM. The planning loop stores that string in `session["fit_card"]` and the UI displays it in the fit card panel. Confirmed in testing: `create_fit_card("", item)` and `create_fit_card("   ", item)` both returned the error string; the mock verified the Groq client was never called. |

---

## Spec Reflection

**One way planning.md helped during implementation:**

The State Management table in planning.md (which key each step writes to and reads from) was directly useful when implementing `run_agent()`. Rather than guessing what to name each session variable or where to thread state, the table gave a mechanical checklist: write `session["search_results"]` after `search_listings`, read `session["search_results"][0]` to set `session["selected_item"]`, pass that into `suggest_outfit`, and so on. It also caught a subtle issue early: by making the read/write dependencies explicit, it was clear that `create_fit_card` reads from `session["outfit_suggestion"]` (the LLM's string) and not from `session["search_results"]` — which meant the early-exit branch only needed to short-circuit before `suggest_outfit`, not before `create_fit_card` separately.

**One divergence from your spec, and why:**

The spec called for using `llama3-8b-8192` as the Groq model, but that model was decommissioned by Groq between when the spec was written and when the implementation ran. The actual implementation uses `llama-3.1-8b-instant` for `create_fit_card` (the direct replacement) and `llama-3.3-70b-versatile` for `suggest_outfit` (a more capable model, chosen because outfit suggestions benefit from stronger reasoning about style combinations). The interface and behavior are identical — both return strings, both respect the empty-input guards — so the divergence is in the model name only, not in how the tools are called or what they return.

---

## AI Tool Usage

### Instance 1 — Implementing the three tools in `tools.py`

**Tool used:** Claude Code

**Input given:** The Tool 1, Tool 2, and Tool 3 spec sections from `planning.md` (what each tool does, exact parameter names and types, return shape, failure behavior), plus the note that `search_listings` must use `load_listings()` from `utils/data_loader.py` rather than re-reading the JSON directly. For `suggest_outfit`, I also included the wardrobe dict structure from `data/wardrobe_schema.json` so the prompt template would reference the right field names (`name`, `category`, `colors`).

**What it produced:** Complete implementations of all three functions inside `tools.py`. `search_listings` filtered by price and size, scored by keyword overlap, and returned sorted results. `suggest_outfit` branched on an empty wardrobe and built two different LLM prompts. `create_fit_card` guarded against an empty `outfit` string and called the LLM at `temperature=0.9`.

**What I changed before using it:** Two things required correction. First, the generated code used `model="llama3-8b-8192"`, which turned out to be decommissioned — the first live test run threw a `groq.BadRequestError` with a deprecation message. I switched `suggest_outfit` to `llama-3.3-70b-versatile` (stronger reasoning for outfit combinations) and `create_fit_card` to `llama-3.1-8b-instant` (the direct replacement). Second, the description cleanup after regex parsing left trailing fragments like `"looking for a"` when both a size and price were stripped — I revised the cleanup regex to strip those leftover connector words before passing the description to `search_listings`.

---

### Instance 2 — Implementing `run_agent()` in `agent.py`

**Tool used:** Claude Code

**Input given:** Three sections from `planning.md` together: the Planning Loop (the 6-step numbered sequence with exact branch conditions), the State Management table (which session key each step writes to and reads from), and the Architecture diagram (the full ASCII flowchart showing the early-exit arrow and which values flow between boxes). Providing all three together let the AI cross-check the implementation against both the prose description and the visual data-flow.

**What it produced:** A complete `run_agent()` using regex to parse `description`, `size`, and `max_price` from the query string; storing results in the correct session keys at each step; and returning early with `session["error"]` when `search_results` was empty.

**What I changed before using it:** The generated regex for size (`size\s*:?\s*([XSML]+)`) didn't match numeric sizes like `"size 8"` or slash sizes like `"S/M"`. I expanded the character class to `([XSML0-9][XSML0-9/]*)` so it would capture those forms. I also verified the state flow mechanically before running — checked each line against the State Management table to confirm every write matched the expected session key — then ran `python agent.py` to exercise both the happy path and the no-results path against the built-in CLI test cases.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
