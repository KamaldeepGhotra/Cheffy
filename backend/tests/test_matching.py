import pytest

from app.models import Ingredient
from app.matching import find_ingredient_matches, normalize_ingredient_name, resolve_or_create_ingredient


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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("boneless skinless chicken breast, diced", "chicken breast"),
        ("garlic, minced", "garlic"),
        ("Chicken Breast", "chicken breast"),
        ("eggs (large), beaten", "egg"),
        ("salt - to taste", "salt"),
        ("butter or margarine", "butter"),
        ("large eggs", "egg"),
        ("cooked cold white rice", "white rice"),
        ("fresh basil", "fresh basil"),
        ("dried basil", "dried basil"),
        ("ground beef", "ground beef"),
        ("extra-large eggs", "egg"),
        ("extra virgin olive oil", "extra virgin olive oil"),
        ("sun-dried tomatoes", "sun-dried tomato"),
        ("tomatoes", "tomato"),
        ("cherries", "cherry"),
        ("brussels sprouts", "brussels sprout"),
        ("green onions", "green onion"),
        ("hummus", "hummus"),
        ("asparagus", "asparagus"),
        ("couscous", "couscous"),
        ("molasses", "molasses"),
        ("swiss cheese", "swiss cheese"),
        ("sea bass", "sea bass"),
        ("  chicken    breast  ", "chicken breast"),
        ("large", "large"),
        (", chopped", "chopped"),
        ("", ""),
        ("   ", ""),
        ("(", ""),
    ],
)
def test_normalize_ingredient_name(raw, expected):
    assert normalize_ingredient_name(raw) == expected


def test_leading_parenthetical_does_not_empty_the_name():
    result = normalize_ingredient_name("(14.5 oz) diced tomatoes")

    assert result
    assert result.endswith("tomato")


@pytest.mark.parametrize("raw", ["", "   ", "(", " - "])
def test_blank_name_is_refused_rather_than_stored(db_session, raw):
    with pytest.raises(ValueError):
        resolve_or_create_ingredient(db_session, raw)

    assert db_session.query(Ingredient).count() == 0


@pytest.mark.parametrize(
    ("stored", "lookup"),
    [
        ("chicken breast", "boneless skinless chicken breast, diced"),
        ("boneless skinless chicken breast, diced", "chicken breast"),
        ("garlic", "garlic, minced"),
        ("eggs", "egg"),
        ("egg", "large eggs"),
        ("tomatoes", "tomato"),
    ],
)
def test_prep_words_and_plurals_resolve_to_the_existing_row(db_session, stored, lookup):
    existing = Ingredient(name=stored)
    db_session.add(existing)
    db_session.commit()

    assert resolve_or_create_ingredient(db_session, lookup).id == existing.id
    assert find_ingredient_matches(db_session, lookup, limit=1)[0][1] == 100


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("fresh basil", "dried basil"),
        ("rice", "rice vinegar"),
        ("black pepper", "bell pepper"),
        ("ground beef", "beef"),
    ],
)
def test_distinct_ingredients_stay_apart(db_session, first, second):
    a = resolve_or_create_ingredient(db_session, first)
    b = resolve_or_create_ingredient(db_session, second)

    assert a.id != b.id
    assert db_session.query(Ingredient).count() == 2


def test_stored_name_is_normalized(db_session):
    created = resolve_or_create_ingredient(db_session, "Large Eggs, beaten")

    assert created.name == "egg"


def test_hummus_is_stored_as_hummus(db_session):
    assert resolve_or_create_ingredient(db_session, "Hummus").name == "hummus"
