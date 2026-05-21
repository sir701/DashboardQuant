"""
main.py — Servidor FastAPI
Endpoint único: POST /analyze — acepta CSV, Excel o JSON → devuelve análisis completo en JSON
"""

import io
import json
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from analysis import analizar_dataset

# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DataLab API",
    description="Análisis exploratorio automático de datasets. Mismo motor que el dashboard .qmd.",
    version="1.0.0",
)

# CORS — permite peticiones desde GitHub Pages (y localhost para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.github.io",   # GitHub Pages (cualquier repo)
        "http://localhost:*",    # Desarrollo local
        "http://127.0.0.1:*",
    ],
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# RUTA DE SALUD — útil para que Render no duerma el servicio
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "service": "DataLab API v1.0"}


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Recibe cualquier archivo CSV, Excel (.xlsx/.xls) o JSON.
    Devuelve el análisis completo en formato JSON:
      - meta: filas, columnas, tipos detectados
      - calidad: faltantes y tipos por variable
      - duplicados: conteo
      - variables: estadísticas + gráficos Plotly (JSON string) por columna
      - resumen_numericas: tabla comparativa
      - charts_global: heatmap + treemap (JSON string)
    """
    filename = file.filename or ""
    content  = await file.read()

    # ── Cargar según extensión ────────────────────────────────
    try:
        if filename.endswith(".csv"):
            # Detecta separador automáticamente
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python",
                             encoding="utf-8", on_bad_lines="skip")
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        elif filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        else:
            # Intenta CSV como fallback
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python",
                             encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        raise HTTPException(status_code=422,
                            detail=f"No se pudo leer el archivo '{filename}': {str(e)}")

    if df.empty:
        raise HTTPException(status_code=422, detail="El archivo está vacío.")

    # ── Análisis ──────────────────────────────────────────────
    try:
        resultado = analizar_dataset(df)
        resultado["filename"] = filename
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error durante el análisis: {str(e)}")

    import math, json

def limpiar_json(obj):
    """Reemplaza NaN/Inf por None recursivamente."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: limpiar_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [limpiar_json(v) for v in obj]
    return obj

return JSONResponse(content=limpiar_json(resultado))


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT DE PREVIEW — primeras N filas
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/preview")
async def preview(file: UploadFile = File(...), n: int = 10):
    """Devuelve las primeras n filas del dataset como JSON."""
    filename = file.filename or ""
    content  = await file.read()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python",
                             on_bad_lines="skip")
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        elif filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python",
                             on_bad_lines="skip")
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    rows    = df.head(n).fillna("").astype(str).to_dict(orient="records")
    columns = list(df.columns)
    return {"columns": columns, "rows": rows, "total_rows": len(df)}
