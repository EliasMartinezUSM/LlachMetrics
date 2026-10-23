"""Servicio FastAPI con EasyOCR para extracción de texto y campos de documentos."""

from __future__ import annotations

import io
import logging
from pathlib import Path
import re
from typing import Any

import easyocr
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / ".easyocr_models"
USER_NETWORK_DIR = MODEL_DIR / "user_network"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
USER_NETWORK_DIR.mkdir(parents=True, exist_ok=True)

_reader: easyocr.Reader | None = None


def get_ocr_reader() -> easyocr.Reader:
    """Inicializa y mantiene en memoria el lector de EasyOCR (español e inglés)."""
    global _reader
    if _reader is None:
        logger.info("Cargando modelos de EasyOCR (es, en)...")
        _reader = easyocr.Reader(
            ["es", "en"],
            gpu=False,
            model_storage_directory=str(MODEL_DIR),
            user_network_directory=str(USER_NETWORK_DIR),
            verbose=False,
        )
    return _reader


app = FastAPI(
    title="LlachMetrics WhatsAPI — EasyOCR",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


KNOWN_LABELS: list[tuple[str, str, str]] = [
    (r"^empresa\b|^raz[oó]n\s+social\b|^compa[ñn][ií]a\b", "Empresa", "empresa"),
    (r"^rut\b|^r\.u\.t\.?\b|^run\b|^dni\b|^id\s*fiscal\b", "RUT / Identificación", "identificacion"),
    (r"^folio\b|^n[°ºo]\s*(?:de\s*)?(?:doc(?:umento)?|gu[ií]a|factura|orden|ot)\b|^gu[ií]a\b|^factura\b|^orden\s+de\s+trabajo\b", "N° Documento / Folio", "documento"),
    (r"^fecha(?:\s+de)?(?:\s+emisi[oó]n|\s+inspecci[oó]n|\s+viaje)?\b", "Fecha", "fecha"),
    (r"^patente\b|^placa\b|^veh[ií]culo\b|^cami[oó]n\b|^tracto\b", "Patente / Vehículo", "vehiculo"),
    (r"^modelo\b|^marca\b", "Modelo", "vehiculo"),
    (r"^conductor\b|^chofer\b|^operador\b|^responsable\b|^inspector\b|^nombre(?:\s+completo)?\b", "Conductor / Responsable", "persona"),
    (r"^kilometraje\b|^kil[oó]metros\b|^od[oó]metro\b|^distancia\b|^km\s+actual\b", "Kilometraje", "metrica"),
    (r"^presi[oó]n\s+inici(?:o|al)\b|^presi[oó]n\s+fr[ií]o\b", "Presión Inicial", "neumatico"),
    (r"^presi[oó]n\s+final\b|^presi[oó]n\s+caliente\b", "Presión Final", "neumatico"),
    (r"^presi[oó]n(?:\s+promedio|\s+neum[aá]ticos?)?\b", "Presión", "neumatico"),
    (r"^profundidad(?:\s+de)?(?:\s+surcos?)?\b|^surcos?\b|^remanente\b", "Profundidad de Surcos", "neumatico"),
    (r"^serie(?:\s+neum[aá]tico)?\b|^n[°ºo]\s*serie\b", "Serie Neumático", "neumatico"),
    (r"^id\s+interno\b|^c[oó]digo\s+interno\b", "ID Interno", "neumatico"),
    (r"^eje\b|^posici[oó]n\b|^ubicaci[oó]n\b", "Eje / Posición", "neumatico"),
    (r"^recauchajes?\b|^n[°ºo]\s*recauchajes?\b", "Recauchajes", "neumatico"),
    (r"^agrietado\b|^grietas\b|^estado\s+banda\b", "Estado / Grietas", "neumatico"),
    (r"^direcci[oó]n\b|^origen\b|^destino\b|^ruta\b|^ciudad\b|^comuna\b", "Dirección / Ruta", "ubicacion"),
    (r"^tel[eé]fono\b|^celular\b|^contacto\b", "Teléfono", "contacto"),
    (r"^correo\b|^email\b|^e-mail\b", "Correo Electrónico", "contacto"),
    (r"^subtotal\b|^neto\b|^monto\s+neto\b", "Monto Neto", "finanzas"),
    (r"^i\.?v\.?a\.?\b|^impuesto\b", "IVA", "finanzas"),
    (r"^costo(?:\s+total)?\b|^total(?:\s+a\s+pagar)?\b|^monto\s+total\b|^valor\b", "Costo / Total", "finanzas"),
    (r"^estado\b|^resultado\b|^recomendaci[oó]n\b|^observaci[oó]n(?:es)?\b|^notas?\b", "Estado / Observaciones", "estado"),
]


def _classify_label(raw_label: str) -> tuple[str, str]:
    cleaned = raw_label.strip(" :.-_#").strip()
    lowered = cleaned.lower()
    for pattern, canonical, category in KNOWN_LABELS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return canonical, category
    # Capitalizar etiqueta original si no coincide con un patrón fijo
    formatted = cleaned[:1].upper() + cleaned[1:] if cleaned else "Campo"
    return formatted, "general"


def _bbox_metrics(bbox: list[list[float]]) -> dict[str, float]:
    xs = [pt[0] for pt in bbox]
    ys = [pt[1] for pt in bbox]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "center_y": (min_y + max_y) / 2.0,
        "height": max(1.0, max_y - min_y),
    }


