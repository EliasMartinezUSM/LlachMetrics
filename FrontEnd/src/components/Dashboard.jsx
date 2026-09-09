import { useState } from 'react'
import { Bell, ChevronDown, LogOut, Menu, Search, Settings2, X } from 'lucide-react'
import Logo from './Logo'
import HomeView from '../views/HomeView'
import MeasurementsView from '../views/MeasurementsView'
import PredictionsView from '../views/PredictionsView'
import { navigation } from '../data/dashboardData'

export default function Dashboard({ user, onLogout }) {
  const [activeView, setActiveView] = useState('inicio')
  const [mobileNav, setMobileNav] = useState(false)
  const views = { inicio: <HomeView onNavigate={setActiveView} />, mediciones: <MeasurementsView />, predicciones: <PredictionsView /> }
  const displayName = user.full_name || user.email.split('@')[0]
  const initials = displayName.charAt(0).toUpperCase()
  return <div className="app-shell"><aside className={mobileNav ? 'sidebar open' : 'sidebar'}><Logo /><nav>{navigation.map(({ id, label, icon: Icon }) => <button key={id} className={activeView === id ? 'nav-item active' : 'nav-item'} onClick={() => { setActiveView(id); setMobileNav(false) }}><Icon size={18} /><span>{label}</span>{id === 'mediciones' && <i className="nav-badge">3</i>}</button>)}</nav><div className="sidebar-bottom"><button className="nav-item"><Settings2 size={18} /><span>Configuracion</span></button><button className="user-card"><span className="avatar">{initials}</span><span><strong>{displayName}</strong><small>{user.email}</small></span><ChevronDown size={15} /></button></div><button className="close-nav" onClick={() => setMobileNav(false)} aria-label="Cerrar menu"><X size={18} /></button></aside><div className="main-area"><header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)} aria-label="Abrir menu"><Menu size={20} /></button><div className="breadcrumb">Workspace <span>/</span> <strong>{navigation.find((item) => item.id === activeView)?.label}</strong></div><div className="top-actions"><button className="icon-button"><Search size={18} /></button><button className="icon-button notification"><Bell size={18} /><i /></button><div className="top-avatar">{initials}</div><button className="logout-button" onClick={onLogout} title="Cerrar sesion"><LogOut size={17} /></button></div></header><main className="content">{views[activeView]}</main><footer className="app-footer"><span>LlachMetrics <b>v2.4.0</b></span><span>Ultima sincronizacion: hace 2 min</span></footer></div></div>
}