# Conversor Lat/Lon → ETRS89 / UTM (Streamlit)

App web para convertir coordenadas **geográficas** (latitud/longitud) a coordenadas planas **X, Y en metros** usando **ETRS89 / UTM**.
Pensada para Lleida y España: por defecto asume **ETRS89 geográficas (EPSG:4258)** y permite salida en **UTM 31N (EPSG:25831)** u otros husos.

---

## ✨ Funciones
- Entrada: CSV o Excel con columnas de **Latitud** y **Longitud** (acepta **coma decimal** `41,84346` o punto `41.84346`).
- **Datum de entrada** seleccionable: `ETRS89 (EPSG:4258)` *(por defecto)* o `WGS84 (EPSG:4326)`.
- **Modos de salida**:
  1. **Forzar ETRS89 / UTM 31N (EPSG:25831)** → recomendado para Lleida/Cataluña.
  2. **Auto por huso (España 29–31N)** → calcula el huso a partir de la longitud por cada fila.
  3. **Fijar huso manual (29N/30N/31N)**.
- Descarga el **CSV convertido** con columnas `X_ETRS89`, `Y_ETRS89`, `EPSG_destino`, `Huso`.

**Validación conocida (Lleida):**
- Longitud = `1,03335`, Latitud = `41,84346` (ETRS89 geográficas)  
→ **X = 336724.563**, **Y = 4634265.720**, **Huso = 31** (modo «Forzar 31N»).

---

## 🚀 Cómo ejecutar en local

```bash
pip install -r requirements.txt
streamlit run etrs89_converter_app.py
```

Se abrirá en `http://localhost:8501`.

---

## ☁️ Despliegue en Streamlit Community Cloud

1. Sube estos archivos a un repositorio de GitHub (en la **raíz**):
   - `etrs89_converter_app.py`
   - `requirements.txt`
   - `README.md`
   - `.gitignore` (opcional)
2. Ve a https://streamlit.io/cloud → **Sign in with GitHub** → **New app**.
3. Rellena:
   - **Repository**: `TU_USUARIO/TU_REPO`
   - **Branch**: `main`
   - **Main file path**: `etrs89_converter_app.py`
4. **Deploy**. La primera build tarda 1–3 min. Obtendrás una **URL pública**.

> Si sale *“This repository does not exist”*: verifica que el repo existe, que diste permisos a Streamlit para verlo (GitHub → Settings → Applications → *Streamlit* → Configure), y que el archivo principal está en la raíz.

---

## 🧭 Uso de la app
1. Sube tu **CSV/Excel**.
2. Elige qué columnas son **Latitud** y **Longitud**. Marca **“coma decimal”** si procede.
3. Selecciona **datum de entrada** (por defecto **ETRS89 – EPSG:4258**).
4. Elige **modo de salida** (Lleida/Cataluña → «Forzar 31N»).
5. Pulsa **Convertir** y **descarga** el CSV con X/Y.

---

## 🛠️ Consejos y resolución de problemas
- **Resultados inesperados**: Revisa que **no hayas intercambiado lat/lon**, que el **datum** sea correcto y la **coma decimal** esté marcada si aplica.
- **Coordenadas fuera de España**: El modo *Auto por huso* limita a 29–31N. Para otras zonas, usa *Fijar huso manual*.
- **Módulos faltantes en Cloud**: Asegúrate de que `streamlit`, `pyproj` y `pandas` están en `requirements.txt`. Recomendado usar versiones fijadas (incluidas).
- **Privacidad**: Streamlit procesa el archivo durante la sesión; descarga el resultado y evita datos sensibles en repos públicos.

---

## 🗂️ Estructura del repo
```
.
├── .devcontainer/
├── etrs89_converter_app.py
├── packages.txt
├── python-version
├── requirements.txt
├── runtime.txt
└── README.md
```

Opcional: `.gitignore`

---

## 📄 Licencia
MIT (o la que prefieras).
