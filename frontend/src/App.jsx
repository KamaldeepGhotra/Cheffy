import { useState } from 'react'
import InventoryPage from './pages/InventoryPage.jsx'
import RecipeSearchPage from './pages/RecipeSearchPage.jsx'
import GroceryListPage from './pages/GroceryListPage.jsx'

const TABS = {
  inventory: InventoryPage,
  recipes: RecipeSearchPage,
  grocery: GroceryListPage,
}

export default function App() {
  const [tab, setTab] = useState('inventory')
  const ActivePage = TABS[tab]

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '1rem' }}>
      <h1>Cheffy</h1>
      <nav>
        {Object.keys(TABS).map((key) => (
          <button key={key} onClick={() => setTab(key)} disabled={tab === key}>
            {key}
          </button>
        ))}
      </nav>
      <ActivePage />
    </div>
  )
}
