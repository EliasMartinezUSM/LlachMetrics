import { useState } from 'react'
import {
  Activity, ArrowUpRight, BarChart3, Bell, ChevronDown, CircleHelp,
  ClipboardList, Gauge, LayoutDashboard, LogOut, Menu, Search, Settings2,
  Sparkles, Thermometer, TrendingUp, UserRound, X,
} from 'lucide-react'
import './App.css'

const navigation = [
  { id: 'inicio', label: 'Inicio', icon: LayoutDashboard },
  { id: 'mediciones', label: 'Vehiculos', icon: ClipboardList },
  { id: 'predicciones', label: 'Predicciones', icon: TrendingUp },
]

const readings = [
  { label: 'Presion media', value: '7,8', unit: 'bar', detail: '+1,2%', icon: Gauge, tone: 'orange' },
  { label: 'Desgaste de banda', value: '68,4', unit: '%', detail: '-0,8%', icon: Activity, tone: 'blue' },
  { label: 'Temperatura rueda', value: '42,7', unit: 'C', detail: '+0,3%', icon: Thermometer, tone: 'purple' },
  { label: 'Flota operativa', value: '94,2', unit: '%', detail: '+4,6%', icon: ClipboardList, tone: 'green' },
]

function Logo() {
  return <div className="brand"><span className="brand-mark"><BarChart3 size={18} /></span><span>Llach<strong>Metrics</strong></span></div>
}

function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    onLogin(email || 'operaciones@llachmetrics.com')
  }

  return <main className="login-shell">
    <div className="login-visual">
      <div className="visual-topline"><span className="status-dot" /> CONTROL INTELIGENTE DE FLOTAS</div>
      <div className="visual-copy"><p className="eyebrow">Mas kilometros. Mas control.</p><h1>Cada ruta empieza<br /><em>en tus neumaticos.</em></h1><p>Convierte cada dato de tu flota en decisiones seguras, eficientes y a tiempo.</p></div>
      <div className="visual-chart"><div className="chart-label">Salud media de la flota <strong>+18,6%</strong></div><svg viewBox="0 0 500 145" preserveAspectRatio="none"><path className="chart-grid" d="M0 30H500 M0 75H500 M0 120H500" /><path className="chart-fill" d="M0 125 C50 122 60 98 102 105 S145 120 180 81 S225 75 250 84 S290 92 315 58 S350 74 375 40 S420 67 450 20 S480 38 500 12 L500 145 L0 145Z" /><path className="chart-line" d="M0 125 C50 122 60 98 102 105 S145 120 180 81 S225 75 250 84 S290 92 315 58 S350 74 375 40 S420 67 450 20 S480 38 500 12" /></svg></div>
      <div className="visual-footer"><span>Datos en tiempo real</span><span>v2.4.0</span></div>
    </div>
    <div className="login-panel"><Logo /><div className="login-form-wrap"><p className="eyebrow">Bienvenido de vuelta</p><h2>Entra a tu espacio</h2><p className="form-intro">Supervisa tus vehiculos y adelanta el mantenimiento de cada neumatico.</p><form onSubmit={handleSubmit}><label htmlFor="email">Correo electronico</label><div className="input-wrap"><UserRound size={18} /><input id="email" type="email" placeholder="nombre@empresa.com" value={email} onChange={(event) => setEmail(event.target.value)} /></div><label htmlFor="password">Contrasena</label><div className="input-wrap"><span className="lock-icon">*</span><input id="password" type="password" placeholder="********" value={password} onChange={(event) => setPassword(event.target.value)} /><button className="input-action" type="button" aria-label="Mostrar contrasena">o</button></div><div className="form-options"><label className="check-label"><input type="checkbox" /> <span>Recordarme</span></label><a href="#forgot">Olvidaste tu contrasena?</a></div><button className="primary-button" type="submit">Acceder <ArrowUpRight size={18} /></button></form><p className="login-help">Necesitas ayuda? <a href="#support">Habla con soporte</a></p></div><div className="login-legal">2024 LlachMetrics <span>-</span> Privacidad <span>-</span> Terminos</div></div>
  </main>
}

