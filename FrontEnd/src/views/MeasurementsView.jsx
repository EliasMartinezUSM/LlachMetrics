import { useState } from 'react'
import { ResponsiveBar } from '@nivo/bar'
import { ResponsiveLine as NivoResponsiveLine } from '@nivo/line'
import { Activity, DollarSign, Gauge, Maximize2, Minimize2, Minus, Plus, RotateCcw, TrendingUp } from 'lucide-react'

const format = (value, digits = 1) => Number(value || 0).toLocaleString('es-ES', { maximumFractionDigits: digits })

function CostRangeVisualization({ points }) {
  const dates = points.map((point) => new Date(point.x).toISOString().slice(0, 10))
  const [start, setStart] = useState(dates[0] || '')
  const [end, setEnd] = useState(dates.at(-1) || '')
  const rangeStart = start <= end ? start : end
  const rangeEnd = start <= end ? end : start
  const filtered = points.filter((point) => {
    const date = new Date(point.x).toISOString().slice(0, 10)
    return date >= rangeStart && date <= rangeEnd
  })
  const cumulative = filtered.reduce((series, point) => {
    const accumulated = (series.at(-1)?.y || 0) + Number(point.y || 0)
    return [...series, { x: new Date(point.x), y: accumulated }]
  }, [])
  const data = [{
    id: 'Costo acumulado',
    data: cumulative,
  }]
  return <div className="cost-range"><div className="cost-range-heading"><strong>Costo acumulado por rango</strong><span>{format(cumulative.at(-1)?.y || 0, 2)} USD</span></div><div className="cost-range-filters"><label>Desde<input type="date" value={start} min={dates[0]} max={dates.at(-1)} onChange={(event) => setStart(event.target.value)} /></label><label>Hasta<input type="date" value={end} min={dates[0]} max={dates.at(-1)} onChange={(event) => setEnd(event.target.value)} /></label></div><div className="cost-range-chart"><NivoResponsiveLine key={`${rangeStart}-${rangeEnd}`} data={data} margin={{ top: 12, right: 20, bottom: 52, left: 72 }} xScale={{ type: 'time', format: 'native', useUTC: false }} xFormat="time:%d/%m/%Y" yScale={{ type: 'linear', min: 'auto', max: 'auto' }} axisBottom={{ tickValues: 5, tickRotation: -30, format: 'time:%d/%m/%Y', legend: 'Tiempo', legendOffset: 45, legendPosition: 'middle' }} axisLeft={{ tickValues: 5, format: ' >-.2f', legend: 'Costo acumulado (USD)', legendOffset: -58, legendPosition: 'middle' }} enableGridX={false} colors={['var(--accent)']} pointSize={3} useMesh theme={{ axis: { ticks: { text: { fill: 'var(--ink)', fontSize: 10 } }, legend: { text: { fill: 'var(--ink)', fontSize: 10, fontWeight: 600 } } }, grid: { line: { stroke: 'var(--line)', strokeDasharray: '3 5' } } }} /></div></div>
}

function ResponsiveLine({ data, ...props }) {
  if (data[0]?.id === 'Costo de viajes') {
    const bars = data[0].data.map((point) => ({ x: point.x, costo: point.y }))
    return <><div className="cost-bars-chart"><ResponsiveBar data={bars} keys={['costo']} indexBy="x" margin={props.margin} padding={0.25} valueScale={{ type: 'linear', min: 0, max: 'auto' }} indexScale={{ type: 'band', round: true }} axisBottom={{ ...props.axisBottom, format: undefined }} axisLeft={props.axisLeft} enableGridX={false} colors={['#23777f']} borderRadius={2} borderColor="#174f56" tooltip={({ data: point }) => <strong>{point.x}: {format(point.costo, 2)} USD</strong>} theme={props.theme} /></div><CostRangeVisualization points={data[0].data} /></>
  }
  return <NivoResponsiveLine data={data} {...props} />
}

