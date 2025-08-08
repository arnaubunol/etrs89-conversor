
import math
import pandas as pd
from pyproj import Transformer
import streamlit as st

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

def _default_index(cols, needle_list):
    # Encuentra el índice de la primera columna que contenga cualquiera de los needles (ignora espacios/casos)
    for i, c in enumerate(cols):
        norm = ''.join(str(c).lower().split())
        for needle in needle_list:
            if needle in norm:
                return i
    return 0

if uploaded is not None:
    # Leer archivo
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)
    st.write("Vista previa del archivo:", df.head())

    cols = list(df.columns)
    lat_idx = _default_index(cols, ["latitud", "latitude", "lat"])
    lon_idx = _default_index(cols, ["longitud", "longitude", "long", "lon", "lng"])

    lat_col = st.selectbox("Columna de **Latitud**", options=cols, index=lat_idx)
    lon_col = st.selectbox("Columna de **Longitud**", options=cols, index=lon_idx)

    use_decimal_comma = st.checkbox("Mis lat/lon usan **coma decimal** (ej. 41,84346)", value=True)

    st.markdown("### Datum de **entrada** (lat/lon)")
    assume_input = st.selectbox(
        "Selecciona el datum de las coordenadas geográficas de entrada",
        ["ETRS89 (EPSG:4258)", "WGS84 (EPSG:4326)"],
        index=0
    )
    input_epsg = "EPSG:4258" if "4258" in assume_input else "EPSG:4326"

    st.markdown("---")
    st.subheader("Salida")
    mode = st.radio(
        "Elige el modo de salida",
        [
            "Forzar **ETRS89 / UTM 31N (EPSG:25831)**",
            "Auto por huso (**ETRS89 / UTM 29–31N** en España)",
            "Fijar huso manual (**ETRS89 / UTM 29N, 30N o 31N**)"
        ],
        index=0
    )
    fixed_zone = None
    if "Fijar huso manual" in mode:
        fixed_zone = st.selectbox("Huso UTM", options=[29, 30, 31], index=1)  # 30 por defecto

    if st.button("Convertir"):
        df2 = df.copy()

        # Parseo robusto de lat/lon
        def to_float_series(s):
            s = s.astype(str)
            if use_decimal_comma:
                s = s.str.replace(",", ".", regex=False)
            return pd.to_numeric(s, errors="coerce")

        lat_s = to_float_series(df2[lat_col])
        lon_s = to_float_series(df2[lon_col])

        # Filtro de filas válidas
        valid = lat_s.between(-90, 90) & lon_s.between(-180, 180)
        n_all = len(df2)
        n_valid = int(valid.sum())
        n_drop = n_all - n_valid

        if n_valid == 0:
            st.error("No hay filas válidas con latitudes/longitudes en rango. Revisa columnas y formato decimal.")
            st.stop()

        df_out = df2.loc[valid].copy()
        lat_v = lat_s[valid].values
        lon_v = lon_s[valid].values

        results = pd.DataFrame(index=df_out.index)

        if "Forzar" in mode:
            transformer = Transformer.from_crs(input_epsg, "EPSG:25831", always_xy=True)
            x, y = transformer.transform(lon_v, lat_v)
            results["X_ETRS89"] = x
            results["Y_ETRS89"] = y
            results["EPSG_destino"] = "EPSG:25831"
            results["Huso"] = 31

        elif "Auto por huso" in mode:
            # España: husos 29/30/31. Calculamos desde longitud.
            zones = ((lon_v + 180.0) // 6.0).astype(int) + 1
            xs, ys, epsgs, husos = [], [], [], []
            for lon, lat, zone in zip(lon_v, lat_v, zones):
                # Limitar a 29..31 para España; si cae fuera, aproximamos al más cercano
                if zone < 29: zone = 29
                if zone > 31: zone = 31
                epsg = f"EPSG:258{int(zone):02d}"
                try:
                    transformer = Transformer.from_crs(input_epsg, epsg, always_xy=True)
                    x, y = transformer.transform(lon, lat)
                except Exception:
                    x, y = float("nan"), float("nan")
                xs.append(x); ys.append(y); epsgs.append(epsg); husos.append(int(zone))
            results["X_ETRS89"] = xs
            results["Y_ETRS89"] = ys
            results["EPSG_destino"] = epsgs
            results["Huso"] = husos

        else:  # Fijar huso manual
            epsg = f"EPSG:258{int(fixed_zone):02d}"
            transformer = Transformer.from_crs(input_epsg, epsg, always_xy=True)
            x, y = transformer.transform(lon_v, lat_v)
            results["X_ETRS89"] = x
            results["Y_ETRS89"] = y
            results["EPSG_destino"] = epsg
            results["Huso"] = int(fixed_zone)

        # Redondeo visual (3 decimales)
        results["X_ETRS89"] = results["X_ETRS89"].round(3)
        results["Y_ETRS89"] = results["Y_ETRS89"].round(3)

        out = pd.concat([df_out.reset_index(drop=True), results.reset_index(drop=True)], axis=1)

        st.success(f"Conversión completada. {n_valid} filas válidas; {n_drop} descartadas por lat/lon inválidas.")
        st.write(out.head())

        csv_bytes = out.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar CSV convertido",
            data=csv_bytes,
            file_name="convertido_ETRS89_UTM.csv",
            mime="text/csv"
        )

        st.info("Para Lleida/Cataluña: usa **Forzar 31N (EPSG:25831)**. Ejemplo (1.03335, 41.84346) → X=336724.563, Y=4634265.720, Huso=31.")
    else:
        st.caption("Configura opciones y pulsa **Convertir**.")
