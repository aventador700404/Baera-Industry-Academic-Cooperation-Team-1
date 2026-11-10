"""네이버 데이터랩 검색어트렌드 + 블로그·카페 검색.

키 발급처가 두 곳이라 둘 다 받는다 (파트 1 리서치, 네이버클라우드 문서):
- NAVER API HUB (2026-07-31 이후 신규 발급은 여기만): naverapihub.apigw.ntruss.com,
  헤더 X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY. 한시 무료, 월 한도(검색 77.5만·트렌드 5만)에 닿으면 차단.
- 예전 개발자센터 키: openapi.naver.com, 헤더 X-Naver-Client-Id / Secret (2027-06-30까지).
  .env 에 NAVER_API_MODE=openapi 를 넣으면 이쪽으로 부른다. 기본은 hub.

그 밖에:
- 데이터랩은 상대지수(0~100)라 비교할 키워드 그룹은 한 요청에 같이 넣는다 (최대 5그룹).
- 블로그·카페 검색은 본문이 아니라 요약(description)만 준다. 감성은 요약문 기준.
- 검색어당 최대 1,000건(start 1~1000). 그래서 언급 수는 하한값이다.
- 카페글은 작성일 필드가 없다 → 날짜별 집계는 못 하고 전체 건수(total)만 기록한다.
"""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from collections.abc import Iterable
from email.utils import parsedate_to_datetime

import pandas as pd

from ._http import env, get_json, post_json

BASES = {"hub": "https://naverapihub.apigw.ntruss.com", "openapi": "https://openapi.naver.com"}
PATHS = {
    "hub": {"datalab": "/search-trend/v1/search", "blog": "/search/v1/blog", "cafe": "/search/v1/cafearticle",
            "news": "/search/v1/news"},
    "openapi": {"datalab": "/v1/datalab/search", "blog": "/v1/search/blog.json",
                "cafe": "/v1/search/cafearticle.json", "news": "/v1/search/news.json"},
}
URL_ENV = {"datalab": "NAVER_DATALAB_URL", "blog": "NAVER_SEARCH_URL", "cafe": "NAVER_CAFE_URL",
           "news": "NAVER_NEWS_URL"}
MAX_ITEMS = 1000  # 검색 API의 start 상한
KST = dt.timezone(dt.timedelta(hours=9))

# 감성 사전 (정규식). 실데이터 원문(data/collected/raw/blog.csv)에서 확인한 오판을 고친 판:
#   '비추천'이 '추천'으로 긍정, '느끼기는/느끼고'(느끼다)가 부정, '지점별로'가 부정, '#간식추천' 같은 해시태그가 긍정,
#   '안 맛있'·'재구매 의사 없'이 긍정으로 잡히던 것.
# 부정 표현을 먼저 찾아 지운 뒤 긍정을 센다 ('비추천'의 '추천', '안 맛있'의 '맛있'이 긍정으로 다시 잡히지 않게).
# '품절'은 감성 단어로 쓰지 않는다: '품절 대란', '재고 있는 매장 꿀팁'처럼 인기를 말하는 글이 많았다 (품절은 주제로 따로 셈).
NEG = tuple(re.compile(p, re.I) for p in (
    r"비추(?:천)?", r"불만족", r"안\s*맛있|맛있(?:지|진|지는|지도)\s*않", r"맛(?:이)?\s*없(?!을\s*수)",
    r"재구매\s*(?:의사\s*)?(?:는\s*)?(?:없|안|x)", r"두\s*번\s*다시|다시는?\s*안\s*(?:먹|사)",
    r"(?<![가-힣])별로(?!\s*안)", r"실망", r"(?<!안\s)비싸(?!지\s*않|진\s*않)", r"느끼(?:하|함|해|한)",
    r"아쉽|아쉬웠|아쉬움", r"최악", r"달기만", r"(?:너무|넘|엄청)\s*달(?!달)",
))
POS = tuple(re.compile(p, re.I) for p in (
    r"맛있", r"존맛", r"(?<!비)추천", r"강추", r"대박", r"최고", r"(?<!불)만족", r"재구매", r"꿀맛", r"맛도리", r"jmt",
    r"또\s*(?:먹고\s*(?:싶|프)|먹으러|사\s*먹)", r"인생\s*(?:템|맛|아이스크림|디저트)",
    r"맛나", r"좋(?:아|았|네|더라|다|음)", r"찬성", r"맛없을\s*수\s*(?:가\s*)?없",
))
_HASHTAG = re.compile(r"#\S+")   # 해시태그는 감성 판단에서 뺀다 (#추천·#존맛 같은 광고·분류용 태그)

