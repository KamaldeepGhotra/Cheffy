import { useEffect, useRef, useState } from 'react'
import { addMealPlanEntry, deleteMealPlanEntry, listRecipes, saveRecipe, searchRecipeCandidates, suggestRecipes } from '../api.js'
import { startOfWeek, toISODate } from '../week.js'
import './recipes.css'

const HOUSEHOLD_ID = 'roommates'
// Candidates aren't saved anywhere, so switching tabs would otherwise lose them and cost
// another Gemini call to get back. sessionStorage keeps them until the browser tab closes.
const CANDIDATES_KEY = 'cheffy.searchCandidates'

function loadCandidates() {
  try {
    return JSON.parse(sessionStorage.getItem(CANDIDATES_KEY)) ?? []
  } catch {
    return []
  }
}

function storeCandidates(candidates) {
  try {
    if (candidates.length === 0) sessionStorage.removeItem(CANDIDATES_KEY)
    else sessionStorage.setItem(CANDIDATES_KEY, JSON.stringify(candidates))
  } catch {}
}

function badgeClass(percentage) {
  if (percentage >= 80) return 'badge badge-success'
  if (percentage >= 40) return 'badge'
  return 'badge badge-muted'
}

function missingLine(names) {
  if (names.length === 0) return 'You have everything'
  const more = names.length - 3
  return `Missing: ${names.slice(0, 3).join(', ')}${more > 0 ? ` +${more} more` : ''}`
}

function byMatch(a, b) {
  return b.match_percentage - a.match_percentage || b.id - a.id
}

function formatQuantity(quantity) {
  return Number.isInteger(quantity) ? quantity : Number(quantity.toFixed(2))
}

function IngredientRows({ items }) {
  return (
    <ul>
      {items.map((item) => (
        <li key={item.ingredient_id} className="row">
          <span>{item.ingredient_name}</span>
          <span className="muted">{formatQuantity(item.quantity)} {item.unit}</span>
        </li>
      ))}
    </ul>
  )
}

function RecipeCard({ recipe, onOpen }) {
  return (
    <button type="button" className="card recipe-card" onClick={onOpen}>
      <span className={badgeClass(recipe.match_percentage)}>{Math.round(recipe.match_percentage)}%</span>
      <span className="recipe-title">{recipe.name}</span>
      <span className="recipe-missing">{missingLine(recipe.missing_ingredients)}</span>
    </button>
  )
}

// A search result that isn't saved yet, so it gets "Use this one" rather than opening a sheet.
function CandidateCard({ candidate, busy, disabled, onUse }) {
  return (
    <div className="card recipe-card candidate-card">
      <span className={badgeClass(candidate.match_percentage)}>{Math.round(candidate.match_percentage)}%</span>
      <span className="recipe-title">{candidate.name}</span>
      <span className="recipe-missing">{missingLine(candidate.missing_ingredients)}</span>
      <span className="muted candidate-meta">
        Serves {candidate.servings} · {candidate.ingredients.length} ingredients
      </span>
      <button type="button" className="btn btn-primary" onClick={onUse} disabled={disabled}>
        {busy ? 'Adding…' : 'Use this one'}
      </button>
    </div>
  )
}

