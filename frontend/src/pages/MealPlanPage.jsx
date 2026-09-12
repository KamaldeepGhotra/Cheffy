import { useEffect, useState } from 'react'
import { addMealPlanEntry, deleteMealPlanEntry, generateGroceryList, getMealPlan, listRecipes } from '../api.js'
import { DAY_NAMES, dayOfWeek, formatDay, shiftWeeks, startOfWeek, toISODate } from '../week.js'
import { MEMBERS, getMe } from '../me.js'
import './plan.css'

const HOUSEHOLD_ID = 'roommates'

export default function MealPlanPage() {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()))
  const [entries, setEntries] = useState([])
  const [recipes, setRecipes] = useState([])
  const [adding, setAdding] = useState(null)
  const [grocery, setGrocery] = useState(null)

  const weekKey = toISODate(weekStart)

  async function refresh() {
    setEntries(await getMealPlan(HOUSEHOLD_ID, weekKey))
  }

  useEffect(() => {
    listRecipes(HOUSEHOLD_ID).then(setRecipes)
  }, [])

  useEffect(() => {
    setGrocery(null)
    refresh()
  }, [weekKey])

  function startAdding(day) {
    setAdding({ day, recipeId: recipes[0]?.id ?? '', assignedTo: getMe() ?? MEMBERS[0], servings: 1 })
  }

  async function submitAdd(e) {
    e.preventDefault()
    if (!adding?.recipeId) return
    await addMealPlanEntry({
      householdId: HOUSEHOLD_ID,
      weekStart: weekKey,
      day: adding.day,
      recipeId: Number(adding.recipeId),
      servings: Number(adding.servings),
      assignedTo: adding.assignedTo,
    })
    setAdding(null)
    refresh()
  }

  async function remove(entryId) {
    await deleteMealPlanEntry(entryId)
    refresh()
  }

  async function groceryForWeek() {
    const servings = {}
    for (const entry of entries) {
      servings[entry.recipe_id] = (servings[entry.recipe_id] ?? 0) + entry.servings
    }
    const recipeIds = Object.keys(servings).map(Number)
    if (recipeIds.length === 0) return
    setGrocery(await generateGroceryList({ householdId: HOUSEHOLD_ID, recipeIds, servings }))
  }

  return (
    <div>
      <div className="week-nav">
        <button type="button" className="btn btn-ghost" onClick={() => setWeekStart(shiftWeeks(weekStart, -1))} aria-label="Previous week">‹</button>
        <h2>Week of {formatDay(weekStart)}</h2>
        <button type="button" className="btn btn-ghost" onClick={() => setWeekStart(shiftWeeks(weekStart, 1))} aria-label="Next week">›</button>
      </div>

      {recipes.length === 0 && <p className="empty">No recipes saved yet. Search for one on the Recipes tab first.</p>}

      {DAY_NAMES.map((name, day) => {
        const dayEntries = entries.filter((e) => e.day === day)
        return (
          <section key={day} className="day">
            <header>
              <span>{name} <span className="muted">{formatDay(dayOfWeek(weekStart, day))}</span></span>
              <button type="button" className="chip" onClick={() => startAdding(day)} disabled={recipes.length === 0}>+ add</button>
            </header>
            {dayEntries.length > 0 && (
              <ul>
                {dayEntries.map((entry) => (
                  <li key={entry.id} className="row">
                    <span>
                      {entry.recipe_name}
                      <span className="muted"> · {entry.servings} {entry.servings === 1 ? 'serving' : 'servings'} · {entry.assigned_to}</span>
                    </span>
                    <button type="button" className="btn btn-ghost" onClick={() => remove(entry.id)} aria-label={`Remove ${entry.recipe_name}`}>×</button>
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
                <button className="btn btn-primary" type="submit">Add</button>
                <button type="button" className="btn" onClick={() => setAdding(null)}>Cancel</button>
              </form>
            )}
          </section>
        )
      })}

      <div className="week-actions">
        <button type="button" className="btn btn-primary" onClick={groceryForWeek} disabled={entries.length === 0}>
          Grocery list for this week
        </button>
      </div>

      {grocery && (
        <div>
          <h3>Already have</h3>
          <ul>
            {grocery.have.length === 0 && <li className="row muted">Nothing yet</li>}
            {grocery.have.map((line, i) => (
              <li key={i} className="row"><span>{line.ingredient_name}</span><span className="muted">{line.needed} {line.unit}</span></li>
            ))}
          </ul>
          <h3>Need to buy</h3>
          <ul>
            {grocery.need.length === 0 && <li className="row muted">Nothing, you're covered</li>}
            {grocery.need.map((line, i) => (
              <li key={i} className="row"><span>{line.ingredient_name}</span><span className="muted">{line.needed} {line.unit}</span></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
