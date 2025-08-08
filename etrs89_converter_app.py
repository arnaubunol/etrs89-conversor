
import math
import io
import pandas as pd
from pyproj import Transformer
import streamlit as st

from converter import convert_dataframe

st.set_page_config(page_title="Conversor Lat/Lon → ETRS89 / UTM", layout="centered")

st.title("Conversor de Lat/Lon a **ETRS89 / UTM**")
st.caption("Pensado para Lleida (ETRS89 / UTM 31N - EPSG:25831) y datos en España.")

with st.expander("Instrucciones rápidas", expanded=True):
    st.markdown(
        """
        1. **Sube tu archivo** (CSV o Excel) con columnas de **latitud** y **longitud** en grados decimales.
        2. Elige qué columnas son **Lat** y **Lon** (marca si usan **coma decimal**).
        3. Selecciona el **datum de entrada** (por defecto **ETRS89 geográficas – EPSG:4258**).
        4. Elige el **modo de salida**:
           - **Forzar 31N (EPSG:25831)** — recomendado para Lleida/Cataluña.
           - **Auto por huso (España 29–31N)** — calcula el huso UTM por cada fila.
           - **Fijar un huso** — 29N/30N/31N manual.
        5. Pulsa **Convertir** y descarga el CSV con **X/Y** en metros.
        """
    )

uploaded = st.file_uploader("Sube un archivo CSV o Excel", type=["csv", "xlsx", "xls"])

# Opciones de lectura CSV
is_csv = False
sep_map = {"Auto (, por defecto)": None, "Coma (,)": ",", "Punto y coma (;)": ";", "Tabulación (TAB)": "\t"}
encodings = ["utf-8", "latin-1", "cp1252"]

if uploaded is not None:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        is_csv = True
        st.markdown("### Opciones de lectura (CSV)")
        sel_sep = st.selectbox("Separador", options=list(sep_map.keys()), index=0)
        sep = sep_map[sel_sep]
        enc = st.selectbox("Encoding", options=encodings, index=0)

    # Leer archivo
    try:
        if is_csv:
            df = pd.read_csv(uploaded, sep=sep if sep else ",", encoding=enc)
        else:
            df = pd.read_excel(uploaded)  # requiere openpyxl
    except Exception as e:
        st.error(f"Error leyendo el archivo: {e}")
        st.stop()

    st.write("Vista previa del archivo:", df.head())

    # Helpers
    def _default_index(cols, needle_list):
        for i, c in enumerate(cols):
            norm = ''.join(str(c).lower().split())
            for needle in needle_list:
                if needle in norm:
                    return i
        return 0

    cols = list(df.columns)
    lat_idx = _default_index(cols, ["latitud", "latitude", "lat"])
    lon_idx = _default_index(cols, ["longitud", "longitude", "long", "lon", "lng"])

    lat_col = st.selectbox("Columna de **Latitud**", options=cols, index=lat_idx)
    lon_col = st.selectbox("Columna de **Longitud**", options=cols, index=lon_idx)

    # Marca esta casilla si las coordenadas usan coma como separador decimal
    use_decimal_comma = st.checkbox("Mis lat/lon usan **coma decimal** (ej. 41,84346)", value=False)

    st.markdown("### Datum de **entrada** (lat/lon)")
    assume_input = st.selectbox(
        "Selecciona el datum de las coordenadas geográficas de entrada",
        ["ETRS89 (EPSG:4258)", "WGS84 (EPSG:4326)"],
        index=0
    )
    input_epsg = "EPSG:4258" if "4258" in assume_input else "EPSG:4326"

    st.markdown("---")
    st.subheader("Salida")
    mode_choice = st.radio(
        "Elige el modo de salida",
        [
            "Forzar **ETRS89 / UTM 31N (EPSG:25831)**",
            "Auto por huso (**ETRS89 / UTM 29–31N** en España)",
            "Fijar huso manual (**ETRS89 / UTM 29N, 30N o 31N**)"
        ],
        index=0
    )
    fixed_zone = None
    if "Fijar huso manual" in mode_choice:
        fixed_zone = st.selectbox("Huso UTM", options=[29, 30, 31], index=1)  # 30 por defecto


    if st.button("Convertir"):
        try:
            out, n_valid, n_drop = convert_dataframe(
                df,
                lat_col,
                lon_col,
                mode=(
                    "force_31n"
                    if "Forzar" in mode_choice
                    else "auto" if "Auto" in mode_choice else "fixed"
                ),
                fixed_zone=fixed_zone,
                use_decimal_comma=use_decimal_comma,
                input_epsg=input_epsg,
            )
        except ValueError as e:
            st.error(str(e))
            st.stop()

        st.success(
            f"Conversión completada. {n_valid} filas válidas; {n_drop} descartadas por lat/lon inválidas."
        )
        st.write(out.head())

        csv_bytes = out.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar CSV convertido",
            data=csv_bytes,
            file_name="convertido_ETRS89_UTM.csv",
            mime="text/csv",
        )

        st.info(
            "Para Lleida/Cataluña: usa **Forzar 31N (EPSG:25831)**. Ejemplo (1.03335, 41.84346) → X=336724.563, Y=4634265.720, Huso=31."
        )
    else:
        st.caption("Configura opciones y pulsa **Convertir**.")
