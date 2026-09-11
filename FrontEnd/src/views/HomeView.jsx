import { AlertTriangle, Bell, ClipboardList, Gauge, Truck } from 'lucide-react'

export default function HomeView({ onNavigate, data }) {
  const { summary, vehicles } = data
  const vehiclesInTrip = vehicles.filter((vehicle) => vehicle.viaje_actual != null).length
  const cards = [
    { label: 'Vehiculos registrados', value: summary.vehiculos, detail: 'Flota total', icon: Truck, tone: 'blue' },
    { label: 'Vehiculos en viaje', value: vehiclesInTrip, detail: 'Viajes actualmente registrados', icon: Truck, tone: 'green' },
    { label: 'Alertas activas', value: 3, detail: 'Requieren seguimiento', icon: AlertTriangle, tone: 'orange' },
    { label: 'Reemplazos urgentes', value: 2, detail: 'Neumaticos por cambiar', icon: Bell, tone: 'purple' },
  ]
  return <>
    <section className="welcome-row"><div><h1>Panel General.</h1></div><button className="outline-button" onClick={() => onNavigate('mediciones')}><ClipboardList size={17} /> Ver métricas</button></section>
    <section className="metrics-grid summary-grid">{cards.map(({ label, value, detail, icon: Icon, tone }) => <article className="metric-card summary-card" key={label}><div className={`metric-icon ${tone}`}><Icon size={19} /></div><div className="metric-meta"><span>{label}</span><small>{detail}</small></div><div className="metric-value">{value}</div></article>)}</section>
    <section className="panel vehicle-summary"><div className="panel-heading"><div><p className="eyebrow">Resumen por vehiculo</p><h2>Estado de la flota</h2></div></div><div className="table-wrap"><table><thead><tr><th>Vehiculo</th><th>Viaje actual</th><th>Modelo</th><th><Gauge size={13} /> Presion promedio</th><th>Surcos promedio</th><th>Neumaticos</th><th>Recomendaciones</th></tr></thead><tbody>{vehicles.map((vehicle) => <tr key={vehicle.patente}><td><strong>{vehicle.patente}</strong></td><td>{vehicle.viaje_actual ? `Viaje #${vehicle.viaje_actual}` : 'Sin viaje'}</td><td>{vehicle.modelo || 'Sin modelo'}</td><td>{vehicle.presion_promedio != null ? `${Number(vehicle.presion_promedio).toFixed(2)} PSI` : '-'}</td><td>{vehicle.profundidad_surcos_media != null ? `${Number(vehicle.profundidad_surcos_media).toFixed(2)} mm` : '-'}</td><td>{vehicle.neumaticos}</td><td><span className="status-pill vehicle-status blue"><i /> {vehicle.recomendacion || 'Pendiente de análisis'}</span></td></tr>)}</tbody></table></div></section>
  </>
}
