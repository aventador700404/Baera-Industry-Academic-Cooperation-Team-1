"""판촉 행사 효과: 행사 기간 판매 − 기준선 = 증분. 증분 ROI = 증분 매출 ÷ 할인 비용."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..config import RULES
from .baseline import Baseline

MIN_FIT_DAYS = 10  # 기준선을 맞춘 행사 없는 날이 이보다 적으면 판정은 잠정


def verdict(roi: float) -> tuple[str, str]:
    if roi >= RULES.roi_keep:
        return "good", "지속"
    if roi >= RULES.roi_adjust:
        return "warn", "조정"
    return "crit", "중단 검토"


def evaluate(promos: pd.DataFrame, dates: list[dt.date], qty: np.ndarray, bl: Baseline | None,
             asof: dt.date, price: int) -> list[dict]:
    out = []
    for p in promos.sort_values("start").itertuples():
        row = {"id": p.promo_id, "name": p.name, "start": p.start.isoformat(), "end": p.end.isoformat(),
               "desc": p.desc, "rate": float(p.discount_rate)}
        if p.end > asof or bl is None:
            # pending = 끝났지만 기준선을 맞출 행사 없는 날이 아직 부족
            row["status"] = "planned" if p.start > asof else "running" if p.end > asof else "pending"
            out.append(row)
            continue
        sel = np.array([p.start <= d <= p.end for d in dates])
        act = float(qty[sel].sum())
        if act <= 0:  # 행사 기간 판매 데이터가 아직 안 들어옴
            row["status"] = "pending"
            out.append(row)
            continue
        base, lo, hi = (float(x[sel].sum()) for x in (bl.base, bl.lo, bl.hi))
        # 곡선 모양(k) 불확실성에 더해, 하루 변동에서 오는 기준선 수준 오차와 행사 기간 판매의 변동을 더한다 (약 95%)
        err = 2 * bl.sigma * np.sqrt(1 / max(bl.n_fit, 1) + 1 / int(sel.sum())) * base
        lo, hi = lo - err, hi + err
        cost_units = act * p.discount_rate      # 할인 비용을 개수로 환산 (단가는 약분됨)
        inc, inc_lo, inc_hi = act - base, act - hi, act - lo
        roi, roi_lo, roi_hi = (x / cost_units for x in (inc, inc_lo, inc_hi))
        v = verdict(roi)
        row.update({
            "status": "done", "act": act, "base": base, "inc": inc, "inc_lo": inc_lo, "inc_hi": inc_hi,
            "inc_pct": inc / base if base else 0.0, "cost_won": cost_units * price,
            "roi": roi, "roi_lo": roi_lo, "roi_hi": roi_hi,
            "verdict": v[0], "verdict_label": v[1],
            "n_fit": bl.n_fit,
        })
        # 잠정 사유: 기준선을 맞춘 행사 없는 날이 적거나, ROI 범위 양 끝의 판정이 다름
        same = verdict(roi_lo)[1] == verdict(roi_hi)[1]
        row["firm"] = same and bl.n_fit >= MIN_FIT_DAYS
        row["tentative_reason"] = None if row["firm"] else ("few_days" if bl.n_fit < MIN_FIT_DAYS else "range")
        out.append(row)
    return out


def first_week_split(dates: list[dt.date], qty: np.ndarray, bl: Baseline | None,
                     promo_mask: np.ndarray, launch: dt.date) -> dict | None:
    if bl is None:
        return None
    sel = np.array([0 <= (d - launch).days < 7 for d in dates])
    total = float(qty[sel].sum())
    inc = float(np.clip(qty - bl.base, 0, None)[sel & promo_mask].sum())
    return {"total": total, "promo": inc, "demand": total - inc, "promo_share": inc / total if total else 0.0}
