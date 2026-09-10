from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from app.models import Ingredient


def make_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_search_ingredients_returns_ranked_matches(db_session):
    db_session.add_all([Ingredient(name="chicken breast"), Ingredient(name="white rice")])
    db_session.commit()

    client = make_client(db_session)
    response = client.get("/ingredients/search", params={"q": "chicken"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["name"] == "chicken breast"
    assert "score" in body[0]

    app.dependency_overrides.clear()
