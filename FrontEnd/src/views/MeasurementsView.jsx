import { useState } from 'react'
import { Activity, DollarSign, Droplets, Gauge, Search, Settings2, TrendingUp } from 'lucide-react'

const tirePositions = ['Todos', 'Exterior', 'Interior']
const format = (value, digits = 1) => Number(value || 0).toLocaleString('es-ES', { maximumFractionDigits: digits })

function chartPoints(values) {
  if (!values.length) return ''
  const visibleValues = values.slice(-20)
  const min = Math.min(...visibleValues)
  const max = Math.max(...visibleValues)
  const spread = max - min || 1
  return visibleValues.map((value, index) => {
    const x = visibleValues.length === 1 ? 180 : (index / (visibleValues.length - 1)) * 360
    const y = 78 - ((value - min) / spread) * 60
    return `${x},${y}`
  }).join(' ')
}

function SeriesChart({ metric }) {
  const Icon = metric.icon
  return <article className={`series-card ${metric.tone}`}><div className="series-heading"><span className="series-icon"><Icon size={17} /></span><div><p>{metric.label}</p><strong>{metric.value} <small>{metric.unit}</small></strong></div><span className="series-change">Datos API</span></div><svg className="series-chart" viewBox="0 0 360 92" preserveAspectRatio="none" aria-label={`Serie temporal de ${metric.label}`} role="img"><path className="series-grid" d="M0 20H360 M0 46H360 M0 72H360" /><polyline points={metric.points} /></svg><div className="series-axis"><span>Anterior</span><span>Viajes registrados</span><span>Actual</span></div></article>
}

export default function MeasurementsView({ data }) {
  const [selectedVehicle, setSelectedVehicle] = useState('Toda la flota')
  const [selectedTire, setSelectedTire] = useState(tirePositions[0])
  const trips = selectedVehicle === 'Toda la flota' ? data.trips : data.trips.filter((trip) => trip.patente === selectedVehicle)
  const selectedVehicles = selectedVehicle === 'Toda la flota' ? data.vehicles : data.vehicles.filter((vehicle) => vehicle.patente === selectedVehicle)
  const values = (() => {
    const pressures = trips.map((trip) => trip.presion_final).filter((value) => value != null)
    const distance = trips.map((trip) => trip.kilometros).filter((value) => value != null)
    const costs = trips.map((trip) => trip.costo).filter((value) => value != null)
    const tread = selectedVehicles.map((vehicle) => vehicle.profundidad_surcos_media).filter((value) => value != null)
    const average = (items) => items.length ? items.reduce((total, value) => total + Number(value), 0) / items.length : 0
    return { pressures, distance, costs, tread, average }
  })()
  const metrics = [
    { id: 'pressure', label: 'Presion final media', unit: 'PSI', value: format(values.average(values.pressures)), icon: Gauge, tone: 'blue', points: chartPoints(values.pressures) },
    { id: 'tread', label: 'Profundidad de surcos', unit: 'mm', value: format(values.average(values.tread)), icon: Activity, tone: 'green', points: chartPoints(values.tread) },
    { id: 'distance', label: 'Kilometraje recorrido', unit: 'km', value: format(values.distance.reduce((total, value) => total + Number(value), 0), 0), icon: TrendingUp, tone: 'orange', points: chartPoints(values.distance) },
    { id: 'cost', label: 'Costo de viajes', unit: 'USD', value: format(values.costs.reduce((total, value) => total + Number(value), 0), 2), icon: DollarSign, tone: 'purple', points: chartPoints(values.costs) },
  ]
  const readings = [
    ['Presion final media', format(values.average(values.pressures)), 'PSI', 'Registrada en Viaje-Vehiculo'],
    ['Profundidad de surcos', format(values.average(values.tread)), 'mm', 'Registrada en Neumatico'],
    ['Kilometros recorridos', format(values.distance.reduce((total, value) => total + Number(value), 0), 0), 'km', 'Registrados en Viaje'],
    ['Costo acumulado', format(values.costs.reduce((total, value) => total + Number(value), 0), 2), 'USD', 'Registrado en Viaje'],
  ]
  return <><section className="page-heading"><div><p className="eyebrow">Control de vehiculos</p><h1>Métricas</h1><p className="subtitle">Valores cargados desde viajes y neumáticos.</p></div><button className="primary-button compact"><Search size={17} /> Nueva consulta</button></section><section className="panel metric-filters"><div className="filter-field"><label htmlFor="vehicle-filter">Vehiculo</label><select id="vehicle-filter" value={selectedVehicle} onChange={(event) => setSelectedVehicle(event.target.value)}><option>Toda la flota</option>{data.vehicles.map((vehicle) => <option key={vehicle.patente}>{vehicle.patente}</option>)}</select></div><div className="filter-field"><label htmlFor="tire-filter">Posicion del neumatico</label><select id="tire-filter" value={selectedTire} onChange={(event) => setSelectedTire(event.target.value)}>{tirePositions.map((tire) => <option key={tire}>{tire}</option>)}</select></div><div className="filter-context"><Droplets size={16} /><span>{selectedVehicle} <b>/</b> {selectedTire}</span><small>{trips.length} viajes disponibles</small></div><button className="filter-button"><Settings2 size={16} /> Aplicar filtros</button></section><section className="series-grid">{metrics.map((metric) => <SeriesChart key={metric.id} metric={metric} />)}</section><section className="panel table-panel"><div className="table-toolbar"><div><p className="eyebrow">Indicadores actuales</p><h2>Lecturas detalladas</h2></div></div><div className="table-wrap"><table><thead><tr><th>Indicador</th><th>Valor actual</th><th>Origen</th></tr></thead><tbody>{readings.map(([label, value, unit, source]) => <tr key={label}><td><strong>{label}</strong></td><td><b>{value}</b> {unit}</td><td>{source}</td></tr>)}</tbody></table></div></section></>
}
