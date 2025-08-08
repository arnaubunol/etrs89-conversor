import sys
from pathlib import Path

import pandas as pd
import pytest

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

