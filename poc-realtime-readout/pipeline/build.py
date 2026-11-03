"""모든 테이블 → 판독 시점별 계산 → web/public/data/readout.json.

웹은 이 JSON만 읽는다. 계산 로직은 전부 여기(파이썬)에 있고 테스트된다.
실행: python -m pipeline.build
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pandas as pd

from .analysis import cards, flavor, promo, reaction, stores
from .analysis import fmt
from .analysis.baseline import estimate_dow, fit_baseline
from .config import LAUNCH, RULES, VIEWS, WEB_OUT, View, assumptions_text
from .io import load_all
from .schema import TABLES

PROV_LABEL = {"raw": "본사 데이터", "api": "공개 API", "mixed": "공개 API + 목", "mock": "목"}


def daterange(a: dt.date, b: dt.date) -> list[dt.date]:
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def _clean(x):
    """JSON으로 못 가는 값 정리 (NaN, numpy 타입, 날짜)."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, np.ndarray):
        return _clean(x.tolist())
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else round(float(x), 4)
    if isinstance(x, (dt.date,)):
        return x.isoformat()
    return x


def build() -> dict:
    T = load_all()
    L = LAUNCH
    sales, sm, promos = T["sales_daily"], T["store_master"], T["promo_calendar"]
    flavor_sales = sales[sales["flavor"] == L.flavor]

    dates_m = daterange(L.launch, L.month_end)
    q = flavor_sales.groupby("date")["qty"].sum().reindex(dates_m).fillna(0).to_numpy(dtype=float)
    promo_mask = np.array([any(p.start <= d <= p.end for p in promos.itertuples()) for d in dates_m])
    dow = estimate_dow(sales[sales["flavor"] != L.flavor].groupby("date")["qty"].sum(), L.launch)
    brand_flavor = sales.groupby(["date", "flavor"], as_index=False)["qty"].sum()
    store_daily = sales.groupby(["date", "store_id"], as_index=False)["qty"].sum()

    reac = T["reaction_daily"]
    chart_start = min(min(reac["date"]), L.launch - dt.timedelta(days=28))
    dates = daterange(chart_start, L.month_end)
    series = reaction.pivot(reac, dates)
    sales_on_axis = [float(q[dates_m.index(d)]) if d in dates_m else None for d in dates]

    trend = series.get("naver_datalab.trend.search_index")
    month_avg_by_flavor = flavor.window_avg(
        brand_flavor, View("month", "월", L.month_end, L.month_end, L.launch, L.month_end))

    views, prev_checks = [], set()
    for i, v in enumerate(VIEWS):
        launched = v.to >= L.launch
        bl = fit_baseline(dates_m, q, promo_mask, dow, L.launch, asof=v.to) if launched else None
        upto = np.array([d <= v.to for d in dates_m])
        cum = float(q[upto].sum())
        promo_rows = promo.evaluate(promos, dates_m, q, bl, v.to, L.unit_price)
        promo_inc = float(np.clip(q - bl.base, 0, None)[upto & promo_mask].sum()) if bl else 0.0
        wsel = np.array([v.start <= d <= v.end for d in dates_m])
        w_avg = float(q[wsel].mean()) if wsel.any() else 0.0
        demand = np.where(promo_mask, bl.base, q) if bl else q
        w_demand = float(demand[wsel].mean()) if wsel.any() else 0.0
        rs = reaction.summary(series, dates, v.to)

        trend_change = None
        if trend:
            di = dates.index(v.to)
            if di >= 21 and trend[di] and trend[di - 21]:
                trend_change = trend[di] / trend[di - 21] - 1

        st = None
        if i > 0:
            st = stores.table(store_daily, sm, v, VIEWS[i - 1],
                              T.frames.get("store_reaction_weekly"), T.frames.get("store_context_weekly"),
                              prev_checks=prev_checks)
            prev_checks = set(st["check_ids"])
        peaks = stores.type_peaks(flavor_sales, sm, v.to) if launched and (v.to - L.launch).days >= 6 else []
        peak_date = rs.get("peak_date")
        for p in peaks:
            p["lag_from_reaction"] = (dt.date.fromisoformat(p["date"]) - dt.date.fromisoformat(peak_date)).days \
                if peak_date else None

        month_rank = list(month_avg_by_flavor.index).index(L.flavor) + 1 if L.flavor in month_avg_by_flavor else None
        ctx = {
            "reaction": rs, "trend_change": trend_change, "cum": cum, "w_avg": w_avg, "w_demand": w_demand,
            "promos": promo_rows, "stores": st, "peaks": peaks,
            "month_avg": float(q.mean()), "month_rank": month_rank,
        }
        kpis = [
            {"k": "누적 판매", "v": "출시 전" if not launched else f"{fmt.n(cum)}개",
             "d": f"{fmt.md(L.launch)} 출시" if not launched else f"{fmt.md(L.launch)}~{fmt.md(v.to)}"},
            {"k": "이번 판독 주간 일평균", "v": "-" if not launched else f"{fmt.n(w_avg)}개",
             "d": "" if not launched else f"맛 수요 {fmt.n(w_demand)}개 + 할인 효과 {fmt.n(w_avg - w_demand)}개"},
            {"k": "누적 판매 중 할인 효과", "v": "-" if not launched else fmt.pct(promo_inc / cum if cum else 0, 1),
             "d": "" if not launched else f"행사 증분 {fmt.n(promo_inc)}개"},
            {"k": "검색지수 최고점", "v": f"{rs['peak']:.0f}" if "peak" in rs else "-",
             "d": (f"{fmt.md(dt.date.fromisoformat(rs['peak_date']))} · 평소의 {rs['peak_x']:.0f}배"
                   if rs.get("peak_x") else "")},
            {"k": "최근 7일 긍정률", "v": fmt.pct(rs["positive_7d"]) if rs.get("positive_7d") is not None else "-",
             "d": "블로그·카페 요약문 감성"},
        ]
        timing = ({"pre": True} if v.id == "pre" else
                  {"read": v.read.isoformat(), "current": L.current_method_read.isoformat(),
                   "gain_days": (L.current_method_read - v.read).days})
        views.append({
            "id": v.id, "label": v.label, "read": v.read, "to": v.to, "start": v.start, "end": v.end,
            "timing": timing, "kpis": kpis, "cards": cards.build(v, ctx),
            "baseline": None if bl is None else {
                "base": bl.base.round(0), "lo": bl.lo.round(0), "hi": bl.hi.round(0),
                "k": bl.k, "k_band": bl.k_band, "n_fit": bl.n_fit},
            "promos": promo_rows,
            "first_week": promo.first_week_split(dates_m, q, bl, promo_mask, L.launch)
            if launched and (v.to - L.launch).days >= 6 else None,
            "flavor": flavor.table(brand_flavor, v, VIEWS[i - 1] if i else None, VIEWS[0]),
            "stores": None if st is None else {k: st[k] for k in ("rows", "total", "counts", "type_delta")},
            "peaks": peaks, "reaction_peak": peak_date,
            "youtube": reaction.youtube_top(T.frames.get("youtube_videos_daily"), v.to),
        })

    out = {
        "meta": {
            "title": "이달의 맛 주간 판독",
            "flavor": L.flavor, "parent_flavor": L.parent_flavor,
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "provenance": {k: PROV_LABEL[v] for k, v in T.provenance.items()},
            "provenance_raw": T.provenance,
            "stores_total": int(len(sm)),
            "assumptions": assumptions_text(),
            "rules": {"roi_keep": RULES.roi_keep, "roi_adjust": RULES.roi_adjust,
                      "unit_price": L.unit_price, "target_daily": L.target_daily},
            "keyword_labels": L.keyword_labels,
            "anchors": [{"date": d, "cum": c} for d, c in L.anchors],
        },
        "dates": dates,
        "launch_dates": dates_m,
        "series": {
            "bra": series.get("naver_datalab.bra.search_index"),
            "trend": trend,
            "mentions": series.get("naver_blog.bra.mentions"),
            "positive": series.get("naver_blog.bra.positive_ratio"),
            "sales": sales_on_axis,
        },
        "promos": [{"id": p.promo_id, "name": p.name, "start": p.start, "end": p.end,
                    "rate": float(p.discount_rate), "desc": p.desc} for p in promos.itertuples()],
        "markers": [{"date": L.teaser, "label": "티저"}, {"date": L.launch, "label": "출시"}],
        "views": views,
        "schema": {name: list(cols) for name, cols in TABLES.items()},
    }
    return _clean(out)


def main() -> None:
    out = build()
    WEB_OUT.parent.mkdir(parents=True, exist_ok=True)
    WEB_OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"→ {WEB_OUT.relative_to(WEB_OUT.parents[3])}  ({WEB_OUT.stat().st_size / 1024:.0f} KB)")
    print("데이터 출처:", out["meta"]["provenance"])
    for v in out["views"]:
        print(f"  [{v['label']}] " + " | ".join(f"{c['title'].split(' ')[0]}: {c['pill']['label']} — {c['head']}"
                                               for c in v["cards"]))


if __name__ == "__main__":
    main()
