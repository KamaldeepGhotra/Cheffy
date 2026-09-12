const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Every call goes through here. `body` is a plain object and is sent as JSON.
// Non-2xx responses throw an Error carrying the server's `detail` message;
// 204 responses resolve to undefined.
async function request(path, { body, ...options } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    ...(body !== undefined && {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      body: JSON.stringify(body),
    }),
  })
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    const detail = typeof errorBody.detail === 'string' ? errorBody.detail : undefined
    throw new Error(detail ?? (response.statusText || `Request failed with status ${response.status}`))
  }
  if (response.status === 204) return undefined
  return response.json()
}

export async function addInventoryItem({ householdId, ingredientName, quantity, unit }) {
  return request('/inventory', {
    method: 'POST',
    body: { household_id: householdId, ingredient_name: ingredientName, quantity, unit },
  })
}

export async function listInventory(householdId) {
  const params = new URLSearchParams({ household_id: householdId })
  return request(`/inventory?${params}`)
}

export async function searchIngredients(query) {
  const params = new URLSearchParams({ q: query })
  return request(`/ingredients/search?${params}`)
}

export async function generateGroceryList({ householdId, recipeIds, servings }) {
  return request('/grocery-list', {
    method: 'POST',
    body: { household_id: householdId, recipe_ids: recipeIds, servings },
  })
}

export async function deleteInventoryItem(itemId) {
  return request(`/inventory/${itemId}`, { method: 'DELETE' })
}

export async function listRecipes(householdId) {
  const params = new URLSearchParams({ household_id: householdId })
  return request(`/recipes?${params}`)
}

export async function getMealPlan(householdId, weekStart) {
  const params = new URLSearchParams({ household_id: householdId, week_start: weekStart })
  return request(`/meal-plan?${params}`)
}

export async function addMealPlanEntry({ householdId, weekStart, day, recipeId, servings, assignedTo }) {
  return request('/meal-plan', {
    method: 'POST',
    body: {
      household_id: householdId,
      week_start: weekStart,
      day,
      recipe_id: recipeId,
      servings,
      assigned_to: assignedTo,
    },
  })
}

export async function deleteMealPlanEntry(entryId) {
  return request(`/meal-plan/${entryId}`, { method: 'DELETE' })
}

// Fields left out are left alone; pass null to clear day or assigned_to.
export async function updateMealPlanEntry(entryId, fields) {
  return request(`/meal-plan/${entryId}`, { method: 'PATCH', body: fields })
}

// Returns several candidates scored against the household's inventory. Saves nothing —
// the caller passes the one the user picks to saveRecipe.
export async function searchRecipeCandidates({ householdId, query, count = 3 }) {
  return request('/recipes/search', {
    method: 'POST',
    body: { query, household_id: householdId, count },
  })
}

export async function saveRecipe({ householdId, candidate }) {
  return request('/recipes', { method: 'POST', body: { candidate, household_id: householdId } })
}

export async function suggestRecipes({ householdId, count = 3 }) {
  return request('/recipes/suggest', { method: 'POST', body: { household_id: householdId, count } })
}
