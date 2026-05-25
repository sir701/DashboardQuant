"""
main.py — Servidor FastAPI
"""

import io
import math
import json
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from analisis import analizar_dataset

app = FastAPI(title="DataLab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.github.io", "http://localhost:*", "http://127.0.0.1:*"],
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


def limpiar_json(obj):
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: limpiar_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [limpiar_json(v) for v in obj]
    return obj


@app.api_route("/", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "service": "DataLab API v1.0"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    filename = file.filename or ""
    content  = await file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python",
                             encoding="utf-8", on_bad_lines="skip")
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        elif filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python",
                             encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo leer '{filename}': {str(e)}")

    if df.empty:
        raise HTTPException(status_code=422, detail="El archivo está vacío.")

    try:
        resultado = analizar_dataset(df)
        resultado["filename"] = filename
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante el análisis: {str(e)}")

    return JSONResponse(content=limpiar_json(resultado))


@app.post("/preview")
async def preview(file: UploadFile = File(...), n: int = 10):
    filename = file.filename or ""
    content  = await file.read()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python", on_bad_lines="skip")
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        elif filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content), sep=None, engine="python", on_bad_lines="skip")
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    rows    = df.head(n).fillna("").astype(str).to_dict(orient="records")
    columns = list(df.columns)
    return {"columns": columns, "rows": rows, "total_rows": len(df)}