function SeriesChart({ metric }) {
  const [xZoom, setXZoom] = useState(1)
  const [yZoom, setYZoom] = useState(1)
  const [expanded, setExpanded] = useState(true)
  const [xStart, setXStart] = useState('')
  const [xEnd, setXEnd] = useState('')
  const [yStart, setYStart] = useState('')
  const [yEnd, setYEnd] = useState('')
  const Icon = metric.icon
  const sourceValues = metric.values
  const sourceLabels = metric.labels || sourceValues.map((_, index) => String(index + 1))
  const defaultXEnd = sourceLabels[sourceLabels.length - 1] || (metric.timeAxis ? '' : String(sourceValues.length))
  const defaultXStart = metric.timeAxis && defaultXEnd
    ? (() => { const date = new Date(defaultXEnd); date.setMonth(date.getMonth() - 6); return date.toISOString().slice(0, 10) })()
    : (sourceLabels[0] || '1')
  const effectiveXStart = xStart || defaultXStart
  const effectiveXEnd = xEnd || defaultXEnd
  const visibleIndexes = sourceValues.map((_, index) => index).filter((index) => {
    if (metric.timeAxis) return sourceLabels[index] >= effectiveXStart && sourceLabels[index] <= effectiveXEnd
    const pointNumber = index + 1
    return pointNumber >= Number(effectiveXStart) && pointNumber <= Number(effectiveXEnd)
  })
  const visibleCount = Math.max(2, Math.ceil(visibleIndexes.length / xZoom))
  const visibleData = visibleIndexes.slice(-visibleCount).map((index) => ({
    index,
    label: sourceLabels[index],
    value: Number(sourceValues[index]),
  }))
  const rawMin = visibleData.length ? Math.min(...visibleData.map((point) => point.value)) : 0
  const rawMax = visibleData.length ? Math.max(...visibleData.map((point) => point.value)) : 1
  const rawSpread = rawMax - rawMin || Math.max(Math.abs(rawMax) * 0.1, 1)
  const center = (rawMin + rawMax) / 2
  const spread = rawSpread / yZoom
  const min = yStart !== '' ? Number(yStart) : center - spread / 2
  const max = yEnd !== '' ? Number(yEnd) : center + spread / 2
  const chartData = [{
    id: metric.label,
    data: visibleData.map((point) => ({
      x: metric.id === 'cost' ? point.label : (metric.timeAxis ? new Date(point.label) : point.index + 1),
      y: point.value,
    })),
  }]
  const resetZoom = () => { setXZoom(1); setYZoom(1); setXStart(''); setXEnd(''); setYStart(''); setYEnd('') }
  const axisInputType = metric.timeAxis ? 'date' : 'number'
  return <article className={`series-card ${metric.tone}${expanded ? ' is-expanded' : ''}`}><div className="series-heading"><span className="series-icon"><Icon size={17} /></span><div><p>{metric.label}</p><strong>{metric.value} <small>{metric.unit}</small></strong></div><span className="series-change">Datos API</span><button className="chart-expand-button" type="button" onClick={() => setExpanded((value) => !value)} aria-label={expanded ? `Contraer ${metric.label}` : `Expandir ${metric.label}`}>{expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}</button></div><div className="chart-toolbar"><span>Zoom X {xZoom.toFixed(1)}x</span><button type="button" onClick={() => setXZoom((zoom) => Math.max(1, zoom - 0.5))} aria-label={`Reducir zoom horizontal de ${metric.label}`}><Minus size={13} /></button><button type="button" onClick={() => setXZoom((zoom) => Math.min(5, zoom + 0.5))} aria-label={`Aumentar zoom horizontal de ${metric.label}`}><Plus size={13} /></button><span>Zoom Y {yZoom.toFixed(1)}x</span><button type="button" onClick={() => setYZoom((zoom) => Math.max(1, zoom - 0.5))} aria-label={`Reducir zoom vertical de ${metric.label}`}><Minus size={13} /></button><button type="button" onClick={() => setYZoom((zoom) => Math.min(5, zoom + 0.5))} aria-label={`Aumentar zoom vertical de ${metric.label}`}><Plus size={13} /></button><button type="button" onClick={resetZoom} aria-label={`Restablecer zoom de ${metric.label}`}><RotateCcw size={13} /></button></div>{expanded && <div className="chart-axis-controls"><label>Eje X inicio<input type={axisInputType} value={effectiveXStart} min={metric.timeAxis ? undefined : 1} onChange={(event) => setXStart(event.target.value)} /></label><label>Eje X termino<input type={axisInputType} value={effectiveXEnd} min={metric.timeAxis ? undefined : 1} onChange={(event) => setXEnd(event.target.value)} /></label><label>Eje Y inicio<input type="number" value={yStart} placeholder={format(rawMin)} onChange={(event) => setYStart(event.target.value)} /></label><label>Eje Y termino<input type="number" value={yEnd} placeholder={format(rawMax)} onChange={(event) => setYEnd(event.target.value)} /></label></div>}<div className="series-chart"><ResponsiveLine data={chartData} margin={{ top: 18, right: 24, bottom: metric.timeAxis ? 82 : 68, left: metric.id === 'distance' ? 112 : 92 }} xScale={{ type: metric.timeAxis ? 'time' : 'linear', format: metric.timeAxis ? 'native' : undefined, useUTC: false }} xFormat={metric.timeAxis ? 'time:%d/%m/%Y' : undefined} yScale={{ type: 'linear', min, max }} axisTop={null} axisRight={null} axisBottom={{ tickValues: 5, tickRotation: metric.timeAxis ? -30 : 0, legend: metric.xTitle, legendOffset: metric.timeAxis ? 68 : 52, legendPosition: 'middle', format: metric.timeAxis ? 'time:%d/%m/%Y' : ' >-.0f' }} axisLeft={{ tickValues: 5, legend: metric.yTitle, legendOffset: metric.id === 'distance' ? -86 : -70, legendPosition: 'middle', format: ' >-.2f' }} enableGridX={false} enableGridY={true} colors={['var(--accent)']} lineWidth={2.5} pointSize={4} pointBorderWidth={1} pointColor="var(--surface)" pointBorderColor="var(--accent)" useMesh={true} enableSlices={false} theme={{ text: { fill: 'var(--ink)', fontSize: expanded ? 12 : 10 }, axis: { ticks: { text: { fill: 'var(--ink)', fontSize: expanded ? 12 : 10 } }, legend: { text: { fill: 'var(--ink)', fontSize: expanded ? 12 : 10, fontWeight: 600 } } }, grid: { line: { stroke: 'var(--line)', strokeDasharray: '3 5' } }, crosshair: { line: { stroke: 'var(--accent)' } }, tooltip: { container: { background: 'var(--surface)', color: 'var(--ink)', fontSize: 12 } } }} /></div></article>
}

