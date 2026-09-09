import { useState } from 'react'
import { ArrowUpRight, UserRound } from 'lucide-react'
import Logo from './Logo'

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const formData = new URLSearchParams({ username: email, password })
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/auth/login`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData,
        },
      )

      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || 'No se pudo iniciar sesión')
      }

      localStorage.setItem('access_token', data.access_token)
      const userResponse = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/auth/me`,
        { headers: { Authorization: `Bearer ${data.access_token}` } },
      )
      const user = await userResponse.json().catch(() => ({}))
      if (!userResponse.ok) {
        throw new Error(user.detail || 'No se pudo obtener el usuario')
      }

      onLogin(user)
    } catch (requestError) {
      setError(requestError.message || 'No se pudo conectar con la API')
    } finally {
      setLoading(false)
    }
  }

  return <main className="login-shell">
    <div className="login-panel"><Logo /><div className="login-form-wrap"><p className="eyebrow">Bienvenido de vuelta</p><h2>Entra a tu espacio</h2><p className="form-intro">Supervisa tus vehiculos y adelanta el mantenimiento de cada neumatico.</p><form onSubmit={handleSubmit}><label htmlFor="email">Correo electronico</label><div className="input-wrap"><UserRound size={18} /><input id="email" type="email" placeholder="nombre@empresa.com" value={email} onChange={(event) => setEmail(event.target.value)} required /></div><label htmlFor="password">Contrasena</label><div className="input-wrap"><span className="lock-icon">*</span><input id="password" type="password" placeholder="********" value={password} onChange={(event) => setPassword(event.target.value)} required /></div>{error && <p className="login-error" role="alert">{error}</p>}<div className="form-options"><label className="check-label"><input type="checkbox" /> <span>Recordarme</span></label><a href="#forgot">Olvidaste tu contrasena?</a></div><button className="primary-button" type="submit" disabled={loading}>{loading ? 'Conectando...' : 'Acceder'} {!loading && <ArrowUpRight size={18} />}</button></form><p className="login-help">Necesitas ayuda? <a href="#support">Habla con soporte</a></p></div><div className="login-legal">2024 LlachMetrics <span>-</span> Privacidad <span>-</span> Terminos</div></div>
  </main>
}