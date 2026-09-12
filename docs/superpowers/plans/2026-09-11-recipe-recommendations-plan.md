> **Superseded on 2026-09-11.** The intent survives; the tasks do not. This plan's Tasks 1–6 were re-scoped once into K1–K6 and then again into **R1–R5** in [2026-09-11-mvp-plan.md](2026-09-11-mvp-plan.md), which is the source of truth. What changed since this file was written: recipes are ranked by inventory match with missing ingredients shown, search returns three unsaved candidates instead of one saved recipe, the grocery list derives from the week's meals (planned and scheduled) rather than a checkbox picker, and "planned" is a `meal_plan_entries` row with a null `day`. Read the MVP plan; use this file only for the worked code examples, and check every signature against §5 there before copying it.

# Recipe Recommendations + Auto Grocery List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "type a dish name, get one recipe" flow with a recipe library that defaults to showing recipes ranked by how much of each you can already make from inventory, seeded by asking Gemini for suggestions based on current inventory. Replace the grocery list's manual recipe-ID text entry with picking recipes from that library.

**Architecture:** A new `compute_match_percentage(db, recipe, household_id)` function (reused, like the ingredient-matching module) scores any recipe against current inventory. A new `POST /recipes/suggest` endpoint asks Gemini for several recipes built around the household's current inventory ingredients and saves them to the recipe library (the existing `Recipe`/`RecipeIngredient` tables — no schema change needed). A new `GET /recipes` endpoint lists the whole library with match percentages, sorted best-match-first. The frontend's Recipe Search page calls this on load (auto-suggesting if the library is empty) instead of requiring a manual search first; the Grocery List page gets a recipe picker instead of a text box for IDs.

**Tech Stack:** Same as the core loop — FastAPI + SQLAlchemy backend, React (Vite) frontend, Gemini for AI calls.

**Read first:**
- Spec: [docs/superpowers/specs/2026-09-10-meal-prep-app-design.md](../specs/2026-09-10-meal-prep-app-design.md)
- Core loop plan (what already exists, don't re-read task-by-task, just know it's there): [docs/superpowers/plans/2026-09-10-core-loop.md](2026-09-10-core-loop.md)

The core loop is done and working: `Ingredient`/`InventoryItem`/`Recipe`/`RecipeIngredient` models, `resolve_or_create_ingredient` (fuzzy ingredient matching), `get_recipe_info(query)` (single-dish Gemini lookup), routers for ingredients/inventory/recipes/grocery, and a 3-tab React frontend. This plan adds to it — it does not replace anything from the core loop.

## Global Constraints

- No AI-authorship attribution anywhere in this repo (commit messages, code comments, README).
- `GEMINI_API_KEY` read from environment, never hardcoded.
- Match percentage is computed by **ingredient presence only** (is there any inventory row for this ingredient_id, regardless of quantity/unit) — not a full quantity-aware check. This mirrors the core loop's own documented simplification (no unit conversion) and keeps this feature shippable; quantity-aware matching is a future improvement, not part of this plan.
- Household is a single hardcoded string `"roommates"` throughout (matches the core loop's existing convention — no multi-household support yet).
- Work happens on branch `feature/recipe-recommendations`, branched from `main` (which already has the working core loop on it).

---

## File Structure

```
backend/
  app/
    recipe_ranking.py          # NEW: compute_match_percentage()
    gemini_client.py            # MODIFY: add suggest_recipes()
    routers/
      recipes.py                 # MODIFY: add GET /recipes, POST /recipes/suggest
    schemas.py                    # MODIFY: add RecipeSuggestRequest, RecipeListItem
  tests/
    test_recipe_ranking.py         # NEW
    test_recipes_router.py          # MODIFY: add tests for the 2 new endpoints

frontend/
  src/
    api.js                            # MODIFY: add listRecipes(), suggestRecipes()
    pages/
      RecipeSearchPage.jsx              # REWRITE: default ranked list + suggest-on-empty
      GroceryListPage.jsx                 # REWRITE: recipe picker instead of ID text box
```

---

## Task 1: Match Percentage Module

**Files:**
- Create: `backend/app/recipe_ranking.py`
- Test: `backend/tests/test_recipe_ranking.py`

**Interfaces:**
- Consumes: `Recipe`, `RecipeIngredient`, `InventoryItem` models
- Produces: `compute_match_percentage(db: Session, recipe: Recipe, household_id: str) -> float` — returns 0-100. A recipe with zero ingredients returns 0.0 (avoid division by zero).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_recipe_ranking.py
from app.models import Ingredient, Recipe, RecipeIngredient, InventoryItem
from app.recipe_ranking import compute_match_percentage


def test_full_match_returns_100(db_session):
    chicken = Ingredient(name="chicken breast")
    rice = Ingredient(name="white rice")
    db_session.add_all([chicken, rice])
    db_session.flush()

    recipe = Recipe(name="Chicken Fried Rice", instructions="cook it")
    db_session.add(recipe)
    db_session.flush()
    db_session.add_all([
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=1, unit="lb"),
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=rice.id, quantity=2, unit="cup"),
    ])
    db_session.add_all([
        InventoryItem(ingredient_id=chicken.id, household_id="roommates", quantity=1, unit="lb"),
        InventoryItem(ingredient_id=rice.id, household_id="roommates", quantity=2, unit="cup"),
    ])
    db_session.commit()

    assert compute_match_percentage(db_session, recipe, "roommates") == 100.0


