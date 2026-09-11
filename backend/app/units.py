# Same table as frontend/src/units.js. Key is the canonical unit, value is every spelling that maps to it.
CANONICAL_UNITS: dict[str, list[str]] = {
    "lb": ["lb", "lbs", "pound", "pounds"],
    "oz": ["oz", "ounce", "ounces"],
    "g": ["g", "gram", "grams"],
    "kg": ["kg", "kilo", "kilos", "kilogram", "kilograms"],
    "cup": ["cup", "cups"],
    "tbsp": ["tbsp", "tbsps", "tablespoon", "tablespoons"],
    "tsp": ["tsp", "tsps", "teaspoon", "teaspoons"],
    "ml": ["ml", "milliliter", "milliliters", "millilitre", "millilitres"],
    "l": ["l", "liter", "liters", "litre", "litres"],
    "each": ["each", "ea", "whole"],
    "clove": ["clove", "cloves"],
    "can": ["can", "cans"],
    "bag": ["bag", "bags"],
    "box": ["box", "boxes"],
    "bunch": ["bunch", "bunches"],
    "pack": ["pack", "packs", "package", "packages"],
    "slice": ["slice", "slices"],
    "piece": ["piece", "pieces", "pc", "pcs"],
}

UNIT_VOCABULARY: list[str] = list(CANONICAL_UNITS)
DEFAULT_UNIT = "each"

_ALIAS_TO_UNIT = {alias: unit for unit, aliases in CANONICAL_UNITS.items() for alias in aliases}


def normalize_unit(raw: str | None) -> str:
    # Unlike the frontend, an unknown unit is kept as typed (lowercased) rather than
    # collapsed to "each", so Gemini's "pinch" or "leaves" stay visible in the data.
    token = (raw or "").strip().lower().rstrip(".")
    if not token:
        return DEFAULT_UNIT
    return _ALIAS_TO_UNIT.get(token, token)
