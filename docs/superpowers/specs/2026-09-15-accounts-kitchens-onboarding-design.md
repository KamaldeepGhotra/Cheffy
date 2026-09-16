# Accounts, Kitchens and Onboarding — Design

**Status:** proposed, 2026-09-15. Builds on the MVP in [2026-09-11-mvp-plan.md](../plans/2026-09-11-mvp-plan.md), which this changes in several pinned contracts (§6).

## 1. Why

Cheffy currently has no users. Every page hardcodes `HOUSEHOLD_ID = 'roommates'`, the people in the app are a literal `MEMBERS = ['Andreas', 'Kam']`, and every endpoint trusts whatever `household_id` the browser sends. Once hosted, anyone with the URL could read and change anyone's kitchen — and the `DELETE`/`PATCH` routes act on any row id without checking whose it is.

Recipe suggestions are also generic because the model knows nothing about who is cooking. This design adds real accounts, shared kitchens, and a short onboarding that feeds the Gemini prompt — and it has to land **before** the app is hosted, while the database is still empty.

## 2. Decisions

| Question | Decision |
|---|---|
| Sign-in | Supabase Auth: **6-digit email code** and **Google**. No passwords. |
| Phone / SMS | Out of scope — costs money per message. Same flow can add it later. |
| Sharing a kitchen | **Invite code**, typed once by the second person. |
| Onboarding | Tap-through questions, each skippable, **editable later** from a profile menu. |
| Recipe lists | **Two lists**: *For you* (your tastes) and *Kitchen* (everyone's). |
| Allergy safety | Prompt **and** a server-side ingredient filter. |
| Schema changes | **Alembic migrations**, starting now. |

Naming: the code keeps `household`; everything a person sees says **kitchen**.

## 3. Architecture

### 3.1 Sign-in flow

```
Browser                         Supabase Auth                   Cheffy API
  |-- signInWithOtp(email) ------->|  emails a 6-digit code
  |-- verifyOtp(email, code) ----->|
  |<------------- session (JWT) ---|
  |-- GET /me  Authorization: Bearer <JWT> ------------------------->|
  |                                |<-- JWKS (cached) --------------|  verify signature, exp, aud, iss
  |<----------------------------------------- profile, kitchen -----|
```

Google follows the same path with `signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } })` instead of the two OTP calls.

- The frontend uses `@supabase/supabase-js` for sign-in and token refresh. It never sees or stores a password.
- `request()` in `api.js` attaches `Authorization: Bearer <access token>` to every call.
- **No request carries `household_id` anymore.** The API derives the kitchen from the verified user.

### 3.2 Token verification (backend)

A FastAPI dependency `current_user` in `backend/app/auth.py`:

1. Reads the `Authorization: Bearer` header. Missing → `401`.
2. Verifies the token with **PyJWT**'s `PyJWKClient` against `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`, accepting `ES256` and `RS256` only. HS256 is rejected — Supabase documents the shared-secret approach as not recommended for production, and accepting it would mean holding a signing secret in the API.
3. Requires `exp` (not expired), `aud == "authenticated"`, `iss == "https://<ref>.supabase.co/auth/v1"`. Any failure → `401`.
4. Returns `sub` (the user's UUID) and `email`.

The JWKS client caches keys in memory. Supabase serves the endpoint with roughly a 10-minute cache, so a rotated key is picked up within minutes without a deploy.

A second dependency, `current_household`, loads the caller's profile and returns their household, or responds `409 {"detail": "no_kitchen"}` when they haven't created or joined one. Every existing router switches from a `household_id` parameter to this dependency.

### 3.3 Why profiles live in our tables

Supabase keeps users in its own `auth.users` table. Cheffy does **not** foreign-key into it: local development runs on SQLite, which has no `auth` schema, and tests would need a live Supabase. Instead a `profiles` row is created **lazily** the first time a verified user calls `GET /me`, keyed by the same UUID. Its `display_name` starts as the token's `user_metadata.full_name` when Google provides one, otherwise the part of the email before `@`, so the column is never empty — the name step (§7.1) lets them correct it before anyone else sees it.

## 4. Data model

All changes land as Alembic migration `0001` (§8). Existing local data is discarded — the app has not launched.

### 4.1 New tables

**`households`**

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `name` | str, not null | defaults to "&lt;creator's display name&gt;'s kitchen", editable |
| `invite_code` | str(6), unique, not null | see §5 |
| `created_at` | datetime | |

**`profiles`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | the Supabase user id (`sub`) |
| `email` | str, not null | copied from the token, for display |
| `display_name` | str, not null | onboarding step 0 |
| `household_id` | FK households, nullable | null until they create or join one |
| `name_confirmed_at` | datetime, nullable | null shows the name step (§11.1) |
| `onboarded_at` | datetime, nullable | null shows onboarding |
| `created_at` | datetime | |

**`preferences`** — one row per **person**, because allergies belong to people.

| Column | Type | Meaning of `null` vs empty |
|---|---|---|
| `profile_id` | UUID PK, FK profiles | |
| `allergies` | JSON list of keys | `null` = **not answered**, `[]` = **answered "none"** |
| `allergies_other` | str, nullable | free text |
| `diets` | JSON list | same rule |
| `dislikes` | JSON list | same rule |
| `dislikes_other` | str, nullable | |
| `cuisines` | JSON list | same rule |
| `spice` | `mild` \| `medium` \| `hot`, nullable | |
| `equipment` | JSON list | same rule |
| `effort` | `quick` \| `hour` \| `afternoon`, nullable | |
| `budget` | `tight` \| `moderate` \| `flexible`, nullable | |
| `batch_days` | int 2–4, nullable | |
| `updated_at` | datetime | |

The `null`/`[]` distinction is load-bearing: a skipped allergy question must never be sent to the prompt as "no allergies".

The row is created on the first `PUT /me/preferences`. Until then, reads return every field as `null` — unanswered, not empty.

### 4.2 Changed tables

| Table | Change |
|---|---|
| `inventory_items` | `household_id` becomes int FK `households.id` |
| `meal_plan_entries` | `household_id` becomes int FK; `assigned_to` (a name string) is replaced by `assigned_to_id`, UUID FK `profiles.id`, nullable |
| `recipes` | gains `household_id` int FK, not null, and `owner_id` UUID FK `profiles.id`, nullable — **null means a kitchen recipe, set means personal** |
| `ingredients`, `recipe_ingredients` | unchanged; ingredient names stay global and canonical |

## 5. Kitchens and invite codes

- **First sign-in with no kitchen** shows two choices: *Create a kitchen* or *Join with a code*.
- **Create** makes the household, attaches the caller, and shows the code with a copy button.
- **Join** takes a code; the input ignores case, spaces and hyphens.
- **Codes** are 6 characters from `ABCDEFGHJKMNPQRSTUVWXYZ23456789` — no `0/O`, `1/I/L`, which get misread off a phone screen. Generated with Python's `secrets`, unique-constrained, retried on the unlikely collision. Displayed as `ABC-234`. That alphabet gives about 887 million codes.
- **Regenerate** from the profile menu replaces the code; the old one stops working immediately. This is the fix for a code shared too widely.
- One kitchen per person. Leaving, removing a member, and transferring a kitchen are out of scope (§12).

## 6. API changes

### 6.1 New endpoints

```
GET   /me                     -> 200 MeOut        creates the profile on first call
PATCH /me  {display_name}     -> 200 MeOut
PUT   /me/preferences  {...}  -> 200 MeOut        first call also sets onboarded_at

POST  /households  {name?}    -> 201 MeOut        409 already in a kitchen
POST  /households/join  {code}-> 200 MeOut        404 unknown code   409 already in a kitchen
POST  /households/invite-code -> 200 MeOut        new code, old one invalid
```

```python
class MemberOut(BaseModel):
    id: UUID
    display_name: str

class KitchenOut(BaseModel):
    id: int
    name: str
    invite_code: str
    members: list[MemberOut]

class MeOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    kitchen: KitchenOut | None
    onboarded: bool
    preferences: PreferencesOut      # every field nullable, per §4.1
```

`PUT /me/preferences` with an empty body is valid: it is how "skip everything" still finishes onboarding.

### 6.2 Changes to existing endpoints

- **Every** `household_id` query parameter and body field is removed. Routes depend on `current_household` instead.
- **Row access is always scoped to the caller's kitchen.** `DELETE /inventory/{id}`, `PATCH /meal-plan/{id}`, `DELETE /meal-plan/{id}` and any recipe-by-id route return **`404`** for a row in another kitchen — not `403`, which would confirm the id exists.
- `MealPlanEntryCreate` / `MealPlanEntryUpdate`: `assigned_to` becomes `assigned_to_id: UUID | None`. An id that isn't a member of the kitchen → `422`. `MealPlanEntryOut` returns both `assigned_to_id` and `assigned_to_name`.

### 6.3 Recipes: personal and kitchen

```
GET   /recipes?scope=mine|kitchen|all          -> 200 list[RankedRecipeOut]
POST  /recipes/suggest  {scope, count=3}       -> 201 list[RankedRecipeOut]
POST  /recipes/search   {query, count=3}       -> 200 list[RecipeCandidate]
POST  /recipes          {candidate, scope}     -> 201 RankedRecipeOut     scope defaults to "mine"
POST  /recipes/{id}/share                      -> 200 RankedRecipeOut     personal -> kitchen
```

- **Visibility:** a person sees every kitchen recipe (`owner_id` null) plus **their own** personal ones. Another member's personal recipes are invisible and `404` by id.
- `scope=mine` → your personal recipes. `scope=kitchen` → kitchen recipes. `scope=all` → both, used when the kitchen has one member.
- **Sharing is one-way.** A kitchen recipe has no owner, so there's nothing to un-share it back to.
- Anyone in the kitchen can plan any recipe they can see. **Planning a personal recipe makes its name visible** to the kitchen on the meal plan and the grocery list ("for Pad Thai") — once it's in the shared week, the kitchen is cooking it. The recipe itself stays personal.
- **Search** is scored and guarded with the *For you* profile, matching where its results save.
- **A one-member kitchen** calls suggest with `scope=kitchen`, so whoever joins later inherits those suggestions instead of starting from an empty list.
- `RankedRecipeOut` gains `scope: "mine" | "kitchen"`.

## 7. Onboarding and preferences

### 7.1 The questions

One per screen, tap chips, **Back** and **Skip** on each, progress dots. Step 0 is required; everything else is skippable.

| # | Screen | Input | Stored as |
|---|---|---|---|
| 0 | What should we call you? | text, prefilled from Google | `display_name` |
| 1 | Any food allergies? | multi: peanuts, tree nuts, dairy, eggs, gluten, shellfish, fish, soy, sesame · **None** · other | `allergies`, `allergies_other` |
| 2 | Do you follow a diet? | multi: vegetarian, vegan, pescatarian, halal, kosher, no pork, no beef · **None** | `diets` |
| 3 | Anything you won't eat? | multi: mushrooms, olives, coriander, seafood, offal, very spicy · **Nothing** · other | `dislikes`, `dislikes_other` |
| 4 | Cuisines you love | multi grid: Italian, Mexican, Chinese, Indian, Thai, Japanese, Korean, Middle Eastern, Mediterranean, American, Caribbean, West African | `cuisines` |
| 5 | How spicy? | mild · medium · hot | `spice` |
| 6 | What's in your kitchen? | multi: oven, hob, microwave, air fryer, rice cooker, slow cooker | `equipment` |
| 7 | On prep day, how long can you cook? | under 30 min · about an hour · happy to spend the afternoon | `effort` |
| 8 | Food budget | tight · moderate · flexible | `budget` |
| 9 | How long should a batch last? | 2 · 3 · 4 days | `batch_days` |

Step 0 is shown **before kitchen setup** (§11.1), because the kitchen's default name and its member list both use it. Steps 1–9 come after.

On questions with a **None** option, choosing it stores `[]`; **Skip** stores `null` everywhere. On a phone the order matters: safety first, then taste, then logistics — if someone quits halfway, the questions that protect them are already answered.

### 7.2 Editing later

The profile menu's **Preferences** page renders the same questions as one scrolling form rather than a wizard, with a single Save. It uses the same components, so the two can't drift apart.

## 8. Migrations

- Add **Alembic** to `backend/`, with `render_as_batch=True` so SQLite can apply the column changes locally.
- Migration `0001` creates the §4 schema from scratch. Any existing local `cheffy.db`, and any tables already created in Supabase during P6 testing, are dropped once before it runs.
- `Base.metadata.create_all` is **removed** from the app's lifespan — Alembic owns the schema. Tests keep using `create_all` on their in-memory database, which is faster.
- A test runs `alembic upgrade head` on a fresh SQLite file and then `alembic check`, which fails when the models have changes no migration covers — so a forgotten migration fails the test suite instead of production.
- On Render, `startCommand` becomes `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## 9. Personalised prompts

### 9.1 Merging a kitchen's preferences

`backend/app/kitchen_profile.py` builds a `KitchenProfile` for a scope:

| Preference | *For you* | *Kitchen* | Why |
|---|---|---|---|
| Allergies | **union of all members** | **union of all members** | Shared fridge, pans and boards; a personal recipe can be planned for someone else. |
| Diets | **yours** | **union of all members** | A diet is a choice; an allergy is not. A vegetarian's roommate can still get meat on their own list. |
| Dislikes | yours | union, as *"try to avoid"* | Soft — a hard union would over-constrain. |
| Cuisines | yours | union | |
| Spice | yours | **mildest** answered | Everyone has to be able to eat it. |
| Equipment | union | union | Everyone is describing the same kitchen. |
| Effort, budget | yours | **lowest** answered | The dish has to work for whoever cooks it. |
| Batch days | yours | longest answered | |
| People eating | 1 | member count | |

Unanswered (`null`) fields are left out of the merge entirely.

### 9.2 Into the prompt

`gemini_client.py`'s hardcoded *"two university housemates"* paragraph is replaced by one rendered from the `KitchenProfile`, in two parts:

- **Must** — allergies and diets, phrased as absolute constraints.
- **Prefer** — everything else.

A kitchen where nobody has onboarded gets today's default wording, so suggestions still work before anyone answers a question. The quality bar and the ladder (cook tonight → a different direction → worth a small shop) from the prompt rewrite are kept.

## 10. Allergy guard

The prompt is not a guarantee, so `backend/app/allergens.py` checks every recipe **before a person sees it**.

- A table maps each allergy key to ingredient keywords, matched on word boundaries against normalized ingredient names. A few entries that are easy to miss:
  - `gluten` → wheat, flour, bread, pasta, couscous, barley, rye, seitan, breadcrumb, **soy sauce**
  - `dairy` → milk, butter, cheese, cream, yogurt, ghee, whey, paneer
  - `peanuts` → peanut, groundnut, satay
  - `soy` → soy, tofu, tempeh, edamame, miso, **soy sauce**
  - `fish` → salmon, tuna, cod, anchovy, sardine, **fish sauce**
- Word boundaries keep `butternut squash` from matching `butter`.
- Free-text `allergies_other` is split into words and matched the same way — best effort.
- **Where it runs:**
  - on Gemini's suggestions and search candidates, before they are saved or returned — matches are dropped;
  - on `GET /recipes`, so if someone with an allergy joins later, existing kitchen recipes that conflict are **hidden, not deleted**.
- If the guard removes some suggestions, the response simply has fewer. It does not re-query Gemini.
- When the kitchen has any allergy recorded, the recipe sheet shows *"Checked against your kitchen's allergies — always read the ingredients."* The guard is a safety net, not a certification, and the UI should not claim otherwise.

## 11. Frontend

### 11.1 App gate

`App.jsx` resolves, in order:

1. **Session loading** → a skeleton, never a flash of the sign-in page.
2. **No session** → `SignInPage`.
3. **Name never confirmed** (new profile) → the name step.
4. **`GET /me` returns no kitchen** → `KitchenSetupPage`.
5. **`onboarded` is false** → `OnboardingFlow`, steps 1–9.
6. Otherwise → the tabs.

A `401` from any call signs out and returns to step 2. A `409 no_kitchen` returns to step 4.

"Name never confirmed" needs to be stored, since a prefilled `display_name` is never empty: `profiles` gets `name_confirmed_at`, datetime nullable, set by the first `PATCH /me`.

### 11.2 Sign-in page

- Email field → **Send code** → a 6-digit input that accepts a pasted code → verify.
- **Resend** is disabled for 60 seconds with a visible countdown, matching Supabase's rate limit, so the button never silently fails.
- **Continue with Google** below a divider.
- Errors in plain words: *"That code didn't work — check it or send a new one."*

### 11.3 Profile menu

The `I'm Kam` chip becomes the person's initial and opens a menu with: name and email, **Kitchen** (members, invite code with copy, regenerate), **Preferences**, **Sign out**.

### 11.4 Recipes tab

- A **For you | Kitchen** switch using the existing `.seg` segmented control, above the list. Defaults to *For you*.
- Hidden when the kitchen has one member; that person gets a single list with `scope=all`.
- Search candidates are unchanged; **Use this one** saves to *For you*.
- The recipe sheet gets **Share with kitchen** on personal recipes.
- The two-row cap and auto-suggest-on-grocery-change from the recipes work apply to whichever list is showing, each tracking its own fingerprint.

### 11.5 Removals

- `HOUSEHOLD_ID` from all four pages, and the `householdId` parameter from every `api.js` function.
- `me.js`'s `MEMBERS`, `getMe` and `setMe`. Members and the current user come from `GET /me`.
- `planDefaults.js` takes `me` and `members` as profile ids.
- The Meal Plan person chip cycles through the kitchen's real members.

## 12. Configuration and setup

### 12.1 Environment

| Where | Variable | Notes |
|---|---|---|
| Backend | `SUPABASE_URL` | issuer and JWKS URL are derived from it |
| Frontend | `VITE_SUPABASE_URL` | |
| Frontend | `VITE_SUPABASE_PUBLISHABLE_KEY` | the anon/publishable key; safe in the browser by design |

New dependencies: backend `alembic`, `PyJWT[crypto]`; frontend `@supabase/supabase-js`.

Local development signs in against the real Supabase project (auth is free) while data stays in local SQLite. Tests never touch the network: they generate an ES256 key pair and hand the verifier that key instead of the JWKS URL.

### 12.2 One-time dashboard setup

**Supabase**
- Authentication → Providers: enable **Email** and **Google**.
- Authentication → Email Templates → **Magic Link**: include `{{ .Token }}` so the email carries the code.
- Authentication → URL Configuration: **Site URL** = the Vercel URL; redirect allow list includes it and `http://localhost:5173`.
- **Custom SMTP before real use.** Supabase's built-in email sender is heavily rate-limited and intended for testing. A free transactional provider is enough for two people.

**Google Cloud**
- Create an OAuth client (web application).
- Authorized JavaScript origins: the Vercel URL and `http://localhost:5173`.
- Authorized redirect URI: `https://<ref>.supabase.co/auth/v1/callback`.
- Until the consent screen is verified, Google shows an "unverified app" warning. That's fine for testers.

## 13. Error handling

| Situation | API | What the person sees |
|---|---|---|
| Missing, expired or forged token | `401` | Signed out, back to sign-in |
| Signed in, no kitchen | `409 no_kitchen` | Kitchen setup |
| Wrong invite code | `404` | "No kitchen with that code." |
| Already in a kitchen, tries to join another | `409` | "You're already in a kitchen." |
| Row from another kitchen | `404` | The page's normal error state |
| Assigning a meal to a non-member | `422` | Not reachable from the UI; guards the API |
| Guard drops every suggestion | `201 []` | "Nothing safe for your kitchen this time — try Get ideas again." |

## 14. Testing

**Backend**
- Auth: valid token accepted; expired, wrong audience, wrong issuer, bad signature, HS256-signed and missing header all `401`.
- Kitchens: create sets a code; join with a valid, invalid and lower-case-hyphenated code; joining twice is `409`; regenerate invalidates the old code.
- **Isolation:** a member of kitchen A gets `404` for kitchen B's inventory rows, meal plan entries and recipes, on read, update and delete. One member's personal recipe is invisible to the other.
- Preferences: skipped allergies stay `null`; *None* stores `[]`; an empty `PUT` completes onboarding.
- Merge rules: each row of the §9.1 table as a unit test, including unanswered fields being left out.
- Prompt: allergies and diets render under *Must*; a kitchen with no preferences falls back to the default wording.
- Guard: `peanut butter` dropped for a peanut allergy; `soy sauce` dropped for gluten; `butternut squash` kept for dairy; free-text allergies match.
- Migrations: `alembic upgrade head` on a fresh database, then autogenerate reports no diff.

**Frontend**
- Vitest for pure modules: invite-code input normalization, `planDefaults` with member ids, the fingerprint per scope.
- Browser, by hand: code sign-in, Google sign-in, create a kitchen, join from a second account, full onboarding and skip-everything, edit preferences, switch *For you*/*Kitchen*, share a recipe, sign out. Plus one run with the backend stopped, to confirm every new screen's error state.

## 15. Out of scope

- SMS / phone sign-in
- Email invitations
- More than one kitchen per person; leaving, removing a member, transferring ownership
- Account deletion and data export
- Rate limiting beyond what Supabase applies
- Recipe images and the "tap the dishes you like" onboarding grid
- Warning when a meal is assigned to someone whose own allergies conflict with a personal recipe (the kitchen-wide guard covers the dangerous case)

## 16. Risks

- **The allergy guard is keyword-based.** Uncommon names will slip through and some safe dishes will be hidden (*cream of tartar* contains no dairy). §10's UI copy is deliberately honest about this.
- **This touches every router and every page.** It is the largest change since the core loop, and the two-person ownership split from the MVP plan does not map onto it cleanly — the plan for this needs a sequencing that avoids both of you rewriting the same router at once.
- **Built-in Supabase email** will throttle testing. Set up SMTP early, not on launch day.
- **A recipe hidden by the guard can still be on the meal plan.** If someone with an allergy joins a kitchen that already planned a conflicting meal, the recipe drops out of the Recipes tab but its meal-plan entry and grocery lines remain. Flagging those entries is a follow-up.
