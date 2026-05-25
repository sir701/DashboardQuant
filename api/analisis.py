"""
analysis.py — Lógica extraída directamente del dashboard.qmd
"""

import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

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


def a_numero(v):
    try:
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

def calcular_mediana(datos):   
    n = len(datos); m = n // 2
    return datos[m] if n % 2 == 1 else (datos[m-1] + datos[m]) / 2

def calcular_cuartil(datos, q): 
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


def analizar_dataset(df: pd.DataFrame) -> dict:
    df = df.copy()
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]) and clasificar_columna(df[col]) == "numerica":
            df[col] = pd.to_numeric(df[col].map(a_numero), errors="coerce")

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

    # Gráficos avanzados (tab "Avanzado")
    charts_adv = charts_avanzados(df, cols_num, cols_cat)

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
        "charts_global":   charts_global,
        "charts_avanzados": charts_adv,
    }


# GRÁFICOS (devuelven JSON string para el frontend)

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

    fig_h = px.histogram(tmp, x=col, nbins=40,
                         color_discrete_sequence=[color],
                         title=f"Histograma — {col}")
    fig_h.update_layout(**_ly(bargap=0.04, showlegend=False,
                              xaxis_title=col, yaxis_title="Frecuencia"))

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


# GRÁFICOS AVANZADOS — Tab "Avanzado" del dashboard web

def _cvar(df: pd.DataFrame, max_cols=18):
    """Columnas numéricas con varianza real (excluye constantes)."""
    return [c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c])
            and df[c].dropna().nunique() > 2
            and float(df[c].std()) > 0][:max_cols]

def _ccat(df: pd.DataFrame, mx=80):
    """Columnas categóricas con 2–mx categorías únicas."""
    return [c for c in df.columns
            if not pd.api.types.is_numeric_dtype(df[c])
            and 2 <= df[c].nunique(dropna=True) <= mx]

def _df_sample(df: pd.DataFrame, n=15000) -> pd.DataFrame:
    """Muestra el DataFrame SOLO si excede n filas (fallback inteligente)."""
    if len(df) > n:
        return df.sample(n=n, random_state=42).reset_index(drop=True)
    return df.reset_index(drop=True)

