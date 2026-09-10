import { useEffect, useState } from 'react'
import { addInventoryItem, listInventory, searchIngredients } from '../api.js'

const HOUSEHOLD_ID = 'roommates'

export default function InventoryPage() {
  const [items, setItems] = useState([])
  const [name, setName] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [quantity, setQuantity] = useState('')
  const [unit, setUnit] = useState('')

  async function refresh() {
    setItems(await listInventory(HOUSEHOLD_ID))
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleNameChange(value) {
    setName(value)
    if (value.length >= 2) {
      setSuggestions(await searchIngredients(value))
    } else {
      setSuggestions([])
    }
  }

  async function handleAdd() {
    if (!name || !quantity || !unit) return
    await addInventoryItem({ householdId: HOUSEHOLD_ID, ingredientName: name, quantity: Number(quantity), unit })
    setName('')
    setQuantity('')
    setUnit('')
    setSuggestions([])
    refresh()
  }

  return (
    <div>
      <h2>Inventory</h2>
      <input
        placeholder="Ingredient name"
        value={name}
        onChange={(e) => handleNameChange(e.target.value)}
      />
      <ul>
        {suggestions.map((s) => (
          <li key={s.id} onClick={() => { setName(s.name); setSuggestions([]) }}>
            {s.name} ({s.score.toFixed(0)})
          </li>
        ))}
      </ul>
      <input placeholder="Quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
      <input placeholder="Unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
      <button onClick={handleAdd}>Add</button>

      <ul>
        {items.map((item) => (
          <li key={item.id}>
            {item.ingredient_name}: {item.quantity} {item.unit}
          </li>
        ))}
      </ul>
    </div>
  )
}
