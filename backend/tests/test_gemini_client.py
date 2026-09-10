import json
from unittest.mock import patch, MagicMock
from app.gemini_client import get_recipe_info


FAKE_RESPONSE_TEXT = json.dumps({
    "name": "Chicken Fried Rice",
    "instructions": "1. Cook rice. 2. Cook chicken. 3. Combine and stir-fry.",
    "ingredients": [
        {"name": "chicken breast", "quantity": 1, "unit": "lb"},
        {"name": "white rice", "quantity": 2, "unit": "cup"},
    ],
    "calories": 450,
    "protein": 35,
    "fat": 12,
    "carbs": 50,
})


@patch("app.gemini_client.genai.GenerativeModel")
def test_get_recipe_info_parses_structured_response(mock_model_cls):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text=FAKE_RESPONSE_TEXT)
    mock_model_cls.return_value = mock_model

    result = get_recipe_info("chicken fried rice")

    assert result["name"] == "Chicken Fried Rice"
    assert result["calories"] == 450
    assert len(result["ingredients"]) == 2
    assert result["ingredients"][0]["name"] == "chicken breast"