def _ph_json(msg: str) -> str:
    """Placeholder con mensaje cuando no hay datos suficientes."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"<b>Sin datos suficientes</b><br><span style='font-size:11px'>{msg}</span>",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(color=_FC, size=13), align="center",
    )
    fig.update_layout(**_ly(height=200,
                            xaxis=dict(visible=False), yaxis=dict(visible=False)))
    return _to_json(fig)


def _chart_violin(df: pd.DataFrame, cols_num: list) -> str:
    try:
        cols = [c for c in cols_num if c in df.columns and df[c].std() > 0][:8]
        if len(cols) < 2:
            return _ph_json("Se necesitan ≥2 variables numéricas con varianza")
        fig = go.Figure()
        for i, col in enumerate(cols):
            fig.add_trace(go.Violin(
                y=df[col].dropna().tolist(),
                name=col[:16], box_visible=True, meanline_visible=True,
                fillcolor=_PAL[i % len(_PAL)], opacity=0.7,
                line_color=_PAL[i % len(_PAL)],
            ))
        fig.update_layout(**_ly(
            title="Distribución por Variable — Violin Plot",
            height=420, showlegend=False, yaxis_title="Valor",
            violingap=0.08, violinmode="overlay",
        ))
        return _to_json(fig)
    except Exception as e:
        return _ph_json(f"Violin — {e}")


def _chart_scatter_matrix(df: pd.DataFrame, cols_num: list) -> str:
    try:
        cols = [c for c in cols_num if c in df.columns and df[c].std() > 0][:6]
        if len(cols) < 2:
            return _ph_json("Se necesitan ≥2 variables con varianza")
        tmp  = _df_sample(df, n=5000)
        cats = _ccat(tmp)
        color_col = cats[0] if cats else None
        splom_dims = [dict(label=c[:14], values=tmp[c].tolist()) for c in cols]
        marker = dict(size=4, opacity=0.5,
                      color=tmp[color_col].astype("category").cat.codes.tolist()
                      if color_col else _PAL[0],
                      colorscale=[[i/max(len(_PAL)-1,1), c] for i,c in enumerate(_PAL)]
                      if color_col else None,
                      showscale=False)
        fig = go.Figure(go.Splom(
            dimensions=splom_dims, marker=marker,
            showupperhalf=False, diagonal_visible=True,
        ))
        fig.update_layout(**_ly(
            title="Scatter Matrix — Relaciones entre Variables Numéricas",
            height=max(500, 130 * len(cols)),
        ))
        return _to_json(fig)
    except Exception as e:
        return _ph_json(f"Scatter Matrix — {e}")


def _chart_parallel(df: pd.DataFrame, cols_num: list) -> str:
    try:
        cols = [c for c in cols_num if c in df.columns and df[c].std() > 0][:8]
        if len(cols) < 3:
            return _ph_json("Se necesitan ≥3 variables con varianza")
        tmp  = _df_sample(df[cols], n=8000)
        dims = []
        for col in cols:
            s = tmp[col].dropna()
            dims.append(dict(label=col[:14], values=tmp[col].tolist(),
                             range=[float(s.min()), float(s.max())]))
        fig = go.Figure(go.Parcoords(
            line=dict(color=tmp[cols[0]].tolist(),
                      colorscale=[[0,_PAL[3]],[0.5,_PAL[0]],[1,_PAL[1]]],
                      showscale=True,
                      cmin=float(tmp[cols[0]].min()), cmax=float(tmp[cols[0]].max())),
            dimensions=dims,
        ))
        fig.update_layout(**_ly(
            title="Coordenadas Paralelas — Vista Multivariable", height=420))
        return _to_json(fig)
    except Exception as e:
        return _ph_json(f"Parallel Coords — {e}")


def _chart_sankey(df: pd.DataFrame, cols_cat: list) -> str:
    try:
        if len(cols_cat) < 2:
            return _ph_json("Se necesitan ≥2 variables categóricas para Sankey")
        src_col, tgt_col = cols_cat[0], cols_cat[1]
        tmp = df[[src_col, tgt_col]].dropna()
        tmp = tmp[tmp[src_col].astype(str).str.len() < 40]
        tmp = tmp[tmp[tgt_col].astype(str).str.len() < 40]
        top_src = tmp[src_col].value_counts().head(8).index.tolist()
        top_tgt = tmp[tgt_col].value_counts().head(8).index.tolist()
        tmp = tmp[tmp[src_col].isin(top_src) & tmp[tgt_col].isin(top_tgt)]
        if len(tmp) < 10:
            return _ph_json("Datos insuficientes para Sankey con estas categorías")
        flows = tmp.groupby([src_col, tgt_col]).size().reset_index(name="n")
        all_nodes = list(dict.fromkeys(flows[src_col].tolist() + flows[tgt_col].tolist()))
        node_idx = {n: i for i, n in enumerate(all_nodes)}
        colors = [_PAL[i % len(_PAL)] for i in range(len(all_nodes))]
        fig = go.Figure(go.Sankey(
            node=dict(label=all_nodes, color=colors, pad=15, thickness=20),
            link=dict(
                source=[node_idx[r[src_col]] for _, r in flows.iterrows()],
                target=[node_idx[r[tgt_col]] for _, r in flows.iterrows()],
                value=flows["n"].tolist(),
                color="rgba(107,143,207,0.3)",
            ),
        ))
        fig.update_layout(**_ly(
            title=f"Sankey — Flujo de {src_col[:18]} → {tgt_col[:18]}", height=440))
        return _to_json(fig)
    except Exception as e:
        return _ph_json(f"Sankey — {e}")


def _chart_grouped_bars(df: pd.DataFrame, cols_cat: list, cols_num: list) -> str:
    try:
        if not cols_cat or not cols_num:
            return _ph_json("Se necesita ≥1 variable categórica y ≥1 numérica")
        cat_col  = cols_cat[0]
        num_cols = [c for c in cols_num if c in df.columns and df[c].std() > 0][:5]
        top_cats = df[cat_col].value_counts().head(10).index.tolist()
        tmp      = df[df[cat_col].isin(top_cats)]
        agg      = tmp.groupby(cat_col)[num_cols].mean().reset_index()
        fig = go.Figure()
        for i, nc in enumerate(num_cols):
            fig.add_trace(go.Bar(name=nc[:18], x=agg[cat_col].tolist(),
                                 y=agg[nc].round(2).tolist(),
                                 marker_color=_PAL[i % len(_PAL)]))
        fig.update_layout(**_ly(
            title=f"Media de Variables Numéricas por {cat_col[:22]}",
            barmode="group", height=420,
            xaxis=dict(title=cat_col, tickangle=-35, showgrid=False),
            yaxis_title="Media"))
        return _to_json(fig)
    except Exception as e:
        return _ph_json(f"Barras agrupadas — {e}")


# 6. Serie & Media Móvil (umbral 15000)
def _chart_rolling(df: pd.DataFrame, cols_num: list, window: int = 20) -> str:
    try:
        cols = [c for c in cols_num if c in df.columns and df[c].std() > 0][:4]
        if not cols:
            return _ph_json("Sin variables numéricas con varianza para serie temporal")
        tmp  = _df_sample(df[cols], n=15000)
        x    = list(range(len(tmp)))
        fig  = go.Figure()
        for i, col in enumerate(cols):
            s    = tmp[col].ffill()
            roll = s.rolling(window=min(window, max(2, len(s)//20)),
                             min_periods=1).mean()
            fig.add_trace(go.Scatter(x=x, y=s.tolist(), mode="lines", name=col[:14],
                                     line=dict(color=_PAL[i % len(_PAL)], width=1),
                                     opacity=0.35))
            fig.add_trace(go.Scatter(x=x, y=roll.tolist(), mode="lines",
                                     name=f"{col[:12]} (media móvil)",
                                     line=dict(color=_PAL[i % len(_PAL)], width=2)))
        fig.update_layout(**_ly(
            title="Serie & Media Móvil — Variables Numéricas", height=420,
            xaxis_title="Índice de registro", yaxis_title="Valor"))
        return _to_json(fig)
    except Exception as e:
        return _ph_json(f"Rolling — {e}")


def charts_avanzados(df: pd.DataFrame, cols_num: list, cols_cat: list) -> dict:
    """Genera todos los gráficos avanzados; devuelve dict de JSON strings."""
    return {
        "violin":         _chart_violin(df, cols_num),
        "scatter_matrix": _chart_scatter_matrix(df, cols_num),
        "parallel":       _chart_parallel(df, cols_num),
        "sankey":         _chart_sankey(df, cols_cat),
        "grouped_bars":   _chart_grouped_bars(df, cols_cat, cols_num),
        "rolling":        _chart_rolling(df, cols_num),
    }
