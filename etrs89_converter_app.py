
import io
import math
import pandas as pd
from pyproj import Transformer
import streamlit as st

st.set_page_config(page_title="Conversor a ETRS89 UTM", layout="centered")

st.title("Conversor de Lat/Lon a **ETRS89 / UTM**")
st.caption("Ideal para Lleida (ETRS89 / UTM 31N - EPSG:25831) o para datos en España.")

with st.expander("Instrucciones rápidas", expanded=True):
    st.markdown(
        """
        1. **Sube tu archivo** (CSV o Excel) con columnas de **latitud** y **longitud** en grados decimales.
        2. Selecciona qué columnas son **Lat** y **Lon** (puedes marcar si usan coma decimal).
        3. Elige el **modo de salida**:
           - **Forzar 31N (EPSG:25831)** — recomendado para Lleida y alrededores.
           - **Por huso** — calcula automáticamente el huso UTM según la longitud.
        4. Pulsa **Convertir** y descarga el CSV con columnas X/Y en metros.
        """
    )

uploaded = st.file_uploader("Sube un archivo CSV o Excel", type=["csv", "xlsx", "xls"])
if uploaded is not None:
    # Read file
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)
    st.write("Vista previa del archivo:", df.head())

    # Select lat/lon columns
    cols = list(df.columns)
    lat_col = st.selectbox("Columna de **Latitud**", options=cols, index=next((i for i,c in enumerate(cols) if "lat" in str(c).lower()), 0))
    lon_col = st.selectbox("Columna de **Longitud**", options=cols, index=next((i for i,c in enumerate(cols) if "lon" in str(c).lower() or "long" in str(c).lower()), 0))

    use_decimal_comma = st.checkbox("Mis lat/lon usan **coma decimal** (ej. 41,8435)", value=True)
    assume_input = st.selectbox("Datum de **entrada** (lat/lon)", ["WGS84 (EPSG:4326)", "ETRS89 (EPSG:4258)"], index=0)
    input_epsg = "EPSG:4326" if "4326" in assume_input else "EPSG:4258"

    st.markdown("---")
    st.subheader("Salida")
    mode = st.radio("Elige el modo de salida", ["Forzar **ETRS89 / UTM 31N (EPSG:25831)**", "Auto por huso (**ETRS89 / UTM 29–31N** en España)"], index=0)
    if st.button("Convertir"):
        df2 = df.copy()
        # Parse lat/lon to numeric
        def to_float_series(s):
            s = s.astype(str)
            if use_decimal_comma:
                s = s.str.replace(",", ".", regex=False)
            return pd.to_numeric(s, errors="coerce")

        lat_s = to_float_series(df2[lat_col])
        lon_s = to_float_series(df2[lon_col])

        # Valid filter
        valid = lat_s.between(-90, 90) & lon_s.between(-180, 180)
        n_all = len(df2)
        n_valid = int(valid.sum())
        n_drop = n_all - n_valid

        df_out = df2.loc[valid].copy()
        lat_v = lat_s[valid].values
        lon_v = lon_s[valid].values

        results = pd.DataFrame(index=df_out.index)

        if "Forzar" in mode:
            transformer = Transformer.from_crs(input_epsg, "EPSG:25831", always_xy=True)
            x, y = transformer.transform(lon_v, lat_v)
            results["X_ETRS89_25831"] = x
            results["Y_ETRS89_25831"] = y
            results["EPSG_destino"] = "EPSG:25831"
            results["Huso"] = 31
        else:
            # Auto by zone for Spain (commonly 29,30,31N). We'll compute zone from longitude.
            zones = ((lon_v + 180.0) // 6.0).astype(int) + 1
            xs = []
            ys = []
            epsgs = []
            husos = []
            for lon, lat, zone in zip(lon_v, lat_v, zones):
                epsg = f"EPSG:258{zone:02d}"
                try:
                    transformer = Transformer.from_crs(input_epsg, epsg, always_xy=True)
                    x, y = transformer.transform(lon, lat)
                    xs.append(x); ys.append(y); epsgs.append(epsg); husos.append(int(zone))
                except Exception:
                    xs.append(float("nan")); ys.append(float("nan")); epsgs.append(None); husos.append(int(zone))
            results["X_ETRS89"] = xs
            results["Y_ETRS89"] = ys
            results["EPSG_destino"] = epsgs
            results["Huso"] = husos

        out = pd.concat([df_out.reset_index(drop=True), results.reset_index(drop=True)], axis=1)
        st.success(f"Conversión completada. {n_valid} filas válidas; {n_drop} descartadas por lat/lon inválidas.")
        st.write(out.head())

        # Download
        csv_bytes = out.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar CSV convertido", data=csv_bytes, file_name="convertido_ETRS89_UTM.csv", mime="text/csv")
        st.info("Recomendación: para Lleida y Cataluña, usa EPSG:25831 (UTM 31N).")
    else:
        st.caption("Configura opciones y pulsa **Convertir**.")
