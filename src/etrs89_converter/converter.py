import numpy as np
import pandas as pd
from functools import lru_cache
from pyproj import Transformer
from pyproj.exceptions import ProjError


@lru_cache(maxsize=None)
def _get_transformer(input_epsg: str, output_epsg: str) -> Transformer:
    """Return a cached ``Transformer`` for the given CRS pair."""
    return Transformer.from_crs(input_epsg, output_epsg, always_xy=True)


def convert_dataframe(
    df: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    mode: str,
    *,
    fixed_zone: int | None = None,
    use_decimal_comma: bool = False,
    input_epsg: str = "EPSG:4258",
    round_decimals: int = 3,
) -> tuple[pd.DataFrame, int, int]:
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
    round_decimals:
        Number of decimal places to round the output coordinates (default 3).

    Returns
    -------
    tuple[pd.DataFrame, int, int]
        converted_df: The converted DataFrame.
        n_valid: Number of valid rows.
        n_drop: Number of discarded rows.
    """
    if lat_col not in df.columns:
        raise ValueError(f"Column '{lat_col}' not found in DataFrame")
    if lon_col not in df.columns:
        raise ValueError(f"Column '{lon_col}' not found in DataFrame")

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

    if mode == "force_31n":
        results = pd.DataFrame(index=df_out.index)
        transformer = _get_transformer(input_epsg, "EPSG:25831")
        x, y = transformer.transform(lon_v, lat_v)
        results["X_ETRS89"] = x
        results["Y_ETRS89"] = y
        results["EPSG_destino"] = "EPSG:25831"
        results["Huso"] = 31

    elif mode == "auto":
        zones = np.clip(((lon_v + 180.0) // 6.0).astype(int) + 1, 29, 31)
        xs = np.full_like(lon_v, np.nan, dtype=float)
        ys = np.full_like(lat_v, np.nan, dtype=float)
        epsgs = np.empty(len(zones), dtype=object)
        husos = zones.astype(int)
        failed = np.zeros(len(zones), dtype=bool)
        last_error: ProjError | None = None
        for zone in np.unique(zones):
            epsg = f"EPSG:258{int(zone):02d}"
            mask = zones == zone
            try:
                transformer = _get_transformer(input_epsg, epsg)
                x, y = transformer.transform(lon_v[mask], lat_v[mask])
            except ProjError as exc:  # pragma: no cover - handled in tests
                failed[mask] = True
                last_error = exc
                continue
            xs[mask] = x
            ys[mask] = y
            epsgs[mask] = epsg
        if failed.any():
            n_fail = int(failed.sum())
            df_out = df_out.loc[~failed].copy()
            xs = xs[~failed]
            ys = ys[~failed]
            epsgs = epsgs[~failed]
            husos = husos[~failed]
            n_valid -= n_fail
            n_drop += n_fail
            if n_valid == 0:
                raise ValueError(
                    f"Coordinate transformation failed for all rows: {last_error}"
                )
        results = pd.DataFrame(index=df_out.index)
        results["X_ETRS89"] = xs
        results["Y_ETRS89"] = ys
        results["EPSG_destino"] = epsgs
        results["Huso"] = husos

    elif mode == "fixed":
        results = pd.DataFrame(index=df_out.index)
        if fixed_zone is None:
            raise ValueError("fixed_zone must be provided when mode='fixed'")
        if fixed_zone not in (29, 30, 31):
            raise ValueError("fixed_zone must be one of 29, 30, or 31")
        epsg = f"EPSG:258{int(fixed_zone):02d}"
        transformer = _get_transformer(input_epsg, epsg)
        x, y = transformer.transform(lon_v, lat_v)
        results["X_ETRS89"] = x
        results["Y_ETRS89"] = y
        results["EPSG_destino"] = epsg
        results["Huso"] = int(fixed_zone)

    else:
        raise ValueError(f"Unknown mode: {mode}")

    results["X_ETRS89"] = results["X_ETRS89"].round(round_decimals)
    results["Y_ETRS89"] = results["Y_ETRS89"].round(round_decimals)

    out = pd.concat(
        [df_out.reset_index(drop=True), results.reset_index(drop=True)],
        axis=1,
    )

    return out, n_valid, n_drop

