import pandas as pd
import pytest
from pyproj import Transformer
from pyproj.exceptions import ProjError

from etrs89_converter.converter import _get_transformer, convert_dataframe


@pytest.fixture(autouse=True)
def clear_transformer_cache():
    _get_transformer.cache_clear()


def _expected_coords(zones, lons, lats):
    coords = []
    for zone, lon, lat in zip(zones, lons, lats):
        transformer = Transformer.from_crs(
            "EPSG:4258", f"EPSG:258{zone:02d}", always_xy=True
        )
        coords.append(transformer.transform(lon, lat))
    return coords


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


def test_round_decimals_changes_precision():
    df = pd.DataFrame({"Lat": [41.84346], "Lon": [1.03335]})
    out2, _, _ = convert_dataframe(
        df, "Lat", "Lon", mode="force_31n", round_decimals=2
    )
    out4, _, _ = convert_dataframe(
        df, "Lat", "Lon", mode="force_31n", round_decimals=4
    )
    row2 = out2.loc[0]
    row4 = out4.loc[0]
    assert row2["X_ETRS89"] == 336724.56
    assert row2["Y_ETRS89"] == 4634265.72
    assert row4["X_ETRS89"] == 336724.5628
    assert row4["Y_ETRS89"] == 4634265.7204


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
    expected = _expected_coords([29, 30, 31], df["Lon"], df["Lat"])
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
    expected = _expected_coords([29, 30, 31], df["Lon"], df["Lat"])
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
    expected = _expected_coords([29, 31], df["Lon"], df["Lat"])
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


@pytest.mark.parametrize("zone", [28, 32])
def test_fixed_mode_zone_out_of_range_raises(zone):
    df = pd.DataFrame({"Lat": [40.0], "Lon": [-3.0]})
    with pytest.raises(ValueError, match="29, 30, or 31"):
        convert_dataframe(df, "Lat", "Lon", mode="fixed", fixed_zone=zone)


def test_auto_projerror_drops_rows(monkeypatch):
    df = pd.DataFrame({"Lat": [43.0, 40.0, 41.5], "Lon": [-8.0, -3.0, 1.5]})
    original_from_crs = Transformer.from_crs

    def failing_from_crs(src, dest, always_xy=True):
        if dest == "EPSG:25830":
            raise ProjError("failure for zone 30")
        return original_from_crs(src, dest, always_xy=always_xy)

    monkeypatch.setattr(Transformer, "from_crs", staticmethod(failing_from_crs))
    out, n_valid, n_drop = convert_dataframe(df, "Lat", "Lon", mode="auto")
    assert n_valid == 2
    assert n_drop == 1
    assert out["Huso"].tolist() == [29, 31]


def test_auto_projerror_all_rows_raise():
    df = pd.DataFrame({"Lat": [43.0], "Lon": [-8.0]})
    with pytest.raises(ValueError, match="Coordinate transformation failed"):
        convert_dataframe(
            df,
            "Lat",
            "Lon",
            mode="auto",
            input_epsg="EPSG:999999",
        )


