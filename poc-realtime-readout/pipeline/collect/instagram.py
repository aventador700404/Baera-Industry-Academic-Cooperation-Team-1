"""인스타그램 Business Discovery: 다른 비즈니스 계정(배라·요아정·설빙·하겐다즈)의 공개 수치.

필요한 것 (파트 1 리서치): 팀 인스타 비즈니스 계정 + 연결된 페이스북 페이지 + Meta 앱의 액세스 토큰.
공식 문서가 일부 기능은 고급 권한 전까지 안 될 수 있다고 경고 → `make check-apis`로 초반에 1회 호출 테스트.
상대 계정의 도달·노출 같은 인사이트는 못 받는다. 팔로워, 게시물별 좋아요·댓글 수까지.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from ._http import env, get_json

FIELDS = ("business_discovery.username({u}){{followers_count,media_count,"
          "media.limit({n}){{timestamp,like_count,comments_count,media_type,permalink}}}}")


def _cfg() -> tuple[str, str, str]:
    uid, tok = env("IG_USER_ID"), env("IG_ACCESS_TOKEN")
    if not (uid and tok):
        raise KeyError("IG_USER_ID / IG_ACCESS_TOKEN 없음 (.env)")
    return uid, tok, env("IG_GRAPH_VERSION", "v21.0")


def parse(resp: dict, account: str, today: dt.date) -> tuple[dict, pd.DataFrame]:
    bd = resp.get("business_discovery", {})
    acc = {"date": today, "account": account, "followers": bd.get("followers_count"),
           "media_count": bd.get("media_count")}
    media = pd.DataFrame([{
        "date": today, "account": account, "posted_at": m.get("timestamp"), "media_type": m.get("media_type"),
        "likes": m.get("like_count"), "comments": m.get("comments_count"), "permalink": m.get("permalink"),
    } for m in bd.get("media", {}).get("data", [])])
    return acc, media


def discover(account: str, n_media: int = 25, today: dt.date | None = None) -> tuple[dict, pd.DataFrame]:
    uid, tok, ver = _cfg()
    r = get_json(f"https://graph.facebook.com/{ver}/{uid}", "instagram business discovery",
                 {"fields": FIELDS.format(u=account, n=n_media), "access_token": tok})
    return parse(r, account, today or dt.date.today())
