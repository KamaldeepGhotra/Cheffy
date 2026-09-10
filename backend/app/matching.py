from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from app.models import Ingredient


def _normalize(name: str) -> str:
    return name.strip().lower()


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
    matches = find_ingredient_matches(db, name, limit=1)

    if matches and matches[0][1] >= threshold:
        return matches[0][0]

    new_ingredient = Ingredient(name=_normalize(name), category=category, default_unit=default_unit)
    db.add(new_ingredient)
    db.commit()
    db.refresh(new_ingredient)
    return new_ingredient
