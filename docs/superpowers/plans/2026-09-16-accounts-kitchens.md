# Accounts and Kitchens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded single-kitchen prototype with real accounts, shared kitchens joined by invite code, and per-kitchen data isolation enforced on every endpoint.

**Architecture:** Supabase Auth issues JWTs to the browser; FastAPI verifies them against Supabase's JWKS and derives the caller's kitchen from a local `profiles` row, so no request ever carries a `household_id` again. Alembic takes ownership of the schema. The frontend gates the app behind session → name → kitchen before showing the tabs.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, PyJWT[crypto], PostgreSQL/SQLite, React 18, `@supabase/supabase-js`, Pytest, Vitest.

**Spec:** [docs/superpowers/specs/2026-09-15-accounts-kitchens-onboarding-design.md](../specs/2026-09-15-accounts-kitchens-onboarding-design.md)

**This plan covers spec sections 1–6, 8, 11–14.** Onboarding questions (§7), preference merging (§9) and the allergy guard (§10) are Plans B and C. Migration `0001` here creates the whole §4 schema anyway, so those plans add no columns.

## Global Constraints

- Sign-in is **Supabase Auth only**: 6-digit email code and Google. No passwords, no SMS.
- Tokens are verified with **ES256 or RS256 against JWKS**. HS256 is rejected — accepting it would mean holding a signing secret in the API.
- **No endpoint accepts `household_id`** from the client after this plan. The kitchen comes from the verified token.
- A row belonging to another kitchen returns **`404`, never `403`** — 403 confirms the id exists.
- `null` in a preference column means **not answered**; `[]` means **answered "none"**. Never collapse the two.
- Code says `household`; every user-facing string says **kitchen**.
- **No AI-authorship attribution** anywhere in the repo: commits, comments, PR text.
- Alembic owns the schema. `Base.metadata.create_all` is removed from the app lifespan (tests keep using it).

## Ownership split

Spec §16 flags that the MVP plan's split doesn't map onto this work. It does, with one rule: **Task 1–4 are a blocking foundation built by one person before anyone else starts.** After that the existing file ownership holds.

| Tasks | Owner | Why |
|---|---|---|
| 1–4 foundation (Alembic, models, auth, invite codes) | **Kam** | Everything else imports these. Nobody else starts until Task 4 is on main. |
| 5–6 recipes + grocery routers | **Kam** | His files under the MVP plan. |
| 7–8 inventory + meal plan routers | **Andreas** | His files. |
| 9–12 frontend auth, gate, sign-in, profile menu | **Andreas** | `App.jsx`, `index.css` and shared modules are his. |
| 13 api.js token wiring | **Kam** | Append-only, lands before 9–12. |
| 14 config and deploy | **Andreas** | He owns hosting. |

Tasks 5–8 touch four different routers and can run in parallel. Tasks 9–12 are sequential within themselves.

---

## File Structure

```
backend/
  alembic.ini                         NEW  Alembic config
  alembic/env.py                      NEW  wired to app.db.Base, render_as_batch
  alembic/versions/0001_accounts.py   NEW  whole §4 schema
  app/
    auth.py                           NEW  token verification, current_user/profile/household
    invite_codes.py                   NEW  generate + normalize
    models.py                         MOD  Household, Profile, Preferences; FKs on 3 tables
    schemas.py                        MOD  MeOut, KitchenOut, MemberOut, PreferencesOut
    main.py                           MOD  mount me/households routers, drop create_all
    routers/
      me.py                           NEW  GET /me, PATCH /me
      households.py                   NEW  create, join, regenerate code
      recipes.py    grocery.py        MOD  household_id param -> current_household
      inventory.py  meal_plan.py      MOD  same
  tests/
    conftest.py                       MOD  ES256 key pair, auth overrides, factories
    test_auth.py  test_households.py  NEW
    test_isolation.py                 NEW  cross-kitchen 404s
    test_*_router.py                  MOD  authenticated clients
frontend/src/
  supabase.js                         NEW  client singleton
  auth.jsx                            NEW  AuthProvider, useAuth, token provider wiring
  api.js                              MOD  Bearer header, householdId params removed
  App.jsx                             MOD  the gate
  me.js                               DEL  replaced by GET /me
  pages/SignInPage.jsx                NEW
  pages/KitchenSetupPage.jsx          NEW
  pages/ProfileMenu.jsx               NEW
  pages/auth.css                      NEW
```

---

## Task 1: Alembic and migration 0001

**Owner:** Kam. **Files:** `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_accounts.py`, `backend/requirements.txt`, `backend/tests/test_migrations.py`, `backend/app/main.py`

**Interfaces:**
- Produces: a database schema matching spec §4, created by `alembic upgrade head`. Later tasks add models that must match it exactly.

- [ ] **Step 1: Add dependencies**

Append to `backend/requirements.txt`:

```
alembic==1.13.3
PyJWT[crypto]==2.9.0
```

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 2: Initialise Alembic**

