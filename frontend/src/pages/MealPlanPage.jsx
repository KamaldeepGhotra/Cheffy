import { useEffect, useState } from 'react'
import {
  addMealPlanEntry,
  deleteMealPlanEntry,
  getMealPlan,
  listRecipes,
  updateMealPlanEntry,
} from '../api.js'
import { DAY_NAMES, dayOfWeek, formatDay, shiftWeeks, startOfWeek, toISODate } from '../week.js'
import { MEMBERS, getMe } from '../me.js'
import './plan.css'

const HOUSEHOLD_ID = 'roommates'

function nextMember(current) {
  return MEMBERS[(MEMBERS.indexOf(current) + 1) % MEMBERS.length]
}

function servingsLabel(count) {
  return `${count} ${count === 1 ? 'serving' : 'servings'}`
}

export default function MealPlanPage() {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()))
  const [entries, setEntries] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [recipes, setRecipes] = useState([])
  const [adding, setAdding] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const weekKey = toISODate(weekStart)
  const planned = (entries ?? []).filter((e) => e.day == null)
  const selected = planned.find((e) => e.id === selectedId) ?? null

  async function refresh() {
    setLoadError(null)
    try {
      setEntries(await getMealPlan(HOUSEHOLD_ID, weekKey))
    } catch (err) {
      setLoadError(err.message)
    }
  }

  useEffect(() => {
    listRecipes(HOUSEHOLD_ID).then(setRecipes).catch(() => setRecipes([]))
  }, [])

  useEffect(() => {
    setEntries(null)
    setSelectedId(null)
    setAdding(null)
    refresh()
  }, [weekKey])

  // Show the change at once and put the old entry back if the server refuses it.
  async function patch(entry, fields) {
    setActionError(null)
    setBusyId(entry.id)
    setEntries((prev) => prev.map((e) => (e.id === entry.id ? { ...e, ...fields } : e)))
    try {
      const updated = await updateMealPlanEntry(entry.id, fields)
      setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
    } catch (err) {
      setEntries((prev) => prev.map((e) => (e.id === entry.id ? entry : e)))
      setActionError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  function schedule(day) {
    if (!selected) return
    const entry = selected
    setSelectedId(null)
    patch(entry, { day, assigned_to: entry.assigned_to ?? getMe() ?? MEMBERS[0] })
  }

  async function remove(entry) {
    setActionError(null)
    setBusyId(entry.id)
    try {
      await deleteMealPlanEntry(entry.id)
      setEntries((prev) => prev.filter((e) => e.id !== entry.id))
      if (selectedId === entry.id) setSelectedId(null)
    } catch (err) {
      setActionError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  function startAdding(day) {
    setAdding({ day, recipeId: recipes[0]?.id ?? '', assignedTo: getMe() ?? MEMBERS[0], servings: 1 })
  }

  // A recipe sitting in the tray is already an entry for this week. Adding it again would
  // make a second one, and the grocery list counts every entry — so move it instead.
  function plannedMatch(recipeId) {
    return planned.find((entry) => entry.recipe_id === Number(recipeId)) ?? null
  }

  async function submitAdd(e) {
    e.preventDefault()
    if (!adding?.recipeId) return

    const existing = plannedMatch(adding.recipeId)
    if (existing) {
      const { day, assignedTo, servings } = adding
      setAdding(null)
      patch(existing, { day, assigned_to: assignedTo, servings: Number(servings) })
      return
    }

    setActionError(null)
    try {
      const created = await addMealPlanEntry({
        householdId: HOUSEHOLD_ID,
        weekStart: weekKey,
        day: adding.day,
        recipeId: Number(adding.recipeId),
        servings: Number(adding.servings),
        assignedTo: adding.assignedTo,
      })
      setEntries((prev) => [...(prev ?? []), created])
      setAdding(null)
    } catch (err) {
      setActionError(err.message)
    }
  }

  return (
    <div>
      <div className="week-nav">
        <button type="button" className="btn btn-ghost" onClick={() => setWeekStart(shiftWeeks(weekStart, -1))} aria-label="Previous week">‹</button>
        <h2>Week of {formatDay(weekStart)}</h2>
        <button type="button" className="btn btn-ghost" onClick={() => setWeekStart(shiftWeeks(weekStart, 1))} aria-label="Next week">›</button>
      </div>

      {loadError && (
        <div className="banner-error">
          <span>{loadError}</span>
          <button type="button" className="btn" onClick={refresh}>Retry</button>
        </div>
      )}
      {actionError && (
        <div className="banner-error">
          <span>{actionError}</span>
        </div>
      )}

      <section className="tray">
        <h3>Planned, no day yet</h3>
        {entries === null && !loadError && (
          <div className="loading" aria-label="Loading">
            <span className="skeleton" />
            <span className="skeleton" />
          </div>
        )}
        {entries && planned.length === 0 && (
          <p className="empty">
            {recipes.length === 0
              ? 'No recipes yet. Search for one on the Recipes tab first.'
              : 'Nothing planned yet. Pick some on the Recipes tab.'}
          </p>
        )}
        {planned.length > 0 && (
          <div className="tray-cards">
            {planned.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className={`tray-card${entry.id === selectedId ? ' selected' : ''}`}
                aria-pressed={entry.id === selectedId}
                disabled={busyId === entry.id}
                onClick={() => setSelectedId(entry.id === selectedId ? null : entry.id)}
              >
                <span className="tray-name">{entry.recipe_name}</span>
                <span className="muted">
                  {servingsLabel(entry.servings)}{entry.assigned_to ? ` · ${entry.assigned_to}` : ''}
                </span>
              </button>
            ))}
          </div>
        )}
        {selected && <p className="hint muted">Tap a day below to schedule {selected.recipe_name}.</p>}
      </section>

      {DAY_NAMES.map((name, day) => {
        const dayEntries = (entries ?? []).filter((e) => e.day === day)
        return (
          <section key={day} className="day">
            <header>
              <span>{name} <span className="muted">{formatDay(dayOfWeek(weekStart, day))}</span></span>
              {selected ? (
                <button type="button" className="btn btn-primary" onClick={() => schedule(day)}>Schedule here</button>
              ) : (
                <button type="button" className="chip" onClick={() => startAdding(day)} disabled={recipes.length === 0 || entries === null}>+ add</button>
              )}
            </header>
            {dayEntries.length > 0 && (
              <ul>
                {dayEntries.map((entry) => (
                  <li key={entry.id} className="row entry">
                    <span className="entry-name">{entry.recipe_name}</span>
                    <span className="entry-controls">
                      <button
                        type="button"
                        className="chip"
                        onClick={() => patch(entry, { assigned_to: nextMember(entry.assigned_to) })}
                        disabled={busyId === entry.id}
                        aria-label={`Assigned to ${entry.assigned_to ?? 'nobody'}, tap to change`}
                      >
                        {entry.assigned_to ?? 'Anyone'}
                      </button>
                      <span className="stepper" aria-label="Servings">
                        <button type="button" onClick={() => patch(entry, { servings: entry.servings - 1 })} disabled={busyId === entry.id || entry.servings <= 1} aria-label="One serving less">−</button>
                        <span>{entry.servings}</span>
                        <button type="button" onClick={() => patch(entry, { servings: entry.servings + 1 })} disabled={busyId === entry.id} aria-label="One serving more">+</button>
                      </span>
                      <button type="button" className="btn btn-ghost" onClick={() => remove(entry)} disabled={busyId === entry.id} aria-label={`Remove ${entry.recipe_name}`}>×</button>
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {adding?.day === day && (
              <form className="add-entry" onSubmit={submitAdd}>
                <select value={adding.recipeId} onChange={(e) => setAdding({ ...adding, recipeId: e.target.value })}>
                  {recipes.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
                <select value={adding.assignedTo} onChange={(e) => setAdding({ ...adding, assignedTo: e.target.value })}>
                  {MEMBERS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
                <input type="number" min="1" value={adding.servings} onChange={(e) => setAdding({ ...adding, servings: e.target.value })} aria-label="Servings" />
                <button className="btn btn-primary" type="submit">
                  {plannedMatch(adding.recipeId) ? 'Move it here' : 'Add'}
                </button>
                <button type="button" className="btn" onClick={() => setAdding(null)}>Cancel</button>
                {plannedMatch(adding.recipeId) && (
                  <p className="hint muted">Already planned this week — this moves it here instead of adding a second one.</p>
                )}
              </form>
            )}
          </section>
        )
      })}
    </div>
  )
}
