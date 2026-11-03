"""매장 순위 급변과 '왜'.

순위 = 판독 주간 일평균 판매(전 맛 합계) 기준 전국 순위.
신호:
  반응↑ 판매↓ 점검: 주변 SNS 언급이 크게 늘었는데 순위가 떨어짐 → 품절·운영 의심
  확산 / 상승: 순위가 크게 오름
설명('왜'): 매장 주변 맥락(유동인구, 경쟁점) → 매장 유형 전반 흐름 → 없으면 비움
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..config import LAUNCH, RULES, View
from . import fmt


def weekly_rank(store_daily: pd.DataFrame, v: View) -> pd.DataFrame:
    """store_daily: date, store_id, qty (전 맛 합계)."""
    seg = store_daily[(store_daily["date"] >= v.start) & (store_daily["date"] <= v.end)]
    days = (v.end - v.start).days + 1
    avg = seg.groupby("store_id")["qty"].sum() / days
    rank = avg.rank(ascending=False, method="first").astype(int)
    return pd.DataFrame({"avg": avg, "rank": rank})


def _context_note(ctx: pd.DataFrame | None, store_id: str, v: View) -> str | None:
    if ctx is None or not len(ctx):
        return None
    lo = v.start - dt.timedelta(days=7)
    hit = ctx[(ctx["store_id"] == store_id) & (ctx["week_start"] >= lo) & (ctx["week_start"] <= v.end)]
    return hit.iloc[-1]["note"] if len(hit) else None


def table(store_daily: pd.DataFrame, sm: pd.DataFrame, v: View, prev: View,
          sns: pd.DataFrame | None, ctx: pd.DataFrame | None, top: int = 6,
          prev_checks: set[str] | None = None) -> dict:
    now, before = weekly_rank(store_daily, v), weekly_rank(store_daily, prev)
    df = sm.set_index("store_id")[["store_name", "type"]].join(now).join(before, rsuffix="_prev")
    df["delta"] = df["rank_prev"] - df["rank"]                 # +면 순위 상승
    df["growth"] = df["avg"] / df["avg_prev"] - 1
    type_growth = df.groupby("type").apply(lambda g: g["avg"].sum() / g["avg_prev"].sum() - 1)
    type_delta = df.groupby("type")["delta"].median()          # 유형 전체가 같이 움직였는지
    if sns is not None and len(sns):
        s_now = sns[sns["week_start"] == v.start].set_index("store_id")["mentions"]
        s_prev = sns[sns["week_start"] == prev.start].set_index("store_id")["mentions"]
        df["sns"] = s_now.reindex(df.index).fillna(0).astype(int)
        df["sns_prev"] = s_prev.reindex(df.index).fillna(0).astype(int)
        df["sns_pct"] = (df["sns"] - df["sns_prev"]) / df["sns_prev"].clip(lower=1) * 100
    else:
        df["sns"] = df["sns_prev"] = 0
        df["sns_pct"] = np.nan

    def flag(r) -> str | None:
        if (r.sns >= RULES.store_sns_min_mentions and r.sns_pct >= RULES.store_sns_up_pct
                and r.delta <= -RULES.store_rank_drop):
            return "check"
        if r.delta >= RULES.store_rank_rise:
            return "spread"
        if r.delta >= RULES.store_rank_rise / 2:
            return "rise"
        if r.delta <= -RULES.store_rank_drop:
            return "drop"
        return None

    df["flag"] = [flag(r) for r in df.itertuples()]
    df["ctx"] = [_context_note(ctx, sid, v) for sid in df.index]
    why = []
    for r in df.itertuples():
        if r.ctx:
            why.append(r.ctx)
        elif r.flag == "check":
            why.append("반응은 느는데 판매 감소 → 품절·재고·운영 의심")
        elif prev_checks and r.Index in prev_checks and r.delta > 0:
            why.append("지난 판독의 점검 매장, 판매 회복")
        else:
            td = type_delta[r.type]
            same_dir = abs(td) >= 50 and np.sign(td) == np.sign(r.delta)
            why.append(f"{r.type} 매장 전반 순위 {'상승' if td > 0 else '하락'} (중앙값 {fmt.signed(td)})"
                       if same_dir else None)
    df["why"] = why

    pick = pd.concat([
        df[df["flag"] == "check"],
        df[df["ctx"].notna() & (df["delta"].abs() >= 50)],
        df.reindex(df["delta"].abs().sort_values(ascending=False).index),
    ])
    pick = pick[~pick.index.duplicated()].head(top)
    rows = [{
        "store_id": sid, "name": r.store_name, "type": r.type, "rank": int(r["rank"]),
        "rank_prev": int(r.rank_prev), "delta": int(r.delta), "sns": int(r.sns), "sns_prev": int(r.sns_prev),
        "sns_pct": None if pd.isna(r.sns_pct) else round(float(r.sns_pct)), "flag": r.flag, "why": r.why if isinstance(r.why, str) else None,
    } for sid, r in pick.iterrows()]
    return {
        "rows": rows, "total": int(len(df)),
        "check_ids": sorted(df.index[df["flag"] == "check"]),
        "alert": next((r for r in rows if r["flag"] == "check"), None),
        "riser": _row(df, df["delta"].idxmax()),
        "counts": {k: int((df["flag"] == k).sum()) for k in ("check", "spread", "drop")},
        "type_growth": {k: round(float(g), 4) for k, g in type_growth.items()},
        "type_delta": {k: int(d) for k, d in type_delta.items()},
    }


def _row(df: pd.DataFrame, sid: str) -> dict:
    r = df.loc[sid]
    return {"store_id": sid, "name": r.store_name, "type": r.type, "rank": int(r["rank"]),
            "rank_prev": int(r.rank_prev), "delta": int(r.delta),
            "why": r.why if isinstance(r.why, str) else None}


def type_peaks(flavor_store_daily: pd.DataFrame, sm: pd.DataFrame, asof: dt.date) -> list[dict]:
    """매장 유형별로 이달의 맛 판매가 다른 유형보다 가장 몰린 날 (출시 후 n일차).

    상대지수 = 그 유형 매장당 판매 ÷ 전체 매장당 판매 (3일 이동평균). 1보다 크면 그 유형에 몰림.
    최고점 뒤로 이틀 이상 데이터가 있어야 '확정'.
    """
    x = flavor_store_daily[flavor_store_daily["date"] <= asof].merge(sm[["store_id", "type"]], on="store_id")
    if x.empty:
        return []
    per = x.groupby(["date", "type"])["qty"].sum().unstack()
    cnt = sm["type"].value_counts()
    overall = x.groupby("date")["qty"].sum() / len(sm)
    rel = (per / cnt).div(overall, axis=0).rolling(3, center=True, min_periods=2).mean()
    last = max(rel.index)
    out = []
    for t in rel.columns:
        d = rel[t].idxmax()
        out.append({
            "type": t, "day": (d - LAUNCH.launch).days + 1, "date": d.isoformat(),
            "index": round(float(rel[t].max()), 3), "firm": (last - d).days >= 2,
        })
    return sorted(out, key=lambda r: r["day"])
