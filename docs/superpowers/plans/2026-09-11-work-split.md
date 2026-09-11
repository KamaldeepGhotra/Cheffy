# Cheffy — Next-Phase Work Split

The core loop (inventory, AI recipe search, grocery list) is done and working on `main` — see [2026-09-10-core-loop.md](2026-09-10-core-loop.md). This document splits the next round of feature work into two independent workstreams so you and your teammate can each hand one .md file to your own Claude and start immediately, in parallel, on separate branches.

## Assignments

| Workstream | Owner | Branch | Status |
|---|---|---|---|
| 1. Recipe Recommendations + Auto Grocery List | **Kam** | `feature/recipe-recommendations` | In progress |
| 2. Inventory Add UX Redesign | **Andreas** | `feature/inventory-ux` | Done, PR #1 |
| 3. Meal Plan | **Andreas** | `feature/meal-plan` | Done, PR #2 (stacked on #1) |

Tell your Claude session which name you are at the start so it works
the right branch and doesn't touch the other person's files.

### Workstream 1: Recipe Recommendations + Auto Grocery List — Kam

**Read this and start:** [2026-09-11-recipe-recommendations-plan.md](2026-09-11-recipe-recommendations-plan.md)

**Branch:** `feature/recipe-recommendations`

This is a fully-specified implementation plan (models, endpoints, exact code, tests) — your Claude can read it and start implementing directly with `superpowers:subagent-driven-development` or `superpowers:executing-plans`. It adds:
- Recipe search page defaults to showing recipes ranked by % of ingredients you already have in inventory
- A new `POST /recipes/suggest` endpoint that asks Gemini for recipes based on your current inventory (not just a typed dish name)
- Grocery list page gets a recipe picker (checkboxes) instead of typing in recipe IDs by hand

### Workstream 2: Inventory Add UX Redesign — Andreas, DONE (PR #1)

**Read this and start:** [2026-09-11-inventory-ux-brief.md](2026-09-11-inventory-ux-brief.md)

**Branch:** `feature/inventory-ux`

Implemented and open as PR #1. The brief was intentionally open; the design that was chosen and what shipped are recorded in the "Decision" section at the bottom of the brief. Frontend-only, no backend contract changes.

### Workstream 3: Meal Plan — Andreas, DONE (PR #2)

**Read:** [2026-09-11-meal-plan.md](2026-09-11-meal-plan.md)

Spec flow 4. Picked up after Workstream 2 since it touched nothing in Workstream 1. **One overlap to know about:** it adds a minimal `GET /recipes` at the end of `backend/app/routers/recipes.py` so the meal-plan picker has a list to choose from. Workstream 1's Task 4 should extend that function (add `match_percentage`, sort) rather than add a second one. Details in the meal-plan doc.

## Why split this way

The two workstreams touch almost entirely different files:
- Workstream 1 touches: `backend/app/recipe_ranking.py` (new), `backend/app/gemini_client.py`, `backend/app/routers/recipes.py`, `backend/app/schemas.py`, `frontend/src/pages/RecipeSearchPage.jsx`, `frontend/src/pages/GroceryListPage.jsx`, `frontend/src/api.js`
- Workstream 2 touched: `frontend/src/pages/InventoryPage.jsx`, `frontend/src/parseInventoryInput.js` (new), `frontend/src/units.js` (new), `frontend/src/index.css` (new), `frontend/src/main.jsx`, `frontend/src/App.jsx`. No backend changes.

The only shared file is `frontend/src/api.js` (Workstream 1 adds `listRecipes`/`suggestRecipes`; Workstream 2 appended `deleteInventoryItem` at the end of the file) — expect at most a small, easy merge conflict there since both are pure additions, not the same lines.

## Merging back

- [ ] Kam reviews and merges PR #1 (`feature/inventory-ux`) into `main`, then PR #2 (`feature/meal-plan`)
- [ ] Kam merges `main` into `feature/recipe-recommendations` before finishing, resolving the small `api.js` conflict if it comes up (keep both sets of changes — they're additive)
- [ ] Run `cd backend && python -m pytest -v` on `main` after both are merged — should still be all-green
- [ ] Manually re-verify the full app in the browser after merge (both features together)

## Coordination notes

- If either Claude session hits a design question not answered by its .md file, decide it together rather than guessing independently on each branch.
- No AI-authorship attribution anywhere in this repo (commit messages, code, README) — carries forward from the core loop's constraints.
- `uvicorn --reload` has been unreliable in this project — if backend changes don't seem to take effect while testing, fully stop and restart the server rather than trusting auto-reload.
