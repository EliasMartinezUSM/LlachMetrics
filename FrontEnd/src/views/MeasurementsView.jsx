import { useEffect, useMemo, useRef, useState } from 'react'
import { ResponsiveBar } from '@nivo/bar'
import { ResponsiveLine as NivoResponsiveLine } from '@nivo/line'
import {
  Activity,
  DollarSign,
  Gauge,
  Maximize2,
  Minimize2,
  Minus,
  Plus,
  RotateCcw,
  Search,
  TrendingUp,
  X,
} from 'lucide-react'

const format = (value, digits = 1) =>
  Number(value || 0).toLocaleString('es-ES', { maximumFractionDigits: digits })

function CostRangeVisualization({ points }) {
  const dates = points.map((point) =>
    new Date(point.x).toISOString().slice(0, 10),
  )
  const [start, setStart] = useState(dates[0] || '')
  const [end, setEnd] = useState(dates.at(-1) || '')
  const rangeStart = start <= end ? start : end
  const rangeEnd = start <= end ? end : start
  // El acumulado vuelve a cero al inicio del rango seleccionado.
  const filtered = points.filter((point) => {
    const date = new Date(point.x).toISOString().slice(0, 10)
    return date >= rangeStart && date <= rangeEnd
  })
  const cumulative = filtered.reduce((series, point) => {
    const accumulated = (series.at(-1)?.y || 0) + Number(point.y || 0)
    return [...series, { x: new Date(point.x), y: accumulated }]
  }, [])
  const data = [
    {
      id: 'Costo acumulado',
      data: cumulative,
    },
  ]
  return (
    <div className="cost-range">
      <div className="cost-range-heading">
        <strong>Costo acumulado por rango</strong>
        <span>{format(cumulative.at(-1)?.y || 0, 2)} USD</span>
      </div>
      <div className="cost-range-filters">
        <label>
          Desde
          <input
            type="date"
            value={start}
            min={dates[0]}
            max={dates.at(-1)}
            onChange={(event) => setStart(event.target.value)}
          />
        </label>
        <label>
          Hasta
          <input
            type="date"
            value={end}
            min={dates[0]}
            max={dates.at(-1)}
            onChange={(event) => setEnd(event.target.value)}
          />
        </label>
      </div>
      <div className="cost-range-chart">
        <NivoResponsiveLine
          key={`${rangeStart}-${rangeEnd}`}
          data={data}
          margin={{ top: 12, right: 20, bottom: 52, left: 72 }}
          xScale={{ type: 'time', format: 'native', useUTC: false }}
          xFormat="time:%d/%m/%Y"
          yScale={{ type: 'linear', min: 'auto', max: 'auto' }}
          axisBottom={{
            tickValues: 5,
            tickRotation: -30,
            format: 'time:%d/%m/%Y',
            legend: 'Tiempo',
            legendOffset: 45,
            legendPosition: 'middle',
          }}
          axisLeft={{
            tickValues: 5,
            format: ' >-.2f',
            legend: 'Costo acumulado (USD)',
            legendOffset: -58,
            legendPosition: 'middle',
          }}
          enableGridX={false}
          colors={['var(--accent)']}
          pointSize={3}
          useMesh
          theme={{
            axis: {
              ticks: { text: { fill: 'var(--ink)', fontSize: 10 } },
              legend: {
                text: { fill: 'var(--ink)', fontSize: 10, fontWeight: 600 },
              },
            },
            grid: { line: { stroke: 'var(--line)', strokeDasharray: '3 5' } },
          }}
        />
      </div>
    </div>
  )
}

