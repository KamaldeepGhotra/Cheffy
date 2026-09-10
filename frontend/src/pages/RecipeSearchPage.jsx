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
      <input placeholder="What do you want to eat?" value={query} onChange={(e) => setQuery(e.target.value)} />
      <button onClick={handleSearch}>Search</button>

      {recipe && (
        <div>
          <h3>{recipe.name}</h3>
          <p>{recipe.instructions}</p>
          <p>
            Calories: {recipe.calories} | Protein: {recipe.protein}g | Fat: {recipe.fat}g | Carbs: {recipe.carbs}g
          </p>
          <ul>
            {recipe.ingredients.map((ing) => (
              <li key={ing.ingredient_id}>
                {ing.ingredient_name}: {ing.quantity} {ing.unit}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
