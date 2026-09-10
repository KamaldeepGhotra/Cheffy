# Cheffy — Meal Prep App Design

## Purpose

Two roommates meal prep together weekly (2-3 days worth), then split
meals to avoid eating the same thing repeatedly. Current pain points:
tracking what groceries are on hand, figuring out what to buy vs.
already have, tracking calories/nutrition, and tracking recipes.

## Architecture

- **Frontend**: React, deployed on Vercel (free tier). Long-term goal
  of iOS/Android apps later — frontend built with this in mind but
  not started now.
- **Backend**: Python + FastAPI, deployed on Render (free tier).
- **Database**: Supabase (hosted Postgres, free tier). Shared across
  both roommates, reachable from anywhere. Supabase auth used for the
  two user accounts.
- **AI**: Google Gemini API (free tier) used for recipe lookup —
  given a dish name/craving, returns structured ingredients (with
  quantity + unit), instructions, and nutrition facts per serving.
  Called through a single backend function (`get_recipe_info(query)`)
  so the implementation can later be swapped for a self-hosted local
  model without touching any other part of the app.

## Data Model

### `Ingredient` (canonical list)
- `id`
- `name` (e.g. "chicken breast")
- `category` (e.g. produce, protein, dairy — for grouping/UI)
- `default_unit` (e.g. lb, oz, each)

This table is the single source of truth for ingredient identity.
Both inventory items and recipe ingredients reference it by id, so
"chicken" typed once and "chicken" typed again always resolve to the
same row — no duplicate-spelling drift.

### `InventoryItem`
- `id`
- `ingredient_id` (FK -> Ingredient)
- `household_id`
- `quantity`
- `unit`
- `added_date`

### `Recipe`
- `id`
- `name`
- `instructions` (text)
- `ingredients` (list of `{ingredient_id, quantity, unit}`)
- `calories`, `protein`, `fat`, `carbs` (per serving)
- `source` (`ai_generated` | `manual`)
- `created_by` (user id)

### `MealPlan`
- `id`
- `week_start_date`
- `entries`: list of `{recipe_id, servings, assigned_to (user id), day}`

## Core Flows

### 1. Add to inventory
User types an ingredient name. Autocomplete queries the canonical
`Ingredient` table using fuzzy search (e.g. trigram similarity via
Postgres `pg_trgm`, or a simple fuzzy-match library). User either:
- selects a matching existing ingredient, or
- confirms creating a new canonical ingredient if no good match exists.

User then sets quantity + unit; row saved to `InventoryItem`.

### 2. Search for a recipe
User types a dish name or craving. Backend calls Gemini asking for a
structured JSON response: ingredient list (name + quantity + unit),
step-by-step instructions, and nutrition facts per serving. Backend
then maps each returned ingredient name onto the canonical
`Ingredient` table using the same fuzzy-match logic as inventory
(reusing the same matching module) — creating new canonical entries
only when no reasonable match exists. Result saved as a `Recipe` and
shown to the user.

### 3. Weekly grocery list
User selects one or more recipes for the week (with servings). Backend
aggregates total ingredient quantities needed across selected recipes,
subtracts what's already in `InventoryItem`, and returns two lists:
what's already covered by inventory, and what still needs to be
bought.

### 4. Meal plan / split
User manually assigns which recipe (and how many servings) each
roommate eats on which day. No automatic rotation/optimization logic
— kept manual and simple for now.

### 5. Recipe detail view
Each recipe shows full instructions and nutrition facts
(calories/protein/fat/carbs per serving).

## Error Handling

- Gemini API call fails or times out: show an error in the UI, allow
  retry. Do not crash the search flow.
- Ambiguous ingredient match (multiple close candidates, or none):
  surface the ambiguity to the user for manual confirmation rather
  than silently guessing.

## Testing Approach

- Unit tests on the ingredient normalization/fuzzy-matching module —
  this is shared by both the inventory and recipe-import flows and is
  the most bug-prone piece.
- Backend tests for grocery-list aggregation math (recipe quantities
  minus inventory quantities).
- Gemini API calls mocked in tests (no live API calls in test suite).
- Manual browser verification of core flows: add inventory item,
  search + save a recipe, generate a weekly grocery list.

## Explicitly Out of Scope (for now)

- Barcode scanning
- Automatic meal-rotation/optimization algorithm
- Push notifications
- Support for more than one household/more than two users
- Native iOS/Android apps (planned later, not part of this build)

These may be added later as separate, individually-scoped features.

## Notes

- No AI-authorship attribution (commit co-author lines, README
  credits, etc.) should appear in this repository — commits and
  project history should read as authored by the two roommates.
