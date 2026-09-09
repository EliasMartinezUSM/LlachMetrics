import { AlertTriangle, ClipboardList, Gauge, ShieldCheck, Truck, Wrench } from 'lucide-react'
import { vehicles } from '../data/dashboardData'

const summary = [
  { label: 'Vehiculos activos', value: '24', detail: '+3 esta semana', icon: Truck, tone: 'blue' },
  { label: 'Alertas abiertas', value: '3', detail: '1 critica', icon: AlertTriangle, tone: 'orange' },
  { label: 'Flota operativa', value: '94%', detail: '+4,6% vs. mes anterior', icon: ShieldCheck, tone: 'green' },
  { label: 'Mantenimientos', value: '5', detail: 'Proximos 7 dias', icon: Wrench, tone: 'purple' },
]

export default function HomeView({ onNavigate }) {
  return <>
    <section className="welcome-row"><div><p className="eyebrow">Lunes, 24 de junio de 2024</p><h1>Panel <em>General.</em></h1><p className="subtitle">Resumen operativo y estado actual de tu flota.</p></div><button className="outline-button" onClick={() => onNavigate('mediciones')}><ClipboardList size={17} /> Ver métricas</button></section>
    <section className="metrics-grid summary-grid">{summary.map(({ label, value, detail, icon: Icon, tone }) => <article className="metric-card summary-card" key={label}><div className={`metric-icon ${tone}`}><Icon size={19} /></div><div className="metric-meta"><span>{label}</span><small>{detail}</small></div><div className="metric-value">{value}</div></article>)}</section>
    <section className="panel vehicle-summary"><div className="panel-heading"><div><p className="eyebrow">Resumen por vehiculo</p><h2>Estado de la flota</h2></div></div><div className="table-wrap"><table><thead><tr><th>Vehiculo</th><th>Ruta actual</th><th><Gauge size={13} /> Presion</th><th>Desgaste</th><th>Temperatura</th><th>Estado</th></tr></thead><tbody>{vehicles.map((vehicle) => <tr key={vehicle.id}><td><strong>{vehicle.id}</strong></td><td>{vehicle.route}</td><td>{vehicle.pressure}</td><td>{vehicle.wear}</td><td>{vehicle.temperature}</td><td><span className={`status-pill vehicle-status ${vehicle.tone}`}><i /> {vehicle.status}</span></td></tr>)}</tbody></table></div></section>
  </>
}
