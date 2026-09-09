import { useState } from 'react'
import { ArrowUpRight, UserRound } from 'lucide-react'
import Logo from './Logo'

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    onLogin(email || 'operaciones@llachmetrics.com')
  }

  return <main className="login-shell">
    <div className="login-panel"><Logo /><div className="login-form-wrap"><p className="eyebrow">Bienvenido de vuelta</p><h2>Entra a tu espacio</h2><p className="form-intro">Supervisa tus vehiculos y adelanta el mantenimiento de cada neumatico.</p><form onSubmit={handleSubmit}><label htmlFor="email">Correo electronico</label><div className="input-wrap"><UserRound size={18} /><input id="email" type="email" placeholder="nombre@empresa.com" value={email} onChange={(event) => setEmail(event.target.value)} /></div><label htmlFor="password">Contrasena</label><div className="input-wrap"><span className="lock-icon">*</span><input id="password" type="password" placeholder="********" value={password} onChange={(event) => setPassword(event.target.value)} /><button className="input-action" type="button" aria-label="Mostrar contrasena">o</button></div><div className="form-options"><label className="check-label"><input type="checkbox" /> <span>Recordarme</span></label><a href="#forgot">Olvidaste tu contrasena?</a></div><button className="primary-button" type="submit">Acceder <ArrowUpRight size={18} /></button></form><p className="login-help">Necesitas ayuda? <a href="#support">Habla con soporte</a></p></div><div className="login-legal">2024 LlachMetrics <span>-</span> Privacidad <span>-</span> Terminos</div></div>
  </main>
}