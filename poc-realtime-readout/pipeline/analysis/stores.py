"""모듈 3 · 매장 순위 급등: 최근 7일 vs 그 전 7일, 판매 순위 변화를 매장 주변 SNS 반응으로 판독.

순위 = 7일 일평균 판매(전 맛 합계) 기준 전국 순위.
판독 (반응으로만 읽는다):
  (주변 언급↑ = 7일 15건 이상, 10건 이상 늘었고, 전국 언급 흐름보다 60% 이상 더 늘어남)
  점검   주변 언급↑ + 순위↓  → 품절·재고·운영 의심
  바이럴 주변 언급↑ + 순위↑  → 콘텐츠·입소문 확산, 재고 선배치
  회복   지난 점검 매장의 순위 회복
  그 외  반응 변화 없이 판매만 움직임 → 확인 필요
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..config import RULES

WEEK = dt.timedelta(days=6)


def _window(df: pd.DataFrame, start: dt.date, end: dt.date, col: str) -> pd.Series:
    seg = df[(df["date"] >= start) & (df["date"] <= end)]
    return seg.groupby("store_id")[col].sum()


def table(store_daily: pd.DataFrame, sm: pd.DataFrame, sns: pd.DataFrame | None, asof: dt.date,
          prev_flags: dict[str, str] | None = None, top: int = 5, watch: set[str] | None = None) -> dict:
    """store_daily: date, store_id, qty (전 맛 합계). sns: date, store_id, mentions."""
    s1, s0 = asof - WEEK, asof - WEEK - dt.timedelta(days=7)
    e0 = asof - dt.timedelta(days=7)
    now = _window(store_daily, s1, asof, "qty") / 7
    before = _window(store_daily, s0, e0, "qty") / 7
    df = sm.set_index("store_id")[["store_name"]].copy()
    df["avg"], df["avg_prev"] = now.reindex(df.index).fillna(0), before.reindex(df.index).fillna(0)
    df["rank"] = df["avg"].rank(ascending=False, method="first").astype(int)
    df["rank_prev"] = df["avg_prev"].rank(ascending=False, method="first").astype(int)
    df["delta"] = df["rank_prev"] - df["rank"]                       # +면 순위 상승
    if sns is not None and len(sns):
        df["sns"] = _window(sns, s1, asof, "mentions").reindex(df.index).fillna(0).astype(int)
        df["sns_prev"] = _window(sns, s0, e0, "mentions").reindex(df.index).fillna(0).astype(int)
    else:
        df["sns"] = df["sns_prev"] = 0
    df["sns_pct"] = (df["sns"] - df["sns_prev"]) / df["sns_prev"].clip(lower=1) * 100
    # 전국 언급 흐름 대비 초과 증가율: (매장 증가 배수 ÷ 전국 증가 배수 − 1).
    # 언급이 적은 매장의 0→3건 같은 배수 폭증을 막으려고 양쪽에 5건씩 더해서 배수를 잰다.
    nat = df["sns"].sum() / max(df["sns_prev"].sum(), 1)
    df["sns_excess"] = (((df["sns"] + 5) / (df["sns_prev"] + 5)) / nat - 1) * 100
    sns_up = ((df["sns"] >= RULES.store_sns_min_mentions)
              & (df["sns"] - df["sns_prev"] >= RULES.store_sns_min_increase)
              & (df["sns_excess"] >= RULES.store_sns_up_pct))
    prev_flags = prev_flags or {}

    def flag(sid: str, r) -> tuple[str | None, str | None]:
        if sns_up[sid] and r.delta <= -RULES.store_rank_drop:
            return "check", "주변 언급은 느는데 판매 감소 → 품절·재고·운영 의심"
        if sns_up[sid] and r.delta >= RULES.store_rank_rise:
            return "viral", "주변 언급과 판매가 같이 급증 → 콘텐츠·입소문 확산"
        if prev_flags.get(sid) == "check" and r.delta > 0:
            return "recover", "지난 점검 매장, 판매 회복"
        if r.delta >= RULES.store_rank_rise:
            return "rise", None
        if r.delta <= -RULES.store_rank_drop:
            return "drop", None
        return None, None

    fw = [flag(sid, r) for sid, r in df.iterrows()]
    df["flag"], df["why"] = [f for f, _ in fw], [w for _, w in fw]
    order = {"check": 0, "viral": 1, "recover": 2}
    pick = pd.concat([
        df[df["flag"].isin(order)].assign(o=lambda x: x["flag"].map(order)).sort_values(["o", "delta"]),
        df.reindex(df["delta"].abs().sort_values(ascending=False).index),
    ])
    pick = pick[~pick.index.duplicated()].head(top)

    def row(sid: str, r) -> dict:
        return {"store_id": sid, "name": r.store_name, "rank": int(r["rank"]), "rank_prev": int(r.rank_prev),
                "delta": int(r.delta), "sns": int(r.sns), "sns_prev": int(r.sns_prev),
                "flag": r.flag, "why": r.why if isinstance(r.why, str) else None}

    rows = [row(sid, r) for sid, r in pick.iterrows()]
    flagged = {sid: f for sid, f in df["flag"].items() if f in ("check", "viral")}
    return {
        "window": {"start": s1.isoformat(), "end": asof.isoformat()},
        "rows": rows, "total": int(len(df)), "national_sns_change": float(nat - 1),
        "counts": {k: int((df["flag"] == k).sum()) for k in ("check", "viral", "rise", "drop")},
        "flags": flagged,
        "alerts": [row(sid, df.loc[sid]) for sid in flagged],
        "riser": row(df["delta"].idxmax(), df.loc[df["delta"].idxmax()]),
        # 주간 판독용: 이번 주에 알림이 떴던 매장의 판독 시점 상태
        "watch": {sid: row(sid, df.loc[sid]) for sid in (watch or set()) if sid in df.index},
    }