# 주제 분류 사전 (시연용 단어 사전. 한 글이 여러 주제에 걸릴 수 있다)
TOPIC_WORDS = {
    "맛": ("맛", "달", "고소", "쫀득", "식감", "피스타치오", "초코"),
    "비교": ("원조", "비교", "두쫀쿠", "쫀득쿠키", "vs", "보다"),
    "가격·할인": ("가격", "비싸", "할인", "쿠폰", "2+1", "1+1", "500원", "더블", "배라위크", "31데이"),
    "품절·재고": ("품절", "재고", "없어서", "못 샀", "다 팔", "솔드아웃"),
    "양·사이즈": ("사이즈", "양이", "하프갤론", "패밀리", "파인트", "쿼터"),
    "매장·서비스": ("직원", "대기", "줄이", "매장", "응대", "포장"),
}


def mode() -> str:
    m = (env("NAVER_API_MODE") or "hub").strip().lower()
    if m not in BASES:
        raise ValueError(f"NAVER_API_MODE={m!r}: hub 또는 openapi")
    return m


def url(kind: str) -> str:
    """kind: datalab | blog | cafe. NAVER_*_URL 이 있으면 그 주소를 그대로 쓴다."""
    return env(URL_ENV[kind]) or BASES[mode()] + PATHS[mode()][kind]


def _headers() -> dict:
    cid, sec = env("NAVER_CLIENT_ID"), env("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        raise KeyError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 없음 (.env)")
    if mode() == "hub":
        return {"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": sec}
    return {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}


# ---------------------------------------------------------------- 데이터랩
def parse_datalab(resp: dict) -> pd.DataFrame:
    rows = []
    for res in resp.get("results", []):
        for p in res.get("data", []):
            rows.append((dt.date.fromisoformat(p["period"]), "naver_datalab", res["title"], "search_index",
                         float(p["ratio"])))
    return pd.DataFrame(rows, columns=["date", "source", "keyword", "metric", "value"])


def datalab(start: dt.date, end: dt.date, groups: dict[str, list[str]]) -> pd.DataFrame:
    body = {
        "startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "date",
        "keywordGroups": [{"groupName": k, "keywords": v[:20]} for k, v in list(groups.items())[:5]],
    }
    return parse_datalab(post_json(url("datalab"), "naver datalab", body, _headers()))


# ---------------------------------------------------------------- 블로그·카페
_TAG = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    return _TAG.sub("", text or "")


def sentiment(text: str) -> int:
    """+1 긍정, −1 부정, 0 판단 안 함. 제목·요약문 기준 사전 방식 (본문은 API가 주지 않는다).
    걸린 표현 종류 수를 비교한다: 긍정 표현이 더 많으면 긍정, 부정이 더 많으면 부정, 같거나 없으면 판단 안 함."""
    t = _HASHTAG.sub(" ", clean(text))
    n = 0
    for rx in NEG:
        if rx.search(t):
            n += 1
            t = rx.sub(" ", t)
    p = sum(1 for rx in POS if rx.search(t))
    return (p > n) - (n > p)


def post_date(it: dict) -> dt.date | None:
    """블로그는 postdate(YYYYMMDD), 뉴스는 pubDate(RFC 2822, +0900). 둘 다 한국 날짜로."""
    if it.get("pubDate"):
        try:
            return parsedate_to_datetime(it["pubDate"]).astimezone(KST).date()
        except (TypeError, ValueError):
            return None
    try:
        return dt.datetime.strptime(it.get("postdate", ""), "%Y%m%d").date()
    except ValueError:
        return None


def relevant(it: dict, must_have: Iterable[str], any_of: Iterable[str]) -> bool:
    """정확도순 결과에는 다른 이야기도 섞인다. 제목·요약에 신제품을 가리키는 말이 있는 글만 남긴다."""
    t = clean(it.get("title", "") + " " + it.get("description", ""))
    return all(w in t for w in must_have) and any(w in t for w in any_of)


