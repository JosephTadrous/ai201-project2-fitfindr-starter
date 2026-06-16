# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.
---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the 40-item mock listings dataset for pieces matching the user's request. It filters by an optional size and price ceiling, scores the remaining listings by keyword overlap with the description, drops zero-score (irrelevant) results, and returns the rest sorted most-relevant first.

**Input parameters:**
- `description` (str): keywords describing what the user wants (e.g. `"vintage graphic tee"`). Required; drives the relevance scoring.
- `size` (str | None): size to filter by, matched case-insensitively (e.g. `"M"` matches `"S/M"`). `None` skips size filtering.
- `max_price` (float | None): inclusive maximum price. `None` skips price filtering.

**What it returns:**
A `list[dict]`, each dict being a full listing with the fields: `id` (str), `title` (str), `description` (str), `category` (str: tops/bottoms/outerwear/shoes/accessories), `style_tags` (list[str]), `size` (str), `condition` (str: excellent/good/fair), `price` (float), `colors` (list[str]), `brand` (str or None), and `platform` (str: depop/thredUp/poshmark). The list is sorted best-match first.

**What happens if it fails or returns nothing:**
Returns an empty list — it never raises. When the list is empty, the planning loop sets `session["error"]` to a "no matching listings" message and returns early, so `suggest_outfit` and `create_fit_card` are never called with empty input.

---

### Tool 2: suggest_outfit

**What it does:**
Takes the thrifted item the user is considering and their wardrobe, and asks the LLM to propose 1–2 complete outfits. When the wardrobe has items, it suggests specific combinations naming pieces the user already owns; when it's empty, it gives general styling advice for the item instead.

**Input parameters:**
- `new_item` (dict): a single listing dict (the top result from `search_listings`), with the same fields listed under Tool 1 — the item to build outfits around.
- `wardrobe` (dict): the user's wardrobe, a dict with an `items` key holding a list of wardrobe-item dicts. May be empty (`items == []`).

**What it returns:**
A non-empty `str` of human-readable outfit suggestions — either concrete combinations pairing `new_item` with named wardrobe pieces, or general styling ideas if the wardrobe is empty.

**What happens if it fails or returns nothing:**
An empty wardrobe is handled by falling back to general styling advice rather than raising or returning an empty string. The LLM call should degrade to a descriptive fallback string on error; the agent stores whatever string comes back in `session["outfit_suggestion"]` and passes it to `create_fit_card`.

---

### Tool 3: create_fit_card

**What it does:**
Turns the outfit suggestion and the thrifted item into a short, shareable social-media caption (an OOTD-style post). It prompts the LLM at a higher temperature so captions feel casual and vary across different inputs.

**Input parameters:**
- `outfit` (str): the outfit suggestion string returned by `suggest_outfit` — the styling content the caption is written around.
- `new_item` (dict): the listing dict for the thrifted item, used to mention the item name, price, and platform naturally (once each).

**What it returns:**
A `str` of 2–4 sentences usable as an Instagram/TikTok caption — casual and authentic in tone, naming the item, price, and platform, and capturing the outfit's vibe.

**What happens if it fails or returns nothing:**
If `outfit` is empty or whitespace-only, it returns a descriptive error message string rather than raising. In practice the planning loop only reaches this tool after a successful `suggest_outfit`, but the guard ensures incomplete input produces a readable message instead of a crash.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The loop runs the same fixed sequence of steps every time — there are no dynamic decisions about which tool to call. The only branching is early-return on failure:

1. **Parse the query.** Extract three values from `session["query"]` using regex:
   - `size`: look for the pattern `size\s*:?\s*([XSML0-9/]+)` case-insensitively (e.g. matches "size M", "size: S/M"). If not found, set to `None`.
   - `max_price`: look for `\$(\d+(?:\.\d+)?)` or `under\s+\$?(\d+)` (e.g. matches "under $30", "$25"). If not found, set to `None`.
   - `description`: remove the matched size/price fragments from the original query string, strip punctuation and whitespace. Whatever remains is the description (e.g. `"vintage graphic tee"`).
   - Store all three in `session["parsed"]` as `{"description": ..., "size": ..., "max_price": ...}`.

2. **Call `search_listings`.** Pass `session["parsed"]["description"]`, `session["parsed"]["size"]`, and `session["parsed"]["max_price"]`. Store the returned list in `session["search_results"]`.
   - **Branch:** if `session["search_results"]` is an empty list, set `session["error"] = "No listings found matching your search. Try broader keywords or remove the size/price filter."` and `return session` immediately. Do not proceed to step 3.

3. **Select the top result.** Set `session["selected_item"] = session["search_results"][0]`. No branching needed — the list is guaranteed non-empty at this point.

4. **Call `suggest_outfit`.** Pass `session["selected_item"]` and `session["wardrobe"]`. Store the returned string in `session["outfit_suggestion"]`. No early-return here — the tool always returns a non-empty string.