def test_partial_match_returns_correct_percentage(db_session):
    chicken = Ingredient(name="chicken breast")
    rice = Ingredient(name="white rice")
    db_session.add_all([chicken, rice])
    db_session.flush()

    recipe = Recipe(name="Chicken Fried Rice", instructions="cook it")
    db_session.add(recipe)
    db_session.flush()
    db_session.add_all([
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=1, unit="lb"),
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=rice.id, quantity=2, unit="cup"),
    ])
    db_session.add(InventoryItem(ingredient_id=chicken.id, household_id="roommates", quantity=1, unit="lb"))
    db_session.commit()

    assert compute_match_percentage(db_session, recipe, "roommates") == 50.0


def test_recipe_with_no_ingredients_returns_zero(db_session):
    recipe = Recipe(name="Empty Recipe", instructions="n/a")
    db_session.add(recipe)
    db_session.commit()

    assert compute_match_percentage(db_session, recipe, "roommates") == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_recipe_ranking.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.recipe_ranking'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/recipe_ranking.py
from sqlalchemy.orm import Session
from app.models import RecipeIngredient, InventoryItem, Recipe


def compute_match_percentage(db: Session, recipe: Recipe, household_id: str) -> float:
    recipe_ingredient_ids = {
        ri.ingredient_id
        for ri in db.query(RecipeIngredient).filter_by(recipe_id=recipe.id).all()
    }
    if not recipe_ingredient_ids:
        return 0.0

    inventory_ingredient_ids = {
        item.ingredient_id
        for item in db.query(InventoryItem).filter_by(household_id=household_id).all()
    }

    have_count = len(recipe_ingredient_ids & inventory_ingredient_ids)
    return (have_count / len(recipe_ingredient_ids)) * 100
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_recipe_ranking.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/recipe_ranking.py backend/tests/test_recipe_ranking.py
git commit -m "Add recipe match-percentage calculation"
```

---

## Task 2: Gemini Suggest-Recipes Function

**Files:**
- Modify: `backend/app/gemini_client.py`
- Modify: `backend/tests/test_gemini_client.py`

**Interfaces:**
- Produces: `suggest_recipes(ingredient_names: list[str], count: int = 3) -> list[dict]` — each dict has the same shape as `get_recipe_info`'s return (`name`, `instructions`, `ingredients`, `calories`, `protein`, `fat`, `carbs`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_gemini_client.py (append)
import json
from unittest.mock import patch, MagicMock
from app.gemini_client import suggest_recipes


FAKE_SUGGESTIONS_RESPONSE = json.dumps([
    {
        "name": "Garlic Rice Bowl",
        "instructions": "1. Cook rice. 2. Saute garlic. 3. Combine.",
        "ingredients": [
            {"name": "white rice", "quantity": 2, "unit": "cup"},
            {"name": "garlic", "quantity": 3, "unit": "clove"},
        ],
        "calories": 300, "protein": 6, "fat": 5, "carbs": 55,
    },
    {
        "name": "Chicken Stir Fry",
        "instructions": "1. Cook chicken. 2. Stir fry vegetables. 3. Combine.",
        "ingredients": [
            {"name": "chicken breast", "quantity": 1, "unit": "lb"},
            {"name": "garlic", "quantity": 2, "unit": "clove"},
        ],
        "calories": 400, "protein": 30, "fat": 10, "carbs": 20,
    },
])


@patch("app.gemini_client.genai.GenerativeModel")
def test_suggest_recipes_parses_list_response(mock_model_cls):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text=FAKE_SUGGESTIONS_RESPONSE)
    mock_model_cls.return_value = mock_model

    result = suggest_recipes(["white rice", "garlic", "chicken breast"], count=2)

    assert len(result) == 2
    assert result[0]["name"] == "Garlic Rice Bowl"
    assert result[1]["ingredients"][0]["name"] == "chicken breast"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_gemini_client.py -v`
