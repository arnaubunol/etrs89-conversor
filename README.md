# Conversor Lat/Lon → ETRS89 / UTM (Streamlit)

App sencilla para convertir columnas de **Latitud/Longitud** (grados decimales) a **ETRS89 / UTM** (X,Y en metros).
Pensada para Lleida (**EPSG:25831**) y para datos en España (modo automático por huso).

## Cómo ejecutar en local

```bash
pip install -r requirements.txt
streamlit run etrs89_converter_app.py
```

Se abrirá en `http://localhost:8501`.

## Despliegue en Streamlit Community Cloud

1. Crea un repositorio en GitHub con estos archivos: `etrs89_converter_app.py`, `requirements.txt` y este `README.md`.
2. Ve a https://streamlit.io/cloud, conéctalo a tu repo y pulsa **Deploy**.
3. La app quedará accesible desde una URL pública.

## Estructura del repo

```
.
├── etrs89_converter_app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Licencia

MIT (o la que prefieras).
