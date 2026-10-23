// Por defecto usa el proxy /api de Vite (mismo origen). Una URL absoluta solo
// funciona si la API comparte sitio con el frontend o usa SameSite=None.
export const apiBaseUrl = (import.meta.env.VITE_API_URL || '/api').replace(
  /\/+$/,
  '',
)

export async function apiFetch(path, options = {}) {
  // El navegador adjunta la cookie HttpOnly de sesión; JavaScript nunca ve el JWT.
  return fetch(`${apiBaseUrl}${path}`, { credentials: 'include', ...options })
}

export async function getCurrentUser() {
  const response = await apiFetch('/auth/me')
  if (!response.ok) return null
  return response.json()
}

export async function logout() {
  await apiFetch('/auth/logout', { method: 'POST' })
}

async function getData(path) {
  const response = await apiFetch(path)
  const data = await response.json().catch(() => ({}))
  if (!response.ok)
    throw new Error(data.detail || 'No se pudieron cargar los datos')
  return data
}

export function getDashboardData() {
  // Solicita en paralelo los recursos que comparten las vistas del dashboard.
  return Promise.all([
    getData('/data/dashboard'),
    getData('/data/trips'),
    getData('/data/tires'),
    getData('/data/pressure-series'),
    getData('/data/distance-series'),
    getData('/data/tread-series'),
  ]).then(
    ([
      dashboard,
      trips,
      tires,
      pressureSeries,
      distanceSeries,
      treadSeries,
    ]) => ({
      ...dashboard,
      trips,
      tires,
      pressureSeries,
      distanceSeries,
      treadSeries,
    }),
  )
}
