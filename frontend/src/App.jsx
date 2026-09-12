import { useState } from 'react'
import InventoryPage from './pages/InventoryPage.jsx'
import RecipeSearchPage from './pages/RecipeSearchPage.jsx'
import GroceryListPage from './pages/GroceryListPage.jsx'
import MealPlanPage from './pages/MealPlanPage.jsx'
import { MEMBERS, getMe, setMe } from './me.js'

const TABS = {
  recipes: RecipeSearchPage,
  inventory: InventoryPage,
  grocery: GroceryListPage,
  'meal plan': MealPlanPage,
}
const TAB_KEYS = Object.keys(TABS)

export default function App() {
  const [tab, setTab] = useState('recipes')
  const [me, setMeState] = useState(getMe)
  const ActivePage = TABS[tab]

  function pick(name) {
    setMe(name)
    setMeState(name)
  }

  if (!me) {
    return (
      <div className="app">
        <header className="bar app-header">
          <h1>Cheffy</h1>
        </header>
        <main className="page">
          <h2>Who are you?</h2>
          <div className="gate">
            {MEMBERS.map((name) => (
              <button key={name} type="button" className="btn" onClick={() => pick(name)}>
                {name}
              </button>
            ))}
          </div>
        </main>
      </div>
    )
  }

  const other = MEMBERS[(MEMBERS.indexOf(me) + 1) % MEMBERS.length]

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
        <button type="button" className="chip me" onClick={() => pick(other)} aria-label={`Switch to ${other}`}>
          {`I'm ${me}`}
        </button>
      </header>
      <main className={`page${tab === 'recipes' ? ' page-wide' : ''}`}>
        <ActivePage />
      </main>
    </div>
  )
}
