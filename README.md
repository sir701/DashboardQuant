# DataLab — Análisis Exploratorio Automático

> Sube cualquier CSV / Excel / JSON y obtén estadísticas, gráficos y calidad de datos en segundos.  
> Motor de análisis idéntico al `dashboard.qmd` del proyecto.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub                                                          │
│                                                                  │
│  /frontend/index.html ──── GitHub Actions ──▶ GitHub Pages       │
│                                  │           (tu-usuario.github.io/repo)
│  /api/main.py (FastAPI)          │                               │
│  /api/analysis.py  ─────── GitHub Actions ──▶ Render.com        │
│  /render.yaml                    │           (datalab-api.onrender.com)
└──────────────────────────────────┘                               │
                                                                   │
  Usuario sube CSV ──▶ GitHub Pages ──▶ POST /analyze ──▶ Render  │
                                ◀── JSON (stats + charts Plotly) ──┘
```

---

## Setup paso a paso

### 1. Crear el repositorio en GitHub

```bash
git init datalab
cd datalab
# Copia todos los archivos de este proyecto
git add .
git commit -m "feat: DataLab inicial"
git remote add origin https://github.com/TU_USUARIO/datalab.git
git push -u origin main
```

---

### 2. Desplegar el backend en Render (gratis)

1. Ve a **[render.com](https://render.com)** y crea una cuenta.
2. **New → Web Service → Connect a repository** → selecciona tu repo.
3. Render detecta el `render.yaml` automáticamente.  
   Si no: configura manualmente:
   - **Build Command:** `pip install -r api/requirements.txt`
   - **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory:** (vacío, usa la raíz)
4. Haz clic en **Create Web Service**.
5. Espera ~3 min. La URL será algo como `https://datalab-api.onrender.com`.
6. Verifica: abre `https://datalab-api.onrender.com/` → debe responder `{"status":"ok"}`.

#### Obtener el Deploy Hook (para el workflow de GitHub Actions)

En Render → tu servicio → **Settings → Deploy Hook → Create hook** → copia la URL.

---

### 3. Configurar GitHub Actions

En tu repo de GitHub ve a **Settings → Secrets and variables → Actions**:

| Tipo     | Nombre                  | Valor                                          |
|----------|-------------------------|------------------------------------------------|
| Variable | `BACKEND_URL`           | `https://datalab-api.onrender.com` (sin `/` final) |
| Secret   | `RENDER_DEPLOY_HOOK_URL`| La URL del deploy hook de Render               |

---

### 4. Activar GitHub Pages

1. **Settings → Pages → Source → GitHub Actions** (no "Deploy from branch").
2. Haz un push a `main` o lanza el workflow manualmente desde la pestaña **Actions**.
3. GitHub Pages publica en `https://TU_USUARIO.github.io/datalab/`.

---

### 5. Probar localmente

```bash
# Backend
cd api
pip install -r requirements.txt
uvicorn main:app --reload
# API en: http://127.0.0.1:8000

# Frontend: abre frontend/index.html en el navegador
# Cambia BACKEND_URL en index.html a "http://127.0.0.1:8000" para desarrollo local
```

---

## Estructura del repositorio

```
datalab/
├── .github/
│   └── workflows/
│       ├── deploy-frontend.yml   ← Auto-publica frontend en GitHub Pages
│       └── deploy-backend.yml    ← Notifica a Render que redepliegue
├── api/
│   ├── analysis.py               ← Toda la lógica del dashboard.qmd
│   ├── main.py                   ← FastAPI: endpoints /analyze y /preview
│   └── requirements.txt
├── frontend/
│   └── index.html                ← SPA: drag & drop + dashboard
├── dashboard.qmd                 ← (opcional) render local con Quarto
├── datos.csv                     ← (opcional) dataset de ejemplo
├── render.yaml                   ← Config de Render.com
└── README.md
```

---

## Endpoints de la API

| Método | Ruta       | Body          | Respuesta                                      |
|--------|------------|---------------|------------------------------------------------|
| GET    | `/`        | —             | `{"status": "ok"}`                             |
| POST   | `/analyze` | `file` (form) | JSON completo: meta, calidad, variables, charts |
| POST   | `/preview` | `file` (form) | Primeras N filas como JSON                     |

---

## ⚠️ Limitación del plan gratuito de Render

El servicio **"duerme"** tras 15 minutos de inactividad.  
El primer request después de un período inactivo tarda ~30 segundos en responder.  
Para producción real, considera **Render Starter** (~$7/mes) o Railway.

---

## Flujo al actualizar el análisis

```
Editas analysis.py  →  git push origin main
                              ↓
                    GitHub Action detecta cambio en /api
                              ↓
                    Llama al Render Deploy Hook
                              ↓
                    Render re-deploya el backend en ~2 min
```

El `.qmd` original sigue funcionando en local exactamente igual — `analysis.py` es la misma lógica, solo expuesta como API.