def _merge_bboxes(b1: list[list[float]], b2: list[list[float]]) -> list[list[float]]:
    xs = [pt[0] for pt in b1] + [pt[0] for pt in b2]
    ys = [pt[1] for pt in b1] + [pt[1] for pt in b2]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return [
        [min_x, min_y],
        [max_x, min_y],
        [max_x, max_y],
        [min_x, max_y],
    ]


def _group_blocks_into_lines(blocks: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Agrupa bloques detectados por EasyOCR que pertenecen a la misma línea horizontal."""
    if not blocks:
        return []

    enriched = []
    for block in blocks:
        metrics = _bbox_metrics(block["bbox"])
        enriched.append({**block, "_m": metrics})

    enriched.sort(key=lambda b: (b["_m"]["center_y"], b["_m"]["min_x"]))

    lines: list[list[dict[str, Any]]] = []
    for item in enriched:
        placed = False
        for line in lines:
            avg_cy = sum(x["_m"]["center_y"] for x in line) / len(line)
            avg_h = sum(x["_m"]["height"] for x in line) / len(line)
            threshold = max(avg_h, item["_m"]["height"]) * 0.55
            if abs(item["_m"]["center_y"] - avg_cy) <= threshold:
                line.append(item)
                placed = True
                break
        if not placed:
            lines.append([item])

    for line in lines:
        line.sort(key=lambda b: b["_m"]["min_x"])

    lines.sort(key=lambda line: sum(x["_m"]["center_y"] for x in line) / len(line))
    return lines


def _extract_fields(blocks: list[dict[str, Any]], grouped_lines: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Extrae pares clave-valor de las líneas y bloques detectados por EasyOCR."""
    fields: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    def add_field(
        raw_label: str,
        raw_value: str,
        confidence: float,
        bbox: list[list[float]],
        override_category: str | None = None,
        block_ids: list[str] | None = None,
    ) -> None:
        val = raw_value.strip(" :.-_|").strip()
        lbl = raw_label.strip(" :.-_|").strip()
        if not val or not lbl or len(val) < 1:
            return
        canonical_label, category = _classify_label(lbl)
        if override_category:
            category = override_category
        display_label = lbl[:1].upper() + lbl[1:] if category == "general" else canonical_label
        dedup_key = (display_label.lower(), val.lower())
        if dedup_key in seen_pairs:
            return
        seen_pairs.add(dedup_key)
        fields.append(
            {
                "id": f"field-{len(fields) + 1}",
                "label": display_label,
                "raw_label": lbl,
                "value": val,
                "confidence": round(float(confidence), 4),
                "category": category,
                "bbox": bbox,
                "block_ids": block_ids or [],
            }
        )

    # 1. Analizar cada bloque individual y cada línea agrupada buscando separadores ':' o '='
    for line in grouped_lines:
        # Primero revisar si dentro de un mismo bloque viene "Etiqueta: Valor"
        consumed_indices: set[int] = set()
        for idx, blk in enumerate(line):
            if idx in consumed_indices:
                continue
            text = blk["text"].strip()
            if ":" in text or "=" in text:
                parts = re.split(r"[:=]", text, maxsplit=1)
                left, right = parts[0].strip(), parts[1].strip()
                if left and right and len(left) <= 42:
                    add_field(left, right, blk["confidence"], blk["bbox"], block_ids=[blk["id"]])
                    consumed_indices.add(idx)
                elif left and not right and idx + 1 < len(line):
                    nxt = line[idx + 1]
                    merged_box = _merge_bboxes(blk["bbox"], nxt["bbox"])
                    avg_conf = (blk["confidence"] + nxt["confidence"]) / 2.0
                    add_field(
                        left,
                        nxt["text"],
                        avg_conf,
                        merged_box,
                        block_ids=[blk["id"], nxt["id"]],
                    )
                    consumed_indices.add(idx)
                    consumed_indices.add(idx + 1)

        # Emparejar bloques adyacentes no consumidos cuando el izquierdo es una etiqueta conocida
        idx = 0
        while idx < len(line) - 1:
            if idx in consumed_indices or (idx + 1) in consumed_indices:
                idx += 1
                continue
            left_blk, right_blk = line[idx], line[idx + 1]
            _, cat = _classify_label(left_blk["text"])
            if cat != "general" or left_blk["text"].strip().endswith(":"):
                merged_box = _merge_bboxes(left_blk["bbox"], right_blk["bbox"])
                avg_conf = (left_blk["confidence"] + right_blk["confidence"]) / 2.0
                add_field(
                    left_blk["text"],
                    right_blk["text"],
                    avg_conf,
                    merged_box,
                    block_ids=[left_blk["id"], right_blk["id"]],
                )
                consumed_indices.add(idx)
                consumed_indices.add(idx + 1)
                idx += 2
            else:
                idx += 1

        # También evaluar la línea completa concatenada si tiene "Clave: Valor"
        if not consumed_indices and len(line) >= 2:
            full_line_text = " ".join(b["text"].strip() for b in line)
            if ":" in full_line_text:
                parts = full_line_text.split(":", 1)
                left, right = parts[0].strip(), parts[1].strip()
                if left and right and len(left) <= 42:
                    line_box = line[0]["bbox"]
                    for b in line[1:]:
                        line_box = _merge_bboxes(line_box, b["bbox"])
                    avg_conf = sum(b["confidence"] for b in line) / len(line)
                    add_field(
                        left,
                        right,
                        avg_conf,
                        line_box,
                        block_ids=[b["id"] for b in line],
                    )

    # 2. Detección por patrones (RUT, Fecha, Patente, Presión PSI, Surcos mm, Kilómetros, Montos)
    existing_categories = {f["category"] for f in fields}
    pattern_detectors = [
        (
            "RUT / Identificación",
            "identificacion",
            r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b",
        ),
        (
            "Fecha",
            "fecha",
            r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{2}[/-]\d{2})\b",
        ),
        (
            "Patente / Vehículo",
            "vehiculo",
            r"\b(?:[BCDFGHJKLMNPRSTVWXYZ]{4}[-\s]?\d{2}|[A-Z]{2}[-\s]?\d{4})\b",
        ),
        (
            "Presión",
            "neumatico",
            r"\b\d{2,3}(?:[.,]\d+)?\s*(?:PSI|psi|Bar|bar)\b",
        ),
        (
            "Profundidad de Surcos",
            "neumatico",
            r"\b\d{1,2}(?:[.,]\d+)?\s*mm\b",
        ),
        (
            "Kilometraje",
            "metrica",
            r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\s*(?:km|KM|Km)\b",
        ),
        (
            "Costo / Total",
            "finanzas",
            r"(?:\$\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\bUSD\s*\d+(?:[.,]\d+)?)",
        ),
    ]

    for label, category, regex in pattern_detectors:
        for blk in blocks:
            match = re.search(regex, blk["text"])
            if match:
                matched_val = match.group(0).strip()
                already_captured = any(matched_val.lower() in f["value"].lower() for f in fields)
                if not already_captured and category not in existing_categories:
                    add_field(
                        label,
                        matched_val,
                        blk["confidence"],
                        blk["bbox"],
                        category,
                        block_ids=[blk["id"]],
                    )

    # 3. Si el documento es de texto libre y no tuvo pares clave-valor explícitos,
    # exponer cada línea detectada como un campo editable para que siempre haya campos útiles.
    if not fields and grouped_lines:
        for idx, line in enumerate(grouped_lines, start=1):
            text_line = " ".join(b["text"].strip() for b in line).strip()
            if not text_line:
                continue
            line_box = line[0]["bbox"]
            for b in line[1:]:
                line_box = _merge_bboxes(line_box, b["bbox"])
            avg_conf = sum(b["confidence"] for b in line) / len(line)
            label = "Título / Encabezado" if idx == 1 else f"Línea {idx}"
            add_field(
                label,
                text_line,
                avg_conf,
                line_box,
                "general",
                block_ids=[b["id"] for b in line],
            )

    return fields


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, Any]:
    """Comprueba que el servidor OCR esté disponible."""
    return {
        "status": "ok",
        "engine": "EasyOCR",
        "languages": ["es", "en"],
        "model_loaded": _reader is not None,
    }


