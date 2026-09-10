import { AlertTriangle, ClipboardList, Gauge, Route, Truck } from 'lucide-react'

const format = (value, digits = 0) => Number(value || 0).toLocaleString('es-ES', { maximumFractionDigits: digits })

export default function HomeView({ onNavigate, data }) {
  const { summary, vehicles } = data
  const cracked = vehicles.reduce((total, vehicle) => total + vehicle.neumaticos_agrietados, 0)
  const cards = [
    { label: 'Vehiculos registrados', value: summary.vehiculos, detail: `${summary.neumaticos} neumáticos`, icon: Truck, tone: 'blue' },
    { label: 'Neumaticos agrietados', value: cracked, detail: 'Según lecturas cargadas', icon: AlertTriangle, tone: 'orange' },
    { label: 'Kilometros acumulados', value: format(summary.kilometros_totales), detail: 'En viajes registrados', icon: Route, tone: 'green' },
    { label: 'Costo acumulado', value: `$${format(summary.costo_total, 2)}`, detail: 'Costo de los viajes', icon: Gauge, tone: 'purple' },
  ]
  return <>
    <section className="welcome-row"><div><p className="eyebrow">Datos operativos</p><h1>Panel <em>General.</em></h1><p className="subtitle">Resumen real de viajes, vehículos y neumáticos.</p></div><button className="outline-button" onClick={() => onNavigate('mediciones')}><ClipboardList size={17} /> Ver métricas</button></section>
    <section className="metrics-grid summary-grid">{cards.map(({ label, value, detail, icon: Icon, tone }) => <article className="metric-card summary-card" key={label}><div className={`metric-icon ${tone}`}><Icon size={19} /></div><div className="metric-meta"><span>{label}</span><small>{detail}</small></div><div className="metric-value">{value}</div></article>)}</section>
    <section className="panel vehicle-summary"><div className="panel-heading"><div><p className="eyebrow">Resumen por vehiculo</p><h2>Estado de la flota</h2></div></div><div className="table-wrap"><table><thead><tr><th>Vehiculo</th><th>Modelo</th><th><Gauge size={13} /> Presion</th><th>Surcos</th><th>Grietas</th></tr></thead><tbody>{vehicles.map((vehicle) => <tr key={vehicle.patente}><td><strong>{vehicle.patente}</strong></td><td>{vehicle.modelo || 'Sin modelo'}</td><td>{vehicle.presion_final ?? vehicle.presion_inicio ?? '-'} PSI</td><td>{vehicle.profundidad_surcos_media ?? '-'} mm</td><td><span className={`status-pill vehicle-status ${vehicle.neumaticos_agrietados ? 'orange' : 'green'}`}><i /> {vehicle.neumaticos_agrietados || 'Sin'} {vehicle.neumaticos_agrietados === 1 ? 'neumático' : 'neumáticos'}</span></td></tr>)}</tbody></table></div></section>
  </>
}
