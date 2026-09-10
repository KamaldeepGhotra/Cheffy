# Cheffy Core Loop — Work Split (You + Roommate)

This document splits the tasks in
[2026-09-10-core-loop.md](2026-09-10-core-loop.md) between two people
working in parallel on separate branches, each with their own Claude
session. Both people should have the spec
([2026-09-10-meal-prep-app-design.md](../specs/2026-09-10-meal-prep-app-design.md))
and the full plan ([2026-09-10-core-loop.md](2026-09-10-core-loop.md))
available — this file only tells each person which tasks are theirs and
how the pieces come back together.

## Why it's split this way

Tasks 1-3 (backend scaffold, database + `Ingredient` model, fuzzy-matching
module) are the foundation every other task imports from
(`app/db.py`, `app/models.py`, `app/matching.py`). They must exist before
anything else can be built, and they're small — one person does them
solo first.

After that, the remaining backend tasks split into two groups that don't
touch each other's files:

- **Ingredients & inventory** (Tasks 4-5): `app/routers/ingredients.py`,
  `app/routers/inventory.py`
- **AI recipe & grocery list** (Tasks 6-8): `app/gemini_client.py`,
  `app/routers/recipes.py`, `app/routers/grocery.py`

Both groups add one line each to `app/main.py` (a new `app.include_router(...)`
call) — this is the only expected merge conflict, and it's trivial to
resolve (keep both lines).

Frontend (Task 9) and end-to-end verification (Task 10) happen after both
backend branches are merged, since the frontend calls all four routers.

## Step 0: Foundation (one person, first)

**Branch:** work directly on `main`

**Owner:** whoever gets to it first — this only takes Tasks 1-3 from the
plan.

- [ ] Do Task 1 (Backend Scaffold) from the plan
- [ ] Do Task 2 (Database Setup + Ingredient Model) from the plan
- [ ] Do Task 3 (Ingredient Fuzzy-Matching Module) from the plan
- [ ] Push to `main`
- [ ] Tell the other person it's ready to branch from

Do not start Step 1A or Step 1B until this is on `main` — both depend on
`app/db.py`, `app/models.py`, and `app/matching.py` existing.

## Step 1A: Ingredients & Inventory

**Branch:** `feature/inventory`

**Tasks:** Task 4 (Ingredient Autocomplete Endpoint), Task 5 (Inventory
Model + CRUD Endpoints) — from the plan, full detail there.

**Files this branch owns:**
- `backend/app/schemas.py` (adds `IngredientMatch`, `InventoryItemCreate`, `InventoryItemOut`)
- `backend/app/routers/ingredients.py`
- `backend/app/routers/inventory.py`
- `backend/app/models.py` (adds `InventoryItem` — appends only, doesn't touch `Ingredient`)
- `backend/app/main.py` (adds `app.include_router(ingredients.router)` and `app.include_router(inventory.router)`)
- `backend/tests/test_ingredients_router.py`, `backend/tests/test_inventory_router.py`

- [ ] Branch from `main`: `git checkout -b feature/inventory`
- [ ] Do Task 4 from the plan
- [ ] Do Task 5 from the plan
- [ ] Push branch, open PR against `main`

## Step 1B: AI Recipe Search & Grocery List

**Branch:** `feature/recipe-grocery`

**Tasks:** Task 6 (Gemini Recipe Client), Task 7 (Recipe Model + Search
Endpoint), Task 8 (Grocery List Endpoint) — from the plan, full detail
there.

**Files this branch owns:**
- `backend/app/gemini_client.py`
- `backend/app/schemas.py` (adds `RecipeSearchRequest`, `RecipeIngredientOut`, `RecipeOut`, `GroceryListRequest`, `GroceryLine`, `GroceryListResponse`)
- `backend/app/routers/recipes.py`
- `backend/app/routers/grocery.py`
- `backend/app/models.py` (adds `Recipe`, `RecipeIngredient` — appends only, doesn't touch `Ingredient`/`InventoryItem`)
- `backend/app/main.py` (adds `app.include_router(recipes.router)` and `app.include_router(grocery.router)`)
- `backend/tests/test_gemini_client.py`, `backend/tests/test_recipes_router.py`, `backend/tests/test_grocery_router.py`

- [ ] Branch from `main`: `git checkout -b feature/recipe-grocery`
- [ ] Do Task 6 from the plan
- [ ] Do Task 7 from the plan
- [ ] Do Task 8 from the plan
- [ ] Push branch, open PR against `main`

**Note:** you'll need a `GEMINI_API_KEY` to test Task 6/7 for real (get a
free one from Google AI Studio) — but the plan's tests mock the Gemini
call, so the test suite passes without a real key.

## Step 2: Merge both branches

**Owner:** whoever finishes first, or do it together

- [ ] Merge `feature/inventory` into `main`
- [ ] Merge `feature/recipe-grocery` into `main`
- [ ] Resolve the expected conflict in `backend/app/main.py` — keep all
      four `app.include_router(...)` lines, plus the imports for all four
      router modules
- [ ] Also check `backend/app/schemas.py` and `backend/app/models.py` for
      the same kind of trivial append-only conflict (both branches add
      classes to the end of these files) — keep both branches' additions
- [ ] Run `cd backend && python -m pytest -v` on `main` — all tests from
      both branches should pass together

## Step 3: Frontend + End-to-End (together, after merge)

**Branch:** work directly on `main`, or a short-lived `feature/frontend`

**Tasks:** Task 9 (Minimal Frontend Skeleton), Task 10 (End-to-End Manual
Verification) — from the plan, full detail there.

Can be split further if useful: one person does `InventoryPage.jsx`, the
other does `RecipeSearchPage.jsx` + `GroceryListPage.jsx` — they're
separate files with no shared state, wired together in `App.jsx` at the
end. For two files vs. one, doing this one together is probably faster
than coordinating a sub-split.

- [ ] Do Task 9 from the plan
- [ ] Do Task 10 from the plan (manual walkthrough)
- [ ] Push to `main`

## Coordination notes

- Both people should read the spec and the full plan file before
  starting — this document only assigns task numbers to people, it
  doesn't repeat the implementation detail.
- If either person's Claude session hits a design question not answered
  by the spec or plan, that's a real gap — decide together rather than
  guessing independently on each branch (avoids the two branches
  contradicting each other on shared assumptions).
- Commit messages and PR descriptions should read as your own work — no
  AI-authorship attribution, per the project's global constraint (see
  the plan's Global Constraints section).
