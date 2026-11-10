"""모듈 1 · 신제품 반응: 검색·언급·긍정률, 주제별 판독, 반응을 끈 콘텐츠, 반응 대비 판매(전환)."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..config import HISTORY_START, LAUNCH, RULES


def pivot(reaction: pd.DataFrame, dates: list[dt.date]) -> dict[str, list[float | None]]:
    """날짜 축에 맞춘 시계열. 키: '{source}.{keyword}.{metric}'."""
    out = {}
    for (src, kw, met), g in reaction.groupby(["source", "keyword", "metric"]):
        s = g.groupby("date")["value"].mean().reindex(dates)
        out[f"{src}.{kw}.{met}"] = [None if pd.isna(x) else float(x) for x in s]
    return out


def z_two_prop(x1: float, n1: float, x2: float, n2: float) -> float:
    """두 비율 x1/n1, x2/n2 차이의 z 값. 표본이 작으면 같은 차이도 z가 작다 (우연일 수 있음)."""
    if n1 <= 0 or n2 <= 0:
        return 0.0
    p = (x1 + x2) / (n1 + n2)
    se = (p * (1 - p) * (1 / n1 + 1 / n2)) ** 0.5
    return (x1 / n1 - x2 / n2) / se if se > 0 else 0.0


def topic_flags(m3: float, pos3: float, neg3: float, tot3: float,
                m14: float, pos14: float, neg14: float, tot14: float) -> dict:
    """주제 하나의 최근 3일 vs 그 전 14일. 알림과 표가 같은 기준을 쓴다.
    긍정률 = 긍정 ÷ (긍정 + 부정). 감성이 안 잡힌 글은 빼고 본다 (블로그 전체 긍정률과 같은 정의)."""
    share, share_prev = (m3 / tot3 if tot3 else 0.0), (m14 / tot14 if tot14 else None)
    n3, n14 = pos3 + neg3, pos14 + neg14
    pos, pos_prev = (pos3 / n3 if n3 else None), (pos14 / n14 if n14 else None)
    enough = m3 >= RULES.topic_min_mentions
    surge = bool(enough and share_prev and share >= RULES.topic_surge_x * share_prev
                 and z_two_prop(m3, tot3, m14, tot14) >= RULES.signif_z)
    neg_up = bool(enough and pos is not None and pos_prev is not None and pos <= pos_prev - 0.15
                  and n3 >= RULES.topic_min_mentions and z_two_prop(pos14, n14, pos3, n3) >= RULES.signif_z)
    return {"share": share, "share_prev": share_prev, "pos": pos, "pos_prev": pos_prev, "surge": surge, "neg_up": neg_up}


def arr(series: list[float | None] | None, n: int) -> np.ndarray:
    if series is None:
        return np.full(n, np.nan)
    return np.array([np.nan if x is None else x for x in series], dtype=float)


def pre_month_mask(dates: list[dt.date]) -> np.ndarray:
    """출시 전 한 달(티저 전) = 판독 지표 '출시 전 한 달 일평균 대비'의 기준 기간."""
    return np.array([HISTORY_START <= d < LAUNCH.teaser for d in dates])


def summary(series: dict, dates: list[dt.date], asof: dt.date) -> dict:
    n = len(dates)
    upto = np.array([d <= asof for d in dates])
    pre = pre_month_mask(dates)
    after = np.array([d >= LAUNCH.launch for d in dates])
    bra = arr(series.get("naver_datalab.bra.search_index"), n)
    ment = arr(series.get("naver_blog.bra.mentions"), n)
    pos = arr(series.get("naver_blog.bra.positive_ratio"), n)
    out: dict = {}
    if np.isfinite(bra[upto]).any():
        i = int(np.nanargmax(np.where(upto, bra, np.nan)))
        base = float(np.nanmean(bra[pre])) if np.isfinite(bra[pre]).any() else np.nan
        last_i = int(np.where(upto & np.isfinite(bra))[0][-1])
        out.update(peak=float(bra[i]), peak_date=dates[i].isoformat(), pre_avg=base, last=float(bra[last_i]),
                   peak_x=float(bra[i] / base) if base else None, last_x=float(bra[last_i] / base) if base else None,
                   from_peak=float(bra[last_i] / bra[i]) if bra[i] else None)
    if np.isfinite(ment[upto]).any():
        idx = np.where(upto & np.isfinite(ment))[0][-7:]
        out["mentions_7d"] = float(np.nansum(ment[idx]))
        p = ment[pre & np.isfinite(ment)]
        out["mentions_pre_7d"] = float(p.mean() * 7) if len(p) else None
    pc, nc = arr(series.get("naver_blog.bra.positive"), n), arr(series.get("naver_blog.bra.negative"), n)
    if np.isfinite(pc[upto]).any():
        # 최근 7일 긍정·부정 건수를 합쳐서 (하루 비율의 평균은 글이 적은 날에 끌려간다)
        last7 = np.array([asof - dt.timedelta(days=6) <= d <= asof for d in dates])
        P, N = np.nansum(pc[last7]), np.nansum(pc[last7]) + np.nansum(nc[last7])
        if N >= RULES.sentiment_min_n:
            out["positive_7d"], out["positive_7d_n"] = float(P / N), int(N)
        return out
    p = pos[upto & after & np.isfinite(pos)]
    if not len(p):
        p = pos[upto & np.isfinite(pos)]
    if len(p):
        out["positive_7d"] = float(p[-7:].mean())
    return out


def topics_table(topics: pd.DataFrame | None, asof: dt.date) -> dict | None:
    """주제별 최근 3일 언급·긍정률과 그 전 14일 대비 비중 변화."""
    if topics is None or not len(topics):
        return None
    t3 = topics[(topics["date"] > asof - dt.timedelta(days=3)) & (topics["date"] <= asof)]
    t14 = topics[(topics["date"] > asof - dt.timedelta(days=17)) & (topics["date"] <= asof - dt.timedelta(days=3))]
    if t3.empty:
        return None
    g3 = t3.groupby("topic")[["mentions", "positive", "negative"]].sum()
    g14 = t14.groupby("topic")[["mentions", "positive", "negative"]].sum().reindex(g3.index).fillna(0)
    tot3, tot14 = g3["mentions"].sum(), g14["mentions"].sum()
    rows = []
    for topic, r in g3.sort_values("mentions", ascending=False).iterrows():
        q = g14.loc[topic]
        f = topic_flags(r.mentions, r.positive, r.negative, tot3, q.mentions, q.positive, q.negative, tot14)
        rows.append({"topic": topic, "mentions": int(r.mentions), "positive": int(r.positive),
                     "negative": int(r.negative), **f})   # 알림과 같은 기준 (alerts.py)
    return {"window": {"start": (asof - dt.timedelta(days=2)).isoformat(), "end": asof.isoformat()}, "rows": rows}


def conversion(dates_m: list[dt.date], sales: np.ndarray, series: dict, dates: list[dt.date],
               asof: dt.date) -> dict | None:
    """반응 대비 판매(전환): 출시 첫 주 = 100으로 맞춘 판매 지수 ÷ 검색 지수 (최근 7일 평균).

    1보다 크면 관심이 식는 속도보다 판매가 덜 빠짐 = 화제성보다 맛 수요가 판매를 끈다.
    1보다 작으면 관심은 남았는데 판매가 빠짐 = 품절·가격·접근성 점검.
    """
    first_week_end = LAUNCH.launch + dt.timedelta(days=6)
    if asof < first_week_end + dt.timedelta(days=7):
        return None
    bra = arr(series.get("naver_datalab.bra.search_index"), len(dates))
    s = pd.Series(sales, index=dates_m)
    b = pd.Series(bra, index=dates)
    fw = lambda x: x[(x.index >= LAUNCH.launch) & (x.index <= first_week_end)].mean()
    last7 = lambda x: x[(x.index > asof - dt.timedelta(days=7)) & (x.index <= asof)].mean()
    s_idx, b_idx = 100 * last7(s) / fw(s), 100 * last7(b) / fw(b)
    return {"sales_idx": float(s_idx), "search_idx": float(b_idx), "ratio": float(s_idx / b_idx)}


def youtube_top(yt: pd.DataFrame | None, asof: dt.date, top: int = 5) -> dict | None:
    """asof 시점 조회수 원값. 합계·비율·증가량 같은 파생 지표는 만들지 않는다 (YouTube API 정책)."""
    if yt is None or not len(yt):
        return None
    snap, basis = yt[yt["date"] <= asof], asof
    if snap.empty:
        # 지나간 기간을 나중에 수집한 경우 (과거 일별 조회수는 API로 못 받음):
        # 그 날까지 올라온 영상만 보여 주고, 조회수는 수집일 기준이라고 asof에 수집일을 적는다
        snap = yt[yt["published_at"] <= asof]
        if snap.empty:
            return None
        basis = snap["date"].max()
    snap = snap.sort_values("date").groupby("video_id").tail(1).sort_values("views", ascending=False)
    return {"asof": basis.isoformat(),
            "videos": [{"title": r.title, "channel_type": r.channel_type, "views": int(r.views)}
                       for r in snap.head(top).itertuples()]}


PROMO_GROUPS = ("barawk", "d31")   # config.COLLECT.promo_keyword_groups 의 행사 키와 맞춤


def promo_reaction(series: dict, dates: list[dt.date], promo: dict) -> dict | None:
    """행사명 검색지수가 행사 기간에 평소(행사 시작 전 4주 중앙값)의 몇 배였나. 브랜드 검색도 같이.

    반응 성과일 뿐 판매 증분이 아니다 (화제가 된 행사가 매출에 컸다는 뜻은 아님).
    31데이는 전날까지 사전예약이 있어 전날부터 본다."""
    key = next((g for g in PROMO_GROUPS if promo["id"].startswith(g)), None)
    if key is None:
        return None
    n = len(dates)
    s = arr(series.get(f"naver_datalab.promo_{key}.search_index"), n)
    b = arr(series.get("naver_datalab.promo_brand.search_index"), n)
    start, end = dt.date.fromisoformat(promo["start"]), dt.date.fromisoformat(promo["end"])
    w_from = start - dt.timedelta(days=1) if key == "d31" else start
    win = np.array([w_from <= d <= end for d in dates])
    base = np.array([start - dt.timedelta(days=28) <= d < w_from for d in dates])
    if not (np.isfinite(s[win]).any() and np.isfinite(s[base]).any()):
        return None

    def lift(x: np.ndarray) -> float | None:
        bv = float(np.nanmedian(x[base])) if np.isfinite(x[base]).any() else 0.0
        return float(np.nanmean(x[win]) / bv) if bv > 0 else None

    return {"lift": lift(s), "brand_lift": lift(b), "peak": float(np.nanmax(s[win])),
            "window": [w_from.isoformat(), end.isoformat()]}
