import { useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowUpDown,
  Check,
  CheckCircle2,
  Combine,
  Copy,
  Crosshair,
  Database,
  Download,
  Eye,
  EyeOff,
  Image as ImageIcon,
  Plus,
  RefreshCw,
  RotateCcw,
  ScanText,
  Sparkles,
  Trash2,
  Unlink,
  Upload,
  X,
} from 'lucide-react'
import Logo from './components/Logo'
import './App.css'

const IDENTIFIER_CATEGORIES = new Set([
  'identificacion',
  'vehiculo',
  'documento',
  'neumatico',
  'contacto',
])

function getBboxBounds(bbox) {
  if (!bbox || !bbox.length) {
    return { minX: 0, minY: 0, maxX: 0, maxY: 0, centerX: 0, centerY: 0, width: 0, height: 0 }
  }
  const xs = bbox.map((pt) => pt[0])
  const ys = bbox.map((pt) => pt[1])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  return {
    minX,
    minY,
    maxX,
    maxY,
    centerX: (minX + maxX) / 2,
    centerY: (minY + maxY) / 2,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  }
}

function mergeBboxList(bboxes) {
  const valid = bboxes.filter((b) => Array.isArray(b) && b.length > 0)
  if (!valid.length) return null
  const allPoints = valid.flat()
  const xs = allPoints.map((pt) => pt[0])
  const ys = allPoints.map((pt) => pt[1])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  return [
    [minX, minY],
    [maxX, minY],
    [maxX, maxY],
    [minX, maxY],
  ]
}

function sortBlocksReadingOrder(blocks) {
  return [...blocks].sort((a, b) => {
    const ba = getBboxBounds(a.bbox)
    const bb = getBboxBounds(b.bbox)
    const rowTolerance = Math.max(ba.height, bb.height) * 0.55
    if (Math.abs(ba.centerY - bb.centerY) <= rowTolerance) {
      return ba.minX - bb.minX
    }
    return ba.centerY - bb.centerY
  })
}

function inferLabelAndValue(selectedBlocks, mode, fallbackLabel) {
  if (!selectedBlocks.length) {
    return { label: fallbackLabel || 'Campo', value: '' }
  }

  const texts = selectedBlocks.map((b) => b.text.trim()).filter(Boolean)
  const joined = texts.join(' ')

  if (mode === 'first-as-label' && texts.length >= 2) {
    const cleanFirst = texts[0].replace(/^[:=\s-]+|[:=\s-]+$/g, '').trim()
    const restValue = texts
      .slice(1)
      .join(' ')
      .replace(/^[:=\s-]+/, '')
      .trim()
    return {
      label: cleanFirst || fallbackLabel || 'Campo',
      value: restValue,
    }
  }

  if (mode === 'all-value') {
    return {
      label: fallbackLabel || 'Campo fusionado',
      value: joined,
    }
  }

  // Modo automático: detectar si hay separador ':' o '='
  const colonMatch = joined.match(/^([^:=]{1,42})\s*[:=]\s*(.+)$/)
  if (colonMatch) {
    return {
      label: colonMatch[1].trim(),
      value: colonMatch[2].trim(),
    }
  }

  if (texts.length >= 2) {
    const cleanFirst = texts[0].replace(/^[:=\s-]+|[:=\s-]+$/g, '').trim()
    const restValue = texts
      .slice(1)
      .join(' ')
      .replace(/^[:=\s-]+/, '')
      .trim()
    if (cleanFirst.length <= 28 && restValue) {
      return {
        label: cleanFirst,
        value: restValue,
      }
    }
  }

  return {
    label: fallbackLabel || 'Campo',
    value: joined,
  }
}

function generateSampleDocumentBlob() {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas')
    canvas.width = 920
    canvas.height = 680
    const ctx = canvas.getContext('2d')

    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    ctx.strokeStyle = '#1e293b'
    ctx.lineWidth = 3
    ctx.strokeRect(28, 28, canvas.width - 56, canvas.height - 56)

    ctx.fillStyle = '#0f172a'
    ctx.font = 'bold 28px sans-serif'
    ctx.fillText('ORDEN DE INSPECCION DE NEUMATICOS', 56, 82)

    ctx.strokeStyle = '#94a3b8'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(56, 102)
    ctx.lineTo(canvas.width - 56, 102)
    ctx.stroke()

    const rows = [
      ['Empresa: Logistica Sierra', 'Folio: OT-2026-0842'],
      ['RUT: 76.543.210-K', 'Fecha: 22/10/2026'],
      ['Patente: KRTW-42', 'Modelo: Volvo FH 500'],
      ['Conductor: Roberto Soto', 'Kilometraje: 148320 km'],
      ['Serie Neumatico: MICH-88412', 'ID Interno: 40512'],
      ['Eje: Eje 2 Izquierdo Exterior', 'Recauchajes: 1'],
      ['Presion Inicial: 112.5 PSI', 'Presion Final: 116.2 PSI'],
      ['Profundidad Surcos: 11.4 mm', 'Agrietado: No'],
      ['Estado: Operativo en ruta', 'Costo Total: $185.000'],
    ]

    ctx.font = '22px monospace'
    ctx.fillStyle = '#0f172a'

    let y = 152
    for (const [leftCol, rightCol] of rows) {
      ctx.fillText(leftCol, 56, y)
      ctx.fillText(rightCol, 485, y)
      y += 54
    }

    canvas.toBlob((blob) => {
      resolve(blob)
    }, 'image/png')
  })
}

