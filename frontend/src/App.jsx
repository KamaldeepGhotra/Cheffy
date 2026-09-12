import { useState } from 'react'
import InventoryPage from './pages/InventoryPage.jsx'
import RecipeSearchPage from './pages/RecipeSearchPage.jsx'
import GroceryListPage from './pages/GroceryListPage.jsx'
import MealPlanPage from './pages/MealPlanPage.jsx'

const TABS = {
  recipes: RecipeSearchPage,
  inventory: InventoryPage,
  grocery: GroceryListPage,
  'meal plan': MealPlanPage,
}
const TAB_KEYS = Object.keys(TABS)

export default function App() {
  const [tab, setTab] = useState('recipes')
  const ActivePage = TABS[tab]

  return (
    <div className="app">
      <header className="bar app-header">
        <h1>Cheffy</h1>
        <nav
          className="seg tabs"
          aria-label="Sections"
          style={{ '--seg-index': TAB_KEYS.indexOf(tab), '--seg-count': TAB_KEYS.length }}
        >
          <span className="seg-indicator" aria-hidden="true" />
          {TAB_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              className="seg-item"
              aria-current={tab === key ? 'page' : undefined}
              onClick={() => setTab(key)}
            >
              {key}
            </button>
          ))}
        </nav>
      </header>
      <main className="page">
        <ActivePage />
      </main>
    </div>
  )
}
