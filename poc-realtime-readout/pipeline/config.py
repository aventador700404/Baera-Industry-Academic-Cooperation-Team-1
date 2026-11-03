"""시연 설정과 가정을 한곳에 모은 파일.

숫자를 바꾸고 싶으면 여기만 고치면 된다. 화면 하단 '가정' 문구도 여기서 만든다.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"              # 본사 데이터: 같은 열 구조의 CSV를 넣으면 목 데이터 대신 쓴다
COLLECTED = DATA / "collected"  # 공개 API 수집분 (make collect)
GENERATED = DATA / "generated"  # 목 데이터 (make mock)
WEB_OUT = ROOT / "web" / "public" / "data" / "readout.json"

D = dt.date.fromisoformat


@dataclass(frozen=True)
class Launch:
    flavor: str = "두바이에서 온 엄마는 외계인"
    parent_flavor: str = "엄마는 외계인"       # 잠식을 볼 원조 맛
    seasonal_flavor: str = "사랑에 빠진 딸기"   # 시즌 상승을 볼 맛
    teaser: dt.date = D("2026-02-27")
    launch: dt.date = D("2026-03-01")
    month_end: dt.date = D("2026-03-31")
    target_daily: int = 50_000                 # 원조 '엄마는 외계인' 일평균 (가정)
    unit_price: int = 3_900                    # 판매 단가 (가정, 원)
    current_method_read: dt.date = D("2026-04-06")  # 지금 방식(월말 정산 후) 판독일 (가정)
    stores_total: int = 1_713                  # 2025 정보공개서 가맹점 수
    # 공개 앵커: 언론 보도된 누적 판매 (날짜까지 포함 누적)
    anchors: tuple = ((D("2026-03-15"), 1_000_000), (D("2026-03-22"), 1_420_000))
    # 네이버 데이터랩: 상대지수라 비교할 키워드는 한 요청에 같이 넣는다
    keyword_groups: dict = field(default_factory=lambda: {
        "bra": ["배스킨라빈스 두바이", "두바이에서 온 엄마는 외계인", "배라 두바이"],
        "trend": ["두바이 쫀득쿠키", "두쫀쿠"],
    })
    keyword_labels: dict = field(default_factory=lambda: {
        "bra": "배라 두바이 검색지수",
        "trend": "업계 키워드 '두바이 쫀득쿠키'",
    })


# ---------------------------------------------------------------- 판독 시점
# 실시간 판독을 3월 출시 리플레이로 시연한다: 하루씩 '그 날까지의 데이터'로 다시 계산.
# d일 데이터는 d+1일 아침에 본다고 가정.
HISTORY_START = D("2026-02-01")            # 차트·기준 기간 시작 (티저 전 약 4주 = 출시 전 한 달)
REPLAY_START = D("2026-02-20")             # 슬라이더 시작
PRE_WEEK = (D("2026-02-22"), D("2026-02-28"))   # 맛 순위·잠식 비교용 출시 전 주간
MILESTONES = (
    ("티저", D("2026-02-27")), ("출시", D("2026-03-01")), ("1주", D("2026-03-07")),
    ("2주", D("2026-03-14")), ("3주", D("2026-03-21")), ("4주", D("2026-03-28")), ("월말", D("2026-03-31")),
)


def asof_dates() -> list[dt.date]:
    return [REPLAY_START + dt.timedelta(days=i) for i in range((LAUNCH.month_end - REPLAY_START).days + 1)]


def read_day(asof: dt.date) -> dt.date:
    """asof까지의 데이터를 보는 날 (다음 날 아침)."""
    return asof + dt.timedelta(days=1)


@dataclass(frozen=True)
class Rules:
    # 판촉: 증분 ROI = 증분 매출 / 할인 비용
    roi_keep: float = 1.3      # 이상이면 지속
    roi_adjust: float = 1.0    # 이상이면 조정, 미만이면 중단 검토
    # 증산·재출시: 할인 효과를 뺀 맛 수요 / 목표
    demand_up: float = 1.2
    demand_hold: float = 0.9
    rerelease_positive: float = 0.70
    # 매장 (최근 7일 vs 그 전 7일): 반응↑ 판매↓ = 품절·운영 의심, 반응↑ 판매↑ = 바이럴 확산
    # 주변 언급 증가는 전국 언급 흐름을 뺀 값으로 본다 (출시 직후 전 매장 언급이 같이 뛰는 것은 신호가 아님)
    store_sns_up_pct: float = 60.0
    store_sns_min_mentions: int = 15
    store_sns_min_increase: int = 10
    store_rank_drop: int = 100
    store_rank_rise: int = 100
    # 알림
    search_spike_x: float = 5.0          # 출시 전 한 달 평균 대비 검색지수 배수
    mentions_spike_x: float = 3.0        # 최근 14일 중앙값 대비 언급량 배수
    topic_surge_x: float = 2.0           # 주제 비중이 최근 14일 대비 몇 배
    topic_min_mentions: int = 150        # 최근 3일 그 주제 언급 최소
    sentiment_drop_pp: float = 5.0       # 최근 3일 긍정률이 그 전 7일보다 몇 %p 하락
    video_milestones: tuple = (1_000_000, 3_000_000)  # 영상 조회수 돌파 (원값 기준)
    trend_fade: float = 0.6              # 업계 키워드가 3주 전의 이 비율 이하로 떨어지면 (40% 이상 하락)


LAUNCH = Launch()
RULES = Rules()


def assumptions_text() -> str:
    L = LAUNCH
    a1, a2 = L.anchors
    return (
        f"가정: 출시일 {L.launch.month}/{L.launch.day} (티저 {L.teaser.month}/{L.teaser.day}) · "
        f"판매 목표 = 원조 '{L.parent_flavor}' 일평균 {L.target_daily:,}개 · 단가 {L.unit_price:,}원 · "
        f"할인 환산율은 행사표의 discount_rate · 지금 방식의 판독 시점은 월말 정산 후 "
        f"{L.current_method_read.month}/{L.current_method_read.day} · "
        "기준선은 행사 없는 날의 추세와 기존 맛의 요일 패턴으로 추정. "
        f"공개 앵커: 출시 {(a1[0] - L.launch).days + 1}일 누적 {a1[1] // 10_000:,}만 개, "
        f"{(a2[0] - L.launch).days + 1}일 누적 {a2[1] // 10_000:,}만 개(언론 보도). 매장명은 예시."
    )
