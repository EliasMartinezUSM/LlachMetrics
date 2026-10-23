import { useEffect, useState } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import { getCurrentUser, logout } from './data/api'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    // Recupera la sesión si la cookie HttpOnly sigue vigente tras recargar la página.
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false))
  }, [])

  async function handleLogout() {
    // Solo la API puede eliminar la cookie HttpOnly.
    await logout().catch(() => {})
    setUser(null)
  }

  if (checkingSession) return null

  return user ? (
    <Dashboard user={user} onLogout={handleLogout} />
  ) : (
    <Login onLogin={setUser} />
  )
}

export default App