export default function App() {
  const fileInputId = useId()
  const rawTextId = useId()
  const fusionLabelId = useId()
  const fusionValueId = useId()
  const fusionTargetId = useId()
  const fileInputRef = useRef(null)
  const svgOverlayRef = useRef(null)

  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [backendOnline, setBackendOnline] = useState(true)
  const [systemApiOnline, setSystemApiOnline] = useState(true)
  const [isSavingToSystem, setIsSavingToSystem] = useState(false)
  const [ingestResult, setIngestResult] = useState(null)
  const [ingestError, setIngestError] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [ocrResult, setOcrResult] = useState(null)

  // Bloques de detección activos en el lienzo (pueden fusionarse o separarse)
  const [activeBlocks, setActiveBlocks] = useState([])
  const [editableFields, setEditableFields] = useState([])
  const [selectedBlockIds, setSelectedBlockIds] = useState([])
  const [fusionMode, setFusionMode] = useState('auto')
  const [fusionTargetFieldId, setFusionTargetFieldId] = useState('auto')
  const [fusionOverrides, setFusionOverrides] = useState({
    key: '',
    label: null,
    value: null,
  })
  const [recentlyUpdatedFieldId, setRecentlyUpdatedFieldId] = useState(null)

  // Selección por arrastre (marquee) sobre el SVG
  const [marquee, setMarquee] = useState(null)
  const suppressNextSvgClickRef = useRef(false)

  const [activeTab, setActiveTab] = useState('campos')
  const [showOverlay, setShowOverlay] = useState(true)
  const [hoveredBoxIds, setHoveredBoxIds] = useState([])
  const [copiedKey, setCopiedKey] = useState('')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => setBackendOnline(res.ok))
      .catch(() => setBackendOnline(false))

    fetch('/backend-api/health')
      .then((res) => setSystemApiOnline(res.ok))
      .catch(() => setSystemApiOnline(false))
  }, [])

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  // Bloques actualmente seleccionados en el orden en que el usuario los eligió
  const selectedBlocks = useMemo(() => {
    const byId = new Map(activeBlocks.map((b) => [b.id, b]))
    return selectedBlockIds.map((id) => byId.get(id)).filter(Boolean)
  }, [activeBlocks, selectedBlockIds])

  // Campos que están vinculados con las cajas seleccionadas actualmente
  const linkedFieldsForSelection = useMemo(() => {
    if (!selectedBlockIds.length) return []
    const idSet = new Set(selectedBlockIds)
    return editableFields.filter((field) => {
      if (Array.isArray(field.block_ids) && field.block_ids.some((bid) => idSet.has(bid))) {
        return true
      }
      return selectedBlocks.some(
        (b) => field.value && b.text && (b.text.includes(field.value) || field.value.includes(b.text)),
      )
    })
  }, [editableFields, selectedBlockIds, selectedBlocks])

  const selectionKey = `${selectedBlockIds.join(',')}|${fusionMode}|${fusionTargetFieldId}`

  const defaultFusionProposal = useMemo(() => {
    if (!selectedBlocks.length) {
      return { label: '', value: '' }
    }
    const targetField =
      fusionTargetFieldId !== 'auto'
        ? editableFields.find((f) => f.id === fusionTargetFieldId)
        : linkedFieldsForSelection[0]

    const fallbackLbl = targetField?.label || 'Campo fusionado'
    const inferred = inferLabelAndValue(selectedBlocks, fusionMode, fallbackLbl)
    return {
      label:
        fusionTargetFieldId !== 'auto' && targetField ? targetField.label : inferred.label,
      value: inferred.value,
    }
  }, [selectedBlocks, fusionMode, fusionTargetFieldId, editableFields, linkedFieldsForSelection])

  const effectiveFusionLabel =
    fusionOverrides.key === selectionKey && fusionOverrides.label !== null
      ? fusionOverrides.label
      : defaultFusionProposal.label

  const effectiveFusionValue =
    fusionOverrides.key === selectionKey && fusionOverrides.value !== null
      ? fusionOverrides.value
      : defaultFusionProposal.value

  const selectDocumentFile = (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setErrorMessage('Por favor selecciona un archivo de imagen válido (PNG, JPG, WEBP).')
      return
    }
    setErrorMessage('')
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
    const nextUrl = URL.createObjectURL(file)
    setSelectedFile(file)
    setPreviewUrl(nextUrl)
  }

  const hydrateFromOcrData = (data) => {
    const initialBlocks = (data.blocks || []).map((b) => ({ ...b }))
    const initialFields = (data.fields || []).map((f) => {
      if (Array.isArray(f.block_ids) && f.block_ids.length > 0) {
        return { ...f }
      }
      const matchedIds = initialBlocks
        .filter((b) => f.value && b.text.includes(f.value))
        .map((b) => b.id)
      return { ...f, block_ids: matchedIds }
    })
    setActiveBlocks(initialBlocks)
    setEditableFields(initialFields)
    setSelectedBlockIds([])
    setFusionTargetFieldId('auto')
    setIngestResult(null)
    setIngestError('')
  }

  const runEasyOcrOnFile = async (fileToProcess) => {
    const targetFile = fileToProcess || selectedFile
    if (!targetFile) {
      setErrorMessage('Selecciona o arrastra una foto de un documento antes de extraer los campos.')
      return
    }

    setIsProcessing(true)
    setErrorMessage('')

    try {
      const formData = new FormData()
      formData.append('file', targetFile)

      const response = await fetch('/api/ocr', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        let detail = `Error HTTP ${response.status}`
        try {
          const errJson = await response.json()
          if (errJson.detail) detail = errJson.detail
        } catch {
          // Ignorar fallo de parseo JSON
        }
        throw new Error(detail)
      }

      const data = await response.json()
      setOcrResult(data)
      hydrateFromOcrData(data)
      setBackendOnline(true)
    } catch (err) {
      setErrorMessage(
        err.message || 'No fue posible procesar el documento con el servicio EasyOCR.',
      )
    } finally {
      setIsProcessing(false)
    }
  }

  const handleFormSubmit = async (event) => {
    event.preventDefault()
    await runEasyOcrOnFile(selectedFile)
  }

  const handleLoadSample = async () => {
    const blob = await generateSampleDocumentBlob()
    if (!blob) return
    const sampleFile = new File([blob], 'inspeccion_neumaticos_ot842.png', {
      type: 'image/png',
    })
    selectDocumentFile(sampleFile)
    await runEasyOcrOnFile(sampleFile)
  }

  const toggleBlockSelection = (blockId) => {
    setShowOverlay(true)
    setSelectedBlockIds((prev) =>
      prev.includes(blockId) ? prev.filter((id) => id !== blockId) : [...prev, blockId],
    )
  }

  const handleSortSelectionReadingOrder = () => {
    const sorted = sortBlocksReadingOrder(selectedBlocks)
    setSelectedBlockIds(sorted.map((b) => b.id))
  }

  // Permite arrastrar un rectángulo en el SVG para seleccionar varias cajas a la vez
  const getSvgCoords = (clientX, clientY) => {
    const svgEl = svgOverlayRef.current
    if (!svgEl || !ocrResult?.image_size) return null
    const rect = svgEl.getBoundingClientRect()
    if (!rect.width || !rect.height) return null
    const scaleX = ocrResult.image_size.width / rect.width
    const scaleY = ocrResult.image_size.height / rect.height
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    }
  }

  const handleSvgMouseDown = (event) => {
    if (event.button !== 0) return
    const pt = getSvgCoords(event.clientX, event.clientY)
    if (!pt) return
    setMarquee({
      startX: pt.x,
      startY: pt.y,
      currentX: pt.x,
      currentY: pt.y,
    })
  }

  const handleSvgMouseMove = (event) => {
    if (!marquee) return
    const pt = getSvgCoords(event.clientX, event.clientY)
    if (!pt) return
    setMarquee((prev) => (prev ? { ...prev, currentX: pt.x, currentY: pt.y } : null))
  }

  const handleSvgMouseUp = () => {
    if (!marquee) return
    const minX = Math.min(marquee.startX, marquee.currentX)
    const maxX = Math.max(marquee.startX, marquee.currentX)
    const minY = Math.min(marquee.startY, marquee.currentY)
    const maxY = Math.max(marquee.startY, marquee.currentY)
    const width = maxX - minX
    const height = maxY - minY

    setMarquee(null)

    // Solo activar selección por área si el usuario arrastró un rectángulo perceptible
    if (width > 12 || height > 12) {
      suppressNextSvgClickRef.current = true
      const enclosed = activeBlocks.filter((block) => {
        const b = getBboxBounds(block.bbox)
        const overlapsX = b.minX <= maxX && b.maxX >= minX
        const overlapsY = b.minY <= maxY && b.maxY >= minY
        return overlapsX && overlapsY
      })
      if (enclosed.length > 0) {
        const ordered = sortBlocksReadingOrder(enclosed)
        setSelectedBlockIds((prev) => {
          const next = new Set(prev)
          for (const blk of ordered) next.add(blk.id)
          return Array.from(next)
        })
      }
    }
  }

  // Fusiona las cajas seleccionadas en una sola caja gráfica y actualiza el campo correspondiente
  const handleMergeSelectedBlocks = () => {
    if (selectedBlocks.length === 0) return

    const mergedBbox = mergeBboxList(selectedBlocks.map((b) => b.bbox))
    const avgConfidence =
      selectedBlocks.reduce((acc, b) => acc + (b.confidence ?? 1), 0) / selectedBlocks.length
    const finalLabel = (effectiveFusionLabel || 'Campo fusionado').trim()
    const finalValue = effectiveFusionValue.trim()
    const combinedRawText = `${finalLabel}: ${finalValue}`

    const selectedSet = new Set(selectedBlockIds)
    const newBlockId =
      selectedBlocks.length === 1 && !selectedBlocks[0].isMerged
        ? selectedBlocks[0].id
        : `block-merged-${Date.now()}`

    const originalAtomicBlocks = selectedBlocks.flatMap((b) =>
      Array.isArray(b.mergedFrom) && b.mergedFrom.length ? b.mergedFrom : [b],
    )

    const mergedBlock = {
      id: newBlockId,
      text: combinedRawText,
      confidence: Number(avgConfidence.toFixed(4)),
      bbox: mergedBbox,
      isMerged: selectedBlocks.length > 1 || Boolean(selectedBlocks[0]?.isMerged),
      mergedFrom: originalAtomicBlocks,
    }

    // Reemplazar los bloques seleccionados por la nueva caja fusionada en la posición del primero
    setActiveBlocks((prev) => {
      const next = []
      let inserted = false
      for (const blk of prev) {
        if (selectedSet.has(blk.id)) {
          if (!inserted) {
            next.push(mergedBlock)
            inserted = true
          }
        } else {
          next.push(blk)
        }
      }
      if (!inserted) next.push(mergedBlock)
      return next
    })

    // Actualizar o fusionar los campos autodetectados asociados a estas cajas
    let updatedFieldId = null
    setEditableFields((prev) => {
      if (fusionTargetFieldId !== 'auto') {
        updatedFieldId = fusionTargetFieldId
        return prev
          .filter((field) => {
            if (field.id === fusionTargetFieldId) return true
            // Eliminar otros campos cuyos bloques hayan quedado completamente absorbidos
            const bIds = field.block_ids || []
            return !(bIds.length > 0 && bIds.every((id) => selectedSet.has(id)))
          })
          .map((field) =>
            field.id === fusionTargetFieldId
              ? {
                  ...field,
                  label: finalLabel,
                  value: finalValue,
                  confidence: Number(avgConfidence.toFixed(4)),
                  bbox: mergedBbox,
                  block_ids: [newBlockId],
                  isMerged: true,
                }
              : field,
          )
      }

      const matchingIndices = []
      prev.forEach((field, idx) => {
        const hasBlockMatch =
          Array.isArray(field.block_ids) && field.block_ids.some((id) => selectedSet.has(id))
        const hasTextMatch = selectedBlocks.some(
          (b) => field.value && b.text && b.text.includes(field.value),
        )
        if (hasBlockMatch || hasTextMatch) {
          matchingIndices.push(idx)
        }
      })

      if (matchingIndices.length > 0) {
        const primaryIdx = matchingIndices[0]
        const primaryField = prev[primaryIdx]
        updatedFieldId = primaryField.id
        const matchedIndexSet = new Set(matchingIndices)
        const nextFields = []

        prev.forEach((field, idx) => {
          if (idx === primaryIdx) {
            nextFields.push({
              ...primaryField,
              label: finalLabel,
              value: finalValue,
              confidence: Number(avgConfidence.toFixed(4)),
              bbox: mergedBbox,
              block_ids: [newBlockId],
              isMerged: true,
            })
          } else if (!matchedIndexSet.has(idx)) {
            nextFields.push(field)
          }
        })
        return nextFields
      }

      const createdId = `field-merged-${Date.now()}`
      updatedFieldId = createdId
      return [
        ...prev,
        {
          id: createdId,
          label: finalLabel,
          value: finalValue,
          confidence: Number(avgConfidence.toFixed(4)),
          category: 'general',
          bbox: mergedBbox,
          block_ids: [newBlockId],
          isMerged: true,
        },
      ]
    })

    setSelectedBlockIds([])
    setFusionTargetFieldId('auto')
    setActiveTab('campos')
    if (updatedFieldId) {
      setRecentlyUpdatedFieldId(updatedFieldId)
      setTimeout(() => setRecentlyUpdatedFieldId(null), 2200)
    }
  }

  // Separa una caja previamente fusionada de vuelta en sus bloques individuales
  const handleUnmergeBlock = (blockToSplit) => {
    if (!blockToSplit?.mergedFrom?.length) return
    const restoredBlocks = blockToSplit.mergedFrom
    setActiveBlocks((prev) =>
      prev.flatMap((b) => (b.id === blockToSplit.id ? restoredBlocks : [b])),
    )
    setSelectedBlockIds(restoredBlocks.map((b) => b.id))
  }

  const handleResetDetections = () => {
    if (!ocrResult) return
    hydrateFromOcrData(ocrResult)
  }

  const handleSelectFieldOnCanvas = (field) => {
    setShowOverlay(true)
    if (Array.isArray(field.block_ids) && field.block_ids.length > 0) {
      const existingIds = new Set(activeBlocks.map((b) => b.id))
      const validIds = field.block_ids.filter((id) => existingIds.has(id))
      if (validIds.length > 0) {
        setSelectedBlockIds(validIds)
        setFusionTargetFieldId(field.id)
        return
      }
    }
    const matching = activeBlocks.filter(
      (b) => field.value && b.text && b.text.includes(field.value),
    )
    if (matching.length > 0) {
      setSelectedBlockIds(matching.map((b) => b.id))
      setFusionTargetFieldId(field.id)
    }
  }

  const handleFieldChange = (id, newValue) => {
    setEditableFields((prev) =>
      prev.map((field) => (field.id === id ? { ...field, value: newValue } : field)),
    )
  }

  const handleFieldLabelChange = (id, newLabel) => {
    setEditableFields((prev) =>
      prev.map((field) => (field.id === id ? { ...field, label: newLabel } : field)),
    )
  }

  const handleDeleteField = (id) => {
    setEditableFields((prev) => prev.filter((field) => field.id !== id))
  }

  const handleAddField = () => {
    const nextIdx = editableFields.length + 1
    setEditableFields((prev) => [
      ...prev,
      {
        id: `field-custom-${Date.now()}`,
        label: `Campo ${nextIdx}`,
        value: '',
        confidence: 1.0,
        category: 'general',
        bbox: null,
        block_ids: [],
      },
    ])
  }

  const copyToClipboard = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(''), 1800)
    } catch {
      // Ignorar si el navegador bloquea el portapapeles
    }
  }

  const handleExportJson = () => {
    const payload = {
      documento: ocrResult?.filename || selectedFile?.name || 'documento',
      fecha_procesamiento: new Date().toISOString(),
      campos: Object.fromEntries(editableFields.map((f) => [f.label, f.value])),
      campos_detalle: editableFields,
      texto_completo: ocrResult?.raw_text || '',
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `campos_documento_${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleIngestToSystem = async () => {
    if (!editableFields.length) {
      setIngestError('No hay campos configurados para ingresar al sistema.')
      return
    }

    setIsSavingToSystem(true)
    setIngestError('')
    setIngestResult(null)

    const payload = {
      documento: ocrResult?.filename || selectedFile?.name || 'documento_ocr',
      campos: editableFields
        .filter((f) => f.label && f.label.trim())
        .map((f) => ({
          label: f.label.trim(),
          value: String(f.value ?? '').trim(),
          category: f.category || 'general',
        })),
    }

    try {
      const response = await fetch('/backend-api/data/measurements', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        let detail = `Error HTTP ${response.status}`
        try {
          const errJson = await response.json()
          if (typeof errJson.detail === 'string') {
            detail = errJson.detail
          } else if (Array.isArray(errJson.detail)) {
            detail = errJson.detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
          }
        } catch {
          // Ignorar fallo de parseo JSON
        }
        throw new Error(detail)
      }

      const data = await response.json()
      setIngestResult(data)
      setSystemApiOnline(true)
    } catch (err) {
      setIngestError(
        err.message ||
          'No fue posible comunicarse con la API Backend para guardar las mediciones.',
      )
    } finally {
      setIsSavingToSystem(false)
    }
  }

  const handleClearAll = () => {
    setSelectedFile(null)
    setPreviewUrl('')
    setOcrResult(null)
    setActiveBlocks([])
    setEditableFields([])
    setSelectedBlockIds([])
    setErrorMessage('')
    setIngestResult(null)
    setIngestError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const hasCustomModifications = useMemo(() => {
    return (
      activeBlocks.some((b) => b.isMerged) ||
      editableFields.some((f) => f.isMerged)
    )
  }, [activeBlocks, editableFields])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <Logo />
          <div className="breadcrumb">
            WhatsAPI <span>/</span> <strong>Extractor de Documentos</strong>
          </div>
        </div>
        <div className="top-actions">
          <span className={`status-pill ${backendOnline ? 'green' : 'red'}`}>
            <i />
            {backendOnline ? 'Sistema OCR Listo' : 'OCR desconectado'}
          </span>
          <span className={`status-pill ${systemApiOnline ? 'green' : 'red'}`}>
            <i />
            {systemApiOnline ? 'API Sistema Conectada' : 'API Sistema desconectada'}
          </span>
        </div>
      </header>

      <main className="content">
        <section className="welcome-row">
          <div>
            <p className="eyebrow">Digitalización de Documentos</p>
            <h1>Extracción de Datos.</h1>
            <p className="subtitle">
              Sube una foto de una orden de trabajo, guía de despacho o factura para extraer sus
              datos y haz clic sobre las cajas de la imagen para fusionarlas o ajustar campos.
            </p>
          </div>
          <div className="welcome-actions">
            <button
              type="button"
              className="outline-button"
              onClick={handleLoadSample}
              disabled={isProcessing}
            >
              <Sparkles size={16} /> Probar con documento de ejemplo
            </button>
            {editableFields.length > 0 && (
              <button
                type="button"
                className="outline-button"
                onClick={handleExportJson}
              >
                <Download size={16} /> Exportar JSON
              </button>
            )}
          </div>
        </section>

        <div className="ocr-grid">
          {/* Panel izquierdo: selección de archivo, lienzo interactivo de cajas y barra de fusión */}
          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Entrada e Interacción Gráfica</p>
                <h2>Fotografía del documento</h2>
              </div>
              {ocrResult && previewUrl && (
                <div className="heading-actions">
                  {hasCustomModifications && (
                    <button
                      type="button"
                      className="outline-button compact"
                      onClick={handleResetDetections}
                      title="Restaurar cajas y campos originales"
                    >
                      <RotateCcw size={14} /> Restaurar original
                    </button>
                  )}
                  <button
                    type="button"
                    className="outline-button compact"
                    onClick={() => setShowOverlay((v) => !v)}
                  >
                    {showOverlay ? <EyeOff size={15} /> : <Eye size={15} />}
                    {showOverlay ? 'Ocultar cajas' : 'Mostrar cajas'}
                  </button>
                </div>
              )}
            </div>

            <form
              method="POST"
              action="/api/ocr"
              encType="multipart/form-data"
              onSubmit={handleFormSubmit}
            >
              <fieldset className="ocr-fieldset">
                <legend className="visually-hidden">Subir fotografía del documento</legend>
                <input
                  ref={fileInputRef}
                  id={fileInputId}
                  name="file"
                  type="file"
                  accept="image/*"
                  className="visually-hidden"
                  aria-describedby={`${fileInputId}-help`}
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      selectDocumentFile(file)
                      runEasyOcrOnFile(file)
                    }
                  }}
                />

                {!selectedFile ? (
                  <label
                    htmlFor={fileInputId}
                    className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setIsDragging(true)
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={(e) => {
                      e.preventDefault()
                      setIsDragging(false)
                      const file = e.dataTransfer.files?.[0]
                      if (file) {
                        selectDocumentFile(file)
                        runEasyOcrOnFile(file)
                      }
                    }}
                  >
                    <div className="dropzone-icon">
                      <Upload size={22} />
                    </div>
                    <strong>Haz clic o arrastra la foto del documento aquí</strong>
                    <span id={`${fileInputId}-help`}>
                      Formatos compatibles: PNG, JPG, JPEG o WEBP.
                    </span>
                  </label>
                ) : (
                  <div className="selected-file-bar">
                    <div className="selected-file-info">
                      <div className="file-icon-badge">
                        <ImageIcon size={18} />
                      </div>
                      <div className="file-text-details">
                        <strong>{selectedFile.name}</strong>
                        <span>
                          {(selectedFile.size / 1024).toFixed(1)} KB
                          {ocrResult?.image_size &&
                            ` · ${ocrResult.image_size.width} × ${ocrResult.image_size.height} px`}
                        </span>
                      </div>
                    </div>
                    <div className="selected-file-actions">
                      <label htmlFor={fileInputId} className="outline-button compact">
                        Cambiar foto
                      </label>
                      <button
                        type="button"
                        className="icon-action-btn"
                        title="Quitar foto"
                        aria-label="Quitar foto"
                        onClick={handleClearAll}
                        disabled={isProcessing}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                )}

                {selectedFile && !ocrResult && (
                  <div className="upload-actions">
                    <button
                      type="submit"
                      className="primary-button"
                      disabled={isProcessing}
                    >
                      {isProcessing ? (
                        <>
                          <RefreshCw size={16} className="spin" /> Leyendo documento...
                        </>
                      ) : (
                        <>
                          <ScanText size={16} /> Extraer datos del documento
                        </>
                      )}
                    </button>
                  </div>
                )}
              </fieldset>
            </form>

            {errorMessage && (
              <div className="alert-banner" role="alert" aria-live="polite">
                <AlertCircle size={18} />
                <span>{errorMessage}</span>
              </div>
            )}

            {ocrResult && previewUrl && (
              <div className="canvas-instructions">
                <Combine size={15} />
                <span>
                  Haz clic en dos o más cajas sobre el documento (o arrastra un área) para{' '}
                  <strong>fusionarlas</strong> en un mismo campo.
                </span>
              </div>
            )}

            {/* Barra de fusión gráfica cuando el usuario selecciona cajas en la imagen */}
            {selectedBlocks.length > 0 && (
              <div className="fusion-panel" role="region" aria-label="Herramienta de fusión de cajas">
                <div className="fusion-header">
                  <div className="fusion-title">
                    <span className="fusion-count-badge">
                      {selectedBlocks.length}{' '}
                      {selectedBlocks.length === 1 ? 'caja seleccionada' : 'cajas seleccionadas'}
                    </span>
                    {selectedBlocks.length >= 2 && (
                      <button
                        type="button"
                        className="outline-button compact"
                        onClick={handleSortSelectionReadingOrder}
                        title="Ordenar de arriba a abajo y de izquierda a derecha"
                      >
                        <ArrowUpDown size={13} /> Orden de lectura
                      </button>
                    )}
                    {selectedBlocks.length === 1 && selectedBlocks[0].isMerged && (
                      <button
                        type="button"
                        className="outline-button compact"
                        onClick={() => handleUnmergeBlock(selectedBlocks[0])}
                      >
                        <Unlink size={13} /> Separar cajas originales
                      </button>
                    )}
                  </div>
                  <button
                    type="button"
                    className="icon-action-btn compact"
                    aria-label="Cancelar selección de cajas"
                    title="Limpiar selección"
                    onClick={() => setSelectedBlockIds([])}
                  >
                    <X size={15} />
                  </button>
                </div>

                <div className="fusion-chips" role="list">
                  {selectedBlocks.map((blk, idx) => (
                    <span key={blk.id} className="fusion-chip" role="listitem">
                      <b>{idx + 1}</b>
                      <span>{blk.text}</span>
                      <button
                        type="button"
                        aria-label={`Quitar caja ${blk.text} de la selección`}
                        onClick={() => toggleBlockSelection(blk.id)}
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>

                {selectedBlocks.length >= 2 && (
                  <div className="fusion-mode-row">
                    <button
                      type="button"
                      className={`mode-pill ${fusionMode === 'auto' ? 'active' : ''}`}
                      aria-pressed={fusionMode === 'auto'}
                      onClick={() => setFusionMode('auto')}
                    >
                      Separar clave y valor automático
                    </button>
                    <button
                      type="button"
                      className={`mode-pill ${fusionMode === 'first-as-label' ? 'active' : ''}`}
                      aria-pressed={fusionMode === 'first-as-label'}
                      onClick={() => setFusionMode('first-as-label')}
                    >
                      1ª caja = Nombre · resto = Valor
                    </button>
                    <button
                      type="button"
                      className={`mode-pill ${fusionMode === 'all-value' ? 'active' : ''}`}
                      aria-pressed={fusionMode === 'all-value'}
                      onClick={() => setFusionMode('all-value')}
                    >
                      Unir todo en el Valor
                    </button>
                  </div>
                )}

                <div className="fusion-inputs-grid">
                  <div className="fusion-field">
                    <label htmlFor={fusionTargetId}>Campo de destino</label>
                    <select
                      id={fusionTargetId}
                      name="fusion_target"
                      className="field-select"
                      value={fusionTargetFieldId}
                      onChange={(e) => setFusionTargetFieldId(e.target.value)}
                    >
                      <option value="auto">
                        {linkedFieldsForSelection.length > 0
                          ? `Reemplazar campo detectado (${linkedFieldsForSelection.map((f) => f.label).join(', ')})`
                          : 'Crear nuevo campo con estas cajas'}
                      </option>
                      {editableFields.map((field) => (
                        <option key={field.id} value={field.id}>
                          Asignar a: {field.label} ({field.value || 'vacío'})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="fusion-field">
                    <label htmlFor={fusionLabelId}>Nombre del campo</label>
                    <input
                      id={fusionLabelId}
                      name="fusion_label"
                      type="text"
                      className="field-input compact"
                      value={effectiveFusionLabel}
                      onChange={(e) =>
                        setFusionOverrides((prev) => ({
                          key: selectionKey,
                          label: e.target.value,
                          value: prev.key === selectionKey ? prev.value : null,
                        }))
                      }
                    />
                  </div>

                  <div className="fusion-field full-width">
                    <label htmlFor={fusionValueId}>Valor resultante</label>
                    <input
                      id={fusionValueId}
                      name="fusion_value"
                      type="text"
                      className="field-input compact"
                      value={effectiveFusionValue}
                      onChange={(e) =>
                        setFusionOverrides((prev) => ({
                          key: selectionKey,
                          label: prev.key === selectionKey ? prev.label : null,
                          value: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>

                <div className="fusion-footer">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleMergeSelectedBlocks}
                  >
                    <Combine size={16} />
                    {selectedBlocks.length >= 2
                      ? `Fusionar ${selectedBlocks.length} cajas y actualizar campo`
                      : 'Actualizar campo desde esta caja'}
                  </button>
                </div>
              </div>
            )}

            {previewUrl && (
              <div className="preview-container">
                <div className="preview-stage">
                  <img src={previewUrl} alt="Vista previa del documento" draggable={false} />
                  {showOverlay && ocrResult?.image_size && (
                    <svg
                      ref={svgOverlayRef}
                      className="bbox-overlay interactive"
                      viewBox={`0 0 ${ocrResult.image_size.width} ${ocrResult.image_size.height}`}
                      preserveAspectRatio="none"
                      onMouseDown={handleSvgMouseDown}
                      onMouseMove={handleSvgMouseMove}
                      onMouseUp={handleSvgMouseUp}
                    >
                      {activeBlocks.map((block) => {
                        const points = block.bbox.map((pt) => `${pt[0]},${pt[1]}`).join(' ')
                        const selectedIdx = selectedBlockIds.indexOf(block.id)
                        const isSelected = selectedIdx !== -1
                        const isHovered = hoveredBoxIds.includes(block.id)
                        const bounds = getBboxBounds(block.bbox)

                        return (
                          <g
                            key={block.id}
                            role="button"
                            tabIndex={0}
                            aria-pressed={isSelected}
                            aria-label={`Caja de texto: ${block.text}`}
                            className="bbox-group"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (suppressNextSvgClickRef.current) {
                                suppressNextSvgClickRef.current = false
                                return
                              }
                              toggleBlockSelection(block.id)
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault()
                                toggleBlockSelection(block.id)
                              } else if (e.key === ' ') {
                                e.preventDefault()
                              }
                            }}
                            onKeyUp={(e) => {
                              if (e.key === ' ') {
                                e.preventDefault()
                                toggleBlockSelection(block.id)
                              }
                            }}
                            onMouseEnter={() => setHoveredBoxIds([block.id])}
                            onMouseLeave={() => setHoveredBoxIds([])}
                          >
                            <title>{`${block.text} (Haz clic para seleccionar/fusionar)`}</title>
                            <polygon
                              points={points}
                              className={[
                                'bbox-polygon',
                                isHovered ? 'active' : '',
                                isSelected ? 'selected' : '',
                                block.isMerged ? 'merged' : '',
                              ]
                                .filter(Boolean)
                                .join(' ')}
                            />
                            {isSelected && (
                              <g className="bbox-order-badge">
                                <rect
                                  x={Math.max(2, bounds.minX)}
                                  y={Math.max(2, bounds.minY - 22)}
                                  width={24}
                                  height={20}
                                  rx={4}
                                />
                                <text
                                  x={Math.max(2, bounds.minX) + 12}
                                  y={Math.max(2, bounds.minY - 22) + 14}
                                  textAnchor="middle"
                                >
                                  {selectedIdx + 1}
                                </text>
                              </g>
                            )}
                          </g>
                        )
                      })}

                      {marquee && (
                        <rect
                          className="marquee-rect"
                          x={Math.min(marquee.startX, marquee.currentX)}
                          y={Math.min(marquee.startY, marquee.currentY)}
                          width={Math.abs(marquee.currentX - marquee.startX)}
                          height={Math.abs(marquee.currentY - marquee.startY)}
                        />
                      )}
                    </svg>
                  )}
                </div>
              </div>
            )}
          </section>

          {/* Panel derecho: campos detectados y texto completo */}
          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Resultados</p>
                <h2>Datos extraídos</h2>
              </div>
              {editableFields.length > 0 && activeTab === 'campos' && (
                <div className="heading-actions">
                  <button
                    type="button"
                    className="outline-button"
                    onClick={handleAddField}
                    disabled={isSavingToSystem}
                  >
                    <Plus size={15} /> Agregar campo
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleIngestToSystem}
                    disabled={isSavingToSystem}
                  >
                    {isSavingToSystem ? (
                      <>
                        <RefreshCw size={15} className="spin" /> Guardando...
                      </>
                    ) : (
                      <>
                        <Database size={15} /> Ingresar datos al sistema
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {ingestError && (
              <div className="alert-banner ingest-alert" role="alert" aria-live="polite">
                <AlertCircle size={18} />
                <span>{ingestError}</span>
              </div>
            )}

            {ingestResult && (
              <div className="ingest-success-card" role="status" aria-live="polite">
                <div className="ingest-success-header">
                  <div className="ingest-success-title">
                    <CheckCircle2 size={18} />
                    <strong>{ingestResult.message}</strong>
                  </div>
                  <button
                    type="button"
                    className="icon-action-btn compact"
                    aria-label="Cerrar notificación de registro"
                    onClick={() => setIngestResult(null)}
                  >
                    <X size={14} />
                  </button>
                </div>
                <div className="ingest-badges">
                  <span className="ingest-badge">
                    Vehículo: <b>{ingestResult.patente}</b>{' '}
                    {ingestResult.vehiculo_creado ? '(Nuevo)' : '(Actualizado)'}
                  </span>
                  <span className="ingest-badge">
                    Empresa: <b>{ingestResult.empresa}</b>
                  </span>
                  {ingestResult.id_viaje && (
                    <span className="ingest-badge">
                      Viaje registrado: <b>#{ingestResult.id_viaje}</b>
                    </span>
                  )}
                  {ingestResult.id_neumatico && (
                    <span className="ingest-badge">
                      Medición neumático: <b>#{ingestResult.id_neumatico}</b>
                    </span>
                  )}
                  {ingestResult.conductor_nombre && (
                    <span className="ingest-badge">
                      Conductor: <b>{ingestResult.conductor_nombre}</b>
                    </span>
                  )}
                </div>
              </div>
            )}

            <div className="tabs-bar" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'campos'}
                className={`tab-btn ${activeTab === 'campos' ? 'active' : ''}`}
                onClick={() => setActiveTab('campos')}
              >
                Campos del documento
                <span className="tab-badge">{editableFields.length}</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'texto'}
                className={`tab-btn ${activeTab === 'texto' ? 'active' : ''}`}
                onClick={() => setActiveTab('texto')}
              >
                Texto completo
              </button>
            </div>

            {!ocrResult && !isProcessing ? (
              <div className="empty-state">
                <div className="dropzone-icon">
                  <ScanText size={22} />
                </div>
                <strong>Esperando documento</strong>
                <p>
                  Sube una foto o haz clic en &ldquo;Probar con documento de ejemplo&rdquo; para
                  extraer sus datos.
                </p>
              </div>
            ) : isProcessing ? (
              <div className="empty-state" aria-live="polite">
                <div className="dropzone-icon">
                  <RefreshCw size={22} className="spin" />
                </div>
                <strong>Procesando documento...</strong>
                <p>Extrayendo texto y organizando los campos de la imagen.</p>
              </div>
            ) : activeTab === 'campos' ? (
              <form
                className="fields-form"
                onSubmit={(e) => {
                  e.preventDefault()
                  handleIngestToSystem()
                }}
              >
                <fieldset className="ocr-fieldset" disabled={isSavingToSystem}>
                  <legend className="visually-hidden">Campos extraídos del documento</legend>
                  {editableFields.length === 0 ? (
                    <div className="empty-state">
                      <p>No se encontraron campos estructurados en este documento.</p>
                      <button
                        type="button"
                        className="outline-button"
                        onClick={handleAddField}
                      >
                        <Plus size={15} /> Agregar campo manualmente
                      </button>
                    </div>
                  ) : (
                    <>
                      {editableFields.map((field) => {
                        const inputId = `ocr-input-${field.id}`
                        const labelInputId = `ocr-label-${field.id}`
                        const isIdentifier = IDENTIFIER_CATEGORIES.has(field.category)
                        const isFieldHoveredFromCanvas =
                          Array.isArray(field.block_ids) &&
                          field.block_ids.some(
                            (bid) => hoveredBoxIds.includes(bid) || selectedBlockIds.includes(bid),
                          )

                        return (
                          <div
                            key={field.id}
                            className={[
                              'form-group',
                              isFieldHoveredFromCanvas ? 'highlighted' : '',
                              recentlyUpdatedFieldId === field.id ? 'just-merged' : '',
                            ]
                              .filter(Boolean)
                              .join(' ')}
                            onMouseEnter={() => {
                              if (Array.isArray(field.block_ids) && field.block_ids.length > 0) {
                                setHoveredBoxIds(field.block_ids)
                              } else if (field.bbox && activeBlocks.length) {
                                const matching = activeBlocks
                                  .filter((b) => field.value && b.text.includes(field.value))
                                  .map((b) => b.id)
                                setHoveredBoxIds(matching)
                              }
                            }}
                            onMouseLeave={() => setHoveredBoxIds([])}
                          >
                            <div className="field-header">
                              <label htmlFor={inputId} className="visually-hidden">
                                {field.label}
                              </label>
                              <input
                                id={labelInputId}
                                type="text"
                                className="field-label-input"
                                value={field.label}
                                aria-label={`Nombre del campo: ${field.label}`}
                                onChange={(e) => handleFieldLabelChange(field.id, e.target.value)}
                              />
                              {field.isMerged && (
                                <span className="merged-pill">
                                  <Combine size={11} /> Fusionado
                                </span>
                              )}
                            </div>
                            <div className="field-input-row">
                              <input
                                id={inputId}
                                name={field.label}
                                type="text"
                                className="field-input"
                                value={field.value}
                                autoCorrect={isIdentifier ? 'off' : 'on'}
                                autoCapitalize={isIdentifier ? 'off' : 'sentences'}
                                spellCheck={!isIdentifier}
                                onChange={(e) => handleFieldChange(field.id, e.target.value)}
                                aria-label={field.label}
                              />
                              {ocrResult && (
                                <button
                                  type="button"
                                  className="icon-action-btn"
                                  title="Seleccionar en la imagen para fusionar con otra caja"
                                  aria-label={`Seleccionar ${field.label} en la imagen para fusionar`}
                                  onClick={() => handleSelectFieldOnCanvas(field)}
                                >
                                  <Crosshair size={16} />
                                </button>
                              )}
                              <button
                                type="button"
                                className="icon-action-btn"
                                title="Copiar valor"
                                aria-label={`Copiar ${field.label}`}
                                onClick={() => copyToClipboard(field.value, field.id)}
                              >
                                {copiedKey === field.id ? <Check size={16} /> : <Copy size={16} />}
                              </button>
                              <button
                                type="button"
                                className="icon-action-btn"
                                title="Eliminar campo"
                                aria-label={`Eliminar ${field.label}`}
                                onClick={() => handleDeleteField(field.id)}
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </div>
                        )
                      })}

                      <div className="ingest-submit-footer">
                        <div className="ingest-submit-hint">
                          Verifica que el campo <strong>Patente</strong> y las mediciones estén
                          correctas antes de guardar en la base de datos.
                        </div>
                        <button
                          type="submit"
                          className="primary-button ingest-submit-btn"
                          disabled={isSavingToSystem}
                        >
                          {isSavingToSystem ? (
                            <>
                              <RefreshCw size={16} className="spin" /> Ingresando mediciones a la
                              base de datos...
                            </>
                          ) : (
                            <>
                              <Database size={16} /> Ingresar datos al sistema
                            </>
                          )}
                        </button>
                      </div>
                    </>
                  )}
                </fieldset>
              </form>
            ) : (
              <div className="raw-textarea-group">
                <div className="field-header">
                  <label htmlFor={rawTextId}>Texto detectado en el documento</label>
                  <button
                    type="button"
                    className="outline-button"
                    onClick={() => copyToClipboard(ocrResult?.raw_text || '', 'raw')}
                  >
                    {copiedKey === 'raw' ? <Check size={14} /> : <Copy size={14} />}
                    {copiedKey === 'raw' ? 'Copiado' : 'Copiar todo'}
                  </button>
                </div>
                <textarea
                  id={rawTextId}
                  name="raw_text"
                  className="raw-textarea"
                  readOnly
                  value={ocrResult?.raw_text || ''}
                />
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="app-footer">
        <span>
          LlachMetrics <b>Extractor de Documentos</b>
        </span>
        <span>Reconocimiento óptico inteligente</span>
      </footer>
    </div>
  )
}
