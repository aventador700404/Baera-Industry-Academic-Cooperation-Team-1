"""목 데이터가 공개 앵커와 정보공개서 숫자에 맞는지."""
import pandas as pd

from pipeline.config import LAUNCH
from pipeline.io import load_all


def test_anchors_exact():
    s = load_all()["sales_daily"]
    m = s[s["flavor"] == LAUNCH.flavor].groupby("date")["qty"].sum()
    for d, cum in LAUNCH.anchors:
        assert int(m[m.index <= d].sum()) == cum


def test_store_count_matches_disclosure():
    assert len(load_all()["store_master"]) == LAUNCH.stores_total


def test_no_monthly_flavor_before_launch():
    s = load_all()["sales_daily"]
    assert s[(s["flavor"] == LAUNCH.flavor) & (s["date"] < LAUNCH.launch)].empty
