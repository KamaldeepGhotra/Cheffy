import { useState } from 'react'
import { searchRecipe } from '../api.js'

export default function RecipeSearchPage() {
  const [query, setQuery] = useState('')
  const [recipe, setRecipe] = useState(null)

  async function handleSearch() {
    if (!query) return
    setRecipe(await searchRecipe(query))
  }

  return (
    <div>
      <h2>Recipe Search</h2>
      <div className="input-row">
        <input placeholder="What do you want to eat?" value={query} onChange={(e) => setQuery(e.target.value)} />
        <button type="button" className="btn btn-primary" onClick={handleSearch}>Search</button>
      </div>

      {recipe && (
        <div className="card">
          <h3>{recipe.name}</h3>
          <p>{recipe.instructions}</p>
          <p className="muted">
            Calories: {recipe.calories} | Protein: {recipe.protein}g | Fat: {recipe.fat}g | Carbs: {recipe.carbs}g
          </p>
          <ul>
            {recipe.ingredients.map((ing) => (
              <li key={ing.ingredient_id} className="row">
                {ing.ingredient_name}: {ing.quantity} {ing.unit}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
