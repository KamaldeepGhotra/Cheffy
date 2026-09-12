import { useEffect, useState } from 'react'
import { addInventoryItem, deleteInventoryItem, listInventory, searchIngredients } from '../api.js'
import { parseInventoryInput, parseInventoryItems } from '../parseInventoryInput.js'
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
  return Number.isInteger(quantity) ? quantity : quantity.toFixed(2).replace(/\.?0+$/, '')
}

function formatItem({ quantity, unit, name }) {
  const qty = formatQuantity(quantity)
  return unit === 'each' ? `${qty} ${name}` : `${qty} ${unit} ${name}`
}

export default function InventoryPage() {
  const [items, setItems] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [text, setText] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [recents, setRecents] = useState(loadRecents)
  const [adding, setAdding] = useState(false)
  const [actionError, setActionError] = useState(null)

  const parsed = parseInventoryItems(text)
  const canAdd = parsed.items.length > 0 && parsed.invalid.length === 0 && !adding

  // Suggestions follow the segment being typed, which is the last one.
  const segments = text.split(/[,\n]/)
  const currentName = parseInventoryInput(segments[segments.length - 1])?.name ?? ''

  async function refresh() {
    setLoadError(null)
    try {
      setItems(await listInventory(HOUSEHOLD_ID))
    } catch (err) {
      setLoadError(err.message)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  useEffect(() => {
    if (currentName.length < 2) {
      setSuggestions([])
      return
    }
    let cancelled = false
    searchIngredients(currentName)
      .then((matches) => {
        if (cancelled) return
        setSuggestions(matches.filter((m) => m.score >= 60 && m.name !== currentName))
      })
      .catch(() => {
        if (!cancelled) setSuggestions([])
      })
    return () => { cancelled = true }
  }, [currentName])

  async function add({ quantity, unit, name }) {
    await addInventoryItem({ householdId: HOUSEHOLD_ID, ingredientName: name, quantity, unit })
    setRecents((prev) => {
      const next = [{ name, quantity, unit }, ...prev.filter((r) => r.name !== name)].slice(0, MAX_RECENTS)
      saveRecents(next)
      return next
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canAdd) return
    setAdding(true)
    setActionError(null)
    const queue = [...parsed.items]
    try {
      while (queue.length > 0) {
        await add(queue[0])
        queue.shift()
        await refresh()
      }
      setText('')
      setSuggestions([])
    } catch (err) {
      // Keep only what did not make it in, so a retry cannot add the first items twice.
      setText(queue.map((item) => item.raw).join(', '))
      setActionError(err.message)
    } finally {
      setAdding(false)
    }
  }

  async function quickAdd(recent) {
    setAdding(true)
    setActionError(null)
    try {
      await add(recent)
      await refresh()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setAdding(false)
    }
  }

  function pickSuggestion(name) {
    const last = parseInventoryInput(segments[segments.length - 1])
    const kept = segments.slice(0, -1).map((s) => s.trim()).filter(Boolean)
    setText([...kept, formatItem({ ...last, name })].join(', '))
    setSuggestions([])
  }

  async function remove(itemId) {
    setActionError(null)
    try {
      await deleteInventoryItem(itemId)
      await refresh()
    } catch (err) {
      setActionError(err.message)
    }
  }

  return (
    <div>
      <h2>Inventory</h2>
      <form className="input-row" onSubmit={handleSubmit}>
        <input
          autoFocus
          placeholder="2 lb chicken breast, 12 eggs, cilantro"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={adding}
        />
        <button className="btn btn-primary" type="submit" disabled={!canAdd}>
          {adding ? 'Adding…' : 'Add'}
        </button>
      </form>
      <div className="preview">
        {parsed.items.map((item, i) => (
          <p key={i}>
            Adding <strong>{item.name}</strong> · {formatQuantity(item.quantity)} {item.unit}
            {!item.unitRecognized && <span className="warn"> · unit not recognized, using "each"</span>}
          </p>
        ))}
        {parsed.invalid.map((raw, i) => (
          <p key={`invalid-${i}`} className="warn">Can't read "{raw}"</p>
        ))}
      </div>
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
      {actionError && (
        <div className="banner-error">
          <span>{actionError}</span>
        </div>
      )}
      {recents.length > 0 && (
        <div className="chips">
          {recents.map((r) => (
            <button key={r.name} type="button" className="chip" onClick={() => quickAdd(r)} disabled={adding}>
              + {r.name}<span className="muted">{formatQuantity(r.quantity)} {r.unit}</span>
            </button>
          ))}
        </div>
      )}

      <h3>On hand{items && ` (${items.length})`}</h3>
      {loadError && (
        <div className="banner-error">
          <span>{loadError}</span>
          <button type="button" className="btn" onClick={refresh}>Retry</button>
        </div>
      )}
      {items === null && !loadError && (
        <div className="loading" aria-label="Loading">
          <span className="skeleton" />
          <span className="skeleton" />
          <span className="skeleton" />
        </div>
      )}
      {items && items.length === 0 && <p className="empty">Nothing on hand yet. Type what you bought above.</p>}
      {items && items.length > 0 && (
        <ul>
          {items.map((item) => (
            <li key={item.id} className="row">
              <span>{item.ingredient_name} <span className="muted">{formatQuantity(item.quantity)} {item.unit}</span></span>
              <button type="button" className="btn btn-ghost" onClick={() => remove(item.id)} aria-label={`Remove ${item.ingredient_name}`}>×</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
