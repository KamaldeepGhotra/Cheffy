import re

from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from app.models import Ingredient

# Everything after the first of these is prep or packaging detail, not the ingredient.
_CUT_AT = re.compile(r",|\(| - | or ")

# Prep participles and size words. "fresh", "dried", "frozen", "canned", "ground", "whole",
# "white" and "brown" are deliberately absent: they change what you buy.
_STOPLIST = frozenset(
    "diced minced chopped sliced cubed shredded grated crushed peeled beaten melted softened "
    "thawed boneless skinless trimmed halved quartered drained rinsed cooked cold warm raw ripe "
    "large medium small extra-large".split()
)

_SINGULAR_EXCEPTIONS = frozenset({"hummus", "asparagus", "couscous", "molasses"})


def _singularize(word: str) -> str:
    if word in _SINGULAR_EXCEPTIONS or word.endswith(("ss", "us")):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("oes"):
        return word[:-3] + "o"
    if word.endswith("s"):
        return word[:-1]
    return word


def normalize_ingredient_name(raw: str) -> str:
    # First non-blank segment, so a leading "(" or "," does not empty the name.
    segments = _CUT_AT.split(raw.lower())
    words = next((segment.split() for segment in segments if segment.strip()), [])
    # A name made only of stoplist words ("large") is kept rather than emptied.
    kept = [word for word in words if word not in _STOPLIST] or words
    if kept:
        kept[-1] = _singularize(kept[-1])
    return " ".join(kept)


def _normalize(name: str) -> str:
    return normalize_ingredient_name(name)


def find_ingredient_matches(db: Session, name: str, limit: int = 5) -> list[tuple[Ingredient, float]]:
    normalized = _normalize(name)
    candidates = db.query(Ingredient).all()

    scored = [
        (candidate, fuzz.token_sort_ratio(normalized, _normalize(candidate.name)))
        for candidate in candidates
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


def resolve_or_create_ingredient(
    db: Session,
    name: str,
    category: str | None = None,
    default_unit: str | None = None,
    threshold: float = 90.0,
) -> Ingredient:
    normalized = _normalize(name)
    if not normalized:
        raise ValueError("ingredient name is empty")

    matches = find_ingredient_matches(db, name, limit=1)

    if matches and matches[0][1] >= threshold:
        return matches[0][0]

    new_ingredient = Ingredient(name=normalized, category=category, default_unit=default_unit)
    db.add(new_ingredient)
    db.flush()
    return new_ingredient