Expected: FAIL with `ImportError: cannot import name 'suggest_recipes'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/gemini_client.py (append)

SUGGEST_PROMPT_TEMPLATE = """You are a recipe assistant. Using primarily these ingredients \
that are already on hand: {ingredients}, suggest {count} different recipes that make good use \
of them (they may also need a few additional common ingredients). Respond with ONLY a JSON \
array (no markdown, no commentary) where each element has this exact shape:
{{
  "name": string,
  "instructions": string,
  "ingredients": [{{"name": string, "quantity": number, "unit": string}}],
  "calories": number,
  "protein": number,
  "fat": number,
  "carbs": number
}}
Nutrition values are per serving.
"""


def suggest_recipes(ingredient_names: list[str], count: int = 3) -> list[dict]:
    model = genai.GenerativeModel("gemini-3.6-flash")
    prompt = SUGGEST_PROMPT_TEMPLATE.format(ingredients=", ".join(ingredient_names), count=count)
    response = model.generate_content(prompt)
    return json.loads(response.text)
```

Note: the model name here matches whatever `get_recipe_info` currently uses in this codebase — check `backend/app/gemini_client.py` for the current value before writing this (Gemini model names get deprecated; use the same one already working elsewhere in this file rather than hardcoding a value from this plan, which may be stale by the time you read it).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_gemini_client.py -v`
Expected: PASS (both the existing `get_recipe_info` test and the new one)

- [ ] **Step 5: Commit**

```bash
git add backend/app/gemini_client.py backend/tests/test_gemini_client.py
git commit -m "Add suggest_recipes for inventory-based recipe suggestions"
```

---

## Task 3: POST /recipes/suggest Endpoint

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/recipes.py`
- Modify: `backend/tests/test_recipes_router.py`

**Interfaces:**
- Consumes: `suggest_recipes` (Task 2), `resolve_or_create_ingredient`, `compute_match_percentage` (Task 1)
- Produces: `POST /recipes/suggest` body `{"household_id": str, "count": int = 3}` -> `201 [RecipeOut-with-match, ...]` where each item is `RecipeOut` plus a `match_percentage: float` field

- [ ] **Step 1: Add schemas**

```python
# backend/app/schemas.py (add import for this at the top-of-file block, not mid-file)
# new imports needed: none beyond what's already imported (BaseModel already there)

class RecipeSuggestRequest(BaseModel):
    household_id: str
    count: int = 3


class RankedRecipeOut(RecipeOut):
    match_percentage: float
```

`RankedRecipeOut` extends the existing `RecipeOut` (already defined from the core loop) — put this class after `RecipeOut` in the file.

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_recipes_router.py (append)
from unittest.mock import patch
from app.models import Ingredient, InventoryItem


FAKE_SUGGESTIONS = [
    {
        "name": "Garlic Rice Bowl",
        "instructions": "cook it",
        "ingredients": [{"name": "white rice", "quantity": 2, "unit": "cup"}],
        "calories": 300, "protein": 6, "fat": 5, "carbs": 55,
    },
]