5. **Call `create_fit_card`.** Pass `session["outfit_suggestion"]` and `session["selected_item"]`. Store the returned string in `session["fit_card"]`. No early-return here — the tool always returns a string.

6. **Return `session`.** `session["error"]` is `None`, `session["fit_card"]` has a value; the caller knows the interaction succeeded.

---

## State Management

**How does information from one tool get passed to the next?**

All state lives in the session dict, which is created by `_new_session()` at the start of `run_agent()` and passed through every step by reference. No global variables; no return values except the final `return session`.

| Step | Writes to | Reads from |
|------|-----------|------------|
| Parse query | `session["parsed"]` | `session["query"]` |
| search_listings | `session["search_results"]` | `session["parsed"]["description"]`, `["size"]`, `["max_price"]` |
| Select top result | `session["selected_item"]` | `session["search_results"][0]` |
| suggest_outfit | `session["outfit_suggestion"]` | `session["selected_item"]`, `session["wardrobe"]` |
| create_fit_card | `session["fit_card"]` | `session["outfit_suggestion"]`, `session["selected_item"]` |

`session["error"]` is written only on early-exit (empty search results) and read by the caller (`app.py`) to decide whether to show the fit card or the error message.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | Returns `[]` — no listings matched the description/size/price filters | Set `session["error"] = "No listings found matching your search. Try broader keywords or remove the size/price filter."` and `return session` immediately. `fit_card` and `outfit_suggestion` remain `None`. |
| `suggest_outfit` | `wardrobe["items"]` is an empty list | The tool itself handles this by calling the LLM with a general-styling prompt instead of a wardrobe-specific one. The loop does not special-case an empty wardrobe — it just stores whatever non-empty string the tool returns. |
| `create_fit_card` | `outfit` is an empty or whitespace-only string | The tool itself returns a descriptive error string (e.g. `"Unable to generate fit card: outfit suggestion was missing."`). The loop stores that string in `session["fit_card"]` and the UI displays it as the fit card panel. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  User (app.py)                                                          │
│  query: "vintage graphic tee under $30"                                 │
│  wardrobe: {items: [...]}                                               │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ run_agent(query, wardrobe)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Planning Loop (agent.py)                                               │
│                                                                         │
│  Step 1 — Parse query (regex)                                           │
│       description = "vintage graphic tee"                               │
│       size        = None                                                │
│       max_price   = 30.0                                                │
│       session["parsed"] = {description, size, max_price}               │
│                │                                                        │
│                ▼                                                        │
│  Step 2 — search_listings(description, size, max_price)                 │
│       ┌────────────────────────────────────┐                           │
│       │  data/listings.json (40 items)     │                           │
│       │  filter by price ≤ 30.0            │                           │
│       │  filter by size (skipped: None)    │                           │
│       │  score by keyword overlap          │                           │
│       │  sort best-first                   │                           │
│       └──────────────┬─────────────────────┘                           │
│                      │ returns list[dict]                               │
│                      ▼                                                  │
│       session["search_results"] = [...]                                 │
│                      │                                                  │
│            ┌─────────┴──────────┐                                      │
│            │ results == [] ?    │                                       │
│           YES                  NO                                       │
│            │                   │                                        │
│            ▼                   ▼                                        │
│  session["error"] =   session["selected_item"] = results[0]            │
│  "No listings found"           │                                        │
│  return session ──────────────────────────────────────────► [EARLY EXIT]│
│                                │                                        │
│  Step 3 — suggest_outfit(selected_item, wardrobe)                       │
│       ┌────────────────────────────────────┐                           │
│       │  Groq LLM                          │                           │
│       │  wardrobe empty?                   │                           │
│       │   YES → general styling prompt     │                           │
│       │   NO  → outfit-with-wardrobe prompt│                           │
│       └──────────────┬─────────────────────┘                           │
│                      │ returns str                                      │
│                      ▼                                                  │
│       session["outfit_suggestion"] = "Pair with..."                    │
│                      │                                                  │
│  Step 4 — create_fit_card(outfit_suggestion, selected_item)             │
│       ┌────────────────────────────────────┐                           │
│       │  Groq LLM (higher temperature)     │                           │
│       │  outfit empty?                     │                           │
│       │   YES → error string (no raise)    │                           │
│       │   NO  → casual OOTD caption        │                           │
│       └──────────────┬─────────────────────┘                           │
│                      │ returns str                                      │
│                      ▼                                                  │
│       session["fit_card"] = "Found this vintage band tee..."           │
│       session["error"]    = None                                        │
│                      │                                                  │
│                      ▼                                                  │
│              return session                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  app.py (handle_query)                                                  │
│  if session["error"]: show error in panel 1, panels 2–3 empty          │
│  else: panel 1 = selected_item details                                  │
│         panel 2 = outfit_suggestion                                     │
│         panel 3 = fit_card                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

I'll implement each tool separately using Claude Code, one at a time, before connecting them.

