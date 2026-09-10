from app.models import Ingredient


def test_create_ingredient(db_session):
    ingredient = Ingredient(name="chicken breast", category="protein", default_unit="lb")
    db_session.add(ingredient)
    db_session.commit()

    fetched = db_session.query(Ingredient).filter_by(name="chicken breast").first()
    assert fetched is not None
    assert fetched.category == "protein"
    assert fetched.default_unit == "lb"
