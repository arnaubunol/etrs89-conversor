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


@pytest.mark.parametrize(
    "cols,missing",
    [
        ({"Lat": [41.0]}, "Lon"),
        ({"Lon": [1.0]}, "Lat"),
    ],
)
def test_missing_columns_raise(cols, missing):
    df = pd.DataFrame(cols)
    with pytest.raises(ValueError, match=missing):
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


def test_auto_zone_boundaries():
    df = pd.DataFrame({"Lat": [40.0, 40.0, 40.0], "Lon": [-12.0, -6.0, 0.0]})
    out, n_valid, n_drop = convert_dataframe(df, "Lat", "Lon", mode="auto")
    assert n_valid == 3
    assert n_drop == 0
    assert out["Huso"].tolist() == [29, 30, 31]
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


def test_auto_clamps_longitudes():
    df = pd.DataFrame({"Lat": [40.0, 40.0], "Lon": [-25.0, 9.0]})
    out, n_valid, n_drop = convert_dataframe(df, "Lat", "Lon", mode="auto")
    assert n_valid == 2
    assert n_drop == 0
    assert out["Huso"].tolist() == [29, 31]
    assert out["EPSG_destino"].tolist() == [
        "EPSG:25829",
        "EPSG:25831",
    ]
    expected = []
    for zone, lon, lat in zip([29, 31], df["Lon"], df["Lat"]):
        transformer = Transformer.from_crs(
            "EPSG:4258", f"EPSG:258{zone:02d}", always_xy=True
        )
        expected.append(transformer.transform(lon, lat))
    for idx, (x, y) in enumerate(expected):
        assert out.loc[idx, "X_ETRS89"] == pytest.approx(x, abs=0.001)
        assert out.loc[idx, "Y_ETRS89"] == pytest.approx(y, abs=0.001)


def test_fixed_mode_coordinates():
    df = pd.DataFrame({"Lat": [40.0], "Lon": [-3.0]})
    out, n_valid, n_drop = convert_dataframe(
        df, "Lat", "Lon", mode="fixed", fixed_zone=30
    )
    assert n_valid == 1
    assert n_drop == 0
    row = out.loc[0]
    assert row["Huso"] == 30
    transformer = Transformer.from_crs(
        "EPSG:4258", "EPSG:25830", always_xy=True
    )
    x, y = transformer.transform(-3.0, 40.0)
    assert row["X_ETRS89"] == pytest.approx(x, abs=0.001)
    assert row["Y_ETRS89"] == pytest.approx(y, abs=0.001)
    assert row["EPSG_destino"] == "EPSG:25830"


def test_fixed_mode_requires_zone():
    df = pd.DataFrame({"Lat": [40.0], "Lon": [-3.0]})
    with pytest.raises(ValueError):
        convert_dataframe(df, "Lat", "Lon", mode="fixed")


def test_auto_mode_boundaries_selection():
    """Auto mode picks the correct UTM zone for boundary longitudes."""
    df = pd.DataFrame({"Lat": [40.0, 40.0, 40.0], "Lon": [-12.0, -6.0, 0.0]})
    out, n_valid, n_drop = convert_dataframe(df, "Lat", "Lon", mode="auto")
    assert n_valid == 3
    assert n_drop == 0
    assert out["Huso"].tolist() == [29, 30, 31]


def test_auto_mode_clamps_out_of_range_longitudes():
    """Auto mode clamps longitudes outside 29–31 to the valid range."""
    df = pd.DataFrame({"Lat": [40.0, 40.0], "Lon": [-25.0, 9.0]})
    out, n_valid, n_drop = convert_dataframe(df, "Lat", "Lon", mode="auto")
    assert n_valid == 2
    assert n_drop == 0
    assert out["Huso"].tolist() == [29, 31]


def test_fixed_mode_returns_expected_coordinates():
    """Fixed mode converts to the requested UTM zone with correct coordinates."""
    df = pd.DataFrame({"Lat": [40.0], "Lon": [-3.0]})
    out, n_valid, n_drop = convert_dataframe(
        df, "Lat", "Lon", mode="fixed", fixed_zone=30
    )
    assert n_valid == 1
    assert n_drop == 0
    row = out.loc[0]
    assert row["Huso"] == 30
    transformer = Transformer.from_crs("EPSG:4258", "EPSG:25830", always_xy=True)
    x, y = transformer.transform(-3.0, 40.0)
    assert row["X_ETRS89"] == pytest.approx(x, abs=0.001)
    assert row["Y_ETRS89"] == pytest.approx(y, abs=0.001)
    assert row["EPSG_destino"] == "EPSG:25830"


def test_fixed_mode_missing_zone_raises_value_error():
    """Omitting fixed_zone in fixed mode results in a ValueError."""
    df = pd.DataFrame({"Lat": [40.0], "Lon": [-3.0]})
    with pytest.raises(ValueError):
        convert_dataframe(df, "Lat", "Lon", mode="fixed")

