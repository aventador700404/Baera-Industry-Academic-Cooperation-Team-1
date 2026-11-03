"""맛별 판매 순위: 판독 주간 일평균, 직전 주간 대비 순위 변화, 잠식·시즌 신호."""
from __future__ import annotations

import pandas as pd

from ..config import LAUNCH, View
from . import fmt


def window_avg(brand_flavor: pd.DataFrame, v: View) -> pd.Series:
    """brand_flavor: date, flavor, qty (브랜드 합계). 구간 일평균, 큰 순."""
    seg = brand_flavor[(brand_flavor["date"] >= v.start) & (brand_flavor["date"] <= v.end)]
    days = (v.end - v.start).days + 1
    s = seg.groupby("flavor")["qty"].sum() / days
    return s[s > 0].sort_values(ascending=False)


def table(brand_flavor: pd.DataFrame, v: View, prev: View | None, pre: View) -> dict:
    now = window_avg(brand_flavor, v)
    prev_rank = list(window_avg(brand_flavor, prev).index) if prev else None
    pre_avg = window_avg(brand_flavor, pre)
    rows = []
    for i, (flavor, avg) in enumerate(now.items()):
        change = None
        if prev_rank is not None:
            change = "new" if flavor not in prev_rank else prev_rank.index(flavor) - i
        signals = []
        if flavor == LAUNCH.flavor:
            signals.append({"kind": "new", "text": "이달의 맛"})
        if v.id != "pre" and flavor in pre_avg:
            g = avg / pre_avg[flavor] - 1
            if flavor == LAUNCH.parent_flavor and g < -0.03:
                signals.append({"kind": "warn", "text": f"잠식 {fmt.pct(g)}"})
            elif flavor == LAUNCH.seasonal_flavor and g > 0.05:
                signals.append({"kind": "good", "text": f"시즌 +{fmt.pct(g)}"})
        rows.append({"rank": i + 1, "flavor": flavor, "avg": round(float(avg)), "change": change,
                     "signals": signals})
    return {"window": {"start": v.start.isoformat(), "end": v.end.isoformat()}, "rows": rows}
