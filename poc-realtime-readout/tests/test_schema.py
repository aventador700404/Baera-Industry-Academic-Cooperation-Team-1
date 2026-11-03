import pandas as pd
import pytest

from pipeline.schema import SchemaError, coerce


def test_missing_column_raises():
    with pytest.raises(SchemaError, match="qty"):
        coerce("sales_daily", pd.DataFrame({"date": ["2026-03-01"], "store_id": ["S1"], "flavor": ["a"]}))


def test_negative_qty_raises():
    df = pd.DataFrame({"date": ["2026-03-01"], "store_id": ["S1"], "flavor": ["a"], "qty": [-1]})
    with pytest.raises(SchemaError):
        coerce("sales_daily", df)


def test_extra_columns_dropped_and_types_coerced():
    df = pd.DataFrame({"date": ["2026-03-01"], "store_id": [101], "flavor": ["a"], "qty": ["7"], "memo": ["x"]})
    out = coerce("sales_daily", df)
    assert list(out.columns) == ["date", "store_id", "flavor", "qty"]
    assert out["store_id"].iloc[0] == "101" and out["qty"].iloc[0] == 7
