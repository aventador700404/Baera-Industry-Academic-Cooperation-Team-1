"""목 데이터 생성기 (3월 두바이 출시 리플레이용).

판매·매장·행사는 공개되어 있지 않아 목으로 만든다. 브랜드 합계는 공개 앵커
(출시 15일 누적 100만 개, 22일 누적 142만 개)에 정확히 맞춘다.
반응(검색·언급·주제·영상)은 공개 API로 받을 수 있는 형식으로 만든다.

시연에서 '감지'되어야 할 사건을 심어 둔다. 정답은 _truth.json 에만 남기고
분석 코드는 이 파일을 읽지 않는다 (테스트만 읽는다).
  - 티저 직후 검색 급등, 출시 직후 소비자 쇼츠 확산
  - 3/7~3/12 '맛' 주제 부정 증가 (너무 달다), 3/9~3/14 '품절' 언급 급증
  - 품절 매장 2곳 (주변 언급↑ 판매↓), 소비자 영상에 나온 매장 1곳 (언급↑ 판매↑)
  - 행사 3개의 실제 증분

실행: python -m pipeline.mock.generate
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pandas as pd

from ..config import GENERATED, HISTORY_START, LAUNCH, D

SEED = 7
DOW = np.array([0.93, 0.92, 0.93, 0.95, 1.08, 1.22, 1.18])  # 월..일 (기존 맛과 이달의 맛 공통)

# 행사 일정·혜택은 공개 보도 기준 (evidence·source 열). 판매에 미친 효과(lift)는 목 데이터의 정답이라
# promo_calendar.csv에는 들어가지 않는다. 할인 환산율은 혜택을 판매가 대비 비율로 바꾼 값 (31데이만 가격으로 계산됨)
PROMOS = [
    dict(promo_id="barawk_feb", name="배라위크", start="2026-02-16", end="2026-02-22", discount_rate=0.10,
         desc="레디팩 2+1 · 아메리카노 1+1 (출시 전 주, 기준 기간에서 제외)",
         evidence="규칙 추정 (매월 셋째 월요일부터 7일)", source="https://www.hankyung.com/amp/202606168540P", lift=0.06),
    dict(promo_id="launch500", name="출시 기념 500원 더블", start="2026-02-24", end="2026-03-01", discount_rate=0.15,
         desc="싱글레귤러 + 500원 → 더블주니어", evidence="혜택 확인 · 기간과 환산율은 가정",
         source="https://www.sateconomy.co.kr/news/view/1065578658659857", lift=0.18),
    dict(promo_id="barawk", name="슈퍼 배라위크", start="2026-03-16", end="2026-03-22", discount_rate=0.10,
         desc="레디팩 2+1 (네이버페이 2+2) · 아메리카노 1+1", evidence="확인 (3/16 보도)",
         source="https://www.catchnews.kr/news/articleView.html?idxno=121661", lift=0.09),
    dict(promo_id="d31", name="31데이", start="2026-03-31", end="2026-03-31", discount_rate=0.21,
         desc="패밀리 → 하프갤론 (26,000원에 31,500원 상품, 혜택 5,500원) · 3/30까지 사전예약",
         evidence="확인 (3/30 보도)", source="https://www.hankyung.com/article/202603305107P", lift=0.45),
]

# 기존 맛 브랜드 전체 일평균 (가정)
REGULARS = {
    "엄마는 외계인": 50_000, "민트 초콜릿 칩": 40_000, "아몬드 봉봉": 37_000, "뉴욕 치즈케이크": 31_000,
    "사랑에 빠진 딸기": 28_000, "바람과 함께 사라지다": 23_000, "체리쥬빌레": 21_000, "슈팅스타": 19_000,
}
CANNIB = (-0.15, -0.13, -0.11, -0.08, -0.06)   # 출시 후 주차별 원조 잠식
SEASON = (0.03, 0.06, 0.09, 0.12, 0.13)        # 출시 후 주차별 딸기 시즌 상승

# 매장 그룹: 이달의 맛 판매가 몰리는 시점이 조금씩 달라 순위가 자연스럽게 움직이게 하는 장치 (화면에는 안 나감)
GROUPS = {"A": (0.10, 2, 1.0), "B": (0.20, 3, 0.7), "C": (0.08, 5, 0.7), "D": (0.12, 7, 0.6), "E": (0.50, 9, 0.5)}
REGIONS = ["서울 서대문구", "서울 종로구", "서울 관악구", "서울 강남구", "서울 마포구", "서울 송파구", "서울 노원구",
           "서울 중구", "서울 영등포구", "경기 수원시", "경기 성남시", "경기 고양시", "경기 용인시", "경기 화성시",
           "인천 남동구", "인천 연수구", "부산 남구", "부산 해운대구", "대구 수성구", "대전 유성구", "광주 북구",
           "경남 창원시", "충남 천안시", "제주 제주시"]

# 반응 주제: (기본 비중, 기본 긍정률). 날짜별 조정은 topic_share()
TOPICS = {
    "맛": (0.38, 0.80), "비교": (0.12, 0.70), "가격·할인": (0.07, 0.65),
    "품절·재고": (0.03, 0.15), "양·사이즈": (0.05, 0.75), "매장·서비스": (0.06, 0.60),
}

# 광고 캠페인 (가정): (이름, 시작, 끝, 첫날 일 노출, 마지막 날 일 노출, 노출 1천 회당 비용(원), 클릭률)
ADS = [
    ("티저", D("2026-02-23"), D("2026-02-23"), 1_200_000, 1_200_000, 6_500, 0.011),
    ("출시", D("2026-02-24"), D("2026-03-05"), 2_600_000, 1_100_000, 6_000, 0.013),
    ("배라위크", D("2026-03-14"), D("2026-03-22"), 1_500_000, 1_200_000, 5_500, 0.009),
    ("31데이", D("2026-03-29"), D("2026-03-31"), 1_000_000, 1_400_000, 5_500, 0.012),
]
AD_CHANNELS = {"유튜브": 0.45, "인스타그램": 0.35, "네이버": 0.20}

VIDEOS = [  # (id, 채널, 제목, 게시일, 최종 조회수, 확산 속도)
    ("yt_off_teaser", "official", "공식 · 두바이에서 온 엄마는 외계인 티저", D("2026-02-23"), 120_000, 3),
    ("yt_off_launch", "official", "공식 · 출시 영상", D("2026-02-24"), 300_000, 4),
    ("yt_con_a", "consumer", "소비자 쇼츠 · 출시일 시식", D("2026-02-24"), 4_100_000, 3),
    ("yt_con_b", "consumer", "소비자 쇼츠 · 두바이 맛 솔직 후기", D("2026-02-25"), 2_600_000, 4),
    ("yt_con_c", "consumer", "소비자 쇼츠 · 원조와 비교 (매장 촬영)", D("2026-03-02"), 1_200_000, 5),
    ("yt_con_d", "consumer", "먹방 · 쿼터 4가지 조합", D("2026-03-06"), 800_000, 6),
]


def daterange(a: dt.date, b: dt.date) -> list[dt.date]:
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def week_no(d: dt.date) -> int:
    return min(max((d - LAUNCH.launch).days // 7, 0), 4)


def promo_of(d: dt.date) -> dict | None:
    return next((p for p in PROMOS if D(p["start"]) <= d <= D(p["end"])), None)


def promo_lift(d: dt.date) -> float:
    p = promo_of(d)
    return p["lift"] if p else 0.0


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

    ks = np.arange(1.0, 400.0, 0.05)
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


def bump(t: float, peak: float) -> float:
    x = max(t, 0) / peak
    return x ** 2 * math.exp(2 * (1 - x))


# ---------------------------------------------------------------- 반응
def search_index(rng: np.random.Generator, days: list[dt.date]):
    L = LAUNCH
    bra, trend = [], []
    for d in days:
        t = (d - L.launch).days
        if d < L.teaser:
            b = 2.5 + rng.random() * 1.2
        elif d < L.launch:
            b = 34 if d == L.teaser else 41
        elif t < 2:
            b = (78, 92)[t]
        else:
            b = 26 + 74 * math.exp(-(t - 2) / 6.5)
        p = promo_of(d)
        b *= {"barawk": 1.12, "d31": 1.25}.get(p["promo_id"].split("_")[0] if p else "", 1.0)
        bra.append(b * (1 + rng.normal(0, 0.04)) if d >= L.teaser else b)
        tt = (d - HISTORY_START).days
        trend.append((82 * math.exp(-tt / 34) + 6) * (1 + rng.normal(0, 0.05)))
    mx = max(max(bra), max(trend))
    return [round(100 * b / mx, 1) for b in bra], [round(100 * x / mx, 1) for x in trend]


def topic_share(topic: str, d: dt.date) -> tuple[float, float]:
    """(비중, 긍정률). 심어 둔 사건이 여기 있다."""
    share, pos = TOPICS[topic]
    t = (d - LAUNCH.launch).days
    p = promo_of(d)
    if topic == "비교":
        share = 0.24 if d < LAUNCH.launch else max(0.10, 0.24 - 0.01 * t)
    if topic == "맛" and D("2026-03-07") <= d <= D("2026-03-12"):
        share, pos = share + 0.06, 0.58            # '너무 달다' 후기 확산
    if topic == "품절·재고" and D("2026-03-09") <= d <= D("2026-03-14"):
        share = 0.14                               # 수요 몰림 + 일부 매장 품절
    if topic == "가격·할인" and p:
        share, pos = 0.18, (0.55 if p["promo_id"].startswith("barawk") else 0.70)
    if topic == "양·사이즈" and p and p["promo_id"] == "d31":
        share = 0.15
    return share, pos


def main() -> dict:
    rng = np.random.default_rng(SEED)
    L = LAUNCH
    GENERATED.mkdir(parents=True, exist_ok=True)

    days_m, brand, truth_base, k = brand_series(rng)
    days_all = daterange(HISTORY_START, L.month_end)
    idx_of = {d: i for i, d in enumerate(days_all)}

    # 매장
    n = L.stores_total
    gnames = list(GROUPS)
    counts = largest_remainder(n, np.array([GROUPS[g][0] for g in gnames]))
    groups = np.repeat(gnames, counts)
    rng.shuffle(groups)
    region = rng.choice(REGIONS, n)
    sm = pd.DataFrame({
        "store_id": [f"S{i + 1:04d}" for i in range(n)],
        "store_name": [f"{r} #{i + 1:04d}" for i, r in enumerate(region)],
        "region": [r.split(" ")[0] for r in region],
    })
    weight = rng.lognormal(0, 0.45, n)

    def near_median(q: float, exclude: set[int]) -> int:
        target = np.quantile(weight, q)
        order = np.argsort(np.abs(weight - target))
        return int(next(i for i in order if i not in exclude))

    planted: dict[str, int] = {}
    planted["stockout_a"] = near_median(0.55, set())
    planted["stockout_b"] = near_median(0.60, set(planted.values()))
    planted["viral"] = near_median(0.50, set(planted.values()))
    events = {  # (매장, 시작, 끝, 이달의 맛 배수, 전 맛 배수, 주변 언급 배수)
        # 품절: 이달의 맛을 찾던 손님이 돌아가 다른 맛 판매도 조금 줄어든다
        "stockout_a": (planted["stockout_a"], D("2026-03-10"), D("2026-03-15"), 0.20, 0.90, 5.0),
        "stockout_b": (planted["stockout_b"], D("2026-03-17"), D("2026-03-22"), 0.20, 0.90, 5.0),
        "viral": (planted["viral"], D("2026-03-05"), D("2026-03-14"), 1.8, 1.12, 6.0),
    }
    flav_mult = np.ones((len(days_all), n))
    all_mult = np.ones((len(days_all), n))
    sns_mult = np.ones((len(days_all), n))
    for s, a, b, fm, am, sn in events.values():
        for d in daterange(a, b):
            i = idx_of[d]
            flav_mult[i, s], all_mult[i, s], sns_mult[i, s] = fm, am, sn

    week_noise = [rng.lognormal(0, 0.01, n) for _ in range(10)]
    noise = rng.lognormal(0, 0.03, (len(days_all), n)) * np.array(
        [week_noise[(d - HISTORY_START).days // 7] for d in days_all])

    rows = []
    for f, base in REGULARS.items():
        for d in days_all:
            i = idx_of[d]
            eff = 0.0
            if d >= L.launch:
                w = week_no(d)
                eff = CANNIB[w] if f == L.parent_flavor else -0.035
                if f == L.seasonal_flavor:
                    eff += SEASON[w]
            brand_f = base * DOW[d.weekday()] * (1 + eff) * (1 + 0.5 * promo_lift(d)) * (1 + rng.normal(0, 0.012))
            qty = np.round(brand_f * weight * all_mult[i] * noise[i] / weight.sum()).astype(np.int64)
            rows.append(pd.DataFrame({"date": d, "store_id": sm["store_id"], "flavor": f, "qty": qty}))
    for j, d in enumerate(days_m):
        i = idx_of[d]
        t = (d - L.launch).days
        m = np.ones(n)
        for g, (_, peak, amp) in GROUPS.items():
            m[groups == g] = 1 + amp * bump(t, peak)
        share = weight * m * all_mult[i] * flav_mult[i] * noise[i]
        rows.append(pd.DataFrame({"date": d, "store_id": sm["store_id"], "flavor": L.flavor,
                                  "qty": largest_remainder(int(brand[j]), share)}))
    sales = pd.concat(rows, ignore_index=True)

    # 반응: 검색지수(데이터랩 형식), 언급 수, 주제별 언급·긍부정 (블로그·카페 요약문 분류 형식)
    rrng = np.random.default_rng(SEED + 1)
    bra, trend = search_index(rrng, days_all)
    reac_rows, topic_rows = [], []
    mentions_by_day = {}
    for d, bi, ti in zip(days_all, bra, trend):
        m_total = round(bi * 34 * (1 + rrng.normal(0, 0.06)))
        mentions_by_day[d] = m_total
        reac_rows += [(d, "naver_datalab", "bra", "search_index", bi),
                      (d, "naver_datalab", "trend", "search_index", ti),
                      (d, "naver_blog", "bra", "mentions", m_total)]
        pos_sum = tot_sum = 0
        for topic in TOPICS:
            share, pos = topic_share(topic, d)
            cnt = int(rrng.poisson(max(m_total * share, 0.1)))
            p = int(rrng.binomial(cnt, min(max(pos + rrng.normal(0, 0.02), 0), 1))) if cnt else 0
            topic_rows.append((d, topic, cnt, p, cnt - p))
            pos_sum += p
            tot_sum += cnt
        if d >= L.teaser and tot_sum:
            reac_rows += [(d, "naver_blog", "bra", "positive_ratio", round(pos_sum / tot_sum, 3)),
                          (d, "naver_blog", "bra", "positive", pos_sum),
                          (d, "naver_blog", "bra", "negative", tot_sum - pos_sum)]
    reaction = pd.DataFrame(reac_rows, columns=["date", "source", "keyword", "metric", "value"])
    topics = pd.DataFrame(topic_rows, columns=["date", "topic", "mentions", "positive", "negative"])

    # 매장 주변 언급 (일별). 실제로는 '배스킨라빈스 + 지점명' 블로그 검색 결과 수
    peak = max(mentions_by_day.values())
    sr = []
    for d in days_all:
        lvl = 0.35 + 1.4 * mentions_by_day[d] / peak
        lam = 0.9 * weight ** 0.6 * lvl * sns_mult[idx_of[d]]
        sr.append(pd.DataFrame({"date": d, "store_id": sm["store_id"], "mentions": rrng.poisson(lam)}))
    store_reaction = pd.concat(sr, ignore_index=True)

    # 유튜브 영상 일별 조회수 (원값만)
    yv = []
    for vid, ch, title, pub, vmax, tau in VIDEOS:
        for d in daterange(pub, L.month_end):
            age = (d - pub).days + 1
            yv.append((d, vid, ch, title, int(round(vmax * (1 - math.exp(-age / tau)) * (1 + rrng.normal(0, 0.01)))), pub))
    yt = pd.DataFrame(yv, columns=["date", "video_id", "channel_type", "title", "views", "published_at"])
    yt["views"] = yt.groupby("video_id")["views"].cummax()

    # 광고 집행 (대행사 리포트 형식: 노출·클릭·비용)
    ad_rows = []
    for name, a, b, imp0, imp1, cpm, ctr in ADS:
        span = daterange(a, b)
        for i, d in enumerate(span):
            imp_day = imp0 + (imp1 - imp0) * (i / max(len(span) - 1, 1))
            for ch, share in AD_CHANNELS.items():
                imp = int(imp_day * share * (1 + rrng.normal(0, 0.05)))
                ad_rows.append((d, name, ch, imp, int(imp * ctr * (1 + rrng.normal(0, 0.08))), int(imp / 1000 * cpm)))
    ads = pd.DataFrame(ad_rows, columns=["date", "campaign", "channel", "impressions", "clicks", "spend"])

    promo_cal = pd.DataFrame([{k_: v for k_, v in p.items() if k_ != "lift"} for p in PROMOS])
    in_launch = [p for p in PROMOS if D(p["end"]) >= L.launch]   # 출시 전 행사는 이달의 맛 증분이 없다

    out = {
        "sales_daily": sales, "store_master": sm, "promo_calendar": promo_cal,
        "reaction_daily": reaction, "reaction_topics_daily": topics,
        "youtube_videos_daily": yt, "store_reaction_daily": store_reaction, "ad_daily": ads,
    }
    for name, df in out.items():
        df.to_csv(GENERATED / f"{name}.csv", index=False)

    truth = {
        "decay_k": k,
        "promos": {p["promo_id"]: {
            "lift": p["lift"],
            "incremental": int(round(sum(brand[j] - truth_base[j] for j, d in enumerate(days_m)
                                         if D(p["start"]) <= d <= D(p["end"])))),
        } for p in in_launch},
        "stores": {k_: {"store_id": sm["store_id"][v[0]], "start": v[1].isoformat(), "end": v[2].isoformat()}
                   for k_, v in events.items()},
        "topic_events": {"맛_부정": ["2026-03-07", "2026-03-12"], "품절·재고": ["2026-03-09", "2026-03-14"]},
    }
    (GENERATED / "_truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return truth


if __name__ == "__main__":
    tr = main()
    print("목 데이터 생성 완료 →", GENERATED)
    print(json.dumps(tr, ensure_ascii=False, indent=2))
