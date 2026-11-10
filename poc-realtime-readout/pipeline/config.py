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
    # 공식 발표는 '3월 이달의 맛'(보도 2/25~26)이지만 매장 판매는 2/24에 시작했다.
    # 2/23 소비자 영상 "내일부터 판매", 2/24 "오늘 출시"이고 검색·블로그·유튜브 댓글 정점이 모두 2/24.
    # 본사 POS가 들어오면 첫 판매일로 바로 확인된다.
    teaser: dt.date = D("2026-02-23")          # 첫 예고 (판매 전날)
    launch: dt.date = D("2026-02-24")          # 실제 판매 시작
    month_end: dt.date = D("2026-03-31")
    target_daily: int = 50_000                 # 원조 '엄마는 외계인' 일평균 (가정)
    unit_price: int = 3_900                    # 판매 단가 (가정, 원)
    current_method_read: dt.date = D("2026-04-06")  # 지금 방식(월말 정산 후) 판독일 (가정)
    stores_total: int = 1_713                  # 2025 정보공개서 가맹점 수
    # 공개 앵커: 언론 보도된 누적 판매 (날짜까지 포함 누적). 출시일(2/24)을 1일째로 센다
    #   "출시 15일 만에 100만 개" (서울경제 3/22) → 3/10, "22일 만에 142만 개" (데일리안) → 3/17
    anchors: tuple = ((D("2026-03-10"), 1_000_000), (D("2026-03-17"), 1_420_000))
    # 네이버 데이터랩: 상대지수라 비교할 키워드는 한 요청에 같이 넣는다
    # 한 그룹 안의 검색어는 합산된다 (그룹당 최대 20개). 사람들이 섞어 쓰는 표기(베라, 베스킨라빈스, 배스킨라벤스 등)도 같이 넣는다
    keyword_groups: dict = field(default_factory=lambda: {
        "bra": ["배스킨라빈스 두바이", "베스킨라빈스 두바이", "배스킨라벤스 두바이", "베스킨라벤스 두바이",
                "배라 두바이", "베라 두바이", "두바이에서 온 엄마는 외계인", "두바이 엄마는 외계인"],
        "trend": ["두바이 쫀득쿠키", "두바이쫀득쿠키", "두쫀쿠"],
    })
    keyword_labels: dict = field(default_factory=lambda: {
        "bra": "배라 두바이 검색지수",
        "trend": "업계 키워드 '두바이 쫀득쿠키'",
    })


# ---------------------------------------------------------------- 판독 시점
# 두 층으로 본다 (팀 장표 5·7번: 일 단위 모니터링 + 주 단위 판독).
#   매일 모니터링: 반응 수집과 급등·급증 알림. d일 데이터는 d+1일 아침에 본다.
#   주간 판독   : 매주 월요일 아침, 일요일까지의 데이터로 결정 3축(증산·재출시 / 판촉 / 매장 지원) 확정. 월말은 따로 한 번.
# 시연은 3월 출시를 하루씩 재생한다.
HISTORY_START = D("2026-01-26")            # 차트·기준 기간 시작 (티저 전 4주 = 출시 전 한 달)
REPLAY_START = D("2026-02-20")             # 슬라이더 시작
PRE_WEEK = (D("2026-02-09"), D("2026-02-15"))   # 맛 순위·잠식 비교용 출시 전 주간 (2월 배라위크 2/16~22 앞 주)
WEEKLY_READ_WEEKDAY = 0                    # 주간 판독 요일 (0 = 월요일). 그 전날까지의 데이터로 판독


def asof_dates() -> list[dt.date]:
    return [REPLAY_START + dt.timedelta(days=i) for i in range((LAUNCH.month_end - REPLAY_START).days + 1)]


def weekly_asofs() -> list[dt.date]:
    """주간 판독에 쓰는 데이터 마감일: 판독 요일 전날들 + 월말."""
    last_day = (WEEKLY_READ_WEEKDAY - 1) % 7
    out = [d for d in asof_dates() if d.weekday() == last_day]
    return out + ([LAUNCH.month_end] if LAUNCH.month_end not in out else [])


def read_day(asof: dt.date) -> dt.date:
    """asof까지의 데이터를 보는 날 (다음 날 아침)."""
    return asof + dt.timedelta(days=1)


# 슬라이더 바로가기: (이름, 데이터 마감일, 판독이면 True → 칩에 판독일 표시)
MILESTONES = (
    ("티저", D("2026-02-23"), False), ("출시", D("2026-02-24"), False),
    ("1주 판독", D("2026-03-01"), True), ("2주 판독", D("2026-03-08"), True), ("3주 판독", D("2026-03-15"), True),
    ("4주 판독", D("2026-03-22"), True), ("월말 판독", D("2026-03-31"), True),
)


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
    # 알림. 비율 비교는 '우연히 이만큼 차이 날 가능성'이 작을 때만 울린다 (두 비율의 z 검정, signif_z 이상)
    # 실데이터는 하루 글 수가 수십 건이라 절대 건수 기준은 쓰지 않고 최소 건수만 둔다
    search_spike_x: float = 5.0          # 출시 전 한 달 평균 대비 검색지수 배수
    mentions_spike_x: float = 3.0        # 최근 14일 중앙값 대비 언급량 배수
    topic_surge_x: float = 2.0           # 주제 비중이 최근 14일 대비 몇 배
    topic_min_mentions: int = 10         # 최근 3일 그 주제 언급 최소 (이보다 적으면 비율을 안 믿음)
    sentiment_drop_pp: float = 5.0       # 최근 3일 긍정률이 그 전 7일보다 몇 %p 하락
    sentiment_min_n: int = 15            # 긍정·부정이 판단된 글이 3일·7일 구간에 각각 이만큼은 있어야 함
    signif_z: float = 2.0                # 비율 차이의 z 값 (약 95%)
    video_milestones: tuple = (1_000_000, 3_000_000)  # 영상 조회수 돌파 (원값 기준)
    trend_fade: float = 0.6              # 업계 키워드가 3주 전의 이 비율 이하로 떨어지면 (40% 이상 하락)


