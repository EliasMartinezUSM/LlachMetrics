import { AlertTriangle, CircleHelp, Gauge, ShieldCheck, Sparkles, Truck, Wrench } from 'lucide-react'

function predictionFor(vehicle) {
  const cracks = vehicle.neumaticos_agrietados || 0
  const tread = Number(vehicle.profundidad_surcos_media || 0)
  const highRisk = cracks > 0 || (tread > 0 && tread < 4)
  return {
    risk: highRisk ? 'Alto' : 'Bajo',
    tone: highRisk ? 'red' : 'green',
    summary: cracks ? `${cracks} neumático(s) con grietas registrados.` : 'Sin grietas registradas en las lecturas.',
    recommendation: highRisk ? 'Programar una inspección del vehículo.' : 'Mantener el plan de revisión.',
  }
}

export default function PredictionsView({ data }) {
  const predictions = data.vehicles.map((vehicle) => ({ vehicle, ...predictionFor(vehicle) }))
  const highRisk = predictions.filter((prediction) => prediction.risk === 'Alto').length
  return <><section className="page-heading"><div><p className="eyebrow">Analisis de mantenimiento</p><h1>Predicciones</h1><p className="subtitle">Indicadores derivados de las lecturas reales de neumáticos.</p></div><button className="outline-button"><CircleHelp size={17} /> Como funciona</button></section><section className="prediction-summary"><article><span className="summary-icon blue"><Truck size={18} /></span><div><small>Vehiculos analizados</small><strong>{predictions.length}</strong></div></article><article><span className="summary-icon orange"><AlertTriangle size={18} /></span><div><small>Requieren atencion</small><strong>{highRisk}</strong></div></article><article><span className="summary-icon green"><ShieldCheck size={18} /></span><div><small>Sin grietas</small><strong>{predictions.length - highRisk}</strong></div></article><article><span className="summary-icon purple"><Wrench size={18} /></span><div><small>Lecturas de neumáticos</small><strong>{data.summary.neumaticos}</strong></div></article></section><section className="prediction-list"><div className="section-heading"><div><p className="eyebrow">Estado por vehiculo</p><h2>Prioridad de mantenimiento</h2></div><span className="model-status"><Sparkles size={14} /> Calculado con datos API</span></div>{predictions.map(({ vehicle, risk, tone, summary, recommendation }) => <article className={`vehicle-prediction ${tone}`} key={vehicle.patente}><div className="vehicle-prediction-main"><div className="vehicle-prediction-title"><span className="vehicle-code">{vehicle.patente}</span><div><h3>{vehicle.modelo || 'Vehículo sin modelo'}</h3><p>{summary}</p></div><span className="risk-label">Riesgo {risk}</span></div><div className="vehicle-recommendation"><div><small>Recomendacion</small><strong>{recommendation}</strong></div><div className="prediction-meta"><span><Gauge size={14} /> Presion: {vehicle.presion_final ?? vehicle.presion_inicio ?? '-'} PSI</span><span><Wrench size={14} /> Surcos: {vehicle.profundidad_surcos_media ?? '-'} mm</span></div></div></div></article>)}</section></>
}
