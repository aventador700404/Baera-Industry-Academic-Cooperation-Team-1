"""모듈 2 · 맛별 판매 순위: 최근 7일 일평균, 그 전 7일 대비 순위 변화, 잠식·시즌 신호."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from ..config import LAUNCH, PRE_WEEK
from . import fmt

WEEK = dt.timedelta(days=6)


def window_avg(brand_flavor: pd.DataFrame, start: dt.date, end: dt.date) -> pd.Series:
    """brand_flavor: date, flavor, qty (브랜드 합계). 구간 일평균, 큰 순."""
    seg = brand_flavor[(brand_flavor["date"] >= start) & (brand_flavor["date"] <= end)]
    s = seg.groupby("flavor")["qty"].sum() / ((end - start).days + 1)
    return s[s > 0].sort_values(ascending=False)


def table(brand_flavor: pd.DataFrame, asof: dt.date) -> dict:
    start = asof - WEEK
    now = window_avg(brand_flavor, start, asof)
    prev_rank = list(window_avg(brand_flavor, start - dt.timedelta(days=7), asof - dt.timedelta(days=7)).index)
    pre_avg = window_avg(brand_flavor, *PRE_WEEK)
    launched = asof >= LAUNCH.launch
    rows = []
    for i, (flavor, avg) in enumerate(now.items()):
        change = "new" if flavor not in prev_rank else prev_rank.index(flavor) - i
        signals = []
        if flavor == LAUNCH.flavor:
            signals.append({"kind": "new", "text": "이달의 맛"})
        if launched and flavor in pre_avg:
            g = avg / pre_avg[flavor] - 1
            if flavor == LAUNCH.parent_flavor and g < -0.03:
                signals.append({"kind": "warn", "text": f"잠식 {fmt.pct(g)}"})
            elif flavor == LAUNCH.seasonal_flavor and g > 0.05:
                signals.append({"kind": "good", "text": f"시즌 +{fmt.pct(g)}"})
        rows.append({"rank": i + 1, "flavor": flavor, "avg": round(float(avg)), "change": change, "signals": signals})
    return {"window": {"start": start.isoformat(), "end": asof.isoformat()}, "rows": rows}
