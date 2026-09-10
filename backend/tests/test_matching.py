from app.models import Ingredient
from app.matching import find_ingredient_matches, resolve_or_create_ingredient


def test_find_ingredient_matches_ranks_close_matches_first(db_session):
    db_session.add_all([
        Ingredient(name="chicken breast"),
        Ingredient(name="chicken thigh"),
        Ingredient(name="white rice"),
    ])
    db_session.commit()

    matches = find_ingredient_matches(db_session, "chicken", limit=5)

    assert len(matches) > 0
    top_names = [m[0].name for m in matches[:2]]
    assert "chicken breast" in top_names
    assert "chicken thigh" in top_names


def test_resolve_or_create_ingredient_reuses_close_match(db_session):
    existing = Ingredient(name="chicken")
    db_session.add(existing)
    db_session.commit()

    resolved = resolve_or_create_ingredient(db_session, "chickenn")

    assert resolved.id == existing.id


def test_resolve_or_create_ingredient_creates_new_when_no_match(db_session):
    resolved = resolve_or_create_ingredient(db_session, "dragonfruit", category="produce", default_unit="each")

    assert resolved.id is not None
    assert resolved.name == "dragonfruit"
    assert resolved.category == "produce"

    fetched = db_session.query(Ingredient).filter_by(name="dragonfruit").first()
    assert fetched is not None
