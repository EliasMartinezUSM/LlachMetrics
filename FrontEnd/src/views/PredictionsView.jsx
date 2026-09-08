import { useState } from 'react'
import { AlertTriangle, ArrowUpRight, ChevronDown, CircleHelp, Gauge, ShieldCheck, Sparkles, Truck, Wrench } from 'lucide-react'

const predictions = [
  {
    id: 'LM-042', route: 'Madrid - Toledo', risk: 'Medio', tone: 'orange', confidence: '94%', summary: 'Desgaste desigual en el eje delantero.', recommendation: 'Programar rotacion en los proximos 2 dias.', due: '1.200 km',
    tires: [
      { position: 'Eje 1 - Izquierdo', wear: '72%', tread: '5,8 mm', remaining: '1.200 km', action: 'Rotar', tone: 'orange' },
      { position: 'Eje 1 - Derecho', wear: '69%', tread: '6,1 mm', remaining: '1.500 km', action: 'Rotar', tone: 'orange' },
      { position: 'Eje 2 - Izquierdo exterior', wear: '54%', tread: '7,4 mm', remaining: '8.400 km', action: 'Sin accion', tone: 'green' },
      { position: 'Eje 2 - Derecho exterior', wear: '51%', tread: '7,7 mm', remaining: '9.100 km', action: 'Sin accion', tone: 'green' },
    ],
  },
  {
    id: 'LM-018', route: 'Valencia - Alicante', risk: 'Alto', tone: 'red', confidence: '91%', summary: 'Presion baja y temperatura elevada.', recommendation: 'Cambiar neumaticos del eje 2 antes de 800 km.', due: '800 km',
    tires: [
      { position: 'Eje 1 - Izquierdo', wear: '64%', tread: '6,4 mm', remaining: '3.200 km', action: 'Inspeccionar', tone: 'orange' },
      { position: 'Eje 1 - Derecho', wear: '61%', tread: '6,6 mm', remaining: '3.600 km', action: 'Inspeccionar', tone: 'orange' },
      { position: 'Eje 2 - Izquierdo exterior', wear: '86%', tread: '2,8 mm', remaining: '800 km', action: 'Cambiar', tone: 'red' },
      { position: 'Eje 2 - Derecho exterior', wear: '83%', tread: '3,1 mm', remaining: '1.000 km', action: 'Cambiar', tone: 'red' },
    ],
  },
  {
    id: 'LM-031', route: 'Sevilla - Cordoba', risk: 'Bajo', tone: 'green', confidence: '97%', summary: 'Desgaste uniforme y parametros estables.', recommendation: 'Mantener el plan de revision mensual.', due: '9.600 km',
    tires: [
      { position: 'Eje 1 - Izquierdo', wear: '42%', tread: '8,2 mm', remaining: '9.600 km', action: 'Sin accion', tone: 'green' },
      { position: 'Eje 1 - Derecho', wear: '43%', tread: '8,1 mm', remaining: '9.400 km', action: 'Sin accion', tone: 'green' },
      { position: 'Eje 2 - Izquierdo exterior', wear: '48%', tread: '7,9 mm', remaining: '8.800 km', action: 'Sin accion', tone: 'green' },
      { position: 'Eje 2 - Derecho exterior', wear: '46%', tread: '8,0 mm', remaining: '9.000 km', action: 'Sin accion', tone: 'green' },
    ],
  },
]

function TireDetails({ tires }) {
  return <div className="tire-details"><div className="tire-details-heading"><span>Posicion</span><span>Desgaste</span><span>Vida estimada</span><span>Recomendacion</span></div>{tires.map((tire) => <div className="tire-row" key={tire.position}><strong>{tire.position}</strong><span>{tire.wear} <small>{tire.tread}</small></span><span>{tire.remaining}</span><span className={`prediction-action ${tire.tone}`}>{tire.action}</span></div>)}</div>
}

export default function PredictionsView() {
  const [expandedVehicle, setExpandedVehicle] = useState('LM-042')
  const highRisk = predictions.filter((prediction) => prediction.risk === 'Alto').length
  return <><section className="page-heading"><div><p className="eyebrow">Mantenimiento predictivo</p><h1>Predicciones</h1><p className="subtitle">Recomendaciones del modelo para anticipar el cambio de neumáticos.</p></div><button className="outline-button"><CircleHelp size={17} /> Como funciona</button></section><section className="prediction-summary"><article><span className="summary-icon blue"><Truck size={18} /></span><div><small>Vehiculos analizados</small><strong>{predictions.length}</strong></div></article><article><span className="summary-icon orange"><AlertTriangle size={18} /></span><div><small>Requieren atencion</small><strong>{highRisk + 1}</strong></div></article><article><span className="summary-icon green"><ShieldCheck size={18} /></span><div><small>Confianza media</small><strong>94%</strong></div></article><article><span className="summary-icon purple"><Wrench size={18} /></span><div><small>Proximo cambio</small><strong>800 km</strong></div></article></section><section className="prediction-list"><div className="section-heading"><div><p className="eyebrow">Recomendaciones por vehiculo</p><h2>Prioridad de mantenimiento</h2></div><span className="model-status"><Sparkles size={14} /> Modelo actualizado hoy</span></div>{predictions.map((prediction) => <article className={`vehicle-prediction ${prediction.tone}`} key={prediction.id}><div className="vehicle-prediction-main"><div className="vehicle-prediction-title"><span className="vehicle-code">{prediction.id}</span><div><h3>{prediction.route}</h3><p>{prediction.summary}</p></div><span className="risk-label">Riesgo {prediction.risk}</span></div><div className="vehicle-recommendation"><div><small>Recomendacion del modelo</small><strong>{prediction.recommendation}</strong></div><div className="prediction-meta"><span><Gauge size={14} /> Confianza {prediction.confidence}</span><span><Wrench size={14} /> Proximo evento: {prediction.due}</span></div></div><button className="details-button" onClick={() => setExpandedVehicle(expandedVehicle === prediction.id ? '' : prediction.id)}>{expandedVehicle === prediction.id ? 'Ocultar neumáticos' : 'Ver neumáticos'} <ChevronDown size={16} className={expandedVehicle === prediction.id ? 'rotated' : ''} /></button></div>{expandedVehicle === prediction.id && <TireDetails tires={prediction.tires} />}</article>)}</section><section className="prediction-note"><Sparkles size={18} /><p><strong>Como funciona el modelo</strong> Analiza desgaste, presion, temperatura, kilometraje y patrones de uso para estimar cuando conviene rotar o cambiar cada neumático.</p><ArrowUpRight size={18} /></section></>
}
