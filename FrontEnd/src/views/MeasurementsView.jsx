import { useState } from 'react'
import { Activity, Droplets, Fuel, Gauge, Search, Settings2, TrendingUp } from 'lucide-react'
import { readings, vehicles } from '../data/dashboardData'

const tires = [
  'Todos los neumaticos',
  'Eje 1 - Izquierdo',
  'Eje 1 - Derecho',
  'Eje 2 - Izquierdo exterior',
  'Eje 2 - Izquierdo interior',
  'Eje 2 - Derecho interior',
  'Eje 2 - Derecho exterior',
  'Eje 3 - Izquierdo exterior',
  'Eje 3 - Izquierdo interior',
  'Eje 3 - Derecho interior',
  'Eje 3 - Derecho exterior',
]

const metricSeries = [
  { id: 'pressure', label: 'Presion de aire', unit: 'PSI', value: '113,8', change: '-2,4%', icon: Gauge, tone: 'blue', points: '0,36 40,43 80,38 120,51 160,45 200,57 240,52 280,65 320,58 360,70' },
  { id: 'tread', label: 'Profundidad de surcos', unit: 'mm', value: '6,8', change: '+0,6 mm', icon: Activity, tone: 'green', points: '0,62 40,58 80,55 120,49 160,45 200,39 240,35 280,29 320,24 360,18' },
  { id: 'distance', label: 'Kilometraje recorrido', unit: 'km', value: '12.480', change: '+8,2%', icon: TrendingUp, tone: 'orange', points: '0,76 40,70 80,66 120,62 160,53 200,49 240,42 280,35 320,29 360,20' },
  { id: 'fuel', label: 'Combustible consumido', unit: 'L', value: '1.284', change: '+3,1%', icon: Fuel, tone: 'purple', points: '0,68 40,62 80,57 120,51 160,47 200,40 240,34 280,28 320,22 360,16' },
]

function SeriesChart({ metric }) {
  const Icon = metric.icon
  return <article className={`series-card ${metric.tone}`}><div className="series-heading"><span className="series-icon"><Icon size={17} /></span><div><p>{metric.label}</p><strong>{metric.value} <small>{metric.unit}</small></strong></div><span className="series-change">{metric.change}</span></div><svg className="series-chart" viewBox="0 0 360 92" preserveAspectRatio="none" aria-label={`Serie temporal de ${metric.label}`} role="img"><path className="series-grid" d="M0 20H360 M0 46H360 M0 72H360" /><polyline points={metric.points} /></svg><div className="series-axis"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>Ahora</span></div></article>
}

export default function MeasurementsView() {
  const [selectedVehicle, setSelectedVehicle] = useState('Toda la flota')
  const [selectedTire, setSelectedTire] = useState(tires[0])
  const ranges = { 'Presion media': '7,0 - 8,5 bar', 'Desgaste de banda': '0 - 80 %', 'Temperatura rueda': '20 - 70 C', 'Flota operativa': '90 - 100 %' }
  return <><section className="page-heading"><div><p className="eyebrow">Control de vehiculos</p><h1>Métricas</h1><p className="subtitle">Analiza el rendimiento por vehículo y neumático.</p></div><button className="primary-button compact"><Search size={17} /> Nueva consulta</button></section><section className="panel metric-filters"><div className="filter-field"><label htmlFor="vehicle-filter">Vehiculo</label><select id="vehicle-filter" value={selectedVehicle} onChange={(event) => setSelectedVehicle(event.target.value)}><option>Toda la flota</option>{vehicles.map((vehicle) => <option key={vehicle.id}>{vehicle.id}</option>)}</select></div><div className="filter-field"><label htmlFor="tire-filter">Posicion del neumatico</label><select id="tire-filter" value={selectedTire} onChange={(event) => setSelectedTire(event.target.value)}>{tires.map((tire) => <option key={tire}>{tire}</option>)}</select></div><div className="filter-context"><Droplets size={16} /><span>{selectedVehicle} <b>/</b> {selectedTire}</span><small>Ultimas 24 horas</small></div><button className="filter-button"><Settings2 size={16} /> Aplicar filtros</button></section><section className="series-grid">{metricSeries.map((metric) => <SeriesChart key={metric.id} metric={metric} />)}</section><section className="panel table-panel"><div className="table-toolbar"><div><p className="eyebrow">Indicadores actuales</p><h2>Lecturas detalladas</h2></div><div className="tabs"><button className="active">Estado actual</button><button>Alertas <span>3</span></button></div></div><div className="table-wrap"><table><thead><tr><th>Indicador</th><th>Valor actual</th><th>Rango seguro</th><th>Tendencia</th><th>Estado</th><th /></tr></thead><tbody>{readings.map((reading) => { const Icon = reading.icon; return <tr key={reading.label}><td><span className={`table-icon ${reading.tone}`}><Icon size={16} /></span><strong>{reading.label}</strong></td><td><b>{reading.value}</b> {reading.unit}</td><td>{ranges[reading.label]}</td><td><span className="trend-up"><TrendingUp size={15} /> {reading.detail}</span></td><td><span className="status-pill"><i /> Dentro del rango</span></td><td><button className="more-button">...</button></td></tr> })}</tbody></table></div></section></>
}