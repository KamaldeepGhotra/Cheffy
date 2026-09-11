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

## Decision (2026-09-11)

Settled after brainstorming; implemented on `feature/inventory-ux`, PR #1.

**Smart single input.** One text box parses `<quantity> <unit> <name>` on
every keystroke and shows a preview line ("Adding ground beef · 3 lb")
before submit. Rules, in `frontend/src/parseInventoryInput.js`:

- Leading number is the quantity. Accepts integers, decimals, fractions
  (`1/2`) and mixed numbers (`1 1/2`). No number means quantity 1.
- The next word is checked against the unit list. If it matches, it's
  the unit; if not, it stays part of the name and the preview warns
  that `each` was used.
- A leading "of" after the unit is dropped (`2 cups of rice`).
- Everything left is the ingredient name, which feeds the existing
  autocomplete endpoint. Picking a suggestion rewrites the input with
  the canonical name but keeps quantity and unit.

**Fixed unit list with aliases**, in `frontend/src/units.js`: lb, oz, g,
kg, cup, tbsp, tsp, ml, l, each, clove, can, bag, box, bunch, pack,
slice, piece. Aliases like `lbs`, `pounds`, `cups`, `tablespoons`
normalize to the canonical form so the grocery-list aggregation (which
keys on ingredient + unit) doesn't fragment. This is the only place
unit spelling is enforced; the backend still stores whatever string it
receives.

**Recent-add chips.** The last 8 distinct adds are kept in
`localStorage` under `cheffy.recentAdds`. Tapping a chip re-adds the
same quantity and unit. Chosen over a backend "frequent items" endpoint
to keep the change frontend-only; revisit if the two households' chips
should be shared.

**Rejected:** separate fields with a unit dropdown (slower for bulk
entry, which is the whole point), and a "fields" fallback toggle next to
the smart input (extra surface for a parser that hasn't shown it needs
one yet — add it if real use turns up inputs it can't handle).

**Also shipped:** per-row remove button using the existing
`DELETE /inventory/{id}`, and a base stylesheet (`frontend/src/index.css`)
because the app set no colors at all and was unreadable in dark mode.

**Tests:** parser has vitest coverage (`cd frontend && npm test`). UI
wiring verified manually in the browser, per step 4 above.
