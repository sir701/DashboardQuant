"""
analysis.py — Lógica extraída directamente del dashboard.qmd
Funciones puras: sin Flask, sin FastAPI. Solo pandas + plotly.
"""

import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# ──────────────────────────────────────────────────────────────────────────────
# PALETA Y TEMA (mismo que el .qmd)
# ──────────────────────────────────────────────────────────────────────────────

_TC  = "#4A6FDC"
_FC  = "#3A4A5E"
_GC  = "#EEF1F5"
_MC  = "#8A9AB5"
_PAL = ["#6B8FCF","#7FBA73","#E9B58F","#F47C7C","#9B79CB",
        "#4A8F8F","#D4A843","#6BC4C4","#C47ABF","#8FA85E"]

def _ly(**kw):
    b = dict(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(color=_TC, size=14),
        font=dict(family="DM Sans, Inter, system-ui", color=_FC, size=11),
        xaxis=dict(showgrid=True, gridcolor=_GC, zeroline=False, linecolor=_GC),
        yaxis=dict(showgrid=True, gridcolor=_GC, zeroline=False, linecolor=_GC),
        margin=dict(l=55, r=30, t=55, b=45),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    )
    b.update(kw)
    return b


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES (idénticas al .qmd)
# ──────────────────────────────────────────────────────────────────────────────

def a_numero(v):
    try:
        # Elimina comas de separador de miles (ej: '1,678' -> 1678.0)
        return float(str(v).replace(",", ""))
    except:
        return None


def clasificar_columna(serie: pd.Series) -> str:
    if serie.dtype in ["int64", "float64", "int32", "float32"]:
        return "numerica"
    no_nulos = [v for v in serie.tolist()
                if v is not None and str(v).strip().lower() not in ("nan","none","")]
    if not no_nulos:
        return "categorica"
    n_num = sum(1 for v in no_nulos if a_numero(v) is not None)
    return "numerica" if (n_num / len(no_nulos)) >= 0.8 else "categorica"


def contar_faltantes(valores: list, n_total: int):
    falt = 0
    for v in valores:
        if v is None:
            falt += 1
        elif isinstance(v, float) and math.isnan(v):
            falt += 1
        elif str(v).strip().lower() in ("nan","none",""):
            falt += 1
    pct = round(falt / n_total * 100, 2) if n_total > 0 else 0
    return falt, pct


def calcular_media(datos):       return sum(datos) / len(datos)

def calcular_mediana(datos):     # datos ya ordenados
    n = len(datos); m = n // 2
    return datos[m] if n % 2 == 1 else (datos[m-1] + datos[m]) / 2

def calcular_cuartil(datos, q):  # datos ya ordenados
    pos = q * (len(datos) - 1); inf = int(pos); frac = pos - inf
    return (datos[inf] + frac*(datos[inf+1]-datos[inf])
            if inf+1 < len(datos) else datos[inf])

def calcular_desv_estandar(datos, media):
    return (sum((x-media)**2 for x in datos) / len(datos)) ** 0.5

def calcular_moda(valores):
    conteo = {}
    for v in valores:
        k = str(v) if v is not None else "NA"
        conteo[k] = conteo.get(k, 0) + 1
    moda = max(conteo, key=lambda k: conteo[k])
    return moda, conteo[moda]

def tabla_frecuencias(valores, max_cat=15):
    n = len(valores); conteo = {}
    for v in valores:
        k = str(v) if v is not None else "NA"
        conteo[k] = conteo.get(k, 0) + 1
    items = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
    tabla = []; acum = 0.0
    for cat, freq in items[:max_cat]:
        pct = round(freq / n * 100, 2)
        acum = round(acum + pct, 2)
        tabla.append({"Categoría": cat, "Frecuencia": freq,
                      "% Relativo": pct, "% Acumulado": acum})
    return tabla


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN MAESTRA (misma del .qmd, adaptada para retornar JSON-serializable)
# ──────────────────────────────────────────────────────────────────────────────

