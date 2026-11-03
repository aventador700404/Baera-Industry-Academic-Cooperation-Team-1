"""네이버 데이터랩 검색어트렌드 + 블로그 검색.

주의 (파트 1 리서치):
- 2026-07-31부터 신규 신청은 NAVER API HUB에서만 된다. 기존 개발자센터 키는 HUB에서 못 쓴다
  (기존 앱은 2027-06-30까지 그대로 사용 가능). HUB 엔드포인트·인증 헤더는 팀이 아직 확인 못 해서
  NAVER_DATALAB_URL / NAVER_SEARCH_URL 로 바꿀 수 있게 열어 둔다.
- 데이터랩은 상대지수(0~100)라 비교할 키워드 그룹은 한 요청에 같이 넣어야 한다 (최대 5그룹).
- 블로그 검색은 본문이 아니라 요약(description)만 준다. 감성은 요약문 기준.
"""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter

import pandas as pd

from ._http import env, get_json, post_json

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"

POS = ("맛있", "존맛", "추천", "대박", "최고", "만족", "재구매", "꿀맛", "또 먹", "인생")
NEG = ("별로", "실망", "비싸", "느끼", "아쉽", "최악", "맛없", "달기만", "품절")


def _headers() -> dict:
    cid, sec = env("NAVER_CLIENT_ID"), env("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        raise KeyError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 없음 (.env)")
    return {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}


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
        "keywordGroups": [{"groupName": k, "keywords": v} for k, v in list(groups.items())[:5]],
    }
    url = env("NAVER_DATALAB_URL", DATALAB_URL)
    return parse_datalab(post_json(url, "naver datalab", body, _headers()))


_TAG = re.compile(r"<[^>]+>")


def sentiment(text: str) -> int:
    """+1 긍정, −1 부정, 0 판단 안 함. 단어 사전 방식이라 시연용."""
    t = _TAG.sub("", text)
    p, n = sum(w in t for w in POS), sum(w in t for w in NEG)
    return (p > n) - (n > p)


def parse_blog(items: list[dict], keyword: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    cnt, pos, neg = Counter(), Counter(), Counter()
    for it in items:
        try:
            d = dt.datetime.strptime(it.get("postdate", ""), "%Y%m%d").date()
        except ValueError:
            continue
        if not (start <= d <= end):
            continue
        cnt[d] += 1
        s = sentiment(it.get("title", "") + " " + it.get("description", ""))
        pos[d] += s > 0
        neg[d] += s < 0
    rows = []
    for d in sorted(cnt):
        rows.append((d, "naver_blog", keyword, "mentions", float(cnt[d])))
        if pos[d] + neg[d] >= 3:  # 판단할 글이 너무 적으면 비움
            rows.append((d, "naver_blog", keyword, "positive_ratio", pos[d] / (pos[d] + neg[d])))
    return pd.DataFrame(rows, columns=["date", "source", "keyword", "metric", "value"])


def blog(query: str, keyword: str, start: dt.date, end: dt.date, max_items: int = 1000) -> pd.DataFrame:
    """최신순으로 최대 1,000건(API 상한). 그 이상은 못 받으므로 언급 수는 하한값이다."""
    url = env("NAVER_SEARCH_URL", SEARCH_URL)
    items: list[dict] = []
    for s in range(1, max_items + 1, 100):
        r = get_json(url, "naver blog", {"query": query, "display": 100, "start": s, "sort": "date"}, _headers())
        batch = r.get("items", [])
        items += batch
        if len(batch) < 100:
            break
        last = batch[-1].get("postdate", "99999999")
        if last < start.strftime("%Y%m%d"):
            break
    return parse_blog(items, keyword, start, end)


def store_mentions(store_names: dict[str, str], start: dt.date, end: dt.date) -> pd.DataFrame:
    """매장별 주간 언급 수: '배스킨라빈스 {지점명}' 블로그 검색. store_names: store_id → 지점명."""
    rows = []
    for sid, name in store_names.items():
        df = blog(f"배스킨라빈스 {name}", sid, start, end, max_items=100)
        n = int(df[df["metric"] == "mentions"]["value"].sum()) if len(df) else 0
        rows.append({"week_start": start, "store_id": sid, "mentions": n})
    return pd.DataFrame(rows)
