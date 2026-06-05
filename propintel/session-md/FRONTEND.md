# PropIntel — Frontend Direction

## Why we pivoted

The original plan used Streamlit + Pydeck as the frontend. This was the right
call for rapid prototyping and getting a working choropleth map on screen fast.
After building the MVP (Session 7), it became clear that the planned "address
intelligence" UX — type an address, pan the map, explore suburb and school zone
context, ask the AI — cannot be delivered well in Streamlit.

Streamlit's execution model re-runs the entire script on every interaction.
For an address-search-then-explore flow this creates flicker, view state resets,
and laggy layer toggles. Workarounds with `st.session_state` exist but produce
janky UX. The intended experience — one unified map, search, click, data panel,
AI chat — is a single-page app pattern. That is React's native territory.

The decision was made after Session 7 to:
- Keep the Streamlit MVP as a working demo of the data pipeline
- Rebuild the frontend in React + Vite + MapLibre GL JS + deck.gl after the
  data layer is complete (post-Session 8)
- Keep FastAPI and the entire backend unchanged

---

## Stack decisions

| Layer | Choice | Reason |
|---|---|---|
| Framework | React via Vite | Lightweight, no SSR overhead, fast local dev. Next.js rejected — no need for its router or API routes when FastAPI handles the API. |
| Basemap | MapLibre GL JS | Open-source Mapbox GL JS fork (post-2021 licence split). WebGL, vector tiles, smooth 60fps pan/zoom. Passes rendering to AMD GPU on Mac Intel. |
| Data layers | deck.gl | Uber's WebGL layer library. GeoJsonLayer, ScatterplotLayer, TextLayer — near-direct port from current Pydeck code. Combined with MapLibre for basemap. |
| Geocoding | Nominatim (OSM) via FastAPI | No API key. Routed through FastAPI, not called directly from the browser. (might also consider VicMap Address and VicMap Property - TBD) |
| Planning overlays | Server-side identify | 650MB GeoJSON is not loaded into the browser. FastAPI runs ST_Intersects in DuckDB and returns text results (e.g. "Heritage Overlay HO1"). |
| School zone geometry | Lazy-loaded GeoJSON | FastAPI serves zone geometry from DuckDB via ST_AsGeoJSON on demand when the user toggles the layer. |

---

## UX flows

### 1. Browse the map (default)
- Melbourne choropleth on load. Default metric: median house price.
- Layer toggles: school zones (primary / secondary + year level), transit stops.
- Metric toggle: price, affordability ratio, SEIFA, price growth, clearance rate.
- Click a suburb polygon → sidebar Zone 1 populates.

### 2. Search for a suburb
- Autocomplete resolves to SAL name via FastAPI + DuckDB.
- Map pans and zooms to suburb, boundary highlighted.
- Sidebar Zone 1 populates with suburb data + AI highlight summary +
  comparable suburbs.

### 3. Search for a school
- Autocomplete resolves to school name via ACARA + school_profiles mart.
- Map pans to school location, catchment zone boundary shown.
- Sidebar shows school profile: name, type, enrolment, size, student-teacher ratio,
  ICSEA (with explicit caveat that ICSEA is not a performance measure). Plus VCAA results for sec schools.
- Note: no primary school performance data available. VCAA results for
  secondary schools only.

### 4. Search for an address
- Address geocoded to lat/lng via Nominatim (might also consider VicMap Address and VicMap Property - TBD).
- Map pans to pin. Suburb boundary and school zone optionally toggled.
- Point-in-polygon lookup: which suburb, which school zone, which planning
  overlays — ST_Intersects in DuckDB, served by FastAPI.
- Sidebar Zone 1: suburb context, school zone, planning overlays, metrics,
  AI highlight summary.
- Sidebar Zone 2: "Generate intelligence report" button → RAG + Claude API
  → full narrative. Explicit click, not auto-fired (cost management).

### 5. Ask PropIntel AI
- Dormant text box at bottom of sidebar until user submits.
- LangGraph agent: parse criteria → filter suburbs in DuckDB → retrieve
  ChromaDB profiles → rank with Claude API → return suburb slugs + reasoning.
- Map highlights matching suburbs. Sidebar shows ranked list with reasoning.
- Multi-turn: agent holds session state (current address, current suburb,
  prior criteria) across turns via LangGraph state graph.

---

## Sidebar zones

**Zone 1 — context (always visible after any selection)**
Suburb name, metrics table, AI highlight summary (pre-generated at pipeline time,
served statically), comparable suburbs as clickable links. Fast — no live AI call.

**Zone 2 — intelligence (address search only)**
"Generate intelligence report" button. On click: RAG retrieval → Claude API
generation → narrative report. Persists for session.

**Zone 3 — AI agent (dormant until used)**
Free-text input. LangGraph agent. Response can update Zone 1 (map highlights)
or Zone 2 (new report). Layout does not change — zones receive new content.

---

## AI layer integration

| Feature | Mechanism | When |
|---|---|---|
| Highlight summary | Claude API, pre-generated at pipeline time | On any suburb/address selection — no live call |
| Comparable suburbs | ChromaDB nearest-neighbour, no LLM | On any suburb/address selection |
| Intelligence report | RAG + Claude API (live) | On explicit button click after address search |
| Agent (criteria search) | LangGraph + Claude API (live) | On AI box submit |

Pre-generation approach for summaries: `rag/generate_summaries.py` runs once
at pipeline time, stores generated strings in DuckDB, FastAPI serves statically.
Re-run quarterly when mart data refreshes. Estimated cost: ~$1.50 per full run
across ~550 Melbourne suburbs.

---

## Data caveats (surfaced in UI)

- **School performance:** VCAA results for secondary only. No primary performance
  data. ICSEA = socioeconomic intake, not results. Displayed with explicit caveat.
- **Property prices:** VicGov quarterly medians. Not real-time.

---

## Where the Streamlit frontend stands

`propintel/frontend/map.py` is retained as a working demo of the data pipeline.
It will not be extended beyond its current state (house price choropleth + school
zone toggle). The React frontend replaces it as the primary user-facing product.

---

## Where this fits in the session plan

Frontend rebuild begins after Session 8 (complete data layer). 
Sessions 9-19 to be re-planned after Session 8 completes. Original session
content remains as reference but ordering and scope will change significantly.
Key anchors that remain: RAG, LangGraph agent, MCP server, Prefect, GCP deploy.
FastAPI and the backend are mostly unaffected by the frontend swap.

Refer to this document for frontend decisions before starting any UI-related session.