@app.post("/ocr")
@app.post("/api/ocr")
async def process_document_ocr(file: UploadFile = File(...)) -> dict[str, Any]:
    """Recibe una imagen de un documento, ejecuta EasyOCR y devuelve campos y bloques."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Debes adjuntar un archivo de imagen.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")

    try:
        pil_image = Image.open(io.BytesIO(raw_bytes))
        pil_image = ImageOps.exif_transpose(pil_image).convert("RGB")
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="El archivo no es una imagen válida (usa PNG, JPG o WEBP).",
        ) from exc

    width, height = pil_image.size
    image_np = np.array(pil_image)

    try:
        reader = get_ocr_reader()
        detections = reader.readtext(image_np, detail=1, paragraph=False)
    except Exception as exc:
        logger.exception("Error ejecutando EasyOCR")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la imagen con EasyOCR: {exc}",
        ) from exc

    blocks: list[dict[str, Any]] = []
    for idx, (bbox, text, prob) in enumerate(detections, start=1):
        cleaned_text = str(text).strip()
        if not cleaned_text:
            continue
        norm_bbox = [[round(float(pt[0]), 1), round(float(pt[1]), 1)] for pt in bbox]
        blocks.append(
            {
                "id": f"block-{idx}",
                "text": cleaned_text,
                "confidence": round(float(prob), 4),
                "bbox": norm_bbox,
            }
        )

    grouped_lines = _group_blocks_into_lines(blocks)
    lines_text = [
        " ".join(item["text"] for item in line).strip()
        for line in grouped_lines
        if any(item["text"].strip() for item in line)
    ]

    fields = _extract_fields(blocks, grouped_lines)
    avg_conf = (
        round(sum(b["confidence"] for b in blocks) / len(blocks), 4)
        if blocks
        else 0.0
    )

    return {
        "filename": file.filename,
        "image_size": {"width": width, "height": height},
        "engine": "EasyOCR (es, en)",
        "average_confidence": avg_conf,
        "total_blocks": len(blocks),
        "fields": fields,
        "blocks": blocks,
        "lines": lines_text,
        "raw_text": "\n".join(lines_text),
    }
