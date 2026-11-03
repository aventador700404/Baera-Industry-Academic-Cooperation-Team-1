"""YouTube Data API v3: 영상 조회수 일별 스냅샷.

정책상 지켜야 할 것 (파트 1 리서치, YouTube API Services 개발자 정책):
- API로 받은 수치로 새 지표(좋아요율 등)를 계산·표시하지 않는다 → 원값(views)만 저장
- 30일 넘게 저장하지 않는다 → prune()이 수집일 기준 30일 지난 행을 지운다
- 쿼터: 일 10,000 units. search.list = 100 units, videos.list = 1 unit (50개씩)
- 과거 일별 조회수는 API로 못 받는다. 매일 스냅샷을 쌓아야 추이가 생긴다
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from ._http import env, get_json

BASE = "https://www.googleapis.com/youtube/v3"
RETENTION_DAYS = 30


def _key() -> str:
    k = env("YOUTUBE_API_KEY")
    if not k:
        raise KeyError("YOUTUBE_API_KEY 없음 (.env)")
    return k


def search_ids(query: str, published_after: dt.date, max_results: int = 25) -> list[str]:
    r = get_json(f"{BASE}/search", "youtube search", {
        "part": "id", "q": query, "type": "video", "order": "viewCount", "maxResults": max_results,
        "publishedAfter": f"{published_after.isoformat()}T00:00:00Z", "regionCode": "KR", "key": _key()})
    return [it["id"]["videoId"] for it in r.get("items", []) if it.get("id", {}).get("videoId")]


def parse_videos(resp: dict, today: dt.date, official_channel: str | None) -> pd.DataFrame:
    rows = []
    for it in resp.get("items", []):
        sn, stt = it.get("snippet", {}), it.get("statistics", {})
        ch = "official" if official_channel and sn.get("channelId") == official_channel else "consumer"
        rows.append((today, it["id"], ch, sn.get("title", ""), int(stt.get("viewCount", 0))))
    return pd.DataFrame(rows, columns=["date", "video_id", "channel_type", "title", "views"])


def snapshot(video_ids: list[str], today: dt.date | None = None) -> pd.DataFrame:
    today = today or dt.date.today()
    frames = []
    for i in range(0, len(video_ids), 50):
        r = get_json(f"{BASE}/videos", "youtube videos", {
            "part": "snippet,statistics", "id": ",".join(video_ids[i:i + 50]), "key": _key()})
        frames.append(parse_videos(r, today, env("YOUTUBE_OFFICIAL_CHANNEL_ID")))
    return pd.concat(frames, ignore_index=True) if frames else parse_videos({}, today, None)


def prune(df: pd.DataFrame, today: dt.date | None = None) -> pd.DataFrame:
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=RETENTION_DAYS)
    return df[pd.to_datetime(df["date"]).dt.date > cutoff].reset_index(drop=True)
