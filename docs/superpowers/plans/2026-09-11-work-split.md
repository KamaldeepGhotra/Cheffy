# Cheffy — Next-Phase Work Split

The core loop (inventory, AI recipe search, grocery list) is done and working on `main` — see [2026-09-10-core-loop.md](2026-09-10-core-loop.md). This document splits the next round of feature work into two independent workstreams so you and your teammate can each hand one .md file to your own Claude and start immediately, in parallel, on separate branches.

## Pick one workstream each

### Workstream 1: Recipe Recommendations + Auto Grocery List

**Read this and start:** [2026-09-11-recipe-recommendations-plan.md](2026-09-11-recipe-recommendations-plan.md)

**Branch:** `feature/recipe-recommendations`

This is a fully-specified implementation plan (models, endpoints, exact code, tests) — your Claude can read it and start implementing directly with `superpowers:subagent-driven-development` or `superpowers:executing-plans`. It adds:
- Recipe search page defaults to showing recipes ranked by % of ingredients you already have in inventory
- A new `POST /recipes/suggest` endpoint that asks Gemini for recipes based on your current inventory (not just a typed dish name)
- Grocery list page gets a recipe picker (checkboxes) instead of typing in recipe IDs by hand

### Workstream 2: Inventory Add UX Redesign

**Read this and start:** [2026-09-11-inventory-ux-brief.md](2026-09-11-inventory-ux-brief.md)

**Branch:** `feature/inventory-ux`

This is a **brief, not a locked plan** — the current inventory-add flow (separate name/quantity/unit fields) is clunky, and the actual redesign is intentionally left open. Your Claude should brainstorm a specific design with you before implementing it.

## Why split this way

The two workstreams touch almost entirely different files:
- Workstream 1 touches: `backend/app/recipe_ranking.py` (new), `backend/app/gemini_client.py`, `backend/app/routers/recipes.py`, `backend/app/schemas.py`, `frontend/src/pages/RecipeSearchPage.jsx`, `frontend/src/pages/GroceryListPage.jsx`, `frontend/src/api.js`
- Workstream 2 touches: `frontend/src/pages/InventoryPage.jsx`, possibly `backend/app/routers/ingredients.py` if the design calls for it

The only shared file is `frontend/src/api.js` (Workstream 1 adds `listRecipes`/`suggestRecipes`; Workstream 2 might touch `addInventoryItem`/`searchIngredients`) — expect at most a small, easy merge conflict there since both are pure additions/edits to different functions in the same file, not the same lines.

## Merging back

- [ ] Whoever finishes first merges their branch into `main`
- [ ] The second person rebases or merges `main` into their branch before finishing, resolving the small `api.js` conflict if it comes up (keep both sets of changes — they're additive)
- [ ] Run `cd backend && python -m pytest -v` on `main` after both are merged — should still be all-green
- [ ] Manually re-verify the full app in the browser after merge (both features together)

## Coordination notes

- If either Claude session hits a design question not answered by its .md file, decide it together rather than guessing independently on each branch.
- No AI-authorship attribution anywhere in this repo (commit messages, code, README) — carries forward from the core loop's constraints.
- `uvicorn --reload` has been unreliable in this project — if backend changes don't seem to take effect while testing, fully stop and restart the server rather than trusting auto-reload.
