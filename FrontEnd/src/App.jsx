import { useState } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
  const [user, setUser] = useState(null)

  function handleLogout() {
    localStorage.removeItem('access_token')
    setUser(null)
  }

  return user ? <Dashboard user={user} onLogout={handleLogout} /> : <Login onLogin={setUser} />
}

export default App
