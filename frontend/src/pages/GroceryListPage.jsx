import { useEffect, useState } from 'react'
import { addInventoryItem, getWeekGroceryList } from '../api.js'
import { startOfWeek, toISODate } from '../week.js'
import './grocery.css'

const HOUSEHOLD_ID = 'roommates'

function formatQuantity(quantity) {
  return Number.isInteger(quantity) ? quantity : Number(quantity.toFixed(2))
}

function lineKey(line) {
  return `${line.ingredient_id}-${line.unit}`
}

function GroceryRow({ line, checked, busy, onBuy }) {
  return (
    <li className="row grocery-row">
      <button
        type="button"
        className="grocery-check"
        onClick={onBuy}
        disabled={busy || checked}
        aria-label={`Mark ${line.ingredient_name} as bought`}
      >
        <span className={checked ? 'tick tick-on' : 'tick'} aria-hidden="true">{checked ? '✓' : ''}</span>
        <span className="grocery-text">
          <span className="grocery-name">{line.ingredient_name}</span>
          {line.recipes.length > 0 && <span className="muted grocery-for">for {line.recipes.join(', ')}</span>}
        </span>
      </button>
      <span className="muted grocery-qty">{formatQuantity(line.needed)} {line.unit}</span>
    </li>
  )
}

export default function GroceryListPage() {
  const [list, setList] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [busyKey, setBusyKey] = useState(null)
  const [buyingAll, setBuyingAll] = useState(false)
  const [showHave, setShowHave] = useState(false)

  const weekStart = toISODate(startOfWeek(new Date()))

  async function load() {
    setLoadError(null)
    try {
      setList(await getWeekGroceryList({ householdId: HOUSEHOLD_ID, weekStart }))
    } catch (err) {
      setLoadError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // Move the line across immediately; a failure puts it back, so a slow network still feels responsive.
  async function buy(line) {
    setActionError(null)
    setBusyKey(lineKey(line))
    const optimistic = {
      need: list.need.filter((l) => lineKey(l) !== lineKey(line)),
      have: [...list.have, line],
    }
    setList(optimistic)
    try {
      await addInventoryItem({
        householdId: HOUSEHOLD_ID,
        ingredientName: line.ingredient_name,
        quantity: line.needed,
        unit: line.unit,
      })
    } catch (err) {
      setList((prev) => ({ need: [line, ...prev.need], have: prev.have.filter((l) => lineKey(l) !== lineKey(line)) }))
      setActionError({ message: err.message, retry: () => buy(line) })
    } finally {
      setBusyKey(null)
    }
  }

  async function buyEverything() {
    setBuyingAll(true)
    // Sequential on purpose: two rows for the same ingredient must merge in order, not race.
    for (const line of [...list.need]) {
      await buy(line)
    }
    setBuyingAll(false)
  }

  return (
    <div>
      <h2>Grocery List</h2>

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

      {list === null && !loadError && (
        <ul aria-label="Loading">
          <li className="row"><span className="skeleton" /></li>
          <li className="row"><span className="skeleton" /></li>
          <li className="row"><span className="skeleton" /></li>
        </ul>
      )}

      {list && list.need.length === 0 && list.have.length === 0 && (
        <p className="empty">Nothing to buy — plan some meals on the Recipes tab.</p>
      )}

      {list && list.need.length > 0 && (
        <>
          <div className="section-head">
            <h3>Need to buy ({list.need.length})</h3>
            <button
              type="button"
              className="btn btn-primary"
              onClick={buyEverything}
              disabled={buyingAll || busyKey !== null}
            >
              {buyingAll ? 'Adding…' : 'Bought everything'}
            </button>
          </div>
          <ul>
            {list.need.map((line) => (
              <GroceryRow
                key={lineKey(line)}
                line={line}
                checked={false}
                busy={busyKey === lineKey(line)}
                onBuy={() => buy(line)}
              />
            ))}
          </ul>
        </>
      )}

      {list && list.need.length === 0 && list.have.length > 0 && (
        <p className="empty">You have everything for this week's meals.</p>
      )}

      {list && list.have.length > 0 && (
        <>
          <div className="section-head">
            <h3>Already have ({list.have.length})</h3>
            <button type="button" className="btn btn-ghost" onClick={() => setShowHave(!showHave)}>
              {showHave ? 'Hide' : 'Show'}
            </button>
          </div>
          {showHave && (
            <ul>
              {list.have.map((line) => (
                <GroceryRow key={lineKey(line)} line={line} checked busy={false} onBuy={() => {}} />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
