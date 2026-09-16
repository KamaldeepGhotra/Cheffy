import json
import os
import google.generativeai as genai
from dotenv import load_dotenv
from app.units import UNIT_VOCABULARY

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

MODEL_NAME = "gemini-3.6-flash"


class GeminiError(Exception):
    """Raised when a Gemini call fails, or its response doesn't have the expected recipe shape."""


RECIPE_JSON_SHAPE = """{
  "name": string,
  "servings": number,
  "instructions": string,
  "ingredients": [{"name": string, "prep": string, "quantity": number, "unit": string}],
  "calories": number,
  "protein": number,
  "fat": number,
  "carbs": number
}"""

REQUIRED_RECIPE_KEYS = {"name", "instructions", "ingredients", "calories", "protein", "fat", "carbs"}
REQUIRED_INGREDIENT_KEYS = {"name", "quantity", "unit"}


# Who we are actually cooking for. Without this the model returns the median internet recipe:
# a protein and a vegetable in a pan, which also happens to reheat badly.
COOKS = (
    "You are cooking for two university housemates who meal prep together at the weekend and eat "
    "what they make over the next two or three days. Cheap supermarket ingredients, a normal hob "
    "and oven, no specialist equipment. They are bored of the same few dinners."
)

# What separates a suggestion worth cooking from one that gets scrolled past.
QUALITY_BAR = """What makes a good suggestion here:
- It has to survive three days in the fridge and reheat without going grey or rubbery. Braises,
  stews, curries, baked pasta, grain bowls, saucy things and marinated roasted things all work.
  If a component is better added when serving than cooked in — herbs, a squeeze of lemon,
  something crunchy — say so in the instructions.
- Something has to carry the flavour: a sauce, a marinade, a spice blend, a dressing, or browning
  done properly. A protein and a vegetable cooked in butter is not a recipe.
- Give it enough components to eat as a real meal, not three ingredients in a pan.
- Prefer dishes someone would recognise and look forward to, or a clear riff on one, and name it
  the way a menu would.
- Make the suggestions genuinely different from each other, not one idea three ways.

Write the instructions as numbered steps someone who cannot really cook could follow: what heat,
rough timings, and what it should look, smell or feel like before moving on."""


def _shape_rules(units: str) -> str:
    return f"""Rules:
- "name" in each ingredient is the base ingredient only (e.g. "chicken breast"), never with prep words in it.
- Put any prep word (diced, minced, chopped, sliced, etc.) in "prep" instead; use an empty string if there is none.
- "unit" must be one of: {units}. Pick the closest match.
- "quantity" is for the whole recipe (all servings combined together), not a single serving.
- Nutrition values (calories, protein, fat, carbs) are per serving."""


def _build_search_prompt(query: str, count: int) -> str:
    units = ", ".join(UNIT_VOCABULARY)
    intro = f"""{COOKS}

They have asked for "{query}". Give {count} genuinely different takes on it — different enough
that someone would have a reason to pick between them, not the same dish with a substitution or
two. Vary the cooking method, the flavour profile, or how much work each one is, and open each
recipe's instructions with a short phrase saying what makes that version distinct."""
    return (
        f"{intro}\n\n{QUALITY_BAR}\n\nRespond with ONLY a JSON array (no markdown, no commentary) "
        f"where each element has this exact shape:\n{RECIPE_JSON_SHAPE}\n{_shape_rules(units)}"
    )


PANTRY = (
    "oil, salt, pepper, dried herbs and spices, stock, flour, sugar, rice, pasta, tinned tomatoes, "
    "soy sauce, vinegar, garlic and onion"
)


def _build_suggest_prompt(ingredient_names: list[str], count: int) -> str:
    units = ", ".join(UNIT_VOCABULARY)

    if ingredient_names:
        # A spread, not N variations on the same match score: the list should read as a ladder
        # from "cook this tonight" to "worth picking up a couple of things for".
        intro = f"""{COOKS}

Right now they have: {', '.join(ingredient_names)}

Suggest {count} dishes, ordered so the list runs from what they can cook immediately to what is
worth a small shop:
- Open with dishes leaning almost entirely on that list plus pantry staples ({PANTRY}).
- Then dishes still built on several of those ingredients but taking them somewhere different,
  needing one or two things they would have to buy.
- Finish with a fresh idea that uses at least one thing they have and earns a short shopping trip.

Do not pad the earlier suggestions with extra shopping to make them fancier — the whole point of
the first ones is that nothing stands between them and dinner."""
    else:
        intro = f"""{COOKS}

Their kitchen is empty, so there is nothing to cook around yet. Suggest {count} dishes worth
building a first shop around: things that keep and reheat well, share overlapping ingredients so
one trip covers all of them, and are interesting enough to be worth the effort."""

    return (
        f"{intro}\n\n{QUALITY_BAR}\n\nRespond with ONLY a JSON array (no markdown, no commentary) "
        f"where each element has this exact shape:\n{RECIPE_JSON_SHAPE}\n{_shape_rules(units)}"
    )


def _validate_recipe_shape(data) -> None:
    if not isinstance(data, dict):
        raise GeminiError(f"Expected a recipe object, got {type(data).__name__}")
    missing = REQUIRED_RECIPE_KEYS - data.keys()
    if missing:
        raise GeminiError(f"Recipe response missing keys: {sorted(missing)}")
    if not isinstance(data["ingredients"], list):
        raise GeminiError("Recipe 'ingredients' must be a list")
    for ingredient in data["ingredients"]:
        if not isinstance(ingredient, dict) or (REQUIRED_INGREDIENT_KEYS - ingredient.keys()):
            raise GeminiError(f"Malformed ingredient entry: {ingredient!r}")


def _call_gemini(prompt: str) -> str:
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return response.text
    except Exception as exc:
        raise GeminiError(f"Gemini API call failed: {exc}") from exc


def _parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeminiError(f"Gemini response was not valid JSON: {exc}") from exc


def _parse_recipe_list(text: str) -> list[dict]:
    data = _parse_json(text)
    if not isinstance(data, list):
        raise GeminiError(f"Expected a JSON array of recipes, got {type(data).__name__}")
    for recipe in data:
        _validate_recipe_shape(recipe)
    return data


def search_recipes(query: str, count: int = 3) -> list[dict]:
    return _parse_recipe_list(_call_gemini(_build_search_prompt(query, count)))


def suggest_recipes(ingredient_names: list[str], count: int = 3) -> list[dict]:
    return _parse_recipe_list(_call_gemini(_build_suggest_prompt(ingredient_names, count)))
