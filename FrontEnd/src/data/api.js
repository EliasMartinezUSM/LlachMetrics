const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function getData(path) {
  const token = localStorage.getItem('access_token')
  const response = await fetch(`${apiBase}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'No se pudieron cargar los datos')
  return data
}

export function getDashboardData() {
  return Promise.all([getData('/data/dashboard'), getData('/data/trips'), getData('/data/tires'), getData('/data/pressure-series'), getData('/data/distance-series'), getData('/data/tread-series')])
    .then(([dashboard, trips, tires, pressureSeries, distanceSeries, treadSeries]) => ({ ...dashboard, trips, tires, pressureSeries, distanceSeries, treadSeries }))
}