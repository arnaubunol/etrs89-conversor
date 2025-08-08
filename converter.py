import pandas as pd
from pyproj import Transformer


def convert_dataframe(
    df: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    mode: str,
    *,
    fixed_zone: int | None = None,
    use_decimal_comma: bool = False,
    input_epsg: str = "EPSG:4258",
):
    """Convert a DataFrame of geographic coordinates to ETRS89/UTM.

    Parameters
    ----------
    df:
        Source DataFrame containing latitude and longitude columns.
    lat_col, lon_col:
        Names of the latitude and longitude columns.
    mode:
        One of ``"force_31n"``, ``"auto"`` or ``"fixed"``. ``"force_31n"``
        converts everything to EPSG:25831. ``"auto"`` picks the UTM zone
        based on longitude (limited to 29–31 for Spain). ``"fixed"`` requires
        ``fixed_zone`` to specify the UTM zone.
    fixed_zone:
        Optional UTM zone used when ``mode == "fixed"``.
    use_decimal_comma:
        If ``True`` decimal commas are converted to decimal points before
        parsing.
    input_epsg:
        EPSG code of the input geographic coordinates.

    Returns
    -------
    Tuple[pd.DataFrame, int, int]
        The converted DataFrame along with the number of valid rows and the
        number of discarded rows.
    """

    df2 = df.copy()

    def to_float_series(series: pd.Series) -> pd.Series:
        series = series.astype(str)
        if use_decimal_comma:
            series = series.str.replace(",", ".", regex=False)
        return pd.to_numeric(series, errors="coerce")

    lat_s = to_float_series(df2[lat_col])
    lon_s = to_float_series(df2[lon_col])

    valid = lat_s.between(-90, 90) & lon_s.between(-180, 180)
    n_all = len(df2)
    n_valid = int(valid.sum())
    n_drop = n_all - n_valid

    if n_valid == 0:
        raise ValueError(
            "No valid rows with latitudes/longitudes in range."
        )

    df_out = df2.loc[valid].copy()
    lat_v = lat_s[valid].values
    lon_v = lon_s[valid].values

    results = pd.DataFrame(index=df_out.index)

    if mode == "force_31n":
        transformer = Transformer.from_crs(
            input_epsg, "EPSG:25831", always_xy=True
        )
        x, y = transformer.transform(lon_v, lat_v)
        results["X_ETRS89"] = x
        results["Y_ETRS89"] = y
        results["EPSG_destino"] = "EPSG:25831"
        results["Huso"] = 31

    elif mode == "auto":
        zones = ((lon_v + 180.0) // 6.0).astype(int) + 1
        xs, ys, epsgs, husos = [], [], [], []
        for lon, lat, zone in zip(lon_v, lat_v, zones):
            if zone < 29:
                zone = 29
            if zone > 31:
                zone = 31
            epsg = f"EPSG:258{int(zone):02d}"
            try:
                transformer = Transformer.from_crs(
                    input_epsg, epsg, always_xy=True
                )
                x, y = transformer.transform(lon, lat)
            except Exception:
                x, y = float("nan"), float("nan")
            xs.append(x)
            ys.append(y)
            epsgs.append(epsg)
            husos.append(int(zone))
        results["X_ETRS89"] = xs
        results["Y_ETRS89"] = ys
        results["EPSG_destino"] = epsgs
        results["Huso"] = husos

    elif mode == "fixed":
        if fixed_zone is None:
            raise ValueError("fixed_zone must be provided when mode='fixed'")
        epsg = f"EPSG:258{int(fixed_zone):02d}"
        transformer = Transformer.from_crs(
            input_epsg, epsg, always_xy=True
        )
        x, y = transformer.transform(lon_v, lat_v)
        results["X_ETRS89"] = x
        results["Y_ETRS89"] = y
        results["EPSG_destino"] = epsg
        results["Huso"] = int(fixed_zone)

    else:
        raise ValueError(f"Unknown mode: {mode}")

    results["X_ETRS89"] = results["X_ETRS89"].round(3)
    results["Y_ETRS89"] = results["Y_ETRS89"].round(3)

    out = pd.concat(
        [df_out.reset_index(drop=True), results.reset_index(drop=True)],
        axis=1,
    )

    return out, n_valid, n_drop

