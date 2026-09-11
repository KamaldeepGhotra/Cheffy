import json
import os
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

PROMPT_TEMPLATE = """You are a recipe assistant. For the dish "{query}", respond with ONLY a JSON object \
(no markdown, no commentary) with this exact shape:
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


def get_recipe_info(query: str) -> dict:
    model = genai.GenerativeModel("gemini-3.6-flash")
    response = model.generate_content(PROMPT_TEMPLATE.format(query=query))
    return json.loads(response.text)