**Tool 1 — `search_listings`:**
- **Input to Claude:** The Tool 1 spec from this file (what it does, exact parameters, return shape, failure behavior) plus the note that data must come from `load_listings()` in `utils/data_loader.py`.
- **Expected output:** A `search_listings()` function in `tools.py` that calls `load_listings()`, filters by `max_price` and `size` (case-insensitive), scores each remaining listing by counting how many words from `description` appear in `title + description + style_tags`, drops zero-score results, and returns the list sorted by score descending.
- **Verification:** Call it directly from a Python shell with three cases — (1) `search_listings("vintage graphic tee", None, 30.0)` should return at least one result with "vintage" or "tee" in the title/tags; (2) `search_listings("designer ballgown", "XXS", 5.0)` should return `[]`; (3) `search_listings("jacket", "M", None)` should return only listings where the size field contains "M" (case-insensitive). Check that the first result is more keyword-relevant than the last.

**Tool 2 — `suggest_outfit`:**
- **Input to Claude:** The Tool 2 spec from this file (parameters, return type, empty-wardrobe fallback) plus the wardrobe dict structure (`{"items": [...]}` with each item having `name`, `category`, `colors`, `style` fields) from `data/wardrobe_schema.json`.
- **Expected output:** A `suggest_outfit()` function that checks `len(wardrobe["items"]) == 0`, branches on that to build one of two Groq prompts (general styling vs wardrobe-specific), calls `_get_groq_client()`, and returns the LLM's response string.
- **Verification:** Call `suggest_outfit(listings[0], get_example_wardrobe())` and confirm the response names at least one wardrobe item from the example wardrobe by name. Then call it with `get_empty_wardrobe()` and confirm the response is non-empty and contains general styling language (not a reference to specific wardrobe pieces).

**Tool 3 — `create_fit_card`:**
- **Input to Claude:** The Tool 3 spec from this file (parameters, caption style requirements, the empty-outfit guard) plus the exact listing dict field names (`title`, `price`, `platform`) so the prompt template references the right keys.
- **Expected output:** A `create_fit_card()` function that guards against empty/whitespace `outfit`, builds a prompt asking for a 2–4 sentence casual OOTD caption mentioning item name, price, and platform once each, calls the Groq API with `temperature=0.9` (higher than the default for variety), and returns the caption string.
- **Verification:** Call it twice with the same inputs and confirm the two captions differ (higher temperature working). Confirm both mention the item title, the price as a dollar amount, and the platform name. Call it with `outfit=""` and confirm it returns a non-empty error string rather than raising.

---

**Milestone 4 — Planning loop and state management:**

- **Input to Claude:** The Planning Loop section of this file (the 6-step sequence with exact branch conditions), the State Management table (which key is written/read at each step), and the Architecture diagram — all three together so Claude can cross-check that the implementation matches the data-flow arrows.
- **Expected output:** A completed `run_agent()` function in `agent.py` that: uses regex to parse `description`/`size`/`max_price` from the query string; calls each tool in order; writes results into the correct session keys; short-circuits with `session["error"]` and `return session` when `search_results` is empty; and returns the session after `create_fit_card`.
- **Verification:** Run `python agent.py` directly — it has two built-in test cases. The happy-path case (`"looking for a vintage graphic tee under $30"`) should print a non-None `selected_item`, a non-empty `outfit_suggestion`, and a non-empty `fit_card`. The no-results case (`"designer ballgown size XXS under $5"`) should print a non-None `error` message and nothing for `fit_card`. If either case fails, diff the session dict against the State Management table to find which key was not written correctly.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**What FitFindr needs to do:** FitFindr takes a natural-language clothing request, finds the best-matching secondhand listing, and styles it into a complete outfit the user could actually wear. The parsed query triggers `search_listings`; the top listing it returns triggers `suggest_outfit` (which falls back to general styling advice when the wardrobe is empty); and that outfit triggers `create_fit_card`. If `search_listings` returns nothing, the agent stops there with a helpful "no matches" message instead of feeding empty input downstream, and the LLM-backed tools degrade to a graceful fallback string rather than raising.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:** The planning loop parses the query into `description="vintage graphic tee"`, `size=None`, `max_price=30.0` and calls `search_listings("vintage graphic tee", None, 30.0)`. This filters listings to those at or under $30, scores the rest by keyword overlap, and returns the matches sorted best-first.

**Step 2:** The agent selects the top-ranked listing (e.g. a vintage band tee at $24) and calls `suggest_outfit(selected_item, wardrobe)`. Because the example wardrobe is non-empty, the LLM is given the tee plus the user's pieces (baggy jeans, chunky sneakers) and returns 1–2 concrete outfit combinations naming those items.

**Step 3:** The agent passes that outfit string and the listing into `create_fit_card(outfit, selected_item)`, which prompts the LLM (at higher temperature) for a casual 2–4 sentence caption mentioning the item, price, and platform once each.

**Final output to user:** Three panels — the chosen listing's details, the outfit suggestion, and the shareable fit card. (Had nothing matched in Step 1, the user would instead see only a "no matching listings found" message and the other two panels would be empty.)
