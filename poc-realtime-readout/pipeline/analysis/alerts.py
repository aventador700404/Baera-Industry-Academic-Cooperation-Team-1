"""실시간 감지: 하루씩 진행하면서 그 날까지의 데이터로만 신호를 잡는다 (미래 데이터 안 씀).

각 알림 = 언제(데이터 날짜), 무엇이 튀었나, 숫자 근거, 마케팅이 할 일, 지금 방식보다 며칠 빨리 봤나.
기준값은 config.RULES. 같은 신호가 며칠 연속 울리지 않게 신호별 대기 기간(cooldown)을 둔다.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from ..config import LAUNCH, RULES, read_day
from . import fmt
from .reaction import arr, pre_month_mask

TOPIC_ACTION = {
    "품절·재고": "매장 재고 확인 → 품절 매장 공지·대체 맛 안내 (매장 모듈의 점검 매장과 대조)",
    "맛": "후기 원문 확인 → 맛 불만이면 페어링·토핑 안내 콘텐츠, 다음 맛 레시피에 반영",
    "비교": "원조·유행 제품과의 차이를 짚는 콘텐츠로 정리",
    "가격·할인": "할인 조건에 대한 불만인지 확인 → 행사 조건 안내 보강",
    "양·사이즈": "사이즈 관련 반응 확인 → 사이즈업 행사 효과와 같이 판독",
    "매장·서비스": "매장 응대·대기 이슈인지 확인 → 해당 지역 운영 점검",
}
PROMO_ACTION = {
    "good": "증분이 할인 비용을 넘김 → 유지하되 대상·사이즈 점검",
    "warn": "할인 대부분이 원래 살 손님에게 돌아감 → 할인 폭 축소 또는 일정 분리",
    "crit": "할인 비용보다 늘어난 매출이 작음 → 대상 품목·채널 축소 또는 중단 검토",
}
TONE_RANK = {"crit": 0, "warn": 1, "good": 2, "info": 3}


@dataclass
class Alert:
    date: str
    kind: str
    module: str          # reaction / flavor / store / promo
    tone: str            # crit / warn / good / info
    title: str
    detail: str
    action: str
    gain_days: int       # 지금 방식(월말 정산 후 판독)보다 며칠 빨리 보는지


class Tracker:
    def __init__(self, series: dict, dates: list[dt.date], topics: pd.DataFrame | None,
                 yt: pd.DataFrame | None, labels: dict, promo_calendar: list[dict]):
        self.dates, self.idx = dates, {d: i for i, d in enumerate(dates)}
        n = len(dates)
        self.bra = arr(series.get("naver_datalab.bra.search_index"), n)
        self.trend = arr(series.get("naver_datalab.trend.search_index"), n)
        self.ment = arr(series.get("naver_blog.bra.mentions"), n)
        self.pos = arr(series.get("naver_blog.bra.positive_ratio"), n)
        pre = pre_month_mask(dates)
        self.bra_pre = float(np.nanmean(self.bra[pre])) if np.isfinite(self.bra[pre]).any() else np.nan
        self.ment_pre = float(np.nanmean(self.ment[pre])) if np.isfinite(self.ment[pre]).any() else np.nan
        self.topics, self.yt, self.labels, self.promo_calendar = topics, yt, labels, promo_calendar
        self.items: list[Alert] = []
        self.last: dict[str, dt.date] = {}
        self.promo_done: set[str] = set()

    # ------------------------------------------------------------ 공통
    def _emit(self, d: dt.date, key: str, cooldown: int | None, **kw) -> bool:
        """cooldown=None 이면 한 번만."""
        prev = self.last.get(key)
        if prev is not None and (cooldown is None or (d - prev).days < cooldown):
            return False
        self.last[key] = d
        gain = (LAUNCH.current_method_read - read_day(d)).days
        self.items.append(Alert(date=d.isoformat(), kind=key.split(":")[0], gain_days=gain, **kw))
        return True

    def _recent(self, d: dt.date, kinds: tuple[str, ...], days: int) -> bool:
        return any(a.kind in kinds and 0 <= (d - dt.date.fromisoformat(a.date)).days < days for a in self.items)

    # ------------------------------------------------------------ 하루 진행
    def step(self, d: dt.date, snap: dict) -> None:
        i = self.idx[d]
        self._search(d, i)
        self._trend(d, i)
        self._videos(d)
        self._topics(d)
        self._sentiment(d, i)
        self._first_week(d, snap)
        self._promos(d, snap)
        self._stores(d, snap)
        self._conversion(d, snap)

    def _search(self, d: dt.date, i: int) -> None:
        b = self.bra[i]
        if np.isfinite(b) and self.bra_pre and b >= RULES.search_spike_x * self.bra_pre:
            m = self.ment[i]
            self._emit(d, "search_spike", None, module="reaction", tone="warn",
                       title=f"검색 급등: 출시 전 한 달 평균의 {fmt.times(b / self.bra_pre)}",
                       detail=f"{self.labels['bra']} {b:.0f} (평소 {self.bra_pre:.1f}) · 블로그·카페 언급 "
                              f"{fmt.n(m)}건 (평소 일평균 {fmt.n(self.ment_pre)}건)",
                       action="출시일 콘텐츠·광고 집행 앞당김 검토, 초도 물량 점검")
        if d >= LAUNCH.launch + dt.timedelta(days=2):
            lo = self.idx.get(LAUNCH.launch, 0)
            seg = self.bra[lo:i + 1]
            j = int(np.nanargmax(seg)) + lo
            if j <= i - 2 and b < 0.85 * self.bra[j]:
                self._emit(d, "search_peak", None, module="reaction", tone="info",
                           title=f"검색 정점 통과 ({fmt.md(self.dates[j])})",
                           detail=f"정점 지수 {self.bra[j]:.0f} → 오늘 {b:.0f}",
                           action="확산기 → 유지기. 이제는 판매가 따라오는지(전환)와 재구매 신호를 봄")

    def _trend(self, d: dt.date, i: int) -> None:
        if i >= 21 and np.isfinite(self.trend[i]) and self.trend[i] <= RULES.trend_fade * self.trend[i - 21]:
            self._emit(d, "trend_fade", None, module="reaction", tone="warn",
                       title=f"{self.labels['trend']} 3주 새 {fmt.pct(1 - self.trend[i] / self.trend[i - 21])} 하락",
                       detail=f"지수 {self.trend[i - 21]:.0f} → {self.trend[i]:.0f}. 유행 키워드에 기대는 메시지는 수명이 짧음",
                       action="유행 편승 문구 비중을 줄이고 맛 자체로 소구하는 메시지 준비")

    def _videos(self, d: dt.date) -> None:
        if self.yt is None or not len(self.yt):
            return
        today = self.yt[self.yt["date"] == d]
        prev = self.yt[self.yt["date"] == d - dt.timedelta(days=1)].set_index("video_id")["views"]
        official = today[today["channel_type"] == "official"].sort_values("views", ascending=False)
        for r in today.itertuples():
            for m in RULES.video_milestones:
                before = prev.get(r.video_id, 0)
                if r.views >= m > before:
                    ref = (f" · 같은 날 {official.iloc[0].title} {fmt.n(official.iloc[0].views)}회"
                           if r.channel_type == "consumer" and len(official) else "")
                    self._emit(d, f"video:{r.video_id}:{m}", None, module="reaction", tone="good",
                               title=f"{'소비자' if r.channel_type == 'consumer' else '공식'} 영상 "
                                     f"조회 {m // 10_000:,}만 회 돌파: {r.title}",
                               detail=f"{fmt.n(r.views)}회 (API 원값){ref}",
                               action="공식 계정 리포스트·크리에이터 협업 제안, 영상 속 조합을 매장 POP로"
                               if r.channel_type == "consumer" else "광고 소재로 확대 집행 검토")

    def _topics(self, d: dt.date) -> None:
        t = self.topics
        if t is None or not len(t):
            return
        t3 = t[(t["date"] > d - dt.timedelta(days=3)) & (t["date"] <= d)].groupby("topic")[
            ["mentions", "positive"]].sum()
        t14 = t[(t["date"] > d - dt.timedelta(days=17)) & (t["date"] <= d - dt.timedelta(days=3))].groupby("topic")[
            ["mentions", "positive"]].sum()
        if t3.empty or t14.empty:
            return
        tot3, tot14 = t3["mentions"].sum(), t14["mentions"].sum()
        promo_now = self._promo_running(d)
        for topic, r in t3.iterrows():
            if r.mentions < RULES.topic_min_mentions or topic not in t14.index or not t14.loc[topic, "mentions"]:
                continue
            share, share_prev = r.mentions / tot3, t14.loc[topic, "mentions"] / tot14
            pos, pos_prev = r.positive / r.mentions, t14.loc[topic, "positive"] / t14.loc[topic, "mentions"]
            expected = promo_now and topic in ("가격·할인", "양·사이즈")   # 행사 중 가격 언급 증가는 당연
            if share >= RULES.topic_surge_x * share_prev and not expected:
                self._emit(d, f"topic_surge:{topic}", 7, module="reaction", tone="crit" if pos < 0.5 else "info",
                           title=f"'{topic}' 언급 급증",
                           detail=f"최근 3일 {fmt.n(r.mentions)}건, 전체 언급 중 비중 {fmt.pct(share_prev)} → "
                                  f"{fmt.pct(share)}, 긍정률 {fmt.pct(pos)}",
                           action=TOPIC_ACTION.get(topic, "후기 원문 확인"))
            if pos <= pos_prev - 0.15:
                self._emit(d, f"topic_neg:{topic}", 7, module="reaction", tone="warn",
                           title=f"'{topic}' 주제 부정 증가",
                           detail=f"긍정률 {fmt.pct(pos_prev)} → {fmt.pct(pos)} (최근 3일 {fmt.n(r.mentions)}건)",
                           action=TOPIC_ACTION.get(topic, "후기 원문 확인"))

    def _sentiment(self, d: dt.date, i: int) -> None:
        if i < 10 or d < LAUNCH.launch:
            return
        w3, w7 = self.pos[i - 2:i + 1], self.pos[i - 9:i - 2]
        if not (np.isfinite(w3).any() and np.isfinite(w7).any()):
            return
        p3, p7 = np.nanmean(w3), np.nanmean(w7)
        if np.isfinite(p3) and np.isfinite(p7) and (p7 - p3) * 100 >= RULES.sentiment_drop_pp \
                and not self._recent(d, ("topic_neg",), 3):
            self._emit(d, "sentiment_drop", 7, module="reaction", tone="warn",
                       title=f"전체 긍정률 {(p7 - p3) * 100:.0f}%p 하락",
                       detail=f"최근 3일 {fmt.pct(p3)} (그 전 7일 {fmt.pct(p7)})",
                       action="주제별 판독에서 어떤 주제가 끌어내렸는지 확인")

    def _first_week(self, d: dt.date, snap: dict) -> None:
        if d == LAUNCH.launch + dt.timedelta(days=6) and snap.get("demand_ratio"):
            r = snap["demand_ratio"]
            tone, act = (("good", "증산 검토") if r >= RULES.demand_up else
                         ("info", "현 물량 유지") if r >= RULES.demand_hold else ("warn", "감산 검토"))
            self._emit(d, "first_week", None, module="flavor", tone=tone,
                       title=f"첫 주 판독: 할인 효과를 뺀 맛 수요가 목표의 {r:.2f}배",
                       detail=f"출시 첫 주 맛 수요 일평균 {fmt.n(snap['demand_avg'])}개 vs 목표 "
                              f"{fmt.n(LAUNCH.target_daily)}개 (원조 일평균)",
                       action=f"{act} → 2주차 물량 계획에 반영")

    def _promos(self, d: dt.date, snap: dict) -> None:
        for p in snap.get("promos", []):
            if p["status"] != "done" or p["id"] in self.promo_done:
                continue
            self.promo_done.add(p["id"])
            label = p["verdict_label"] + ("" if p["firm"] else " (잠정)")
            self._emit(d, f"promo:{p['id']}", None, module="promo", tone=p["verdict"],
                       title=f"{p['name']} 판독: 증분 ROI {p['roi']:.2f} → {label}",
                       detail=f"행사 기간 판매 {fmt.n(p['act'])}개 중 행사 덕분 {fmt.n(p['inc'])}개 "
                              f"({fmt.pct(p['inc_pct'])}), 할인 비용 {fmt.million_won(p['cost_won'])} (가정)",
                       action=PROMO_ACTION[p["verdict"]])

    def _stores(self, d: dt.date, snap: dict) -> None:
        st = snap.get("stores")
        if not st:
            return
        for r in st["alerts"]:
            if r["flag"] == "check":
                self._emit(d, f"store_check:{r['store_id']}", 14, module="store", tone="crit",
                           title=f"매장 점검: {r['name']}",
                           detail=f"주변 언급 {r['sns_prev']}→{r['sns']}건(7일)인데 순위 {r['rank_prev']}→{r['rank']}위",
                           action="재고·운영 확인 → 품절이면 공지·대체 맛 안내, 긴급 배송")
            elif r["flag"] == "viral":
                self._emit(d, f"store_viral:{r['store_id']}", 14, module="store", tone="good",
                           title=f"바이럴 매장: {r['name']}",
                           detail=f"주변 언급 {r['sns_prev']}→{r['sns']}건(7일), 순위 {r['rank_prev']}→{r['rank']}위",
                           action="재고 선배치, 해당 매장 언급 콘텐츠를 공식 채널에서 확산")

    def _conversion(self, d: dt.date, snap: dict) -> None:
        c = snap.get("conversion")
        if not c:
            return
        if c["ratio"] >= 1.5:
            self._emit(d, "conversion_hold", None, module="reaction", tone="good",
                       title="관심은 식는데 판매는 유지: 반응 대비 판매 지수 "
                             f"{c['ratio']:.1f}",
                       detail=f"출시 첫 주 = 100 기준 판매 {c['sales_idx']:.0f} vs 검색 {c['search_idx']:.0f} (최근 7일)",
                       action="화제성보다 맛 수요가 판매를 끎 → 광고는 재방문·재구매 쪽으로, 물량은 판매 기준으로")
        elif c["ratio"] <= 0.8:
            self._emit(d, "conversion_drop", 14, module="reaction", tone="warn",
                       title=f"관심 대비 판매 부진: 반응 대비 판매 지수 {c['ratio']:.1f}",
                       detail=f"출시 첫 주 = 100 기준 판매 {c['sales_idx']:.0f} vs 검색 {c['search_idx']:.0f}",
                       action="품절·가격·접근성 점검")

    def _promo_running(self, d: dt.date) -> bool:
        return any(dt.date.fromisoformat(p["start"]) - dt.timedelta(days=2) <= d <= dt.date.fromisoformat(p["end"])
                   for p in self.promo_calendar)

    # ------------------------------------------------------------ 출력
    def upto(self, d: dt.date) -> list[dict]:
        return [asdict(a) for a in self.items if a.date <= d.isoformat()]

    def all(self) -> list[dict]:
        return [asdict(a) for a in self.items]


def pick_for_card(alerts: list[dict], d: dt.date, module: str, days: int = 3) -> dict | None:
    """카드에 올릴 최근 알림: 최근 days일 안에서 심각도 우선, 같으면 최신."""
    recent = [a for a in alerts if a["module"] == module and 0 <= (d - dt.date.fromisoformat(a["date"])).days < days]
    if not recent:
        return None
    return sorted(recent, key=lambda a: (TONE_RANK[a["tone"]], -dt.date.fromisoformat(a["date"]).toordinal()))[0]