function MetricCard({ reading }) {
  const Icon = reading.icon
  return <article className="metric-card"><div className={`metric-icon ${reading.tone}`}><Icon size={19} /></div><div className="metric-meta"><span>{reading.label}</span><small>Ultimas 24 h</small></div><div className="metric-value">{reading.value}<small>{reading.unit}</small></div><div className="metric-change"><ArrowUpRight size={14} /> {reading.detail}</div></article>
}

function HomeView({ onNavigate }) {
  return <><section className="welcome-row"><div><p className="eyebrow">Lunes, 24 de junio de 2024</p><h1>Buenos dias, <em>Elias.</em></h1><p className="subtitle">Este es el estado de tu flota y la salud de sus neumaticos.</p></div><button className="outline-button" onClick={() => onNavigate('mediciones')}><ClipboardList size={17} /> Ver vehiculos</button></section><section className="metrics-grid">{readings.map((reading) => <MetricCard key={reading.label} reading={reading} />)}</section><section className="content-grid"><article className="panel chart-panel"><div className="panel-heading"><div><p className="eyebrow">Actividad de la flota</p><h2>Disponibilidad semanal</h2></div><button className="select-button">Esta semana <ChevronDown size={15} /></button></div><div className="big-chart"><div className="y-labels"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div><div className="chart-area"><div className="grid-lines"><i /><i /><i /><i /><i /></div><svg viewBox="0 0 680 220" preserveAspectRatio="none"><path className="area-fill" d="M0 180 C40 170 60 125 105 140 S150 190 195 120 S250 95 285 120 S340 180 380 115 S435 78 470 105 S500 160 530 82 S580 55 610 80 S650 48 680 25 L680 220 L0 220Z" /><path className="area-line" d="M0 180 C40 170 60 125 105 140 S150 190 195 120 S250 95 285 120 S340 180 380 115 S435 78 470 105 S500 160 530 82 S580 55 610 80 S650 48 680 25" /></svg><div className="x-labels"><span>Lun</span><span>Mar</span><span>Mie</span><span>Jue</span><span>Vie</span><span>Sab</span><span>Dom</span></div></div></div></article><article className="panel status-panel"><div className="panel-heading"><div><p className="eyebrow">Estado general</p><h2>Salud de la flota</h2></div><span className="live-tag"><i /> En vivo</span></div><div className="health-score"><div className="score-ring"><strong>87</strong><span>/ 100</span></div><div><h3>Flota en buen estado</h3><p>La mayoria de los vehiculos esta dentro de los parametros.</p></div></div><div className="status-list"><div><span><i className="dot green-dot" />Presion de neumaticos</span><b>Optima</b></div><div><span><i className="dot yellow-dot" />Revisiones pendientes</span><b>En 2 dias</b></div><div><span><i className="dot blue-dot" />Proxima inspeccion</span><b>Manana, 08:00</b></div></div></article></section></>
}

function MeasurementsView() {
  const ranges = { 'Presion media': '7,0 - 8,5 bar', 'Desgaste de banda': '0 - 80 %', 'Temperatura rueda': '20 - 70 C', 'Flota operativa': '90 - 100 %' }
  return <><section className="page-heading"><div><p className="eyebrow">Control de vehiculos</p><h1>Vehiculos</h1><p className="subtitle">Supervisa cada unidad y el estado de sus neumaticos.</p></div><button className="primary-button compact"><Search size={17} /> Nueva consulta</button></section><section className="panel table-panel"><div className="table-toolbar"><div className="tabs"><button className="active">Toda la flota</button><button>Alertas <span>3</span></button></div><button className="filter-button"><Settings2 size={16} /> Filtrar</button></div><div className="table-wrap"><table><thead><tr><th>Indicador</th><th>Valor actual</th><th>Rango seguro</th><th>Tendencia</th><th>Estado</th><th /></tr></thead><tbody>{readings.map((reading) => { const Icon = reading.icon; return <tr key={reading.label}><td><span className={`table-icon ${reading.tone}`}><Icon size={16} /></span><strong>{reading.label}</strong></td><td><b>{reading.value}</b> {reading.unit}</td><td>{ranges[reading.label]}</td><td><span className="trend-up"><TrendingUp size={15} /> {reading.detail}</span></td><td><span className="status-pill"><i /> Dentro del rango</span></td><td><button className="more-button">...</button></td></tr> })}</tbody></table></div></section></>
}

