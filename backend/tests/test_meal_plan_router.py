from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from app.models import Recipe


def make_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def seed_recipe(db_session, name="Chicken Fried Rice"):
    recipe = Recipe(name=name, instructions="cook it")
    db_session.add(recipe)
    db_session.commit()
    return recipe


def test_add_and_list_entries_for_a_week(db_session):
    recipe = seed_recipe(db_session)
    client = make_client(db_session)

    created = client.post("/meal-plan", json={
        "household_id": "roommates",
        "week_start": "2026-09-14",
        "day": 2,
        "recipe_id": recipe.id,
        "servings": 2,
        "assigned_to": "Andreas",
    })
    assert created.status_code == 201
    assert created.json()["recipe_name"] == "Chicken Fried Rice"

    listed = client.get("/meal-plan", params={"household_id": "roommates", "week_start": "2026-09-14"})
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["day"] == 2
    assert body[0]["assigned_to"] == "Andreas"
    assert body[0]["servings"] == 2

    app.dependency_overrides.clear()


def test_entries_are_scoped_to_week_and_household(db_session):
    recipe = seed_recipe(db_session)
    client = make_client(db_session)

    for household, week in [("roommates", "2026-09-14"), ("roommates", "2026-09-21"), ("other", "2026-09-14")]:
        client.post("/meal-plan", json={
            "household_id": household, "week_start": week, "day": 0,
            "recipe_id": recipe.id, "servings": 1, "assigned_to": "Kam",
        })

    body = client.get("/meal-plan", params={"household_id": "roommates", "week_start": "2026-09-14"}).json()
    assert len(body) == 1

    app.dependency_overrides.clear()


def test_entries_come_back_ordered_by_day(db_session):
    recipe = seed_recipe(db_session)
    client = make_client(db_session)

    for day in [5, 0, 3]:
        client.post("/meal-plan", json={
            "household_id": "roommates", "week_start": "2026-09-14", "day": day,
            "recipe_id": recipe.id, "servings": 1, "assigned_to": "Kam",
        })

    body = client.get("/meal-plan", params={"household_id": "roommates", "week_start": "2026-09-14"}).json()
    assert [e["day"] for e in body] == [0, 3, 5]

    app.dependency_overrides.clear()


def test_rejects_unknown_recipe_and_bad_day(db_session):
    recipe = seed_recipe(db_session)
    client = make_client(db_session)

    missing = client.post("/meal-plan", json={
        "household_id": "roommates", "week_start": "2026-09-14", "day": 0,
        "recipe_id": 999, "servings": 1, "assigned_to": "Kam",
    })
    assert missing.status_code == 404

    bad_day = client.post("/meal-plan", json={
        "household_id": "roommates", "week_start": "2026-09-14", "day": 7,
        "recipe_id": recipe.id, "servings": 1, "assigned_to": "Kam",
    })
    assert bad_day.status_code == 422

    app.dependency_overrides.clear()


def test_delete_entry(db_session):
    recipe = seed_recipe(db_session)
    client = make_client(db_session)

    entry_id = client.post("/meal-plan", json={
        "household_id": "roommates", "week_start": "2026-09-14", "day": 0,
        "recipe_id": recipe.id, "servings": 1, "assigned_to": "Kam",
    }).json()["id"]

    assert client.delete(f"/meal-plan/{entry_id}").status_code == 204
    assert client.delete(f"/meal-plan/{entry_id}").status_code == 404
    assert client.get("/meal-plan", params={"household_id": "roommates", "week_start": "2026-09-14"}).json() == []

    app.dependency_overrides.clear()
