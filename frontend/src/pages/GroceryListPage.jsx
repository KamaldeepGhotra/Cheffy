import { useState } from 'react'
import { generateGroceryList } from '../api.js'

const HOUSEHOLD_ID = 'roommates'

export default function GroceryListPage() {
  const [recipeIdsInput, setRecipeIdsInput] = useState('')
  const [result, setResult] = useState(null)

  async function handleGenerate() {
    const recipeIds = recipeIdsInput
      .split(',')
      .map((s) => Number(s.trim()))
      .filter((n) => !Number.isNaN(n))
    if (recipeIds.length === 0) return

    const servings = Object.fromEntries(recipeIds.map((id) => [id, 1]))
    setResult(await generateGroceryList({ householdId: HOUSEHOLD_ID, recipeIds, servings }))
  }

  return (
    <div>
      <h2>Grocery List</h2>
      <div className="input-row">
        <input
          placeholder="Recipe IDs, comma separated"
          value={recipeIdsInput}
          onChange={(e) => setRecipeIdsInput(e.target.value)}
        />
        <button type="button" className="btn btn-primary" onClick={handleGenerate}>Generate</button>
      </div>

      {result && (
        <div>
          <h3>Already have</h3>
          <ul>
            {result.have.map((line, i) => (
              <li key={i} className="row">{line.ingredient_name}: {line.needed} {line.unit}</li>
            ))}
          </ul>
          <h3>Need to buy</h3>
          <ul>
            {result.need.map((line, i) => (
              <li key={i} className="row">{line.ingredient_name}: {line.needed} {line.unit}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
