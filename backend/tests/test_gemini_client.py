import json
import pytest
from unittest.mock import patch, MagicMock
from app.gemini_client import search_recipes, suggest_recipes, GeminiError


FAKE_RECIPE = {
    "name": "Chicken Fried Rice",
    "servings": 4,
    "instructions": "1. Cook rice. 2. Cook chicken. 3. Combine and stir-fry.",
    "ingredients": [
        {"name": "chicken breast", "prep": "diced", "quantity": 1, "unit": "lb"},
        {"name": "white rice", "prep": "", "quantity": 2, "unit": "cup"},
    ],
    "calories": 450,
    "protein": 35,
    "fat": 12,
    "carbs": 50,
}


def _mock_model(mock_model_cls, response_text):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text=response_text)
    mock_model_cls.return_value = mock_model
    return mock_model


@patch("app.gemini_client.genai.GenerativeModel")
def test_search_recipes_parses_structured_response(mock_model_cls):
    second = {**FAKE_RECIPE, "name": "Thai Fried Rice"}
    mock_model = _mock_model(mock_model_cls, json.dumps([FAKE_RECIPE, second]))

    result = search_recipes("chicken fried rice", count=2)

    assert [r["name"] for r in result] == ["Chicken Fried Rice", "Thai Fried Rice"]
    assert result[0]["servings"] == 4
    assert result[0]["calories"] == 450
    assert len(result[0]["ingredients"]) == 2
    assert result[0]["ingredients"][0]["name"] == "chicken breast"
    assert result[0]["ingredients"][0]["prep"] == "diced"
    # The prompt has to ask for distinct options, or Gemini returns near-duplicates.
    prompt = mock_model.generate_content.call_args[0][0]
    assert "2 genuinely different recipes" in prompt


@patch("app.gemini_client.genai.GenerativeModel")
def test_search_recipes_raises_gemini_error_when_response_is_not_a_list(mock_model_cls):
    _mock_model(mock_model_cls, json.dumps(FAKE_RECIPE))

    with pytest.raises(GeminiError):
        search_recipes("chicken fried rice")


@patch("app.gemini_client.genai.GenerativeModel")
def test_search_recipes_raises_gemini_error_on_invalid_json(mock_model_cls):
    _mock_model(mock_model_cls, "not json at all")

    with pytest.raises(GeminiError):
        search_recipes("chicken fried rice")


@patch("app.gemini_client.genai.GenerativeModel")
def test_search_recipes_raises_gemini_error_on_missing_required_key(mock_model_cls):
    broken = dict(FAKE_RECIPE)
    del broken["calories"]
    _mock_model(mock_model_cls, json.dumps([broken]))

    with pytest.raises(GeminiError):
        search_recipes("chicken fried rice")


@patch("app.gemini_client.genai.GenerativeModel")
def test_search_recipes_raises_gemini_error_when_api_call_fails(mock_model_cls):
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("network exploded")
    mock_model_cls.return_value = mock_model

    with pytest.raises(GeminiError):
        search_recipes("chicken fried rice")


@patch("app.gemini_client.genai.GenerativeModel")
def test_suggest_recipes_parses_list_response(mock_model_cls):
    second_recipe = dict(FAKE_RECIPE, name="Garlic Rice Bowl")
    _mock_model(mock_model_cls, json.dumps([FAKE_RECIPE, second_recipe]))

    result = suggest_recipes(["white rice", "chicken breast"], count=2)

    assert len(result) == 2
    assert result[0]["name"] == "Chicken Fried Rice"
    assert result[1]["name"] == "Garlic Rice Bowl"


@patch("app.gemini_client.genai.GenerativeModel")
def test_suggest_recipes_raises_gemini_error_on_garbage(mock_model_cls):
    _mock_model(mock_model_cls, "definitely not json")

    with pytest.raises(GeminiError):
        suggest_recipes(["white rice"], count=1)


@patch("app.gemini_client.genai.GenerativeModel")
def test_suggest_recipes_raises_gemini_error_when_response_is_not_a_list(mock_model_cls):
    _mock_model(mock_model_cls, json.dumps(FAKE_RECIPE))

    with pytest.raises(GeminiError):
        suggest_recipes(["white rice"], count=1)


@patch("app.gemini_client.genai.GenerativeModel")
def test_suggest_recipes_uses_empty_inventory_wording_when_no_ingredients(mock_model_cls):
    mock_model = _mock_model(mock_model_cls, json.dumps([FAKE_RECIPE]))

    suggest_recipes([], count=3)

    prompt_sent = mock_model.generate_content.call_args[0][0]
    assert "simple, popular dishes" in prompt_sent
    assert "Using primarily these ingredients" not in prompt_sent


@patch("app.gemini_client.genai.GenerativeModel")
def test_suggest_recipes_mentions_ingredients_in_prompt_when_provided(mock_model_cls):
    mock_model = _mock_model(mock_model_cls, json.dumps([FAKE_RECIPE]))

    suggest_recipes(["white rice", "garlic"], count=2)

    prompt_sent = mock_model.generate_content.call_args[0][0]
    assert "white rice, garlic" in prompt_sent
    assert "simple, popular dishes" not in prompt_sent