def analizar_dataset(df: pd.DataFrame) -> dict:
    # ── ⓪ LIMPIEZA: convierte columnas numéricas-de-texto a números reales ──
    # Esto resuelve el caso de comas como separador de miles (ej: '1,678').
    # Sin esto, .corr() y .std() fallan sobre columnas de texto.
    df = df.copy()
    for col in df.columns:
        # Si NO es ya un tipo numérico de pandas pero clasifica como numérica → convertir
        if not pd.api.types.is_numeric_dtype(df[col]) and clasificar_columna(df[col]) == "numerica":
            df[col] = pd.to_numeric(df[col].map(a_numero), errors="coerce")

    # ① Duplicados
    vistas = set(); duplicados = 0
    for _, fila in df.iterrows():
        clave = tuple(str(v) for v in fila)
        if clave in vistas: duplicados += 1
        else: vistas.add(clave)

    calidad = []; cols_num = []; cols_cat = []
    variables = {}; resumen = []

    for col in df.columns:
        valores  = list(df[col])
        n_total  = len(valores)
        tipo     = clasificar_columna(df[col])
        falt, pct = contar_faltantes(valores, n_total)

        # Campos enriquecidos para coincidir con lo que espera el frontend
        no_nulos_count = n_total - falt
        unicos = int(df[col].nunique(dropna=True))
        ratio  = unicos / max(n_total, 1)
        cardinalidad = "alta" if ratio > 0.5 else ("media" if ratio > 0.05 else "baja")
        calidad.append({
            "variable"     : col,
            "tipo"         : str(df[col].dtype),
            "Tipo"         : "Numérica" if tipo == "numerica" else "Categórica",
            "no_nulos"     : no_nulos_count,
            "nulos"        : falt,
            "% nulos"      : f"{pct}%",
            "unicos"       : unicos,
            "cardinalidad" : cardinalidad,
        })

        # ── Numérica ──────────────────────────────────────────
        if tipo == "numerica":
            cols_num.append(col)
            validos = sorted([a_numero(v) for v in valores if a_numero(v) is not None])
            if validos:
                media   = calcular_media(validos)
                mediana = calcular_mediana(validos)
                q1      = calcular_cuartil(validos, 0.25)
                q3      = calcular_cuartil(validos, 0.75)
                desv    = calcular_desv_estandar(validos, media)
                minimo  = validos[0]; maximo = validos[-1]
                rango   = maximo - minimo
                dma     = sum(abs(x - media) for x in validos) / len(validos)

                estadisticas = [
                    {"Grupo": "M.D.T.C — Tendencia central","Medida":"Media",                "Valor": round(media,3)},
                    {"Grupo": "M.D.L — Localización",       "Medida":"Q1  (25%)",            "Valor": round(q1,3)},
                    {"Grupo": "M.D.L — Localización",       "Medida":"Mediana  (50%)",       "Valor": round(mediana,3)},
                    {"Grupo": "M.D.L — Localización",       "Medida":"Q3  (75%)",            "Valor": round(q3,3)},
                    {"Grupo": "M.D.D — Dispersión",         "Medida":"Rango",                "Valor": round(rango,3)},
                    {"Grupo": "M.D.D — Dispersión",         "Medida":"Desv. media absoluta", "Valor": round(dma,3)},
                    {"Grupo": "M.D.D — Dispersión",         "Medida":"Desv. estándar",       "Valor": round(desv,3)},
                    {"Grupo": "M.D.F — Extremos",           "Medida":"Mínimo",               "Valor": round(minimo,3)},
                    {"Grupo": "M.D.F — Extremos",           "Medida":"Máximo",               "Valor": round(maximo,3)},
                ]
                variables[col] = {
                    "tipo": "numerica",
                    "meta": {"Obs. válidas": len(validos), "Faltantes": falt, "% Faltantes": pct},
                    "estadisticas": estadisticas,
                    "charts": _charts_numerica(df, col, validos),
                }
                resumen.append({"Variable": col, "Media": round(media,3),
                    "Mediana": round(mediana,3), "Q1": round(q1,3),
                    "Q3": round(q3,3), "Desv. Est.": round(desv,3),
                    "Mínimo": round(minimo,3), "Máximo": round(maximo,3)})
            else:
                variables[col] = {"tipo":"numerica","meta":{"Obs. válidas":0},"estadisticas":[],"charts":{}}

        # ── Categórica ────────────────────────────────────────
        else:
            cols_cat.append(col)
            moda, freq_moda = calcular_moda(valores)
            variables[col] = {
                "tipo": "categorica",
                "meta": {"Total categorías": df[col].nunique(),
                         "Moda": moda, "Frecuencia moda": freq_moda, "% Faltantes": pct},
                "tabla_frecuencias": tabla_frecuencias(valores),
                "charts": _charts_categorica(df, col),
            }

    # Gráficos globales
    charts_global = {
        "heatmap": _chart_heatmap(df, cols_num),
        "treemap": _chart_treemap(df, cols_cat, cols_num),
    }

    return {
        "meta":         {"filas": len(df), "columnas": len(df.columns),
                         "cols_numericas": len(cols_num),
                         "cols_categoricas": len(cols_cat)},
        "calidad":      calidad,
        "duplicados":   duplicados,
        "cols_con_faltantes": sum(1 for r in calidad if r["nulos"] > 0),
        "cols_numericas":  cols_num,
        "cols_categoricas": cols_cat,
        "variables":    variables,
        "resumen_numericas": resumen,
        "charts_global": charts_global,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GRÁFICOS (devuelven JSON string para el frontend)
# ──────────────────────────────────────────────────────────────────────────────

def _sample(df, col, n=6000):
    """Devuelve valores muestreados para no serializar datasets enormes."""
    s = df[col].dropna()
    if len(s) > n:
        s = s.sample(n=n, random_state=42)
    return s.tolist()

def _to_json(fig) -> str:
    return fig.to_json()


def _charts_numerica(df: pd.DataFrame, col: str, validos: list) -> dict:
    color = _PAL[0]
    vals  = _sample(df, col)
    tmp   = pd.DataFrame({col: vals})

    # Histograma
    fig_h = px.histogram(tmp, x=col, nbins=40,
                         color_discrete_sequence=[color],
                         title=f"Histograma — {col}")
    fig_h.update_layout(**_ly(bargap=0.04, showlegend=False,
                              xaxis_title=col, yaxis_title="Frecuencia"))

    # Boxplot
    fig_b = px.box(tmp, y=col,
                   color_discrete_sequence=[color],
                   title=f"Boxplot — {col}")
    fig_b.update_layout(**_ly(showlegend=False, yaxis_title=col))

    return {"histograma": _to_json(fig_h), "boxplot": _to_json(fig_b)}


def _charts_categorica(df: pd.DataFrame, col: str, top_n=15) -> dict:
    tabla = tabla_frecuencias(list(df[col]), max_cat=top_n)
    df_t  = pd.DataFrame(tabla)
    n_cats = len(df_t)

    if n_cats <= 5:
        fig = px.pie(df_t, names="Categoría", values="Frecuencia", hole=0.4,
                     title=f"Distribución — {col}",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(**_ly(title_font_color=_TC))
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_t["Categoría"], y=df_t["Frecuencia"],
                             name="Frecuencia", marker_color="#7FBA73"))
        fig.add_trace(go.Scatter(x=df_t["Categoría"], y=df_t["% Acumulado"],
                                 name="% Acumulado", mode="lines+markers",
                                 marker_color="#E9B58F", yaxis="y2"))
        fig.update_layout(**_ly(
            title=f"Pareto — {col}",
            showlegend=False,
            xaxis=dict(title=col, tickangle=-40, showgrid=False),
            yaxis=dict(title="Frecuencia", showgrid=True, gridcolor=_GC),
            yaxis2=dict(title="% Acumulado", overlaying="y", side="right",
                        range=[0,105], showgrid=False),
        ))
    return {"categorico": _to_json(fig)}


