import sys
from pathlib import Path

import pandas as pd
import pytest
from pyproj import Transformer

sys.path.append(str(Path(__file__).resolve().parents[1]))
from converter import convert_dataframe


def test_forzar_31n_sample():
    df = pd.DataFrame({"Lat": [41.84346], "Lon": [1.03335]})
    out, n_valid, n_drop = convert_dataframe(
        df, "Lat", "Lon", mode="force_31n"
    )
    assert n_valid == 1
    assert n_drop == 0
    row = out.loc[0]
    assert row["Huso"] == 31
    assert row["X_ETRS89"] == pytest.approx(336724.563, abs=0.001)
    assert row["Y_ETRS89"] == pytest.approx(4634265.720, abs=0.001)


def test_decimal_comma_true():
    df = pd.DataFrame({"Lat": ["41,84346"], "Lon": ["1,03335"]})
    out, _, _ = convert_dataframe(
        df, "Lat", "Lon", mode="force_31n", use_decimal_comma=True
    )
    row = out.loc[0]
    assert row["Huso"] == 31
    assert row["X_ETRS89"] == pytest.approx(336724.563, abs=0.001)
    assert row["Y_ETRS89"] == pytest.approx(4634265.720, abs=0.001)


def test_decimal_comma_false_raises():
    df = pd.DataFrame({"Lat": ["41,84346"], "Lon": ["1,03335"]})
    with pytest.raises(ValueError):
        convert_dataframe(df, "Lat", "Lon", mode="force_31n")


def test_auto_multiple_zones():
    df = pd.DataFrame(
        {"Lat": [43.0, 40.0, 41.5], "Lon": [-8.0, -3.0, 1.5]}
    )
    out, n_valid, n_drop = convert_dataframe(df, "Lat", "Lon", mode="auto")
    assert n_valid == 3
    assert n_drop == 0
    assert out["EPSG_destino"].tolist() == [
        "EPSG:25829",
        "EPSG:25830",
        "EPSG:25831",
    ]
    expected = []
    for zone, lon, lat in zip([29, 30, 31], df["Lon"], df["Lat"]):
        transformer = Transformer.from_crs(
            "EPSG:4258", f"EPSG:258{zone:02d}", always_xy=True
        )
        expected.append(transformer.transform(lon, lat))
    for idx, (x, y) in enumerate(expected):
        assert out.loc[idx, "X_ETRS89"] == pytest.approx(x, abs=0.001)
        assert out.loc[idx, "Y_ETRS89"] == pytest.approx(y, abs=0.001)

