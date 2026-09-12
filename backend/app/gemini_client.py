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


def _shape_rules(units: str) -> str:
    return f"""Rules:
- "name" in each ingredient is the base ingredient only (e.g. "chicken breast"), never with prep words in it.
- Put any prep word (diced, minced, chopped, sliced, etc.) in "prep" instead; use an empty string if there is none.
- "unit" must be one of: {units}. Pick the closest match.
- "quantity" is for the whole recipe (all servings combined together), not a single serving.
- Nutrition values (calories, protein, fat, carbs) are per serving."""


def _build_search_prompt(query: str, count: int) -> str:
    units = ", ".join(UNIT_VOCABULARY)
    intro = (
        f'You are a recipe assistant. Give {count} genuinely different recipes for "{query}" — '
        "different enough that someone would have a reason to pick between them, not the same dish "
        "with a substitution or two. Vary the cooking method, the flavour profile, or how much work "
        "each one is, and open each recipe's instructions by saying in one short phrase what makes "
        "that version distinct."
    )
    return (
        f"{intro} Respond with ONLY a JSON array (no markdown, no commentary) where each element has "
        f"this exact shape:\n{RECIPE_JSON_SHAPE}\n{_shape_rules(units)}"
    )


def _build_suggest_prompt(ingredient_names: list[str], count: int) -> str:
    units = ", ".join(UNIT_VOCABULARY)
    if ingredient_names:
        intro = (
            "You are a recipe assistant. Using primarily these ingredients that are already on hand: "
            f"{', '.join(ingredient_names)}, suggest {count} different recipes that make good use of them "
            "(they may also need a few additional common ingredients)."
        )
    else:
        intro = (
            "You are a recipe assistant. The household has no inventory on hand yet, so suggest "
            f"{count} simple, popular dishes."
        )
    return (
        f"{intro} Respond with ONLY a JSON array (no markdown, no commentary) where each element has this "
        f"exact shape:\n{RECIPE_JSON_SHAPE}\n{_shape_rules(units)}"
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
