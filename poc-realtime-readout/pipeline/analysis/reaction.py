"""신제품 반응: 검색지수·블로그 언급·긍정률 (공개 API 형식), 유튜브 영상 조회수 (원값)."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..config import LAUNCH


def pivot(reaction: pd.DataFrame, dates: list[dt.date]) -> dict[str, list[float | None]]:
    """날짜 축에 맞춘 시계열. 키: '{source}.{keyword}.{metric}'."""
    out = {}
    for (src, kw, met), g in reaction.groupby(["source", "keyword", "metric"]):
        s = g.groupby("date")["value"].mean().reindex(dates)
        out[f"{src}.{kw}.{met}"] = [None if pd.isna(x) else float(x) for x in s]
    return out


def _arr(series: list[float | None]) -> np.ndarray:
    return np.array([np.nan if x is None else x for x in series], dtype=float)


def summary(series: dict, dates: list[dt.date], asof: dt.date) -> dict:
    upto = np.array([d <= asof for d in dates])
    pre_teaser = np.array([d < LAUNCH.teaser for d in dates])
    after_launch = np.array([d >= LAUNCH.launch for d in dates])
    bra = _arr(series.get("naver_datalab.bra.search_index", [None] * len(dates)))
    ment = _arr(series.get("naver_blog.bra.mentions", [None] * len(dates)))
    pos = _arr(series.get("naver_blog.bra.positive_ratio", [None] * len(dates)))
    out: dict = {}
    if np.isfinite(bra[upto]).any():
        b = np.where(upto, bra, np.nan)
        i = int(np.nanargmax(b))
        base = float(np.nanmean(bra[pre_teaser])) if np.isfinite(bra[pre_teaser]).any() else np.nan
        last_i = int(np.where(upto & np.isfinite(bra))[0][-1])
        out.update(peak=float(bra[i]), peak_date=dates[i].isoformat(), pre_avg=base,
                   last=float(bra[last_i]), peak_x=float(bra[i] / base) if base else None,
                   last_x=float(bra[last_i] / base) if base else None)
    if np.isfinite(ment[upto]).any():
        idx = np.where(upto & np.isfinite(ment))[0][-7:]
        out["mentions_7d"] = float(np.nansum(ment[idx]))
        pre = ment[pre_teaser & np.isfinite(ment)]
        out["mentions_pre_7d"] = float(pre.mean() * 7) if len(pre) else None
    p = pos[upto & after_launch & np.isfinite(pos)]
    if len(p):
        out["positive_7d"] = float(p[-7:].mean())
    elif np.isfinite(pos[upto]).any():
        out["positive_7d"] = float(pos[upto & np.isfinite(pos)][-1])
    return out


def youtube_top(yt: pd.DataFrame | None, asof: dt.date, top: int = 5) -> dict | None:
    """asof 시점 조회수 원값. 좋아요율 같은 파생 지표는 만들지 않는다 (YouTube API 정책)."""
    if yt is None or not len(yt):
        return None
    snap = yt[yt["date"] <= asof].sort_values("date").groupby("video_id").tail(1)
    if snap.empty:
        return None
    snap = snap.sort_values("views", ascending=False)
    # 영상별 원값만 넘긴다. 합계·비율도 파생 지표로 볼 수 있어 만들지 않는다.
    return {
        "asof": asof.isoformat(),
        "videos": [{"title": r.title, "channel_type": r.channel_type, "views": int(r.views)}
                   for r in snap.head(top).itertuples()],
    }
