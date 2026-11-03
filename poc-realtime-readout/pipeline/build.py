"""모든 테이블 → 하루씩 '그 날까지의 데이터'로 판독 → web/public/data/readout.json.

실시간 판독을 리플레이로 재현한다. 슬라이더의 하루 = 그 날 밤까지 쌓인 데이터를 다음 날 아침에 본 결과.
계산 로직은 전부 여기(파이썬)에 있고 테스트된다. 웹은 JSON만 그린다.
실행: python -m pipeline.build
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np

from .analysis import alerts as alerts_mod
from .analysis import cards, flavor, fmt, promo, reaction, stores
from .analysis.baseline import estimate_dow, fit_baseline
from .config import (HISTORY_START, LAUNCH, MILESTONES, RULES, WEB_OUT, asof_dates, assumptions_text, read_day)
from .io import Tables, load_all
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
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else round(float(x), 4)
    if isinstance(x, dt.date):
        return x.isoformat()
    return x


def build(tables: Tables | None = None) -> dict:
    """tables를 주면 그걸로 (테스트에서 데이터를 잘라 미래 데이터를 안 쓰는지 확인할 때)."""
    T = tables or load_all()
    L = LAUNCH
    sales, sm, promos = T["sales_daily"], T["store_master"], T["promo_calendar"]
    flavor_sales = sales[sales["flavor"] == L.flavor]

    dates_m = daterange(L.launch, L.month_end)
    q = flavor_sales.groupby("date")["qty"].sum().reindex(dates_m).fillna(0).to_numpy(dtype=float)
    promo_mask = np.array([any(p.start <= d <= p.end for p in promos.itertuples()) for d in dates_m])
    dow = estimate_dow(sales[sales["flavor"] != L.flavor].groupby("date")["qty"].sum(), L.launch)
    brand_flavor = sales.groupby(["date", "flavor"], as_index=False)["qty"].sum()
    store_daily = sales.groupby(["date", "store_id"], as_index=False)["qty"].sum()
    sns = T.frames.get("store_reaction_daily")
    topics = T.frames.get("reaction_topics_daily")
    yt = T.frames.get("youtube_videos_daily")

    reac = T["reaction_daily"]
    dates = daterange(min(min(reac["date"]), HISTORY_START), L.month_end)
    series = reaction.pivot(reac, dates)
    promo_list = [{"id": p.promo_id, "name": p.name, "start": p.start.isoformat(), "end": p.end.isoformat(),
                   "rate": float(p.discount_rate), "desc": p.desc} for p in promos.itertuples()]
    month_avg = flavor.window_avg(brand_flavor, L.launch, L.month_end)
    month_rank = list(month_avg.index).index(L.flavor) + 1 if L.flavor in month_avg else None

    tracker = alerts_mod.Tracker(series, dates, topics, yt, L.keyword_labels, promo_list)
    days, check_seen = [], {}
    for d in asof_dates():
        launched = d >= L.launch
        bl = fit_baseline(dates_m, q, promo_mask, dow, L.launch, asof=d) if launched else None
        upto = np.array([x <= d for x in dates_m])
        cum = float(q[upto].sum())
        promo_rows = promo.evaluate(promos, dates_m, q, bl, d, L.unit_price)
        promo_inc = float(np.clip(q - bl.base, 0, None)[upto & promo_mask].sum()) if bl else 0.0

        demand_avg = sales_avg = demand_ratio = None
        if launched:
            start = max(L.launch, d - dt.timedelta(days=6))
            w = np.array([start <= x <= d for x in dates_m])
            demand = np.where(promo_mask, bl.base, q) if bl else q
            sales_avg, demand_avg = float(q[w].mean()), float(demand[w].mean())
            demand_ratio = demand_avg / L.target_daily

        fl = flavor.table(brand_flavor, d)
        cannib = next((s["text"] for r in fl["rows"] if r["flavor"] == L.parent_flavor
                       for s in r["signals"] if s["kind"] == "warn"), None)
        rs = reaction.summary(series, dates, d)
        conv = reaction.conversion(dates_m, q, series, dates, d)

        st = None
        if d >= L.launch + dt.timedelta(days=6):
            recent = {sid: "check" for sid, seen in check_seen.items() if (d - seen).days <= 14}
            st = stores.table(store_daily, sm, sns, d, prev_flags=recent)
            for sid, f in st["flags"].items():
                if f == "check":
                    check_seen[sid] = d

        snap = {"promos": promo_rows, "stores": st, "demand_ratio": demand_ratio, "demand_avg": demand_avg,
                "conversion": conv}
        tracker.step(d, snap)
        alerts_now = tracker.upto(d)

        ctx = {"reaction": rs, "alerts": alerts_now, "cum": cum, "sales_avg": sales_avg, "demand_avg": demand_avg,
               "demand_ratio": demand_ratio, "baseline_ready": bl is not None, "cannib": cannib,
               "promos": promo_rows, "stores": st, "month_avg": float(q.mean()), "month_rank": month_rank}
        fw_ratio = None
        if d >= L.launch + dt.timedelta(days=6):
            fw = np.array([0 <= (x - L.launch).days < 7 for x in dates_m])
            dem = np.where(promo_mask, bl.base, q) if bl else q
            fw_ratio = float(dem[fw].mean()) / L.target_daily
        kpis = [
            {"k": "검색지수 (출시 전 한 달 대비)", "v": fmt.times(rs["last_x"]) if rs.get("last_x") else "-",
             "d": f"지수 {rs['last']:.0f} · 정점 {fmt.md(dt.date.fromisoformat(rs['peak_date']))}" if "last" in rs else ""},
            {"k": "블로그·카페 언급 (최근 7일)", "v": f"{fmt.n(rs['mentions_7d'])}건" if "mentions_7d" in rs else "-",
             "d": f"출시 전 한 달의 {fmt.times(rs['mentions_7d'] / rs['mentions_pre_7d'])}"
             if rs.get("mentions_pre_7d") else ""},
            {"k": "긍정률 (최근 7일)", "v": fmt.pct(rs["positive_7d"]) if rs.get("positive_7d") is not None else "-",
             "d": "블로그·카페 요약문 주제 분류"},
            {"k": "첫 주 목표 대비 (맛 수요)",
             "v": f"{fw_ratio:.2f}배" if fw_ratio else (f"{demand_ratio:.2f}배" if demand_ratio else "-"),
             "d": "확정 (출시 첫 주)" if fw_ratio else ("첫 주 진행 중 · 잠정" if launched else f"목표 일평균 {fmt.n(L.target_daily)}개")},
            {"k": "누적 판매", "v": f"{fmt.n(cum)}개" if launched else "출시 전",
             "d": f"할인 효과 {fmt.pct(promo_inc / cum, 1)} 포함" if launched and bl else (
                 "할인 효과 분리 전" if launched else f"{fmt.md(L.launch)} 출시")},
            {"k": "반응 대비 판매 (전환)", "v": f"{conv['ratio']:.1f}" if conv else "-",
             "d": f"판매 {conv['sales_idx']:.0f} / 검색 {conv['search_idx']:.0f} (첫 주=100)" if conv else "출시 2주 차부터"},
        ]
        days.append({
            "date": d, "read": read_day(d), "gain_days": (L.current_method_read - read_day(d)).days,
            "kpis": kpis, "cards": cards.build(d, ctx),
            "baseline": None if bl is None else {"base": bl.base.round(0), "lo": bl.lo.round(0), "hi": bl.hi.round(0),
                                                 "n_fit": bl.n_fit},
            "promos": promo_rows,
            "first_week": promo.first_week_split(dates_m, q, bl, promo_mask, L.launch)
            if d >= L.launch + dt.timedelta(days=6) else None,
            "flavor": fl,
            "stores": None if st is None else {k: st[k] for k in ("window", "rows", "total", "counts")},
            "topics": reaction.topics_table(topics, d),
            "youtube": reaction.youtube_top(yt, d),
            "conversion": conv,
        })

    out = {
        "meta": {
            "title": "이달의 맛 실시간 반응 판독",
            "flavor": L.flavor, "parent_flavor": L.parent_flavor,
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "provenance": {k: PROV_LABEL[v] for k, v in T.provenance.items()},
            "provenance_raw": T.provenance,
            "stores_total": int(len(sm)),
            "assumptions": assumptions_text(),
            "rules": {"roi_keep": RULES.roi_keep, "roi_adjust": RULES.roi_adjust,
                      "unit_price": L.unit_price, "target_daily": L.target_daily},
            "keyword_labels": L.keyword_labels,
            "current_read": L.current_method_read,
            "milestones": [{"label": lb, "date": d} for lb, d in MILESTONES],
        },
        "dates": dates,
        "launch_dates": dates_m,
        "series": {
            "bra": series.get("naver_datalab.bra.search_index"),
            "trend": series.get("naver_datalab.trend.search_index"),
            "mentions": series.get("naver_blog.bra.mentions"),
            "sales": [float(q[dates_m.index(x)]) if x in dates_m else None for x in dates],
        },
        "promos": promo_list,
        "markers": [{"date": L.teaser, "label": "티저"}, {"date": L.launch, "label": "출시"}],
        "alerts": tracker.all(),
        "days": days,
        "schema": {name: list(cols) for name, cols in TABLES.items()},
    }
    return _clean(out)


def main() -> None:
    out = build()
    WEB_OUT.parent.mkdir(parents=True, exist_ok=True)
    WEB_OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"→ {WEB_OUT.relative_to(WEB_OUT.parents[3])}  ({WEB_OUT.stat().st_size / 1024:.0f} KB, "
          f"{len(out['days'])}일, 알림 {len(out['alerts'])}건)")
    print("데이터 출처:", out["meta"]["provenance"])
    for a in out["alerts"]:
        print(f"  {a['date'][5:]} [{a['module']:8}|{a['tone']:4}] {a['title']}  (+{a['gain_days']}일)")


if __name__ == "__main__":
    main()