function ResponsiveLine({ data, ...props }) {
  if (data[0]?.id === 'Costo de viajes') {
    const bars = data[0].data.map((point) => ({ x: point.x, costo: point.y }))
    return (
      <>
        <div className="cost-bars-chart">
          <ResponsiveBar
            data={bars}
            keys={['costo']}
            indexBy="x"
            margin={props.margin}
            padding={0.25}
            valueScale={{ type: 'linear', min: 0, max: 'auto' }}
            indexScale={{ type: 'band', round: true }}
            axisBottom={{ ...props.axisBottom, format: undefined }}
            axisLeft={props.axisLeft}
            enableGridX={false}
            colors={props.colors}
            borderRadius={2}
            borderColor="var(--accent)"
            tooltip={({ data: point }) => (
              <strong>
                {point.x}: {format(point.costo, 2)} USD
              </strong>
            )}
            theme={props.theme}
          />
        </div>
        <CostRangeVisualization points={data[0].data} />
      </>
    )
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
  const sourceLabels =
    metric.labels || sourceValues.map((_, index) => String(index + 1))
  const defaultXEnd =
    sourceLabels[sourceLabels.length - 1] ||
    (metric.timeAxis ? '' : String(sourceValues.length))
  const defaultXStart =
    metric.timeAxis && defaultXEnd
      ? (() => {
          const date = new Date(defaultXEnd)
          date.setMonth(date.getMonth() - 6)
          return date.toISOString().slice(0, 10)
        })()
      : sourceLabels[0] || '1'
  const effectiveXStart = xStart || defaultXStart
  const effectiveXEnd = xEnd || defaultXEnd
  // Permite filtrar el eje X tanto por fechas como por número de observación.
  const visibleIndexes = sourceValues
    .map((_, index) => index)
    .filter((index) => {
      if (metric.timeAxis)
        return (
          sourceLabels[index] >= effectiveXStart &&
          sourceLabels[index] <= effectiveXEnd
        )
      const pointNumber = index + 1
      return (
        pointNumber >= Number(effectiveXStart) &&
        pointNumber <= Number(effectiveXEnd)
      )
    })
  const visibleCount = Math.max(2, Math.ceil(visibleIndexes.length / xZoom))
  const visibleData = visibleIndexes.slice(-visibleCount).map((index) => ({
    index,
    label: sourceLabels[index],
    value: Number(sourceValues[index]),
  }))
  const rawMin = visibleData.length
    ? Math.min(...visibleData.map((point) => point.value))
    : 0
  const rawMax = visibleData.length
    ? Math.max(...visibleData.map((point) => point.value))
    : 1
  const rawSpread = rawMax - rawMin || Math.max(Math.abs(rawMax) * 0.1, 1)
  const center = (rawMin + rawMax) / 2
  const spread = rawSpread / yZoom
  const min = yStart !== '' ? Number(yStart) : center - spread / 2
  const max = yEnd !== '' ? Number(yEnd) : center + spread / 2
  const chartData = [
    {
      id: metric.label,
      data: visibleData.map((point) => ({
        x:
          metric.id === 'cost'
            ? point.label
            : metric.timeAxis
              ? new Date(point.label)
              : point.index + 1,
        y: point.value,
      })),
    },
  ]
  const resetZoom = () => {
    setXZoom(1)
    setYZoom(1)
    setXStart('')
    setXEnd('')
    setYStart('')
    setYEnd('')
  }
  const axisInputType = metric.timeAxis ? 'date' : 'number'
  return (
    <article
      className={`series-card ${metric.tone}${expanded ? ' is-expanded' : ''}`}
    >
      <div className="series-heading">
        <span className="series-icon">
          <Icon size={17} />
        </span>
        <div>
          <p>{metric.label}</p>
          <strong>
            {metric.value} <small>{metric.unit}</small>
          </strong>
        </div>
        <span className="series-change">Datos API</span>
        <button
          className="chart-expand-button"
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-label={
            expanded ? `Contraer ${metric.label}` : `Expandir ${metric.label}`
          }
        >
          {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
        </button>
      </div>
      <div className="chart-toolbar">
        <span>Zoom X {xZoom.toFixed(1)}x</span>
        <button
          type="button"
          onClick={() => setXZoom((zoom) => Math.max(1, zoom - 0.5))}
          aria-label={`Reducir zoom horizontal de ${metric.label}`}
        >
          <Minus size={13} />
        </button>
        <button
          type="button"
          onClick={() => setXZoom((zoom) => Math.min(5, zoom + 0.5))}
          aria-label={`Aumentar zoom horizontal de ${metric.label}`}
        >
          <Plus size={13} />
        </button>
        <span>Zoom Y {yZoom.toFixed(1)}x</span>
        <button
          type="button"
          onClick={() => setYZoom((zoom) => Math.max(1, zoom - 0.5))}
          aria-label={`Reducir zoom vertical de ${metric.label}`}
        >
          <Minus size={13} />
        </button>
        <button
          type="button"
          onClick={() => setYZoom((zoom) => Math.min(5, zoom + 0.5))}
          aria-label={`Aumentar zoom vertical de ${metric.label}`}
        >
          <Plus size={13} />
        </button>
        <button
          type="button"
          onClick={resetZoom}
          aria-label={`Restablecer zoom de ${metric.label}`}
        >
          <RotateCcw size={13} />
        </button>
      </div>
      {expanded && (
        <div className="chart-axis-controls">
          <label>
            Eje X inicio
            <input
              type={axisInputType}
              value={effectiveXStart}
              min={metric.timeAxis ? undefined : 1}
              onChange={(event) => setXStart(event.target.value)}
            />
          </label>
          <label>
            Eje X termino
            <input
              type={axisInputType}
              value={effectiveXEnd}
              min={metric.timeAxis ? undefined : 1}
              onChange={(event) => setXEnd(event.target.value)}
            />
          </label>
          <label>
            Eje Y inicio
            <input
              type="number"
              value={yStart}
              placeholder={format(rawMin)}
              onChange={(event) => setYStart(event.target.value)}
            />
          </label>
          <label>
            Eje Y termino
            <input
              type="number"
              value={yEnd}
              placeholder={format(rawMax)}
              onChange={(event) => setYEnd(event.target.value)}
            />
          </label>
        </div>
      )}
      <div className="series-chart">
        <ResponsiveLine
          data={chartData}
          margin={{
            top: 18,
            right: 24,
            bottom: metric.timeAxis ? 82 : 68,
            left: metric.id === 'distance' ? 112 : 92,
          }}
          xScale={{
            type: metric.timeAxis ? 'time' : 'linear',
            format: metric.timeAxis ? 'native' : undefined,
            useUTC: false,
          }}
          xFormat={metric.timeAxis ? 'time:%d/%m/%Y' : undefined}
          yScale={{ type: 'linear', min, max }}
          axisTop={null}
          axisRight={null}
          axisBottom={{
            tickValues: 5,
            tickRotation: metric.timeAxis ? -30 : 0,
            legend: metric.xTitle,
            legendOffset: metric.timeAxis ? 68 : 52,
            legendPosition: 'middle',
            format: metric.timeAxis ? 'time:%d/%m/%Y' : ' >-.0f',
          }}
          axisLeft={{
            tickValues: 5,
            legend: metric.yTitle,
            legendOffset: metric.id === 'distance' ? -86 : -70,
            legendPosition: 'middle',
            format: ' >-.2f',
          }}
          enableGridX={false}
          enableGridY={true}
          colors={['var(--accent)']}
          lineWidth={2.5}
          pointSize={4}
          pointBorderWidth={1}
          pointColor="var(--surface)"
          pointBorderColor="var(--accent)"
          useMesh={true}
          enableSlices={false}
          theme={{
            text: { fill: 'var(--ink)', fontSize: expanded ? 12 : 10 },
            axis: {
              ticks: {
                text: { fill: 'var(--ink)', fontSize: expanded ? 12 : 10 },
              },
              legend: {
                text: {
                  fill: 'var(--ink)',
                  fontSize: expanded ? 12 : 10,
                  fontWeight: 600,
                },
              },
            },
            grid: { line: { stroke: 'var(--line)', strokeDasharray: '3 5' } },
            crosshair: { line: { stroke: 'var(--accent)' } },
            tooltip: {
              container: {
                background: 'var(--surface)',
                color: 'var(--ink)',
                fontSize: 12,
              },
            },
          }}
        />
      </div>
    </article>
  )
}

const formatInternalId = (value) =>
  value != null ? String(value).padStart(5, '0') : ''

function tireMatchesIdentifier(tire, rawQuery) {
  const query = rawQuery.trim().toLowerCase()
  if (!query) return true
  const internalFormatted = formatInternalId(tire.id_interno).toLowerCase()
  const internalRaw =
    tire.id_interno != null ? String(tire.id_interno).toLowerCase() : ''
  const serial = (tire.serie || '').toLowerCase()
  const dbId = String(tire.id).toLowerCase()
  return (
    internalFormatted.includes(query) ||
    internalRaw === query ||
    serial.includes(query) ||
    dbId === query
  )
}

function findMatchingTire(allTires, rawQuery) {
  const query = rawQuery.trim().toLowerCase()
  if (!query) return null
  const numericQuery = /^\d+$/.test(query) ? String(Number(query)) : null
  const exactMatch = allTires.find((tire) => {
    const internalFormatted = formatInternalId(tire.id_interno).toLowerCase()
    const internalRaw =
      tire.id_interno != null ? String(tire.id_interno).toLowerCase() : ''
    const serial = (tire.serie || '').toLowerCase()
    return (
      internalFormatted === query ||
      internalRaw === query ||
      (numericQuery !== null && internalRaw === numericQuery) ||
      serial === query ||
      String(tire.id).toLowerCase() === query
    )
  })
  if (exactMatch) return exactMatch

  const partialMatches = allTires.filter((tire) =>
    tireMatchesIdentifier(tire, query),
  )
  return partialMatches.length === 1 ? partialMatches[0] : null
}

export default function MeasurementsView({ data }) {
  const Droplets = Gauge
  const [tireSearch, setTireSearch] = useState('')
  const [selectedVehicle, setSelectedVehicle] = useState('Toda la flota')
  const [selectedAxle, setSelectedAxle] = useState('Todos')
  const [selectedSide, setSelectedSide] = useState('Todos')
  const [selectedPosition, setSelectedPosition] = useState('Todos')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const searchContainerRef = useRef(null)

  const searchSuggestions = useMemo(() => {
    const query = tireSearch.trim().toLowerCase()
    if (!query) return []
    const results = []
    const seen = new Set()

    for (const tire of data.tires) {
      const internalStr = tire.id_interno != null ? String(tire.id_interno) : ''
      const paddedInternal = formatInternalId(tire.id_interno)
      const serial = tire.serie || ''

      // Sugerir ID interno si coincide con lo escrito
      if (
        internalStr &&
        (internalStr.toLowerCase().includes(query) ||
          paddedInternal.toLowerCase().includes(query))
      ) {
        const val = paddedInternal || internalStr
        if (!seen.has(val)) {
          seen.add(val)
          results.push({ value: val, tire })
        }
      }

      // Sugerir número de serie si coincide con lo escrito
      if (serial && serial.toLowerCase().includes(query)) {
        if (!seen.has(serial)) {
          seen.add(serial)
          results.push({ value: serial, tire })
        }
      }

      if (results.length >= 8) break
    }
    return results
  }, [data.tires, tireSearch])

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(event.target)
      ) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('pointerdown', handleClickOutside)
    return () => {
      document.removeEventListener('pointerdown', handleClickOutside)
    }
  }, [])

  const applyTireFilters = (tire) => {
    setSelectedVehicle(tire.patente || 'Toda la flota')
    setSelectedAxle(tire.eje != null ? String(tire.eje) : 'Todos')
    setSelectedSide(tire.lado || 'Todos')
    setSelectedPosition(tire.posicion || 'Todos')
  }

  const handleSelectSuggestion = (item) => {
    setTireSearch(item.value)
    applyTireFilters(item.tire)
    setIsDropdownOpen(false)
    setSelectedIndex(-1)
  }

  const handleTireSearchChange = (event) => {
    const nextValue = event.target.value
    setTireSearch(nextValue)
    setIsDropdownOpen(Boolean(nextValue.trim()))
    setSelectedIndex(-1)
    if (!nextValue.trim()) {
      setSelectedVehicle('Toda la flota')
      setSelectedAxle('Todos')
      setSelectedSide('Todos')
      setSelectedPosition('Todos')
      return
    }
    const matchedTire = findMatchingTire(data.tires, nextValue)
    if (matchedTire) {
      applyTireFilters(matchedTire)
    }
  }

  const handleTireSearchKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!isDropdownOpen && searchSuggestions.length > 0) {
        setIsDropdownOpen(true)
        setSelectedIndex(0)
        return
      }
      setSelectedIndex((prev) =>
        prev < searchSuggestions.length - 1 ? prev + 1 : 0
      )
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setSelectedIndex((prev) =>
        prev > 0 ? prev - 1 : searchSuggestions.length - 1
      )
      return
    }
    if (event.key === 'Escape') {
      setIsDropdownOpen(false)
      setSelectedIndex(-1)
      return
    }
    if (event.key === 'Enter') {
      if (
        isDropdownOpen &&
        selectedIndex >= 0 &&
        searchSuggestions[selectedIndex]
      ) {
        event.preventDefault()
        handleSelectSuggestion(searchSuggestions[selectedIndex])
        return
      }
      const query = tireSearch.trim()
      if (!query) return
      const matchedTire =
        findMatchingTire(data.tires, query) ||
        data.tires.find((tire) => tireMatchesIdentifier(tire, query))
      if (matchedTire) {
        applyTireFilters(matchedTire)
        setIsDropdownOpen(false)
      }
    }
  }

  const activeMatchedTire = findMatchingTire(data.tires, tireSearch)

  // Los filtros de selección se aplican a viajes, neumáticos y series antes de calcular métricas.
  const trips =
    selectedVehicle === 'Toda la flota'
      ? data.trips
      : data.trips.filter((trip) => trip.patente === selectedVehicle)
  const tires = data.tires.filter(
    (tire) =>
      tireMatchesIdentifier(tire, tireSearch) &&
      (selectedVehicle === 'Toda la flota' ||
        tire.patente === selectedVehicle) &&
      (selectedAxle === 'Todos' || String(tire.eje) === selectedAxle) &&
      (selectedSide === 'Todos' || tire.lado === selectedSide) &&
      (selectedPosition === 'Todos' || tire.posicion === selectedPosition),
  )
  const pressureSeries = data.pressureSeries.filter(
    (point) =>
      selectedVehicle === 'Toda la flota' || point.patente === selectedVehicle,
  )
  const distanceSeries = data.distanceSeries.filter(
    (point) =>
      selectedVehicle === 'Toda la flota' || point.patente === selectedVehicle,
  )
  const treadSeries = data.treadSeries.filter((point) => {
    const pointTire = data.tires.find((tire) => tire.id === point.id)
    return (
      (!pointTire || tireMatchesIdentifier(pointTire, tireSearch)) &&
      (selectedVehicle === 'Toda la flota' ||
        point.patente === selectedVehicle) &&
      // Las series de surco guardan el ID del neumático, no sus datos de posición.
      (selectedAxle === 'Todos' || pointTire?.eje === Number(selectedAxle)) &&
      (selectedSide === 'Todos' || pointTire?.lado === selectedSide) &&
      (selectedPosition === 'Todos' || pointTire?.posicion === selectedPosition)
    )
  })
  const values = (() => {
    const pressures = pressureSeries
      .map((point) => point.presion_final)
      .filter((value) => value != null)
    const distance = distanceSeries
      .map((point) =>
        selectedVehicle === 'Toda la flota'
          ? point.kilometros_acumulados
          : point.kilometros_acumulados_vehiculo,
      )
      .filter((value) => value != null)
    const costs = trips
      .map((trip) => trip.costo)
      .filter((value) => value != null)
    const tread = treadSeries
      .map((point) => point.profundidad_surcos)
      .filter((value) => value != null)
    const average = (items) =>
      items.length
        ? items.reduce((total, value) => total + Number(value), 0) /
          items.length
        : 0
    return { pressures, distance, costs, tread, average }
  })()
  const metrics = [
    {
      id: 'pressure',
      label: 'Presion final media',
      unit: 'PSI',
      value: format(values.average(values.pressures)),
      icon: Gauge,
      tone: 'blue',
      values: values.pressures,
      labels: pressureSeries.map((point) => point.fecha),
      timeAxis: true,
      yTitle: 'Presion (PSI)',
      xTitle: 'Tiempo',
    },
    {
      id: 'tread',
      label: 'Profundidad de surcos',
      unit: 'mm',
      value: format(values.average(values.tread)),
      icon: Activity,
      tone: 'green',
      values: values.tread,
      labels: treadSeries.map((point) => point.fecha),
      timeAxis: true,
      yTitle: 'Profundidad (mm)',
      xTitle: 'Tiempo',
    },
    {
      id: 'distance',
      label: 'Kilometraje acumulado',
      unit: 'km',
      value: format(values.distance.at(-1) || 0, 0),
      icon: TrendingUp,
      tone: 'orange',
      values: values.distance,
      labels: distanceSeries.map((point) => point.fecha),
      timeAxis: true,
      yTitle: 'Kilometraje (km)',
      xTitle: 'Tiempo',
    },
    {
      id: 'cost',
      label: 'Costo de viajes',
      unit: 'USD',
      value: format(
        values.costs.reduce((total, value) => total + Number(value), 0),
        2,
      ),
      icon: DollarSign,
      tone: 'purple',
      values: values.costs,
      labels: trips.map((trip) => trip.fecha),
      timeAxis: true,
      yTitle: 'Costo (USD)',
      xTitle: 'Viaje',
    },
  ]
  return (
    <>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Control de vehiculos</p>
          <h1>Métricas</h1>
          <p className="subtitle">
            Valores cargados desde viajes y neumáticos.
          </p>
        </div>
      </section>
      <section className="panel metric-filters">
        <div className="filter-field search-field" ref={searchContainerRef}>
          <label htmlFor="tire-search-filter">ID interno / Serie</label>
          <div className="filter-search-input">
            <Search size={14} />
            <input
              id="tire-search-filter"
              name="tireSearch"
              type="text"
              autoComplete="off"
              value={tireSearch}
              onChange={handleTireSearchChange}
              onKeyDown={handleTireSearchKeyDown}
              onFocus={() => {
                if (tireSearch.trim() && searchSuggestions.length > 0) {
                  setIsDropdownOpen(true)
                }
              }}
              placeholder="Ej: 10001 o MICH-..."
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              enterKeyHint="search"
            />
            {tireSearch && (
              <button
                type="button"
                className="filter-search-clear"
                onClick={() => {
                  setTireSearch('')
                  setIsDropdownOpen(false)
                  setSelectedVehicle('Toda la flota')
                  setSelectedAxle('Todos')
                  setSelectedSide('Todos')
                  setSelectedPosition('Todos')
                }}
                aria-label="Limpiar búsqueda"
              >
                <X size={13} />
              </button>
            )}
          </div>
          {isDropdownOpen && searchSuggestions.length > 0 && (
            <div className="filter-search-dropdown" role="listbox">
              {searchSuggestions.map((item, index) => (
                <button
                  key={`${item.value}-${index}`}
                  type="button"
                  role="option"
                  aria-selected={index === selectedIndex}
                  className={`filter-search-dropdown-item ${
                    index === selectedIndex ? 'is-selected' : ''
                  }`}
                  onClick={() => handleSelectSuggestion(item)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  {item.value}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="filter-field">
          <label htmlFor="vehicle-filter">Vehiculo</label>
          <select
            id="vehicle-filter"
            value={selectedVehicle}
            onChange={(event) => {
              const nextVehicle = event.target.value
              setSelectedVehicle(nextVehicle)
              if (
                tireSearch &&
                activeMatchedTire &&
                activeMatchedTire.patente !== nextVehicle
              ) {
                setTireSearch('')
              }
            }}
          >
            <option>Toda la flota</option>
            {data.vehicles.map((vehicle) => (
              <option key={vehicle.patente}>{vehicle.patente}</option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="axle-filter">Eje</label>
          <select
            id="axle-filter"
            value={selectedAxle}
            onChange={(event) => {
              const nextAxle = event.target.value
              setSelectedAxle(nextAxle)
              if (
                tireSearch &&
                activeMatchedTire &&
                String(activeMatchedTire.eje) !== nextAxle
              ) {
                setTireSearch('')
              }
            }}
          >
            <option>Todos</option>
            {[
              ...new Set(
                data.tires
                  .map((tire) => tire.eje)
                  .filter((axle) => axle != null),
              ),
            ]
              .sort((firstAxle, secondAxle) => firstAxle - secondAxle)
              .map((axle) => (
                <option key={axle}>{axle}</option>
              ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="side-filter">Lado</label>
          <select
            id="side-filter"
            value={selectedSide}
            onChange={(event) => {
              const nextSide = event.target.value
              setSelectedSide(nextSide)
              if (
                tireSearch &&
                activeMatchedTire &&
                activeMatchedTire.lado !== nextSide
              ) {
                setTireSearch('')
              }
            }}
          >
            <option>Todos</option>
            {[...new Set(data.tires.map((tire) => tire.lado).filter(Boolean))]
              .sort()
              .map((side) => (
                <option key={side}>{side}</option>
              ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="position-filter">Posicion</label>
          <select
            id="position-filter"
            value={selectedPosition}
            onChange={(event) => {
              const nextPosition = event.target.value
              setSelectedPosition(nextPosition)
              if (
                tireSearch &&
                activeMatchedTire &&
                activeMatchedTire.posicion !== nextPosition
              ) {
                setTireSearch('')
              }
            }}
          >
            <option>Todos</option>
            {[
              ...new Set(
                data.tires.map((tire) => tire.posicion).filter(Boolean),
              ),
            ]
              .sort()
              .map((position) => (
                <option key={position}>{position}</option>
              ))}
          </select>
        </div>
        <div className="filter-context">
          <Droplets size={16} />
          <span>
            {selectedVehicle} <b>/</b> Eje {selectedAxle} <b>/</b>{' '}
            {selectedSide} <b>/</b> {selectedPosition}
            {activeMatchedTire && (
              <>
                {' '}
                <b>/</b> ID {formatInternalId(activeMatchedTire.id_interno)}
              </>
            )}
          </span>
          <small>
            {trips.length} viajes · {tires.length} lecturas de neumáticos
          </small>
        </div>
      </section>
      <section className="series-grid">
        {metrics.map((metric) => (
          <SeriesChart key={metric.id} metric={metric} />
        ))}
      </section>
      <section className="panel table-panel">
        <div className="table-toolbar">
          <div>
            <p className="eyebrow">Detalle de neumáticos</p>
            <h2>Registros de la base de datos</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>ID Interno</th>
                <th>Serie</th>
                <th>Vehículo</th>
                <th>Eje</th>
                <th>Lado</th>
                <th>Posición</th>
                <th>Adquisición</th>
                <th>Recauchajes</th>
                <th>Profundidad</th>
                <th>Agrietado</th>
                <th>Kilómetros</th>
              </tr>
            </thead>
            <tbody>
              {tires.length ? (
                tires.map((tire) => (
                  <tr key={tire.id}>
                    <td>{tire.id}</td>
                    <td>
                      {tire.id_interno != null
                        ? String(tire.id_interno).padStart(5, '0')
                        : '-'}
                    </td>
                    <td>{tire.serie || '-'}</td>
                    <td>
                      <strong>{tire.patente}</strong>
                    </td>
                    <td>{tire.eje ?? '-'}</td>
                    <td>{tire.lado || '-'}</td>
                    <td>{tire.posicion || '-'}</td>
                    <td>
                      {tire.fecha_adquisicion
                        ? new Date(
                            `${tire.fecha_adquisicion}T00:00:00`,
                          ).toLocaleDateString('es-ES')
                        : '-'}
                    </td>
                    <td>{tire.cantidad_recauchajes ?? '-'}</td>
                    <td>
                      {tire.profundidad_surcos != null
                        ? `${format(tire.profundidad_surcos, 2)} mm`
                        : '-'}
                    </td>
                    <td>
                      {tire.agrietado == null
                        ? '-'
                        : tire.agrietado
                          ? 'Sí'
                          : 'No'}
                    </td>
                    <td>
                      {tire.kilometros != null
                        ? `${format(tire.kilometros, 0)} km`
                        : '-'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={12}>
                    No hay neumáticos para los filtros seleccionados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}