function PredictionsView() {
  return <><section className="page-heading"><div><p className="eyebrow">Mantenimiento predictivo</p><h1>Predicciones</h1><p className="subtitle">Anticipate averias antes de que detengan una ruta.</p></div><button className="outline-button"><CircleHelp size={17} /> Como funciona</button></section><section className="prediction-layout"><article className="prediction-hero"><div className="prediction-icon"><Sparkles size={22} /></div><p className="eyebrow">Prediccion destacada</p><h2>Rotacion recomendada<br /><em>en 2 dias</em></h2><p>El eje delantero del vehiculo LM-042 muestra un desgaste desigual. Programa una rotacion antes de su proxima ruta larga.</p><div className="prediction-confidence"><span>Confianza del modelo</span><b>94%</b><div><i /></div></div></article><div className="prediction-side"><article className="panel forecast-card"><div className="panel-heading"><div><p className="eyebrow">Proximos 7 dias</p><h2>Riesgo de averia</h2></div><span className="forecast-temp">12 <small>alertas</small></span></div><div className="weather-row"><div><span>Hoy</span><strong>OK</strong><b>96%</b></div><div><span>Mar</span><strong>OK</strong><b>94%</b></div><div><span>Mie</span><strong>!</strong><b>82%</b></div><div><span>Jue</span><strong>OK</strong><b>91%</b></div><div><span>Vie</span><strong>OK</strong><b>95%</b></div></div></article><article className="panel alert-card"><span className="alert-icon"><Bell size={18} /></span><div><p className="eyebrow">Aviso inteligente</p><h3>Desgaste en aumento</h3><p>El vehiculo LM-042 podria superar el limite de desgaste en 1.200 km. Revisa el eje delantero.</p></div><ArrowUpRight size={19} /></article></div></section></>
}

function Dashboard({ user, onLogout }) {
  const [activeView, setActiveView] = useState('inicio')
  const [mobileNav, setMobileNav] = useState(false)
  const views = { inicio: <HomeView onNavigate={setActiveView} />, mediciones: <MeasurementsView />, predicciones: <PredictionsView /> }
  return <div className="app-shell"><aside className={mobileNav ? 'sidebar open' : 'sidebar'}><Logo /><nav>{navigation.map(({ id, label, icon: Icon }) => <button key={id} className={activeView === id ? 'nav-item active' : 'nav-item'} onClick={() => { setActiveView(id); setMobileNav(false) }}><Icon size={18} /><span>{label}</span>{id === 'mediciones' && <i className="nav-badge">3</i>}</button>)}</nav><div className="sidebar-bottom"><button className="nav-item"><Settings2 size={18} /><span>Configuracion</span></button><div className="upgrade-card"><Sparkles size={17} /><strong>Prueba Llach Pro</strong><span>Alertas avanzadas para toda tu flota</span><button>Ver planes <ArrowUpRight size={13} /></button></div><button className="user-card"><span className="avatar">E</span><span><strong>{user.split('@')[0]}</strong><small>Administrador</small></span><ChevronDown size={15} /></button></div><button className="close-nav" onClick={() => setMobileNav(false)} aria-label="Cerrar menu"><X size={18} /></button></aside><div className="main-area"><header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)} aria-label="Abrir menu"><Menu size={20} /></button><div className="breadcrumb">Workspace <span>/</span> <strong>{navigation.find((item) => item.id === activeView)?.label}</strong></div><div className="top-actions"><button className="icon-button"><Search size={18} /></button><button className="icon-button notification"><Bell size={18} /><i /></button><div className="top-avatar">E</div><button className="logout-button" onClick={onLogout} title="Cerrar sesion"><LogOut size={17} /></button></div></header><main className="content">{views[activeView]}</main><footer className="app-footer"><span>LlachMetrics <b>v2.4.0</b></span><span>Ultima sincronizacion: hace 2 min</span></footer></div></div>
}

function App() {
  const [user, setUser] = useState(null)
  return user ? <Dashboard user={user} onLogout={() => setUser(null)} /> : <Login onLogin={setUser} />
}

export default App
