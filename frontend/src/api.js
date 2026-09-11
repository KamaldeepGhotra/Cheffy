const BASE_URL = 'http://localhost:8000'

export async function addInventoryItem({ householdId, ingredientName, quantity, unit }) {
  const response = await fetch(`${BASE_URL}/inventory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      household_id: householdId,
      ingredient_name: ingredientName,
      quantity,
      unit,
    }),
  })
  return response.json()
}

export async function listInventory(householdId) {
  const response = await fetch(`${BASE_URL}/inventory?household_id=${encodeURIComponent(householdId)}`)
  return response.json()
}

export async function searchIngredients(query) {
  const response = await fetch(`${BASE_URL}/ingredients/search?q=${encodeURIComponent(query)}`)
  return response.json()
}

export async function searchRecipe(query) {
  const response = await fetch(`${BASE_URL}/recipes/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  return response.json()
}

export async function generateGroceryList({ householdId, recipeIds, servings }) {
  const response = await fetch(`${BASE_URL}/grocery-list`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ household_id: householdId, recipe_ids: recipeIds, servings }),
  })
  return response.json()
}

export async function deleteInventoryItem(itemId) {
  await fetch(`${BASE_URL}/inventory/${itemId}`, { method: 'DELETE' })
}

export async function listRecipes(householdId) {
  const response = await fetch(`${BASE_URL}/recipes?household_id=${encodeURIComponent(householdId)}`)
  return response.json()
}

export async function getMealPlan(householdId, weekStart) {
  const params = new URLSearchParams({ household_id: householdId, week_start: weekStart })
  const response = await fetch(`${BASE_URL}/meal-plan?${params}`)
  return response.json()
}

export async function addMealPlanEntry({ householdId, weekStart, day, recipeId, servings, assignedTo }) {
  const response = await fetch(`${BASE_URL}/meal-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      household_id: householdId,
      week_start: weekStart,
      day,
      recipe_id: recipeId,
      servings,
      assigned_to: assignedTo,
    }),
  })
  return response.json()
}

export async function deleteMealPlanEntry(entryId) {
  await fetch(`${BASE_URL}/meal-plan/${entryId}`, { method: 'DELETE' })
}