@dataclass(frozen=True)
class Collect:
    """공개 API 수집 범위. 키를 .env에 넣고 `make collect` 하면 이 설정대로 모은다.

    지나간 기간을 지금 모으는 것이라 API마다 받을 수 있는 것이 다르다 (docs/DATA.md):
    데이터랩은 과거 일별 그대로, 블로그는 검색어당 최대 1,000건(언급 수는 하한), 카페는 작성일이 없어
    전체 건수만, 유튜브는 지금 시점 조회수 + 댓글 작성일.
    """
    start: dt.date = D("2025-11-01")       # 두쫀쿠 유행 시작 무렵
    end: dt.date = D("2026-03-31")         # 두바이 출시 달 말
    # 블로그: 여러 검색어 × (정확도순, 최신순)으로 모아 중복 제거. 그중 신제품 이야기인 글만 쓴다
    # 표기가 섞여 쓰인다: 배스킨라빈스·베스킨라빈스·배스킨라벤스·베스킨라벤스, 배라·베라. 검색어마다 API 호출이 늘어
    # (블로그는 검색어당 최대 20회, 유튜브 검색은 1회 100 units) 많이 쓰이는 표기 위주로 넣고, 글 거르기는 any_of 로 넓게 잡는다
    blog_queries: tuple = ("두바이에서 온 엄마는 외계인", "두바이 엄마는 외계인", "배라 두바이", "베라 두바이",
                           "배스킨라빈스 두바이", "베스킨라빈스 두바이", "배스킨라벤스 두바이")
    blog_keyword: str = "bra"
    must_have: tuple = ("두바이",)                              # 글에 꼭 있어야 하는 말
    any_of: tuple = ("배스킨", "베스킨", "라빈스", "라벤스", "배라", "베라", "엄마는 외계인")  # 이 중 하나는 있어야 함
    cafe_queries: tuple = ("두바이에서 온 엄마는 외계인", "배라 두바이", "베라 두바이")
    # 유튜브: 출시 전후 올라온 영상 + 상위 영상의 댓글 작성일. 유튜브 검색은 표기 차이를 어느 정도 흡수해 4개만
    youtube_queries: tuple = ("배스킨라빈스 두바이", "두바이에서 온 엄마는 외계인", "배라 두바이", "베라 두바이")
    youtube_after: dt.date = D("2026-02-15")
    youtube_max_videos: int = 25           # 검색어당
    comment_videos: int = 10               # 댓글을 모을 상위 영상 수
    comment_pages: int = 5                 # 영상당 최대 페이지 (100개씩)
    official_channel_hint: tuple = ("배스킨라빈스", "베스킨라빈스", "baskin")  # 공식 채널 ID가 없을 때 채널명으로 판별
    # 유튜브 검색은 관련 없는 '두바이 초콜릿' 영상도 돌려준다. 제목·설명·태그에 배라를 가리키는 말이 있는 영상만 쓴다
    youtube_any_of: tuple = ("배스킨", "베스킨", "라빈스", "라벤스", "배라", "베라", "엄마는 외계인", "엄마는외계인", "baskin")
    # 뉴스: 보도자료에서 행사 일정·혜택과 회사가 발표한 성과 수치를 뽑는다 (pipeline/collect/events.py)
    # 월을 넣은 검색어는 매달 하는 행사(배라위크·31데이)의 지난 기사가 1,000건 안에 들어오게 하려는 것
    news_queries: tuple = ("배스킨라빈스 이달의 맛", "배스킨라빈스 배라위크", "배스킨라빈스 31데이", "배스킨라빈스 프로모션",
                           "배스킨라빈스 할인 혜택", "두바이에서 온 엄마는 외계인",
                           "2월 배라위크", "3월 배라위크", "3월 31데이", "1월 31데이")
    news_lookback_days: int = 10           # 기간 시작 며칠 전 기사부터 (행사 예고 기사)
    # 행사 반응: 행사명 검색지수. 브랜드 전체와 한 요청에 넣어 상대 크기를 비교한다 (키는 promo_id 접두어와 맞춤)
    promo_keyword_groups: dict = field(default_factory=lambda: {
        "brand": ["배스킨라빈스", "베스킨라빈스", "배라"],
        "barawk": ["배라위크", "슈퍼 배라위크", "배스킨라빈스 배라위크"],
        "d31": ["배스킨라빈스 31데이", "배라 31데이", "베라 31데이", "31데이 하프갤론"],
    })
    raw_retention_days: int = 30           # 원문 저장 기간 (유튜브 정책 30일에 맞춤)


LAUNCH = Launch()
RULES = Rules()
COLLECT = Collect()


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
