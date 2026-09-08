import { ArrowUpRight } from 'lucide-react'

export default function MetricCard({ reading }) {
  const Icon = reading.icon
  return <article className="metric-card"><div className={`metric-icon ${reading.tone}`}><Icon size={19} /></div><div className="metric-meta"><span>{reading.label}</span><small>Ultimas 24 h</small></div><div className="metric-value">{reading.value}<small>{reading.unit}</small></div><div className="metric-change"><ArrowUpRight size={14} /> {reading.detail}</div></article>
}