@patch("app.routers.recipes.suggest_recipes", return_value=FAKE_SUGGESTIONS)
def test_suggest_recipes_endpoint_creates_and_ranks_recipes(mock_suggest, db_session):
    rice = Ingredient(name="white rice")
    db_session.add(rice)
    db_session.flush()
    db_session.add(InventoryItem(ingredient_id=rice.id, household_id="roommates", quantity=2, unit="cup"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post("/recipes/suggest", json={"household_id": "roommates", "count": 1})

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Garlic Rice Bowl"
    assert body[0]["match_percentage"] == 100.0

    app.dependency_overrides.clear()
```

(`make_client` and `app` are already imported/defined at the top of this test file from the core loop's Task 7.)

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_recipes_router.py -v`
Expected: FAIL (route doesn't exist)

- [ ] **Step 4: Write minimal implementation**

```python
# backend/app/routers/recipes.py (add these imports at the top, alongside existing ones)
from app.gemini_client import get_recipe_info, suggest_recipes
from app.recipe_ranking import compute_match_percentage
from app.schemas import RecipeSearchRequest, RecipeOut, RecipeIngredientOut, RecipeSuggestRequest, RankedRecipeOut
from app.models import Ingredient, InventoryItem

# ... existing search_recipe route stays unchanged above this ...


@router.post("/suggest", response_model=list[RankedRecipeOut], status_code=201)
def suggest_recipes_route(payload: RecipeSuggestRequest, db: Session = Depends(get_db)):
    inventory_items = db.query(InventoryItem).filter_by(household_id=payload.household_id).all()
    ingredient_names = [item.ingredient.name for item in inventory_items]

    suggestions = suggest_recipes(ingredient_names, count=payload.count)

    results = []
    for info in suggestions:
        recipe = Recipe(
            name=info["name"],
            instructions=info["instructions"],
            calories=info.get("calories"),
            protein=info.get("protein"),
            fat=info.get("fat"),
            carbs=info.get("carbs"),
            source="ai_suggested",
        )
        db.add(recipe)
        db.flush()

        ingredient_outs = []
        for raw_ingredient in info["ingredients"]:
            ingredient = resolve_or_create_ingredient(db, raw_ingredient["name"])
            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=raw_ingredient["quantity"],
                unit=raw_ingredient["unit"],
            ))
            ingredient_outs.append(RecipeIngredientOut(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                quantity=raw_ingredient["quantity"],
                unit=raw_ingredient["unit"],
            ))

        db.commit()
        match_pct = compute_match_percentage(db, recipe, payload.household_id)

        results.append(RankedRecipeOut(
            id=recipe.id, name=recipe.name, instructions=recipe.instructions,
            calories=recipe.calories, protein=recipe.protein, fat=recipe.fat, carbs=recipe.carbs,
            ingredients=ingredient_outs, match_percentage=match_pct,
        ))

    return results
```

Note: `resolve_or_create_ingredient` and `Recipe`/`RecipeIngredient` are already imported in this file from the core loop's Task 7 — don't re-import, just add the new imports listed above alongside them.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_recipes_router.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/recipes.py backend/tests/test_recipes_router.py
git commit -m "Add POST /recipes/suggest endpoint"
```

---

## Task 4: GET /recipes Endpoint (Ranked Library Listing)

**Files:**
- Modify: `backend/app/routers/recipes.py`
- Modify: `backend/tests/test_recipes_router.py`

**Interfaces:**
- Produces: `GET /recipes?household_id=` -> `200 [RankedRecipeOut, ...]` sorted by `match_percentage` descending

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_recipes_router.py (append)
from app.models import Recipe as RecipeModel, RecipeIngredient as RecipeIngredientModel


def test_list_recipes_sorted_by_match_percentage(db_session):
    chicken = Ingredient(name="chicken breast")
    rice = Ingredient(name="white rice")
    db_session.add_all([chicken, rice])
    db_session.flush()

    full_match = RecipeModel(name="Full Match Recipe", instructions="x")
    partial_match = RecipeModel(name="Partial Match Recipe", instructions="x")
    db_session.add_all([full_match, partial_match])
    db_session.flush()

    db_session.add_all([
        RecipeIngredientModel(recipe_id=full_match.id, ingredient_id=rice.id, quantity=1, unit="cup"),
        RecipeIngredientModel(recipe_id=partial_match.id, ingredient_id=rice.id, quantity=1, unit="cup"),
        RecipeIngredientModel(recipe_id=partial_match.id, ingredient_id=chicken.id, quantity=1, unit="lb"),
    ])
    db_session.add(InventoryItem(ingredient_id=rice.id, household_id="roommates", quantity=1, unit="cup"))
    db_session.commit()

    client = make_client(db_session)
    response = client.get("/recipes", params={"household_id": "roommates"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["name"] == "Full Match Recipe"
    assert body[0]["match_percentage"] == 100.0
    assert body[1]["name"] == "Partial Match Recipe"
    assert body[1]["match_percentage"] == 50.0

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_recipes_router.py -v`
Expected: FAIL (route doesn't exist)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/routers/recipes.py (add this route, e.g. above the /search route)

@router.get("", response_model=list[RankedRecipeOut])
def list_recipes(household_id: str, db: Session = Depends(get_db)):
    recipes = db.query(Recipe).all()

    results = []
    for recipe in recipes:
        recipe_ingredients = db.query(RecipeIngredient).filter_by(recipe_id=recipe.id).all()
        ingredient_outs = [
            RecipeIngredientOut(
                ingredient_id=ri.ingredient_id,
                ingredient_name=ri.ingredient.name,
                quantity=ri.quantity,
                unit=ri.unit,
            )
            for ri in recipe_ingredients
        ]
        match_pct = compute_match_percentage(db, recipe, household_id)
        results.append(RankedRecipeOut(
            id=recipe.id, name=recipe.name, instructions=recipe.instructions,
            calories=recipe.calories, protein=recipe.protein, fat=recipe.fat, carbs=recipe.carbs,
            ingredients=ingredient_outs, match_percentage=match_pct,
        ))

    results.sort(key=lambda r: r.match_percentage, reverse=True)
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_recipes_router.py -v`
Expected: PASS

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/recipes.py backend/tests/test_recipes_router.py
git commit -m "Add GET /recipes endpoint listing recipes ranked by inventory match"
```

---

## Task 5: Frontend — Recipe Search Page Defaults to Ranked Suggestions

**Files:**
- Modify: `frontend/src/api.js`
- Rewrite: `frontend/src/pages/RecipeSearchPage.jsx`

**Interfaces:**
- Consumes: `GET /recipes?household_id=`, `POST /recipes/suggest`, existing `POST /recipes/search`

- [ ] **Step 1: Add API functions**

```javascript
// frontend/src/api.js (append)

export async function listRecipes(householdId) {
  const response = await fetch(`${BASE_URL}/recipes?household_id=${encodeURIComponent(householdId)}`)
  return response.json()
}

export async function suggestRecipes(householdId, count = 3) {
  const response = await fetch(`${BASE_URL}/recipes/suggest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ household_id: householdId, count }),
  })
  return response.json()
}
```

- [ ] **Step 2: Rewrite RecipeSearchPage.jsx**

```jsx
import { useEffect, useState } from 'react'
import { listRecipes, suggestRecipes, searchRecipe } from '../api.js'

