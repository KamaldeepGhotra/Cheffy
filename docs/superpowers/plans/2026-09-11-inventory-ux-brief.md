# Inventory Add UX — Design Brief

**This is a brief, not a locked implementation plan.** Read it, then use the `superpowers:brainstorming` skill (or equivalent design-then-approve process) to propose a design to your human partner before implementing. Do not start writing code from this document directly — it intentionally leaves the actual UX undecided.

## Read first

- Spec: [docs/superpowers/specs/2026-09-10-meal-prep-app-design.md](../specs/2026-09-10-meal-prep-app-design.md)
- Core loop plan (context on what already exists): [docs/superpowers/plans/2026-09-10-core-loop.md](2026-09-10-core-loop.md)

The core loop is done and working. `InventoryPage.jsx` currently has three separate text inputs (ingredient name with autocomplete, a raw quantity number field, a raw unit text field) and an Add button. It works, but it's clunky — typing a unit as free text, three separate fields to fill for one item, no quick way to add something you add often.

## The problem

The current inventory-add flow is: type ingredient name → wait for autocomplete → maybe click a suggestion → tab to quantity → type a number → tab to unit → type a unit string → click Add. That's a lot of friction for what should be a fast, frequent action (you're doing this every time you unpack groceries).

## What to design

A better inventory-add flow. Some directions worth considering (not prescriptive — this is what brainstorming is for):
- Combining fields (e.g. one smart input like "2 lb chicken" that gets parsed) vs. keeping them separate but faster to fill (e.g. quantity/unit as a stepper or dropdown of common units instead of free text)
- Quick-add for frequently-used ingredients (e.g. a row of buttons/chips for common items that adds with sensible defaults in one tap)
- Whether unit should be a free-form text field at all, or a constrained dropdown (lb, oz, cup, clove, each, etc.) — a dropdown avoids "lbs" vs "lb" vs "pounds" fragmentation that the ingredient-matching system doesn't currently handle for units (only ingredient names are fuzzy-matched, not units)

## Constraints

- Must still call the existing backend: `POST /inventory` with `{household_id, ingredient_name, quantity, unit}` — this plan is frontend-only unless you find a real reason the backend contract needs to change (if so, that's worth raising with your human partner before changing it, since the other in-progress workstream — recipe recommendations — also touches `backend/app/routers/recipes.py` and `schemas.py`, not inventory, so there's low collision risk, but any inventory endpoint change should still be called out).
- Must still use `GET /ingredients/search?q=&limit=` for autocomplete (or propose changing it — it's a small, self-contained endpoint in `backend/app/routers/ingredients.py`).
- Keep it framework-free like the rest of the frontend (no new UI library) unless you make a case for one — the existing frontend is deliberately dependency-light (plain React + Vite, no styling library, no component library).
- Global constraint from the core loop still applies: no AI-authorship attribution anywhere in this repo (commit messages, code comments, README).

## Branch

Work on `feature/inventory-ux`, branched from `main` (which has the working core loop).

## Process

1. Read the spec and core-loop plan linked above.
2. Run `superpowers:brainstorming` (or ask your human partner directly) to settle on a specific design — what fields, what interaction, any backend changes.
3. Get explicit approval on the design before implementing (this is a real UX decision, not a bug fix).
4. Implement with tests where there's real logic (e.g. a parser, if you go the "smart input" direction) — plain UI wiring doesn't need automated tests, same as the rest of this frontend, but verify manually in a browser before calling it done.
5. Commit as you go, no AI-authorship attribution.
