import { useState } from 'react'
import { AlertTriangle, CalendarClock, CircleDot, CircleDollarSign, CircleHelp, Fuel, Gauge, Search, ShieldCheck, Sparkles, Truck, Wrench } from 'lucide-react'

function predictionFor(index) {
  const states = [
    { risk: 'Bajo', tone: 'green', summary: 'Operación estable y sin señales urgentes.', recommendation: 'Mantener el plan preventivo actual.' },
    { risk: 'Moderado', tone: 'yellow', summary: 'Requiere seguimiento preventivo periódico.', recommendation: 'Revisar presión de aire y desgaste de neumáticos.' },
    { risk: 'Alto', tone: 'orange', summary: 'Presenta condiciones que requieren atención prioritaria.', recommendation: 'Programar una inspección del vehículo.' },
    { risk: 'Crítico', tone: 'red', summary: 'Requiere intervención prioritaria antes de continuar la operación.', recommendation: 'Evaluar estado de salud del vehículo con urgencia.' },
  ]
  return states[index % states.length]
}

function SavingsHighlight() {
  return <section className="savings-highlight"><div className="savings-intro"><span className="savings-kicker">Impacto estimado</span><h2>Ahorro generado por mantenimiento preventivo</h2><p>El poder de tomar decisiones guiadas por datos.</p></div><div className="savings-metrics"><div><CircleDot size={17} /><strong>300</strong><span>Neumáticos recauchados</span></div><div><Fuel size={17} /><strong>1.240 L</strong><span>Combustible ahorrado</span></div><div><CircleDollarSign size={22} /><strong>US$ 4.680</strong><span>Ahorro total estimado</span></div></div></section>
}

export default function PredictionsView({ data }) {
  const [searchTerm, setSearchTerm] = useState('')
  const predictions = data.vehicles.map((vehicle, index) => ({ vehicle, ...predictionFor(index) }))
  const highRisk = predictions.filter((prediction) => prediction.tone === 'red').length
  const normalizedSearch = searchTerm.trim().toLocaleLowerCase()
  const filteredPredictions = predictions.filter(({ vehicle }) => `${vehicle.patente} ${vehicle.modelo || ''}`.toLocaleLowerCase().includes(normalizedSearch))
  return <><section className="page-heading"><div><p className="eyebrow">Analisis de mantenimiento</p><h1>Predicciones</h1><p className="subtitle">Indicadores derivados de las lecturas reales de neumáticos.</p></div><button className="outline-button"><CircleHelp size={17} /> Como funciona</button></section><SavingsHighlight /><section className="prediction-summary"><article><span className="summary-icon blue"><Truck size={18} /></span><div><small>Vehiculos analizados</small><strong>{predictions.length}</strong></div></article><article><span className="summary-icon orange"><AlertTriangle size={18} /></span><div><small>Requieren atencion</small><strong>{highRisk}</strong></div></article><article><span className="summary-icon green"><ShieldCheck size={18} /></span><div><small>Sin grietas</small><strong>{predictions.length - highRisk}</strong></div></article><article><span className="summary-icon purple"><CalendarClock size={18} /></span><div><small>Reemplazos urgentes</small><strong>4</strong></div></article></section><section className="prediction-list"><div className="section-heading"><div><p className="eyebrow">Estado por vehiculo</p><h2>Prioridad de mantenimiento</h2></div><label className="prediction-search"><Search size={16} /><input type="search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Buscar patente o modelo" aria-label="Buscar por patente o modelo" /></label></div>{filteredPredictions.length ? filteredPredictions.map(({ vehicle, risk, tone, summary, recommendation }) => <article className={`vehicle-prediction ${tone}`} key={vehicle.patente}><div className="vehicle-prediction-main"><div className="vehicle-prediction-title"><span className="vehicle-code">{vehicle.patente}</span><div><h3>{vehicle.modelo || 'Vehículo sin modelo'}</h3><p>{summary}</p></div><span className="risk-label">Riesgo {risk}</span></div><div className="vehicle-recommendation"><div><small>Recomendacion</small><strong>{recommendation}</strong></div><div className="prediction-meta"><span><Gauge size={14} /> Presion: {vehicle.presion_final ?? vehicle.presion_inicio ?? '-'} PSI</span><span><Wrench size={14} /> Surcos: {vehicle.profundidad_surcos_media ?? '-'} mm</span></div></div></div></article>) : <p className="prediction-empty">No se encontraron vehículos para “{searchTerm}”.</p>}</section></>
}