def parse_blog(items: list[dict], keyword: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    cnt, pos, neg = Counter(), Counter(), Counter()
    for it in items:
        d = post_date(it)
        if d is None or not (start <= d <= end):
            continue
        cnt[d] += 1
        s = sentiment(it.get("title", "") + " " + it.get("description", ""))
        pos[d] += s > 0
        neg[d] += s < 0
    rows = []
    for d in sorted(cnt):
        rows.append((d, "naver_blog", keyword, "mentions", float(cnt[d])))
        # 긍정·부정 건수도 남긴다. 알림은 비율의 평균이 아니라 구간 건수를 합쳐서 본다 (글이 적은 날의 0%·100% 방지)
        rows += [(d, "naver_blog", keyword, "positive", float(pos[d])),
                 (d, "naver_blog", keyword, "negative", float(neg[d]))]
        if pos[d] + neg[d] >= 3:  # 판단할 글이 너무 적으면 비움
            rows.append((d, "naver_blog", keyword, "positive_ratio", pos[d] / (pos[d] + neg[d])))
    return pd.DataFrame(rows, columns=["date", "source", "keyword", "metric", "value"])


def parse_topics(items: list[dict], start: dt.date, end: dt.date) -> pd.DataFrame:
    """reaction_topics_daily 형식: 날짜 x 주제별 언급·긍정·부정. 감성 판단이 안 되는 글은 언급만 센다."""
    cnt: Counter = Counter()
    for it in items:
        d = post_date(it)
        if d is None or not (start <= d <= end):
            continue
        text = clean(it.get("title", "") + " " + it.get("description", ""))
        s = sentiment(text)
        for topic, words in TOPIC_WORDS.items():
            if any(w in text for w in words):
                cnt[(d, topic, "m")] += 1
                cnt[(d, topic, "p")] += s > 0
                cnt[(d, topic, "n")] += s < 0
    keys = sorted({(d, t) for d, t, _ in cnt})
    return pd.DataFrame([{"date": d, "topic": t, "mentions": cnt[(d, t, "m")], "positive": cnt[(d, t, "p")],
                          "negative": cnt[(d, t, "n")]} for d, t in keys],
                        columns=["date", "topic", "mentions", "positive", "negative"])


def fetch_items(query: str, start: dt.date | None = None, max_items: int = MAX_ITEMS, sort: str = "date",
                kind: str = "blog") -> list[dict]:
    """100건씩 넘기며 최대 max_items(API 상한 1,000). 최신순은 start보다 오래된 글이 나오면 멈춘다."""
    items: list[dict] = []
    for s in range(1, min(max_items, MAX_ITEMS) + 1, 100):
        r = get_json(url(kind), f"naver {kind}", {"query": query, "display": 100, "start": s, "sort": sort},
                     _headers())
        batch = r.get("items", [])
        items += batch
        if len(batch) < 100:
            break
        last = post_date(batch[-1])
        if sort == "date" and start and last and last < start:
            break
    return items


def collect_posts(queries: Iterable[str], start: dt.date, end: dt.date,
                  max_items: int = MAX_ITEMS, kind: str = "blog") -> tuple[list[dict], dict]:
    """검색어마다 정확도순 + 최신순으로 받아 링크 기준 중복 제거. 지난 기간은 최신순으로 닿지 않을 수 있어
    정확도순을 같이 쓴다. 돌려주는 stats는 데이터 출처 화면에 그대로 쓴다."""
    seen, items, fetched, calls = set(), [], 0, 0
    for q in queries:
        for sort in ("sim", "date"):
            got = fetch_items(q, start, max_items, sort, kind)
            fetched += len(got)
            calls += max(1, -(-len(got) // 100))
            for it in got:
                key = it.get("originallink") or it.get("link") or (clean(it.get("title", "")), post_date(it))
                if key in seen:
                    continue
                seen.add(key)
                items.append(it)
    dates = [d for d in map(post_date, items) if d and start <= d <= end]
    stats = {"queries": list(queries), "fetched": fetched, "unique": len(items), "in_period": len(dates),
             "first": min(dates).isoformat() if dates else None, "last": max(dates).isoformat() if dates else None,
             "calls": calls}
    return items, stats


def blog(query: str, keyword: str, start: dt.date, end: dt.date, max_items: int = MAX_ITEMS) -> pd.DataFrame:
    """최신순으로 최대 1,000건(API 상한). 그 이상은 못 받으므로 언급 수는 하한값이다."""
    return parse_blog(fetch_items(query, start, max_items), keyword, start, end)


def cafe_total(query: str) -> int:
    """카페글은 작성일이 없어 날짜별로 못 센다. 검색 결과 전체 건수만 (1건만 요청)."""
    r = get_json(url("cafe"), "naver cafe", {"query": query, "display": 1, "start": 1, "sort": "sim"}, _headers())
    return int(r.get("total", 0))


def store_mentions(store_names: dict[str, str], start: dt.date, end: dt.date) -> pd.DataFrame:
    """store_reaction_daily 형식: '배스킨라빈스 {지점명}' 블로그 검색의 날짜별 글 수. store_names: store_id → 지점명."""
    frames = []
    for sid, name in store_names.items():
        df = blog(f"배스킨라빈스 {name}", sid, start, end, max_items=100)
        m = df[df["metric"] == "mentions"]
        frames.append(pd.DataFrame({"date": m["date"], "store_id": sid, "mentions": m["value"].astype(int)}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "store_id", "mentions"])