const HOUSEHOLD_ID = 'roommates'

export default function RecipeSearchPage() {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)

  async function loadRecipes() {
    setLoading(true)
    let library = await listRecipes(HOUSEHOLD_ID)
    if (library.length === 0) {
      library = await suggestRecipes(HOUSEHOLD_ID, 3)
    }
    setRecipes(library)
    setLoading(false)
  }

  useEffect(() => {
    loadRecipes()
  }, [])

  async function handleSearch() {
    if (!query) return
    setSearching(true)
    await searchRecipe(query)
    setQuery('')
    await loadRecipes()
    setSearching(false)
  }

  return (
    <div>
      <h2>Recipes</h2>

      <div>
        <input
          placeholder="Search a specific dish"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={handleSearch} disabled={searching}>
          {searching ? 'Searching...' : 'Search'}
        </button>
      </div>

      {loading && <p>Loading recipes...</p>}

      {!loading && recipes.map((recipe) => (
        <div key={recipe.id}>
          <h3>{recipe.name} — {recipe.match_percentage.toFixed(0)}% match</h3>
          <p>{recipe.instructions}</p>
          <p>
            Calories: {recipe.calories} | Protein: {recipe.protein}g | Fat: {recipe.fat}g | Carbs: {recipe.carbs}g
          </p>
          <ul>
            {recipe.ingredients.map((ing) => (
              <li key={ing.ingredient_id}>{ing.ingredient_name}: {ing.quantity} {ing.unit}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}
```

There's no automated test for this page (thin UI wiring, same as the core loop's frontend task) — verify manually in Task 7.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.js frontend/src/pages/RecipeSearchPage.jsx
git commit -m "Default recipe page to inventory-ranked suggestions"
```

---

## Task 6: Frontend — Grocery List Page Uses a Recipe Picker

**Files:**
- Modify: `frontend/src/pages/GroceryListPage.jsx`

**Interfaces:**
- Consumes: `listRecipes` (Task 5's api.js addition), existing `generateGroceryList`

- [ ] **Step 1: Rewrite GroceryListPage.jsx**

```jsx
import { useEffect, useState } from 'react'
import { listRecipes, generateGroceryList } from '../api.js'

const HOUSEHOLD_ID = 'roommates'

export default function GroceryListPage() {
  const [recipes, setRecipes] = useState([])
  const [selected, setSelected] = useState({})
  const [result, setResult] = useState(null)

  useEffect(() => {
    listRecipes(HOUSEHOLD_ID).then(setRecipes)
  }, [])

  function toggleRecipe(recipeId) {
    setSelected((prev) => {
      const next = { ...prev }
      if (next[recipeId]) {
        delete next[recipeId]
      } else {
        next[recipeId] = 1
      }
      return next
    })
  }

  function setServings(recipeId, servings) {
    setSelected((prev) => ({ ...prev, [recipeId]: Number(servings) }))
  }

  async function handleGenerate() {
    const recipeIds = Object.keys(selected).map(Number)
    if (recipeIds.length === 0) return
    setResult(await generateGroceryList({ householdId: HOUSEHOLD_ID, recipeIds, servings: selected }))
  }

  return (
    <div>
      <h2>Grocery List</h2>

      <ul>
        {recipes.map((recipe) => (
          <li key={recipe.id}>
            <input
              type="checkbox"
              checked={!!selected[recipe.id]}
              onChange={() => toggleRecipe(recipe.id)}
            />
            {recipe.name}
            {selected[recipe.id] && (
              <input
                type="number"
                min="1"
                value={selected[recipe.id]}
                onChange={(e) => setServings(recipe.id, e.target.value)}
                style={{ width: '3em', marginLeft: '0.5em' }}
              />
            )}
          </li>
        ))}
      </ul>

      <button onClick={handleGenerate}>Generate</button>

      {result && (
        <div>
          <h3>Already have</h3>
          <ul>
            {result.have.map((line, i) => (
              <li key={i}>{line.ingredient_name}: {line.needed} {line.unit}</li>
            ))}
          </ul>
          <h3>Need to buy</h3>
          <ul>
            {result.need.map((line, i) => (
              <li key={i}>{line.ingredient_name}: {line.needed} {line.unit}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/GroceryListPage.jsx
git commit -m "Replace manual recipe-ID entry with a recipe picker on grocery list"
```

---

## Task 7: End-to-End Manual Verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend suite one more time**

Run: `cd backend && python -m pytest -v`
Expected: all tests pass

- [ ] **Step 2: Start backend and frontend**

Same as the core loop: `cd backend && GEMINI_API_KEY=<key> uvicorn app.main:app --reload` and `cd frontend && npm run dev`. Note: `--reload` has been unreliable in this project before — if changes don't seem to take effect, stop and fully restart the server rather than trusting it.

- [ ] **Step 3: Walk through the flow**

1. Add a couple of ingredients to inventory (e.g. rice, garlic).
2. Go to the Recipes tab with an empty recipe library — confirm it automatically calls suggest and shows 3 recipes with match percentages, sorted highest first.
3. Search a specific dish by name — confirm it's added and the list refreshes.
4. Go to the Grocery List tab — confirm recipes appear as checkboxes (not a text box), select one or two with different servings counts, click Generate, confirm "have"/"need" splits correctly.

- [ ] **Step 4: Commit any fixes found during verification**

```bash
git add -A
git commit -m "Fix issues found during manual end-to-end verification"
```

(Only if verification turned up fixes.)
