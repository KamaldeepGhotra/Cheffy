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

export default function App() {
  const [tab, setTab] = useState('recipes')
  const ActivePage = TABS[tab]

  return (
    <div className="app">
      <header className="app-header">
        <h1>Cheffy</h1>
      </header>
      <nav className="tabs">
        {Object.keys(TABS).map((key) => (
          <button
            key={key}
            type="button"
            className="btn tab"
            aria-current={tab === key ? 'page' : undefined}
            onClick={() => setTab(key)}
          >
            {key}
          </button>
        ))}
      </nav>
      <ActivePage />
    </div>
  )
}
