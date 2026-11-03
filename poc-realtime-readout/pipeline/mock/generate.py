"""목 데이터 생성기.

본사 판매 데이터가 없어서 만든 시연용 데이터. 브랜드 합계는 공개 앵커
(출시 15일 누적 100만 개, 22일 누적 142만 개)에 정확히 맞춘다.
매장 x 맛 x 일 단위로 만들어서, 분석 코드는 본사 데이터가 들어와도 같은 방식으로 돈다.

정답(행사의 실제 증분, 심어 둔 매장 이벤트)은 _truth.json 에만 남긴다.
분석 코드는 이 파일을 읽지 않는다. 테스트만 읽는다.

실행: python -m pipeline.mock.generate
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pandas as pd

from ..config import GENERATED, LAUNCH, VIEWS, D

SEED = 7
DOW = np.array([0.93, 0.92, 0.93, 0.95, 1.08, 1.22, 1.18])  # 월..일 (기존 맛과 이달의 맛 공통)
HISTORY_START = D("2026-02-01")

# lift는 목 데이터의 정답이다. promo_calendar.csv에는 들어가지 않는다.
PROMOS = [
    dict(promo_id="baraday", name="배라데이", start="2026-03-01", end="2026-03-03",
         discount_rate=0.15, desc="출시 직후 최대 할인 (제휴 결제 할인)", lift=0.18),
    dict(promo_id="barawk", name="배라위크", start="2026-03-16", end="2026-03-22",
         discount_rate=0.10, desc="레디팩 2+1 · 음료 1+1", lift=0.09),
    dict(promo_id="d31", name="31데이", start="2026-03-31", end="2026-03-31",
         discount_rate=0.20, desc="패밀리 → 하프갤론 사이즈업", lift=0.45),
]

# 기존 맛 브랜드 전체 일평균 (가정)
REGULARS = {
    "엄마는 외계인": 50_000, "민트 초콜릿 칩": 40_000, "아몬드 봉봉": 37_000, "뉴욕 치즈케이크": 31_000,
    "사랑에 빠진 딸기": 28_000, "바람과 함께 사라지다": 23_000, "체리쥬빌레": 21_000, "슈팅스타": 19_000,
}
CANNIB = {"pre": 0, "w1": -0.15, "w2": -0.13, "w3": -0.11, "w4": -0.08, "w5": -0.06}
SEASON = {"pre": 0, "w1": 0.03, "w2": 0.06, "w3": 0.09, "w4": 0.12, "w5": 0.13}

# 매장 유형: (매장 비중, 이달의 맛 판매가 몰리는 날(출시 후), 몰림 강도, 지역 예시)
TYPES = {
    "대학가": (0.10, 2, 1.0, ["서울 서대문구", "서울 종로구", "서울 관악구", "부산 남구", "대전 유성구", "광주 북구", "경기 수원시"]),
    "역세권": (0.20, 3, 0.7, ["서울 강남구", "서울 마포구", "서울 송파구", "부산 부산진구", "대전 서구", "인천 남동구"]),
    "관광": (0.08, 5, 0.7, ["제주 제주시", "경북 경주시", "강원 강릉시", "부산 해운대구", "전북 전주시"]),
    "오피스": (0.12, 7, 0.6, ["서울 중구", "서울 영등포구", "경기 성남시", "서울 구로구"]),
    "주거": (0.50, 9, 0.5, ["경기 고양시", "경기 용인시", "경기 화성시", "인천 연수구", "대구 수성구",
                           "서울 노원구", "경남 창원시", "충남 천안시"]),
}


def daterange(a: dt.date, b: dt.date) -> list[dt.date]:
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def window_of(d: dt.date) -> str:
    for v in VIEWS:
        if v.start <= d <= v.end:
            return v.id
    return "pre" if d < LAUNCH.launch else VIEWS[-1].id


def promo_lift(d: dt.date) -> float:
    for p in PROMOS:
        if D(p["start"]) <= d <= D(p["end"]):
            return p["lift"]
    return 0.0


def promo_id_of(d: dt.date) -> str | None:
    for p in PROMOS:
        if D(p["start"]) <= d <= D(p["end"]):
            return p["promo_id"]
    return None


# ---------------------------------------------------------------- 브랜드 합계
def brand_series(rng: np.random.Generator):
    """이달의 맛 브랜드 일별 판매. 행사 없는 수요 = 바닥 + 지수 감소, 행사일은 lift만큼 증가."""
    L = LAUNCH
    days = daterange(L.launch, L.month_end)
    t = np.arange(len(days))
    dow = DOW[[d.weekday() for d in days]]
    lift = np.array([promo_lift(d) for d in days])
    (d1, c1), (d2, c2) = L.anchors
    i1, i2 = (d1 - L.launch).days + 1, (d2 - L.launch).days + 1
    target = (c2 - c1) / c1

    def actual(k: float) -> np.ndarray:
        return (0.55 + 0.75 * np.exp(-t / k)) * dow * (1 + lift)

    ks = np.arange(1.0, 60.0, 0.01)
    ratios = np.array([actual(k)[i1:i2].sum() / actual(k)[:i1].sum() for k in ks])
    k = float(ks[np.argmin(np.abs(ratios - target))])
    a = actual(k)
    a = a * c1 / a[:i1].sum()
    a = a * (1 + rng.normal(0, 0.025, len(a)))
    a[:i1] *= c1 / a[:i1].sum()
    a[i1:i2] *= (c2 - c1) / a[i1:i2].sum()
    a = np.round(a).astype(np.int64)
    a[i1 - 1] += c1 - a[:i1].sum()
    a[i2 - 1] += c2 - a[:i2].sum()
    truth_base = a / (1 + lift)
    return days, a, truth_base, k


def largest_remainder(total: int, weights: np.ndarray) -> np.ndarray:
    """정수 total을 weights 비율로 나누되 합이 정확히 total이 되게."""
    raw = weights / weights.sum() * total
    base = np.floor(raw).astype(np.int64)
    rest = int(total - base.sum())
    if rest > 0:
        base[np.argsort(-(raw - base))[:rest]] += 1
    return base


def bump(t: np.ndarray, peak: float) -> np.ndarray:
    x = np.clip(t, 0, None) / peak
    return x ** 2 * np.exp(2 * (1 - x))


# ---------------------------------------------------------------- 매장
def make_stores(rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    n = LAUNCH.stores_total
    names = list(TYPES)
    shares = np.array([TYPES[k][0] for k in names])
    counts = largest_remainder(n, shares)
    types = np.repeat(names, counts)
    rng.shuffle(types)
    region = np.array([rng.choice(TYPES[t][3]) for t in types])
    ids = [f"S{i + 1:04d}" for i in range(n)]
    sm = pd.DataFrame({
        "store_id": ids,
        "store_name": [f"{r} #{i + 1:04d}" for i, r in enumerate(region)],
        "type": types,
        "region": [r.split(" ")[0] for r in region],
    })
    weight = rng.lognormal(0, 0.45, n)
    return sm, weight


def pick(sm: pd.DataFrame, weight: np.ndarray, typ: str, q: float) -> int:
    """유형 안에서 매출 규모가 q 분위 근처인 매장 하나 (심어 둔 이벤트용)."""
    idx = np.where(sm["type"].to_numpy() == typ)[0]
    target = np.quantile(weight[idx], q)
    return int(idx[np.argmin(np.abs(weight[idx] - target))])


def main() -> dict:
    rng = np.random.default_rng(SEED)
    L = LAUNCH
    GENERATED.mkdir(parents=True, exist_ok=True)

    days_m, brand, truth_base, k = brand_series(rng)
    sm, weight = make_stores(rng)
    n = len(sm)
    types = sm["type"].to_numpy()
    days_all = daterange(HISTORY_START, L.month_end)
    idx_of = {d: i for i, d in enumerate(days_all)}

    # 심어 둔 매장 이벤트 (정답)
    planted = {
        "stockout_w2": pick(sm, weight, "역세권", 0.55),
        "stockout_w3": pick(sm, weight, "대학가", 0.6),
        "popup_w3": pick(sm, weight, "주거", 0.5),
        "competitor_w4": pick(sm, weight, "관광", 0.6),
    }
    ctx = np.ones((len(days_all), n))       # 전체 판매에 곱함 (유동인구, 경쟁점)
    stock = np.ones((len(days_all), n))     # 이달의 맛에만 곱함 (품절)
    for d in days_all:
        i = idx_of[d]
        if D("2026-03-10") <= d <= D("2026-03-15"):
            stock[i, planted["stockout_w2"]] = 0.30
        if D("2026-03-17") <= d <= D("2026-03-22"):
            stock[i, planted["stockout_w3"]] = 0.30
        if d >= D("2026-03-16"):
            ctx[i, planted["popup_w3"]] = 1.25
        if d >= D("2026-03-23"):
            ctx[i, planted["competitor_w4"]] = 0.78

    week_noise = {v.id: rng.lognormal(0, 0.01, n) for v in VIEWS}
    noise = rng.lognormal(0, 0.03, (len(days_all), n)) * np.array(
        [week_noise[window_of(d)] for d in days_all])

    rows = []
    # 기존 맛
    for f, base in REGULARS.items():
        for d in days_all:
            i = idx_of[d]
            w = window_of(d) if d >= L.launch else "pre"
            eff = 0.0
            if d >= L.launch:
                eff = CANNIB[w] if f == L.parent_flavor else -0.035
                if f == L.seasonal_flavor:
                    eff += SEASON[w]
            brand_f = base * DOW[d.weekday()] * (1 + eff) * (1 + 0.5 * promo_lift(d)) * (1 + rng.normal(0, 0.012))
            share = weight * ctx[i] * noise[i]
            qty = np.round(brand_f * share / (weight.sum())).astype(np.int64)
            rows.append(pd.DataFrame({"date": d, "store_id": sm["store_id"], "flavor": f, "qty": qty}))
    # 이달의 맛: 매장 유형별로 판매가 몰리는 날이 다르다
    for j, d in enumerate(days_m):
        i = idx_of[d]
        t = (d - L.launch).days
        m = np.ones(n)
        for typ, (_, peak, amp, _) in TYPES.items():
            m[types == typ] = 1 + amp * bump(np.array([t]), peak)[0]
        share = weight * m * ctx[i] * stock[i] * noise[i]
        qty = largest_remainder(int(brand[j]), share)
        rows.append(pd.DataFrame({"date": d, "store_id": sm["store_id"], "flavor": L.flavor, "qty": qty}))
    sales = pd.concat(rows, ignore_index=True)

    # 매장 주변 SNS 언급 (주간). 실제로는 '배스킨라빈스 + 지점명' 네이버 블로그 검색 결과 수
    sr_rows = []
    react_w = {"pre": 0.4, "w1": 1.0, "w2": 0.9, "w3": 0.75, "w4": 0.6, "w5": 0.5}
    for v in VIEWS:
        lam = 6 * weight ** 0.6 * react_w[v.id]
        if v.id == "w1":
            lam[types == "대학가"] *= 1.5
        if v.id in ("w2", "w3"):
            lam[types == "주거"] *= 1.2
        lam[planted["stockout_w2"]] = {"w1": 22, "w2": 46}.get(v.id, lam[planted["stockout_w2"]])
        lam[planted["stockout_w3"]] = {"w2": 20, "w3": 41}.get(v.id, lam[planted["stockout_w3"]])
        sr_rows.append(pd.DataFrame({"week_start": v.start, "store_id": sm["store_id"],
                                     "mentions": rng.poisson(lam)}))
    store_reaction = pd.concat(sr_rows, ignore_index=True)

    store_context = pd.DataFrame([
        {"week_start": D("2026-03-16"), "store_id": sm["store_id"][planted["popup_w3"]],
         "kind": "floating_pop_change_pct", "value": 22.0, "note": "주변 신규 입주 단지 입주 시작, 유동인구 +22%"},
        {"week_start": D("2026-03-23"), "store_id": sm["store_id"][planted["competitor_w4"]],
         "kind": "competitor_open", "value": 1.0, "note": "500m 안에 요거트 아이스크림 전문점 개점"},
    ])

    # 반응 (네이버 데이터랩 상대지수 형식, 블로그 언급, 긍정률)
    rrng = np.random.default_rng(SEED + 1)
    days_r = daterange(HISTORY_START, L.month_end)
    bra, trend = [], []
    for d in days_r:
        t = (d - L.launch).days
        if d < L.teaser:
            b = 2.5 + rrng.random() * 1.2
        elif d < L.launch:
            b = 34 if d == L.teaser else 41
        elif t < 2:
            b = (78, 92)[t]
        else:
            b = 26 + 74 * math.exp(-(t - 2) / 6.5)
        b *= {"barawk": 1.12, "d31": 1.25}.get(promo_id_of(d), 1.0)
        bra.append(b * (1 + rrng.normal(0, 0.04)) if d >= L.teaser else b)
        tt = (d - HISTORY_START).days
        trend.append((82 * math.exp(-tt / 34) + 6) * (1 + rrng.normal(0, 0.05)))
    mx = max(max(bra), max(trend))
    reac_rows = []
    for d, b, tr in zip(days_r, bra, trend):
        bi, ti = round(100 * b / mx, 1), round(100 * tr / mx, 1)
        t = (d - L.launch).days
        reac_rows += [
            (d, "naver_datalab", "bra", "search_index", bi),
            (d, "naver_datalab", "trend", "search_index", ti),
            (d, "naver_blog", "bra", "mentions", round(bi * 34 * (1 + rrng.normal(0, 0.06)))),
        ]
        if d >= L.teaser:
            pos = min(0.86, max(0.62, 0.82 - 0.004 * max(t, 0) + rrng.normal(0, 0.012)))
            reac_rows.append((d, "naver_blog", "bra", "positive_ratio", round(pos, 3)))
    reaction = pd.DataFrame(reac_rows, columns=["date", "source", "keyword", "metric", "value"])

    # 유튜브 영상 일별 조회수 (원값만. 약관상 API 수치로 새 지표를 만들지 않는다)
    videos = [
        ("yt_off_teaser", "official", "공식 · 두바이에서 온 엄마는 외계인 티저", D("2026-02-27"), 120_000, 3),
        ("yt_off_launch", "official", "공식 · 출시 영상", D("2026-03-01"), 300_000, 4),
        ("yt_con_a", "consumer", "소비자 쇼츠 · 출시일 시식", D("2026-03-01"), 4_100_000, 3),
        ("yt_con_b", "consumer", "소비자 쇼츠 · 두바이 맛 솔직 후기", D("2026-03-02"), 2_600_000, 4),
        ("yt_con_c", "consumer", "소비자 쇼츠 · 원조와 비교", D("2026-03-05"), 1_200_000, 5),
        ("yt_con_d", "consumer", "먹방 · 쿼터 4가지 조합", D("2026-03-09"), 800_000, 6),
    ]
    yv = []
    for vid, ch, title, pub, vmax, tau in videos:
        for d in daterange(pub, L.month_end):
            age = (d - pub).days + 1
            views = vmax * (1 - math.exp(-age / tau)) * (1 + rrng.normal(0, 0.01))
            yv.append((d, vid, ch, title, int(round(views))))
    yt = pd.DataFrame(yv, columns=["date", "video_id", "channel_type", "title", "views"])
    yt["views"] = yt.groupby("video_id")["views"].cummax()

    promo_cal = pd.DataFrame([{k: v for k, v in p.items() if k != "lift"} for p in PROMOS])

    out = {
        "sales_daily": sales, "store_master": sm, "promo_calendar": promo_cal,
        "reaction_daily": reaction, "youtube_videos_daily": yt,
        "store_reaction_weekly": store_reaction, "store_context_weekly": store_context,
    }
    for name, df in out.items():
        df.to_csv(GENERATED / f"{name}.csv", index=False)

    truth = {
        "decay_k": k,
        "promos": {
            p["promo_id"]: {
                "lift": p["lift"],
                "incremental": int(round(sum(
                    brand[j] - truth_base[j] for j, d in enumerate(days_m)
                    if D(p["start"]) <= d <= D(p["end"])))),
            } for p in PROMOS
        },
        "planted": {k_: sm["store_id"][v] for k_, v in planted.items()},
        "type_peak_day": {t: TYPES[t][1] for t in TYPES},
    }
    (GENERATED / "_truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2))
    return truth


if __name__ == "__main__":
    tr = main()
    print("목 데이터 생성 완료 →", GENERATED)
    print(json.dumps(tr, ensure_ascii=False, indent=2))
