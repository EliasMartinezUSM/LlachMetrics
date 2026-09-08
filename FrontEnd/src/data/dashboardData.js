import { Activity, ClipboardList, Gauge, LayoutDashboard, Thermometer, TrendingUp } from 'lucide-react'

export const navigation = [
  { id: 'inicio', label: 'Panel General', icon: LayoutDashboard },
  { id: 'mediciones', label: 'Métricas', icon: ClipboardList },
  { id: 'predicciones', label: 'Predicciones', icon: TrendingUp },
]

export const readings = [
  { label: 'Presion media', value: '7,8', unit: 'bar', detail: '+1,2%', icon: Gauge, tone: 'orange' },
  { label: 'Desgaste de banda', value: '68,4', unit: '%', detail: '-0,8%', icon: Activity, tone: 'blue' },
  { label: 'Temperatura rueda', value: '42,7', unit: 'C', detail: '+0,3%', icon: Thermometer, tone: 'purple' },
  { label: 'Flota operativa', value: '94,2', unit: '%', detail: '+4,6%', icon: ClipboardList, tone: 'green' },
]