def _chart_heatmap(df: pd.DataFrame, cols_num: list, max_cols=18) -> str | None:
    # Solo columnas con varianza real
    cols = [c for c in cols_num[:max_cols]
            if c in df.columns and df[c].nunique() > 2 and df[c].std() > 0]
    if len(cols) < 2:
        return None
    corr   = df[cols].corr()
    labels = [c[:14] for c in cols]
    z      = corr.values.round(3)
    fig = go.Figure(go.Heatmap(
        z=z.tolist(), x=labels, y=labels,
        colorscale=[[0,"#F47C7C"],[0.5,"#F7F9FC"],[1,"#6B8FCF"]],
        zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=8, color=_FC),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>r = %{z:.3f}<extra></extra>",
        colorbar=dict(title=dict(text="r", font=dict(color=_FC)),
                      tickfont=dict(color=_MC),
                      bgcolor="rgba(0,0,0,0)", borderwidth=0),
    ))
    fig.update_layout(**_ly(
        title="Correlación entre Variables Numéricas",
        height=max(400, 30*len(cols)+120),
        xaxis=dict(tickangle=-45, showgrid=False, tickfont=dict(color=_MC, size=9)),
        yaxis=dict(showgrid=False, tickfont=dict(color=_MC, size=9)),
    ))
    return _to_json(fig)


def _chart_treemap(df: pd.DataFrame, cols_cat: list, cols_num: list) -> str | None:
    if not cols_cat:
        return None
    path_c = cols_cat[:2]
    tmp = df[path_c].copy()
    for c in path_c:
        tmp[c] = tmp[c].fillna("(Sin dato)").astype(str)
    if cols_num:
        # Solo la primera numérica con varianza
        num_var = [c for c in cols_num if c in df.columns and df[c].std() > 0]
        if num_var:
            tmp["_v"] = df[num_var[0]].abs().fillna(0)
            val, lbl = "_v", num_var[0][:18]
        else:
            tmp["_v"] = 1; val, lbl = "_v", "Conteo"
    else:
        tmp["_v"] = 1; val, lbl = "_v", "Conteo"

    fig = px.treemap(tmp, path=[px.Constant("Total")] + path_c,
                     values=val, color=val,
                     color_continuous_scale=[[0,"#EEF1F5"],[0.5,_PAL[0]],[1,_TC]],
                     title=f"Treemap — Distribución por {path_c[0][:22]} ({lbl})")
    fig.update_traces(textfont=dict(color="white", size=11),
                      hovertemplate="<b>%{label}</b><br>%{value:,.0f}<extra></extra>")
    fig.update_layout(**_ly(height=480))
    return _to_json(fig)