Run: `cd backend && alembic init alembic`

- [ ] **Step 3: Point env.py at the app's metadata**

Replace the generated `backend/alembic/env.py` body with:

```python
from logging.config import fileConfig
from alembic import context
from app.db import Base, DATABASE_URL
from app import models  # noqa: F401  registers every table on Base

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # render_as_batch lets SQLite apply ALTERs by rebuilding the table.
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Write the failing test**

```python
# backend/tests/test_migrations.py
import subprocess
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_upgrade_head_then_no_model_drift(tmp_path):
    env = {"DATABASE_URL": f"sqlite:///{tmp_path/'m.db'}", "PATH": __import__("os").environ["PATH"]}

    upgrade = subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert upgrade.returncode == 0, upgrade.stderr

    # Fails when models have changes no migration covers.
    check = subprocess.run(["alembic", "check"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
```

- [ ] **Step 5: Run it to see it fail**

Run: `cd backend && python -m pytest tests/test_migrations.py -v`
Expected: FAIL — no migration exists yet.

- [ ] **Step 6: Write migration 0001**

Create `backend/alembic/versions/0001_accounts.py`. It creates the full §4 schema: `ingredients`, `households`, `profiles`, `preferences`, `inventory_items`, `recipes`, `recipe_ingredients`, `meal_plan_entries`. Columns exactly as Task 2's models define them.

```python
"""accounts, kitchens, and kitchen-scoped data"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("invite_code", sa.String(6), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("display_name", sa.String, nullable=False),
        sa.Column("household_id", sa.Integer, sa.ForeignKey("households.id"), nullable=True),
        sa.Column("name_confirmed_at", sa.DateTime, nullable=True),
        sa.Column("onboarded_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "preferences",
        sa.Column("profile_id", sa.String(36), sa.ForeignKey("profiles.id"), primary_key=True),
        sa.Column("allergies", sa.JSON, nullable=True),
        sa.Column("allergies_other", sa.String, nullable=True),
        sa.Column("diets", sa.JSON, nullable=True),
        sa.Column("dislikes", sa.JSON, nullable=True),
        sa.Column("dislikes_other", sa.String, nullable=True),
        sa.Column("cuisines", sa.JSON, nullable=True),
        sa.Column("spice", sa.String, nullable=True),
        sa.Column("equipment", sa.JSON, nullable=True),
        sa.Column("effort", sa.String, nullable=True),
        sa.Column("budget", sa.String, nullable=True),
        sa.Column("batch_days", sa.Integer, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True, index=True),
        sa.Column("category", sa.String, nullable=True),
        sa.Column("default_unit", sa.String, nullable=True),
    )
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("household_id", sa.Integer, sa.ForeignKey("households.id"), nullable=False, index=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("profiles.id"), nullable=True, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("servings", sa.Integer, nullable=False),
        sa.Column("instructions", sa.String, nullable=False),
        sa.Column("calories", sa.Float, nullable=True),
        sa.Column("protein", sa.Float, nullable=True),
        sa.Column("fat", sa.Float, nullable=True),
        sa.Column("carbs", sa.Float, nullable=True),
        sa.Column("source", sa.String, nullable=True),
    )
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("ingredient_id", sa.Integer, sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String, nullable=False),
    )
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("household_id", sa.Integer, sa.ForeignKey("households.id"), nullable=False, index=True),
        sa.Column("ingredient_id", sa.Integer, sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String, nullable=False),
        sa.Column("added_date", sa.DateTime, nullable=True),
    )
    op.create_table(
        "meal_plan_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("household_id", sa.Integer, sa.ForeignKey("households.id"), nullable=False, index=True),
        sa.Column("week_start", sa.Date, nullable=False, index=True),
        sa.Column("day", sa.Integer, nullable=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("servings", sa.Integer, nullable=False),
        sa.Column("assigned_to_id", sa.String(36), sa.ForeignKey("profiles.id"), nullable=True),
    )


def downgrade() -> None:
    for table in (
        "meal_plan_entries", "inventory_items", "recipe_ingredients", "recipes",
        "ingredients", "preferences", "profiles", "households",
    ):
        op.drop_table(table)
```

- [ ] **Step 7: Remove create_all from the app lifespan**

In `backend/app/main.py`, delete the `Base.metadata.create_all(bind=engine)` line and the now-unused `Base, engine` import, leaving the lifespan as a bare `yield`. Tests still call `create_all` themselves.

- [ ] **Step 8: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_migrations.py -v`
Expected: PASS. It will fail until Task 2's models match this migration exactly — run it again at the end of Task 2.

- [ ] **Step 9: Delete stale local databases**

Run: `cd backend && rm -f cheffy.db`

- [ ] **Step 10: Commit**

```bash
git add backend/alembic.ini backend/alembic backend/requirements.txt backend/tests/test_migrations.py backend/app/main.py
git commit -m "Put the schema under Alembic and add the accounts migration"
```

---

## Task 2: Models for profiles, kitchens and preferences

**Owner:** Kam. **Files:** `backend/app/models.py`, `backend/tests/test_models.py`

**Interfaces:**
- Consumes: Task 1's migration — columns must match exactly or `alembic check` fails.
- Produces: `Household(id, name, invite_code, created_at, members, )`, `Profile(id: str, email, display_name, household_id, name_confirmed_at, onboarded_at, household, preferences)`, `Preferences(profile_id, …)`. `InventoryItem.household_id`/`MealPlanEntry.household_id` become `Integer` FKs; `MealPlanEntry.assigned_to` becomes `assigned_to_id`; `Recipe` gains `household_id` and `owner_id`.

Profile ids are stored as `String(36)` holding the Supabase UUID, because SQLite has no native UUID type and the same code has to run on both databases.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py (append)
from datetime import datetime, timezone
from app.models import Household, Profile


def test_profile_belongs_to_a_household(db_session):
    kitchen = Household(name="Flat 3", invite_code="ABC234", created_at=datetime.now(timezone.utc))
    db_session.add(kitchen)
    db_session.flush()

    profile = Profile(
        id="11111111-1111-1111-1111-111111111111",
        email="kam@example.com",
        display_name="Kam",
        household_id=kitchen.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(profile)
    db_session.commit()

    assert profile.household.name == "Flat 3"
    assert [m.display_name for m in kitchen.members] == ["Kam"]
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL — `cannot import name 'Household'`.

- [ ] **Step 3: Add the new models**

Append to `backend/app/models.py`:

```python
class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    invite_code = Column(String(6), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    members = relationship("Profile", back_populates="household", order_by="Profile.created_at")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True)          # Supabase user uuid
    email = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True, index=True)
    name_confirmed_at = Column(DateTime, nullable=True)
    onboarded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    household = relationship("Household", back_populates="members")
    preferences = relationship("Preferences", uselist=False, back_populates="profile")


class Preferences(Base):
    __tablename__ = "preferences"

    # null means the question was skipped; [] means answered "none". Plans B and C rely on this.
    profile_id = Column(String(36), ForeignKey("profiles.id"), primary_key=True)
    allergies = Column(JSON, nullable=True)
    allergies_other = Column(String, nullable=True)
    diets = Column(JSON, nullable=True)
    dislikes = Column(JSON, nullable=True)
    dislikes_other = Column(String, nullable=True)
    cuisines = Column(JSON, nullable=True)
    spice = Column(String, nullable=True)
    equipment = Column(JSON, nullable=True)
    effort = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    batch_days = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    profile = relationship("Profile", back_populates="preferences")
```

Add `JSON` to the `sqlalchemy` import at the top of the file.

- [ ] **Step 4: Convert the existing tables**

In the same file:
- `InventoryItem.household_id` → `Column(Integer, ForeignKey("households.id"), nullable=False, index=True)`
- `MealPlanEntry.household_id` → same; replace `assigned_to = Column(String, nullable=True)` with `assigned_to_id = Column(String(36), ForeignKey("profiles.id"), nullable=True)` and add `assigned_to = relationship("Profile")`
- `Recipe` gains, above `name`:

```python
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
```

- [ ] **Step 5: Run both tests**

Run: `cd backend && python -m pytest tests/test_models.py tests/test_migrations.py -v`
Expected: PASS, including `alembic check` reporting no drift. If it reports drift, the migration and the models disagree — fix the migration to match the models.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "Add profile, kitchen and preference models and scope existing tables to a kitchen"
```

---

## Task 3: Token verification

**Owner:** Kam. **Files:** `backend/app/auth.py`, `backend/tests/conftest.py`, `backend/tests/test_auth.py`

**Interfaces:**
- Produces:
  - `AuthUser(id: str, email: str, full_name: str | None)` — frozen dataclass
  - `decode_token(token: str) -> dict` — raises `HTTPException(401)`
  - `_signing_key(token: str)` — the JWKS lookup, **monkeypatched by tests**
  - `current_user(authorization: str | None = Header(None)) -> AuthUser`
  - `current_profile(user=Depends(current_user), db=Depends(get_db)) -> Profile` — creates the row on first call
  - `current_household(profile=Depends(current_profile)) -> Household` — `409 {"detail": "no_kitchen"}` when they have none

- [ ] **Step 1: Add test fixtures for signing tokens**

Append to `backend/tests/conftest.py`:

```python
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

ISSUER = "https://test.supabase.co/auth/v1"


@pytest.fixture(scope="session")
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture()
def make_token(signing_key, monkeypatch):
    """Mints tokens the API will accept, without touching the network."""
    from app import auth

    monkeypatch.setattr(auth, "_signing_key", lambda token: signing_key.public_key())
    monkeypatch.setattr(auth, "ISSUER", ISSUER)

    def _make(sub="11111111-1111-1111-1111-111111111111", email="kam@example.com", **claims):
        payload = {
            "sub": sub, "email": email, "aud": "authenticated", "iss": ISSUER,
            "exp": __import__("time").time() + 3600, **claims,
        }
        return jwt.encode(payload, signing_key, algorithm="ES256")

    return _make
```

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_auth.py
import time
import jwt
import pytest
from fastapi import HTTPException
from app import auth


def test_valid_token_is_accepted(make_token):
    user = auth.decode_token(make_token())
    assert user["sub"] == "11111111-1111-1111-1111-111111111111"


def test_expired_token_is_rejected(make_token):
    with pytest.raises(HTTPException) as exc:
        auth.decode_token(make_token(exp=time.time() - 10))
    assert exc.value.status_code == 401


def test_wrong_audience_is_rejected(make_token):
    with pytest.raises(HTTPException) as exc:
        auth.decode_token(make_token(aud="anon"))
    assert exc.value.status_code == 401


def test_wrong_issuer_is_rejected(make_token):
    with pytest.raises(HTTPException) as exc:
        auth.decode_token(make_token(iss="https://evil.example.com/auth/v1"))
    assert exc.value.status_code == 401


def test_hs256_token_is_rejected(monkeypatch):
    """A shared-secret token must never be accepted, even if the secret leaked."""
    monkeypatch.setattr(auth, "_signing_key", lambda token: "a-shared-secret")
    forged = jwt.encode(
        {"sub": "x", "aud": "authenticated", "iss": auth.ISSUER, "exp": time.time() + 60},
        "a-shared-secret", algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        auth.decode_token(forged)
    assert exc.value.status_code == 401
```

- [ ] **Step 3: Run them to see them fail**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL — `No module named 'app.auth'`.

- [ ] **Step 4: Write auth.py**

```python
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Household, Profile

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://test.supabase.co").rstrip("/")
ISSUER = f"{SUPABASE_URL}/auth/v1"
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
# Asymmetric only. HS256 would mean holding a signing secret in the API.
ALGORITHMS = ["ES256", "RS256"]


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    full_name: str | None


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    return PyJWKClient(JWKS_URL)


def _signing_key(token: str):
    """Split out so tests can hand back a local key instead of calling Supabase."""
    return _jwk_client().get_signing_key_from_jwt(token).key


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _signing_key(token),
            algorithms=ALGORITHMS,
            audience="authenticated",
            issuer=ISSUER,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Not signed in") from exc


def current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in")
    claims = decode_token(authorization.split(" ", 1)[1].strip())
    metadata = claims.get("user_metadata") or {}
    return AuthUser(
        id=claims["sub"],
        email=claims.get("email") or "",
        full_name=metadata.get("full_name"),
    )


def current_profile(user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> Profile:
    profile = db.query(Profile).filter_by(id=user.id).first()
    if profile:
        return profile
    # First authenticated call for this user: give them a row and a usable name.
    profile = Profile(
        id=user.id,
        email=user.email,
        display_name=user.full_name or (user.email.split("@")[0] if user.email else "Cook"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def current_household(profile: Profile = Depends(current_profile)) -> Household:
    if profile.household is None:
        raise HTTPException(status_code=409, detail="no_kitchen")
    return profile.household
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/app/auth.py backend/tests/test_auth.py backend/tests/conftest.py
git commit -m "Verify Supabase tokens against JWKS and derive the caller's kitchen"
```

---

## Task 4: Kitchens, invite codes, and /me

**Owner:** Kam. **Files:** `backend/app/invite_codes.py`, `backend/app/routers/me.py`, `backend/app/routers/households.py`, `backend/app/schemas.py`, `backend/app/main.py`, `backend/tests/test_households.py`

**Interfaces:**
- Consumes: Task 3's dependencies.
- Produces: `generate_code() -> str`, `normalize_code(raw: str) -> str`; endpoints `GET /me`, `PATCH /me`, `POST /households`, `POST /households/join`, `POST /households/invite-code`; schemas `MemberOut`, `KitchenOut`, `PreferencesOut`, `MeOut`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_households.py
from app.invite_codes import generate_code, normalize_code


def test_codes_avoid_characters_that_misread():
    for _ in range(200):
        assert set(generate_code()).isdisjoint(set("O0I1L"))


def test_normalize_accepts_how_people_actually_type_it():
    assert normalize_code(" abc-234 ") == "ABC234"


def test_me_creates_a_profile_on_first_call(client, make_token):
    body = client.get("/me", headers={"Authorization": f"Bearer {make_token()}"}).json()
    assert body["kitchen"] is None
    assert body["display_name"] == "kam"
    assert body["onboarded"] is False


def test_create_then_join_a_kitchen(client, make_token):
    kam = {"Authorization": f"Bearer {make_token()}"}
    other = {"Authorization": f"Bearer {make_token(sub='22222222-2222-2222-2222-222222222222', email='a@example.com')}"}

    created = client.post("/households", json={}, headers=kam).json()
    code = created["kitchen"]["invite_code"]

    joined = client.post("/households/join", json={"code": code.lower()}, headers=other).json()
    assert joined["kitchen"]["id"] == created["kitchen"]["id"]
    assert len(joined["kitchen"]["members"]) == 2


def test_joining_twice_is_rejected(client, make_token):
    kam = {"Authorization": f"Bearer {make_token()}"}
    client.post("/households", json={}, headers=kam)
    assert client.post("/households/join", json={"code": "ABC234"}, headers=kam).status_code == 409


def test_unknown_code_is_404(client, make_token):
    other = {"Authorization": f"Bearer {make_token(sub='33333333-3333-3333-3333-333333333333')}"}
    assert client.post("/households/join", json={"code": "ZZZ999"}, headers=other).status_code == 404


def test_regenerating_invalidates_the_old_code(client, make_token):
    kam = {"Authorization": f"Bearer {make_token()}"}
    old = client.post("/households", json={}, headers=kam).json()["kitchen"]["invite_code"]
    new = client.post("/households/invite-code", headers=kam).json()["kitchen"]["invite_code"]
    assert new != old

    other = {"Authorization": f"Bearer {make_token(sub='44444444-4444-4444-4444-444444444444')}"}
    assert client.post("/households/join", json={"code": old}, headers=other).status_code == 404
```

Add a `client` fixture to `conftest.py` that overrides `get_db` with `db_session` and returns a `TestClient(app)`, following the pattern already in the router tests.

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && python -m pytest tests/test_households.py -v`
Expected: FAIL — `No module named 'app.invite_codes'`.

- [ ] **Step 3: Write invite_codes.py**

```python
import secrets

# No O/0, I/1/L: they get misread off a phone screen. ~887 million codes.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LENGTH = 6


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def normalize_code(raw: str) -> str:
    return "".join(ch for ch in (raw or "").upper() if ch.isalnum())
```

- [ ] **Step 4: Add the schemas**

Append to `backend/app/schemas.py`:

```python
class MemberOut(BaseModel):
    id: str
    display_name: str


class KitchenOut(BaseModel):
    id: int
    name: str
    invite_code: str
    members: list[MemberOut]


class PreferencesOut(BaseModel):
    allergies: list[str] | None = None
    allergies_other: str | None = None
    diets: list[str] | None = None
    dislikes: list[str] | None = None
    dislikes_other: str | None = None
    cuisines: list[str] | None = None
    spice: str | None = None
    equipment: list[str] | None = None
    effort: str | None = None
    budget: str | None = None
    batch_days: int | None = None


class MeOut(BaseModel):
    id: str
    email: str
    display_name: str
    name_confirmed: bool
    kitchen: KitchenOut | None
    onboarded: bool
    preferences: PreferencesOut


class DisplayNameUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


class HouseholdCreate(BaseModel):
    name: str | None = None


class JoinRequest(BaseModel):
    code: str
```

- [ ] **Step 5: Write the /me router**

```python
# backend/app/routers/me.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth import current_profile
from app.db import get_db
from app.models import Profile
from app.schemas import DisplayNameUpdate, KitchenOut, MeOut, MemberOut, PreferencesOut

router = APIRouter(tags=["me"])


def to_me(profile: Profile) -> MeOut:
    kitchen = profile.household
    prefs = profile.preferences
    return MeOut(
        id=profile.id,
        email=profile.email,
        display_name=profile.display_name,
        name_confirmed=profile.name_confirmed_at is not None,
        kitchen=None if kitchen is None else KitchenOut(
            id=kitchen.id,
            name=kitchen.name,
            invite_code=kitchen.invite_code,
            members=[MemberOut(id=m.id, display_name=m.display_name) for m in kitchen.members],
        ),
        onboarded=profile.onboarded_at is not None,
        preferences=PreferencesOut() if prefs is None else PreferencesOut(
            allergies=prefs.allergies, allergies_other=prefs.allergies_other,
            diets=prefs.diets, dislikes=prefs.dislikes, dislikes_other=prefs.dislikes_other,
            cuisines=prefs.cuisines, spice=prefs.spice, equipment=prefs.equipment,
            effort=prefs.effort, budget=prefs.budget, batch_days=prefs.batch_days,
        ),
    )


@router.get("/me", response_model=MeOut)
def read_me(profile: Profile = Depends(current_profile)):
    return to_me(profile)


@router.patch("/me", response_model=MeOut)
def update_me(payload: DisplayNameUpdate, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    profile.display_name = payload.display_name.strip()
    profile.name_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return to_me(profile)
```

- [ ] **Step 6: Write the households router**

```python
# backend/app/routers/households.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth import current_profile
from app.db import get_db
from app.invite_codes import generate_code, normalize_code
from app.models import Household, Profile
from app.routers.me import to_me
from app.schemas import HouseholdCreate, JoinRequest, MeOut

router = APIRouter(prefix="/households", tags=["households"])


def _unique_code(db: Session) -> str:
    for _ in range(10):
        code = generate_code()
        if not db.query(Household).filter_by(invite_code=code).first():
            return code
    raise HTTPException(status_code=500, detail="Could not allocate an invite code")


@router.post("", response_model=MeOut, status_code=201)
def create_household(payload: HouseholdCreate, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    if profile.household_id is not None:
        raise HTTPException(status_code=409, detail="You're already in a kitchen.")
    kitchen = Household(
        name=(payload.name or f"{profile.display_name}'s kitchen").strip(),
        invite_code=_unique_code(db),
        created_at=datetime.now(timezone.utc),
    )
    db.add(kitchen)
    db.flush()
    profile.household_id = kitchen.id
    db.commit()
    db.refresh(profile)
    return to_me(profile)


@router.post("/join", response_model=MeOut)
def join_household(payload: JoinRequest, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    if profile.household_id is not None:
        raise HTTPException(status_code=409, detail="You're already in a kitchen.")
    kitchen = db.query(Household).filter_by(invite_code=normalize_code(payload.code)).first()
    if kitchen is None:
        raise HTTPException(status_code=404, detail="No kitchen with that code.")
    profile.household_id = kitchen.id
    db.commit()
    db.refresh(profile)
    return to_me(profile)


@router.post("/invite-code", response_model=MeOut)
def regenerate_invite_code(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    if profile.household is None:
        raise HTTPException(status_code=409, detail="no_kitchen")
    profile.household.invite_code = _unique_code(db)
    db.commit()
    db.refresh(profile)
    return to_me(profile)
```

- [ ] **Step 7: Mount both routers**

In `backend/app/main.py`, import `me` and `households` alongside the existing routers and add `app.include_router(me.router)` and `app.include_router(households.router)`.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_households.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 9: Commit**

```bash
git add backend/app/invite_codes.py backend/app/routers/me.py backend/app/routers/households.py backend/app/schemas.py backend/app/main.py backend/tests/test_households.py backend/tests/conftest.py
git commit -m "Add kitchens, invite codes and the profile endpoint"
```

**Foundation complete. Merge to main before Tasks 5–8 begin.**

---

## Tasks 5–8: Scope the four routers

Each task follows the same shape against a different router, so they can run in parallel. **Tasks 5–6 are Kam's, 7–8 are Andreas's.**

The pattern, applied in every case:

1. Delete the `household_id` query parameter or body field.
2. Add `kitchen: Household = Depends(current_household)` to the signature.
3. Replace `filter_by(household_id=<param>)` with `filter_by(household_id=kitchen.id)`.
4. For any route taking a row id, filter by **both** id and `household_id=kitchen.id`, and `404` when the query returns nothing.
5. Remove the matching field from the request schema in `schemas.py`.

### Task 5: Recipes router — Kam

**Files:** `backend/app/routers/recipes.py`, `backend/app/schemas.py`, `backend/tests/test_recipes_router.py`

Recipes gain an owner. In this plan every recipe is a **kitchen** recipe: `_persist_recipe` sets `household_id=kitchen.id` and leaves `owner_id` null. Plan C adds personal recipes and the `scope` parameter.

- [ ] **Step 1: Write the failing test**

```python
def test_recipes_are_scoped_to_the_callers_kitchen(client, make_token, two_kitchens):
    a_headers, b_headers, a_recipe_id = two_kitchens
    assert client.get("/recipes", headers=b_headers).json() == []
    assert client.get("/recipes", headers=a_headers).json()[0]["id"] == a_recipe_id
```

- [ ] **Step 2: Run it to see it fail** — `pytest tests/test_recipes_router.py -v`, fails because `GET /recipes` still takes `household_id`.
- [ ] **Step 3: Apply the five-step pattern** to `list_recipes`, `search_recipe`, `suggest`, and `save_recipe`; `_on_hand_ids` and `_on_hand_names` take `kitchen.id`.
- [ ] **Step 4: Update every existing test in the file** to pass an auth header and drop `household_id` from bodies.
- [ ] **Step 5: Run the file** — all green.
- [ ] **Step 6: Commit** — `git commit -m "Scope recipes to the caller's kitchen"`

### Task 6: Grocery router — Kam

**Files:** `backend/app/routers/grocery.py`, `backend/app/schemas.py`, `backend/tests/test_grocery_router.py`

- [ ] Same five steps. `_build_list` takes `household_id: int`. `GET /grocery-list` keeps `week_start` and loses `household_id`. `POST /grocery-list` keeps `recipe_ids`/`servings`; verify each recipe id belongs to the kitchen and `404` otherwise.
- [ ] Test: a recipe id from another kitchen in `recipe_ids` returns `404`.
- [ ] Commit — `git commit -m "Scope the grocery list to the caller's kitchen"`

### Task 7: Inventory router — Andreas

**Files:** `backend/app/routers/inventory.py`, `backend/app/schemas.py`, `backend/tests/test_inventory_router.py`

- [ ] Same five steps. `DELETE /inventory/{id}` must filter on `household_id` too.
- [ ] Test: deleting another kitchen's item returns `404` **and leaves the row in place**.
- [ ] Commit — `git commit -m "Scope inventory to the caller's kitchen"`

### Task 8: Meal plan router — Andreas

**Files:** `backend/app/routers/meal_plan.py`, `backend/app/schemas.py`, `backend/tests/test_meal_plan_router.py`

- [ ] Same five steps, plus: `assigned_to` becomes `assigned_to_id: str | None` on create and update; `MealPlanEntryOut` returns `assigned_to_id` and `assigned_to_name`.
- [ ] An `assigned_to_id` that isn't a member of the kitchen → `422`.
- [ ] Test: `PATCH` and `DELETE` on another kitchen's entry both return `404`.
- [ ] Commit — `git commit -m "Scope the meal plan to the caller's kitchen and assign by profile"`

---

## Task 9: Cross-kitchen isolation suite

**Owner:** Kam, after 5–8 merge. **Files:** `backend/tests/conftest.py`, `backend/tests/test_isolation.py`

One test file that proves the whole promise in §14, rather than trusting four separate router tests.

**Interfaces:** Produces a `two_kitchens` fixture used by Task 5's test.

- [ ] **Step 1: Add the fixture**

```python
# backend/tests/conftest.py (append)
@pytest.fixture()
def two_kitchens(client, make_token):
    """Kitchen A with one inventory item, one recipe and one meal; kitchen B empty."""
    a = {"Authorization": f"Bearer {make_token(sub='aaaaaaaa-0000-0000-0000-000000000001')}"}
    b = {"Authorization": f"Bearer {make_token(sub='bbbbbbbb-0000-0000-0000-000000000002', email='b@example.com')}"}
    client.post("/households", json={}, headers=a)
    client.post("/households", json={}, headers=b)
    return a, b, client.post("/inventory", json={"ingredient_name": "rice", "quantity": 1, "unit": "cup"}, headers=a).json()["id"]
```

- [ ] **Step 2: Write the tests** — for each of inventory items, meal plan entries and recipes: reading kitchen B's list never shows kitchen A's row; `DELETE`/`PATCH` by A's row id from B returns `404`; and the row still exists afterwards when read back as A.
- [ ] **Step 3: Run them** — `pytest tests/test_isolation.py -v`, all green.
- [ ] **Step 4: Commit** — `git commit -m "Prove kitchens cannot see or change each other's rows"`

---

## Task 10: api.js sends the token

**Owner:** Kam. **Files:** `frontend/src/api.js`, `frontend/src/api.test.js`

Lands before Tasks 11–13 so Andreas's pages have it.

**Interfaces:** Produces `setTokenProvider(fn: () => Promise<string | null>)`. `request()` attaches `Authorization: Bearer <token>` when the provider returns one. A provider indirection avoids `api.js` importing the auth context, which would be circular.

- [ ] **Step 1: Write the failing test**

```python
it('attaches the bearer token from the provider', async () => {
  const fetchMock = vi.fn().mockResolvedValue(respond(200, []))
  vi.stubGlobal('fetch', fetchMock)
  setTokenProvider(async () => 'test-token')

  await listInventory()

  expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token')
})
```

- [ ] **Step 2: Run it to see it fail** — `npx vitest run`, `setTokenProvider is not a function`.
- [ ] **Step 3: Implement**

```javascript
let tokenProvider = async () => null

export function setTokenProvider(fn) {
  tokenProvider = fn
}

async function request(path, { body, ...options } = {}) {
  const token = await tokenProvider()
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(body !== undefined && { 'Content-Type': 'application/json' }),
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
    ...(body !== undefined && { body: JSON.stringify(body) }),
  })
  // ...unchanged error handling
}
```

- [ ] **Step 4: Remove `householdId`** from every exported function's parameters and bodies, and add `getMe`, `updateDisplayName`, `createKitchen`, `joinKitchen`, `regenerateInviteCode`.
- [ ] **Step 5: Run the suite** — all green.
- [ ] **Step 6: Commit** — `git commit -m "Send the access token with every API call"`

---

## Task 11: Supabase client and auth context — Andreas

**Files:** `frontend/package.json`, `frontend/src/supabase.js`, `frontend/src/auth.jsx`, `frontend/src/main.jsx`

**Interfaces:** Produces `useAuth() -> { session, loading, signOut }` and an `AuthProvider` that calls `setTokenProvider` on mount.

- [ ] **Step 1: Install** — `cd frontend && npm install @supabase/supabase-js`
- [ ] **Step 2: Create the client**

```javascript
// frontend/src/supabase.js
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
)
```

- [ ] **Step 3: Write the provider** — `AuthProvider` holds `session` and `loading`, subscribes to `supabase.auth.onAuthStateChange`, seeds from `getSession()`, and calls `setTokenProvider(async () => (await supabase.auth.getSession()).data.session?.access_token ?? null)` once on mount. `signOut` calls `supabase.auth.signOut()`.
- [ ] **Step 4: Wrap `<App />` in `<AuthProvider>`** in `main.jsx`.
- [ ] **Step 5: Verify in the browser** — the app loads with no session and no console errors.
- [ ] **Step 6: Commit** — `git commit -m "Add the Supabase client and session context"`

---

## Task 12: Sign-in page — Andreas

**Files:** `frontend/src/pages/SignInPage.jsx`, `frontend/src/pages/auth.css`

- [ ] Email field → **Send code** → 6-digit input that accepts a pasted code → **Verify**, via `supabase.auth.signInWithOtp({ email })` then `verifyOtp({ email, token, type: 'email' })`.
- [ ] **Resend** disabled for 60 seconds with a visible countdown, matching Supabase's rate limit so the button never silently fails.
- [ ] **Continue with Google** below a divider: `signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } })`.
- [ ] Errors in plain words: *"That code didn't work — check it or send a new one."* All three states from the MVP plan's §3.1 apply.
- [ ] Verify by hand: wrong code shows the error, correct code lands in the app, Google round-trips.
- [ ] Commit — `git commit -m "Add the sign-in page"`

---

## Task 13: The app gate and kitchen setup — Andreas

**Files:** `frontend/src/App.jsx`, `frontend/src/pages/KitchenSetupPage.jsx`, `frontend/src/pages/ProfileMenu.jsx`, `frontend/src/me.js` (deleted), `frontend/src/planDefaults.js`, `frontend/src/pages/MealPlanPage.jsx`

- [ ] **Gate order** per §11.1: session loading → skeleton; no session → `SignInPage`; `name_confirmed` false → name step; no kitchen → `KitchenSetupPage`; otherwise the tabs. Onboarding (step 5 in the spec) arrives in Plan B — until then, treat `onboarded` as satisfied.
- [ ] A `401` from any call signs out; a `409 no_kitchen` sends them to kitchen setup.
- [ ] `KitchenSetupPage`: *Create a kitchen* or *Join with a code*. After creating, show the code as `ABC-234` with a copy button.
- [ ] `ProfileMenu`: the `I'm Kam` chip becomes the person's initial, opening name, email, kitchen members, the invite code with copy and regenerate, and **Sign out**.
- [ ] **Delete `me.js`.** `MEMBERS` becomes `kitchen.members` from `GET /me`; `planDefaults.js` takes profile ids; the meal plan person chip cycles real members.
- [ ] Update `planDefaults.test.js` for ids instead of names; run `npx vitest run`.
- [ ] Verify by hand: create a kitchen, join from a second account in a private window, both see two members.
- [ ] Commit — `git commit -m "Gate the app behind sign-in and kitchen setup"`

---

## Task 14: Configuration and deploy — Andreas

**Files:** `backend/.env.example`, `frontend/.env.example`, `render.yaml`, `README.md`

- [ ] Add `SUPABASE_URL` to the backend example and `render.yaml` envVars; `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` to the frontend example.
- [ ] Render `startCommand` becomes `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] README: the §12.2 dashboard steps — enable Email and Google providers, put `{{ .Token }}` in the Magic Link template so the email carries a code, set Site URL and the redirect allow list, and **configure custom SMTP before real use** because the built-in sender is heavily rate-limited.
- [ ] Verify: a fresh clone with the documented variables runs `alembic upgrade head` and serves `/health`.
- [ ] Commit — `git commit -m "Document and configure Supabase auth for deployment"`

---

## Self-review against the spec

| Spec section | Covered by |
|---|---|
| §3.1 sign-in flow | 11, 12 |
| §3.2 token verification | 3 |
| §3.3 lazy profiles | 3 (`current_profile`) |
| §4 data model | 1, 2 |
| §5 kitchens and invite codes | 4, 13 |
| §6.1 new endpoints | 4 (`PUT /me/preferences` is Plan B) |
| §6.2 scoping and 404s | 5–8, 9 |
| §6.3 personal vs kitchen recipes | **Plan C** — Task 5 leaves `owner_id` null |
| §7 onboarding | **Plan B** |
| §8 migrations | 1 |
| §9 merged prompts | **Plan C** |
| §10 allergy guard | **Plan C** |
| §11 frontend | 11, 12, 13 |
| §12 configuration | 14 |
| §13 error handling | 3, 4, 5–8, 13 |
| §14 testing | 3, 4, 9, plus per-task tests |

Two deliberate deviations from the spec, both noted above: migration `0001` creates the preferences table and `recipes.owner_id` before the features that use them, and the gate treats `onboarded` as satisfied until Plan B ships.
