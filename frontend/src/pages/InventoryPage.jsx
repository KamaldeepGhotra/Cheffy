import { useEffect, useState } from 'react'
import { addInventoryItem, deleteInventoryItem, listInventory, searchIngredients } from '../api.js'
import { parseInventoryInput } from '../parseInventoryInput.js'
import './inventory.css'

const HOUSEHOLD_ID = 'roommates'
const RECENTS_KEY = 'cheffy.recentAdds'
const MAX_RECENTS = 8

function loadRecents() {
  try {
    return JSON.parse(localStorage.getItem(RECENTS_KEY)) ?? []
  } catch {
    return []
  }
}

function saveRecents(recents) {
  try {
    localStorage.setItem(RECENTS_KEY, JSON.stringify(recents))
  } catch {}
}

function formatQuantity(quantity) {
  return Number.isInteger(quantity) ? quantity : quantity.toFixed(2).replace(/0+$/, '')
}

export default function InventoryPage() {
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [recents, setRecents] = useState(loadRecents)

  const parsed = parseInventoryInput(text)

  async function refresh() {
    setItems(await listInventory(HOUSEHOLD_ID))
  }

  useEffect(() => {
    refresh()
  }, [])

  useEffect(() => {
    if (!parsed || parsed.name.length < 2) {
      setSuggestions([])
      return
    }
    let cancelled = false
    searchIngredients(parsed.name).then((matches) => {
      if (cancelled) return
      setSuggestions(matches.filter((m) => m.score >= 60 && m.name !== parsed.name))
    })
    return () => { cancelled = true }
  }, [parsed?.name])

  async function add({ quantity, unit, name }) {
    await addInventoryItem({ householdId: HOUSEHOLD_ID, ingredientName: name, quantity, unit })
    const next = [{ name, quantity, unit }, ...recents.filter((r) => r.name !== name)].slice(0, MAX_RECENTS)
    setRecents(next)
    saveRecents(next)
    refresh()
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!parsed) return
    await add(parsed)
    setText('')
    setSuggestions([])
  }

  function pickSuggestion(name) {
    const qty = formatQuantity(parsed.quantity)
    setText(parsed.unit === 'each' ? `${qty} ${name}` : `${qty} ${parsed.unit} ${name}`)
    setSuggestions([])
  }

  async function remove(itemId) {
    await deleteInventoryItem(itemId)
    refresh()
  }

  return (
    <div>
      <h2>Inventory</h2>
      <form className="input-row" onSubmit={handleSubmit}>
        <input
          autoFocus
          placeholder='e.g. "2 lb chicken breast" or "eggs"'
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="btn btn-primary" type="submit" disabled={!parsed}>Add</button>
      </form>
      <p className="preview">
        {parsed && (
          <>
            Adding <strong>{parsed.name}</strong> · {formatQuantity(parsed.quantity)} {parsed.unit}
            {!parsed.unitRecognized && <span className="warn"> · unit not recognized, using "each"</span>}
          </>
        )}
      </p>
      {suggestions.length > 0 && (
        <ul className="suggestions">
          {suggestions.map((s) => (
            <li key={s.id} onClick={() => pickSuggestion(s.name)}>
              <span>{s.name}</span>
              <span className="muted">already in list</span>
            </li>
          ))}
        </ul>
      )}
      {recents.length > 0 && (
        <div className="chips">
          {recents.map((r) => (
            <button key={r.name} type="button" className="chip" onClick={() => add(r)}>
              {r.name}<span className="muted">{formatQuantity(r.quantity)} {r.unit}</span>
            </button>
          ))}
        </div>
      )}

      <h3>On hand</h3>
      <ul>
        {items.map((item) => (
          <li key={item.id} className="row">
            <span>{item.ingredient_name} <span className="muted">{formatQuantity(item.quantity)} {item.unit}</span></span>
            <button type="button" className="btn btn-ghost" onClick={() => remove(item.id)} aria-label={`Remove ${item.ingredient_name}`}>×</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