function RecipeSheet({ recipe, plannedEntryId, busy, onPlan, onUndo, onClose }) {
  const missing = new Set(recipe.missing_ingredients)
  const need = recipe.ingredients.filter((item) => missing.has(item.ingredient_name))
  const have = recipe.ingredients.filter((item) => !missing.has(item.ingredient_name))

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={recipe.name} onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <div>
            <span className={badgeClass(recipe.match_percentage)}>{Math.round(recipe.match_percentage)}% of ingredients on hand</span>
            <h3>{recipe.name}</h3>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close">×</button>
        </div>
        {need.length > 0 ? (
          <>
            <h4>To cook this, buy</h4>
            <IngredientRows items={need} />
          </>
        ) : (
          <p className="muted">You have everything for this one.</p>
        )}
        {have.length > 0 && (
          <>
            <h4>Already in your kitchen</h4>
            <IngredientRows items={have} />
          </>
        )}
        <h4>How to make it</h4>
        <p className="recipe-steps">{recipe.instructions}</p>
        <p className="meta">
          Serves {recipe.servings}
          {recipe.calories != null && ` · ${Math.round(recipe.calories)} kcal`}
          {recipe.protein != null && ` · ${Math.round(recipe.protein)}g protein`}
          {' per serving'}
        </p>
        <div className="recipe-actions">
          {plannedEntryId ? (
            <>
              <span className="badge badge-success">Planned ✓</span>
              <button type="button" className="btn btn-ghost" onClick={onUndo} disabled={busy}>Undo</button>
            </>
          ) : (
            <button type="button" className="btn btn-primary" onClick={onPlan} disabled={busy}>
              {busy ? 'Planning…' : 'Plan this week'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function RecipeSearchPage() {
  const [recipes, setRecipes] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [suggesting, setSuggesting] = useState(false)
  const [candidates, setCandidatesState] = useState(loadCandidates)
  const [savingIndex, setSavingIndex] = useState(null)
  const [openId, setOpenId] = useState(null)
  const [planned, setPlanned] = useState({})
  const [planningId, setPlanningId] = useState(null)
  // React StrictMode runs effects twice in dev; without this guard an empty library gets six suggestions.
  const autoSuggested = useRef(false)

  // One writer, so what's on screen and what's in storage can't drift apart.
  function setCandidates(next) {
    storeCandidates(next)
    setCandidatesState(next)
  }

  async function getIdeas() {
    setActionError(null)
    setSuggesting(true)
    try {
      const fresh = await suggestRecipes({ householdId: HOUSEHOLD_ID, count: 3 })
      setRecipes((prev) => [...fresh, ...(prev ?? [])].sort(byMatch))
    } catch (err) {
      setActionError({ message: err.message, retry: getIdeas })
    } finally {
      setSuggesting(false)
    }
  }

  async function load() {
    setLoadError(null)
    try {
      const list = await listRecipes(HOUSEHOLD_ID)
      setRecipes(list)
      if (list.length === 0 && !autoSuggested.current) {
        autoSuggested.current = true
        getIdeas()
      }
    } catch (err) {
      setLoadError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function runSearch(text) {
    setActionError(null)
    setSearching(true)
    try {
      const results = await searchRecipeCandidates({ householdId: HOUSEHOLD_ID, query: text })
      setCandidates(results)
      setQuery('')
    } catch (err) {
      setActionError({ message: err.message, retry: () => runSearch(text) })
    } finally {
      setSearching(false)
    }
  }

  // Candidates aren't in the library yet, so picking one is what actually saves it.
  async function useCandidate(candidate, index) {
    setActionError(null)
    setSavingIndex(index)
    try {
      const saved = await saveRecipe({ householdId: HOUSEHOLD_ID, candidate })
      setRecipes((prev) => [saved, ...(prev ?? []).filter((r) => r.id !== saved.id)])
      setCandidates([])
      setOpenId(saved.id)
    } catch (err) {
      setActionError({ message: err.message, retry: () => useCandidate(candidate, index) })
    } finally {
      setSavingIndex(null)
    }
  }

  function handleSearch(e) {
    e.preventDefault()
    const text = query.trim()
    if (text) runSearch(text)
  }

  async function planThisWeek(recipe) {
    setActionError(null)
    setPlanningId(recipe.id)
    try {
      const entry = await addMealPlanEntry({
        householdId: HOUSEHOLD_ID,
        weekStart: toISODate(startOfWeek(new Date())),
        recipeId: recipe.id,
        servings: 1,
      })
      setPlanned((prev) => ({ ...prev, [recipe.id]: entry.id }))
    } catch (err) {
      setActionError({ message: err.message, retry: () => planThisWeek(recipe) })
    } finally {
      setPlanningId(null)
    }
  }

  async function undoPlan(recipe) {
    setActionError(null)
    setPlanningId(recipe.id)
    try {
      await deleteMealPlanEntry(planned[recipe.id])
      setPlanned((prev) => {
        const next = { ...prev }
        delete next[recipe.id]
        return next
      })
    } catch (err) {
      setActionError({ message: err.message, retry: () => undoPlan(recipe) })
    } finally {
      setPlanningId(null)
    }
  }

  const list = recipes ?? []
  const openRecipe = list.find((recipe) => recipe.id === openId) ?? null

  return (
    <div>
      <h2>Recipe Search</h2>
      <form className="input-row search-row" onSubmit={handleSearch}>
        <input
          placeholder="What do you want to eat?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={searching}
        />
        <button className="btn btn-primary" type="submit" disabled={searching || !query.trim()}>
          {searching ? 'Searching…' : 'Search'}
        </button>
      </form>

      {loadError && (
        <div className="banner-error">
          <span>{loadError}</span>
          <button type="button" className="btn" onClick={load}>Retry</button>
        </div>
      )}
      {actionError && (
        <div className="banner-error">
          <span>{actionError.message}</span>
          <button type="button" className="btn" onClick={actionError.retry}>Retry</button>
        </div>
      )}

      {candidates.length > 0 && (
        <>
          <div className="section-head">
            <p className="from-search">Pick one to add to your recipes</p>
            <button type="button" className="btn btn-ghost" onClick={() => setCandidates([])}>Dismiss</button>
          </div>
          <div className="recipe-list">
            {candidates.map((candidate, index) => (
              <CandidateCard
                key={`${candidate.name}-${index}`}
                candidate={candidate}
                busy={savingIndex === index}
                disabled={savingIndex !== null}
                onUse={() => useCandidate(candidate, index)}
              />
            ))}
          </div>
        </>
      )}

      <div className="section-head">
        <h3>Suggested for your kitchen</h3>
        <button type="button" className="btn" onClick={getIdeas} disabled={suggesting}>
          {suggesting ? 'Thinking…' : 'Get ideas'}
        </button>
      </div>
      {recipes === null && !loadError && (
        <div className="recipe-list" aria-label="Loading">
          <div className="card recipe-skeleton"><span className="skeleton" /><span className="skeleton" /></div>
          <div className="card recipe-skeleton"><span className="skeleton" /><span className="skeleton" /></div>
          <div className="card recipe-skeleton"><span className="skeleton" /><span className="skeleton" /></div>
        </div>
      )}
      {recipes && list.length === 0 && (
        <p className="empty">
          {suggesting ? 'Thinking about what you can make…' : "No recipes yet. Tap Get ideas and we'll suggest some from your inventory."}
        </p>
      )}
      {list.length > 0 && (
        <div className="recipe-list">
          {list.map((recipe) => (
            <RecipeCard key={recipe.id} recipe={recipe} onOpen={() => setOpenId(recipe.id)} />
          ))}
        </div>
      )}

      {openRecipe && (
        <RecipeSheet
          recipe={openRecipe}
          plannedEntryId={planned[openRecipe.id]}
          busy={planningId === openRecipe.id}
          onPlan={() => planThisWeek(openRecipe)}
          onUndo={() => undoPlan(openRecipe)}
          onClose={() => setOpenId(null)}
        />
      )}
    </div>
  )
}