export default function MeasurementsView({ data }) {
  const Droplets = Gauge
  const [selectedVehicle, setSelectedVehicle] = useState('Toda la flota')
  const [selectedAxle, setSelectedAxle] = useState('Todos')
  const [selectedSide, setSelectedSide] = useState('Todos')
  const [selectedPosition, setSelectedPosition] = useState('Todos')
  const trips = selectedVehicle === 'Toda la flota' ? data.trips : data.trips.filter((trip) => trip.patente === selectedVehicle)
  const tires = data.tires.filter((tire) => (
    (selectedVehicle === 'Toda la flota' || tire.patente === selectedVehicle)
    && (selectedAxle === 'Todos' || String(tire.eje) === selectedAxle)
    && (selectedSide === 'Todos' || tire.lado === selectedSide)
    && (selectedPosition === 'Todos' || tire.posicion === selectedPosition)
  ))
  const pressureSeries = data.pressureSeries.filter((point) => (
    selectedVehicle === 'Toda la flota' || point.patente === selectedVehicle
  ))
  const distanceSeries = data.distanceSeries.filter((point) => (
    selectedVehicle === 'Toda la flota' || point.patente === selectedVehicle
  ))
  const treadSeries = data.treadSeries.filter((point) => (
    (selectedVehicle === 'Toda la flota' || point.patente === selectedVehicle)
    && (selectedAxle === 'Todos' || data.tires.find((tire) => tire.id === point.id)?.eje === Number(selectedAxle))
    && (selectedSide === 'Todos' || data.tires.find((tire) => tire.id === point.id)?.lado === selectedSide)
    && (selectedPosition === 'Todos' || data.tires.find((tire) => tire.id === point.id)?.posicion === selectedPosition)
  ))
  const values = (() => {
    const pressures = pressureSeries.map((point) => point.presion_final).filter((value) => value != null)
    const distance = distanceSeries.map((point) => selectedVehicle === 'Toda la flota' ? point.kilometros_acumulados : point.kilometros_acumulados_vehiculo).filter((value) => value != null)
    const costs = trips.map((trip) => trip.costo).filter((value) => value != null)
    const tread = treadSeries.map((point) => point.profundidad_surcos).filter((value) => value != null)
    const average = (items) => items.length ? items.reduce((total, value) => total + Number(value), 0) / items.length : 0
    return { pressures, distance, costs, tread, average }
  })()
  const metrics = [
    { id: 'pressure', label: 'Presion final media', unit: 'PSI', value: format(values.average(values.pressures)), icon: Gauge, tone: 'blue', values: values.pressures, labels: pressureSeries.map((point) => point.fecha), timeAxis: true, yTitle: 'Presion (PSI)', xTitle: 'Tiempo' },
    { id: 'tread', label: 'Profundidad de surcos', unit: 'mm', value: format(values.average(values.tread)), icon: Activity, tone: 'green', values: values.tread, labels: treadSeries.map((point) => point.fecha), timeAxis: true, yTitle: 'Profundidad (mm)', xTitle: 'Tiempo' },
    { id: 'distance', label: 'Kilometraje acumulado', unit: 'km', value: format(values.distance.at(-1) || 0, 0), icon: TrendingUp, tone: 'orange', values: values.distance, labels: distanceSeries.map((point) => point.fecha), timeAxis: true, yTitle: 'Kilometraje (km)', xTitle: 'Tiempo' },
    { id: 'cost', label: 'Costo de viajes', unit: 'USD', value: format(values.costs.reduce((total, value) => total + Number(value), 0), 2), icon: DollarSign, tone: 'purple', values: values.costs, labels: trips.map((trip) => trip.fecha), timeAxis: true, yTitle: 'Costo (USD)', xTitle: 'Viaje' },
  ]
  const readings = [
    ['Presion final media', format(values.average(values.pressures)), 'PSI', 'Registrada en Viaje-Vehiculo'],
    ['Profundidad de surcos', format(values.average(values.tread)), 'mm', 'Registrada en Neumatico'],
    ['Kilometros acumulados', format(values.distance.at(-1) || 0, 0), 'km', 'Acumulados por fecha de viaje'],
    ['Costo acumulado', format(values.costs.reduce((total, value) => total + Number(value), 0), 2), 'USD', 'Registrado en Viaje'],
  ]
  return <><section className="page-heading"><div><p className="eyebrow">Control de vehiculos</p><h1>Métricas</h1><p className="subtitle">Valores cargados desde viajes y neumáticos.</p></div></section><section className="panel metric-filters"><div className="filter-field"><label htmlFor="vehicle-filter">Vehiculo</label><select id="vehicle-filter" value={selectedVehicle} onChange={(event) => setSelectedVehicle(event.target.value)}><option>Toda la flota</option>{data.vehicles.map((vehicle) => <option key={vehicle.patente}>{vehicle.patente}</option>)}</select></div><div className="filter-field"><label htmlFor="axle-filter">Eje</label><select id="axle-filter" value={selectedAxle} onChange={(event) => setSelectedAxle(event.target.value)}><option>Todos</option>{[...new Set(data.tires.map((tire) => tire.eje).filter((axle) => axle != null))].sort((firstAxle, secondAxle) => firstAxle - secondAxle).map((axle) => <option key={axle}>{axle}</option>)}</select></div><div className="filter-field"><label htmlFor="side-filter">Lado</label><select id="side-filter" value={selectedSide} onChange={(event) => setSelectedSide(event.target.value)}><option>Todos</option>{[...new Set(data.tires.map((tire) => tire.lado).filter(Boolean))].sort().map((side) => <option key={side}>{side}</option>)}</select></div><div className="filter-field"><label htmlFor="position-filter">Posicion</label><select id="position-filter" value={selectedPosition} onChange={(event) => setSelectedPosition(event.target.value)}><option>Todos</option>{[...new Set(data.tires.map((tire) => tire.posicion).filter(Boolean))].sort().map((position) => <option key={position}>{position}</option>)}</select></div><div className="filter-context"><Droplets size={16} /><span>{selectedVehicle} <b>/</b> Eje {selectedAxle} <b>/</b> {selectedSide} <b>/</b> {selectedPosition}</span><small>{trips.length} viajes · {tires.length} lecturas de neumáticos</small></div></section><section className="series-grid">{metrics.map((metric) => <SeriesChart key={metric.id} metric={metric} />)}</section><section className="panel table-panel"><div className="table-toolbar"><div><p className="eyebrow">Indicadores actuales</p><h2>Lecturas detalladas</h2></div></div><div className="table-wrap"><table><thead><tr><th>Indicador</th><th>Valor actual</th><th>Origen</th></tr></thead><tbody>{readings.map(([label, value, unit, source]) => <tr key={label}><td><strong>{label}</strong></td><td><b>{value}</b> {unit}</td><td>{source}</td></tr>)}</tbody></table></div></section></>
}
