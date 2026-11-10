"""YouTube Data API v3: 영상 조회수 스냅샷 + 댓글 작성일.

정책상 지켜야 할 것 (파트 1 리서치, YouTube API Services 개발자 정책):
- API로 받은 수치로 새 지표(좋아요율 등)를 계산·표시하지 않는다 → 원값(views)만 저장
- 30일 넘게 저장하지 않는다 → prune()이 수집일 기준 30일 지난 행을 지운다. 발표 전에 다시 수집해 갱신
- 쿼터: 일 10,000 units. search.list = 100, videos.list = 1 (50개씩), commentThreads.list = 1 (100개씩)
- 과거 일별 조회수는 API로 못 받는다. 지나간 기간은 '지금 시점 조회수 + 게시일'로만 보여 준다
- 댓글은 본문을 저장하지 않고 작성일만 날짜별로 센다 (반응이 언제 몰렸는지)
- 시각은 UTC로 오므로 한국 날짜(KST)로 바꿔 센다 (밤 9시 이후 댓글이 전날로 잡히지 않게)
- 검색 결과에는 관련 없는 영상(일반 '두바이 초콜릿' 영상 등)이 섞인다 → 제목·설명·태그로 거른다
"""
from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Iterable

import pandas as pd

from ._http import ApiError, env, get_json

BASE = "https://www.googleapis.com/youtube/v3"
RETENTION_DAYS = 30
COLUMNS = ["date", "video_id", "channel_type", "title", "views", "published_at"]
KST = dt.timezone(dt.timedelta(hours=9))


def kst_date(ts: str) -> dt.date | None:
    """'2026-03-02T21:00:00Z' → 2026-03-03 (한국 날짜)."""
    if not ts:
        return None
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(KST).date()
    except ValueError:
        return dt.date.fromisoformat(ts[:10])


def is_relevant(snippet: dict, any_of: Iterable[str]) -> bool:
    text = " ".join([snippet.get("title", ""), snippet.get("description", ""), snippet.get("channelTitle", ""),
                     " ".join(snippet.get("tags", []))])
    text = text.lower()
    return any(w.lower() in text for w in any_of)


def _key() -> str:
    k = env("YOUTUBE_API_KEY")
    if not k:
        raise KeyError("YOUTUBE_API_KEY 없음 (.env)")
    return k


def _ts(d: dt.date) -> str:
    return f"{d.isoformat()}T00:00:00Z"


def search_ids(query: str, published_after: dt.date, published_before: dt.date | None = None,
               max_results: int = 25) -> list[str]:
    params = {"part": "id", "q": query, "type": "video", "order": "viewCount", "maxResults": max_results,
              "publishedAfter": _ts(published_after), "regionCode": "KR", "key": _key()}
    if published_before:
        params["publishedBefore"] = _ts(published_before + dt.timedelta(days=1))
    r = get_json(f"{BASE}/search", "youtube search", params)
    return [it["id"]["videoId"] for it in r.get("items", []) if it.get("id", {}).get("videoId")]


def channel_type(snippet: dict, official_channel: str | None, hints: Iterable[str] = ()) -> str:
    if official_channel:
        return "official" if snippet.get("channelId") == official_channel else "consumer"
    title = (snippet.get("channelTitle") or "").lower()
    return "official" if any(h.lower() in title for h in hints) else "consumer"


def parse_videos(resp: dict, today: dt.date, official_channel: str | None,
                 hints: Iterable[str] = (), any_of: Iterable[str] | None = None) -> pd.DataFrame:
    """any_of를 주면 제목·설명·태그에 그 말이 하나도 없는 영상은 뺀다."""
    rows = []
    for it in resp.get("items", []):
        sn, stt = it.get("snippet", {}), it.get("statistics", {})
        if any_of is not None and not is_relevant(sn, any_of):
            continue
        pub = kst_date(sn.get("publishedAt") or "")
        rows.append((today, it["id"], channel_type(sn, official_channel, hints), sn.get("title", ""),
                     int(stt.get("viewCount", 0)), pub or today))
    return pd.DataFrame(rows, columns=COLUMNS)


def raw_rows(resp: dict, any_of: Iterable[str] | None = None) -> list[dict]:
    """원문 보관용 최소 정보 (설명 앞부분까지). 정책상 30일 안에 지운다."""
    out = []
    for it in resp.get("items", []):
        sn, stt = it.get("snippet", {}), it.get("statistics", {})
        out.append({"video_id": it["id"], "title": sn.get("title", ""), "channel": sn.get("channelTitle", ""),
                    "published_at": sn.get("publishedAt", ""), "views": int(stt.get("viewCount", 0)),
                    "description": (sn.get("description") or "")[:300],
                    "relevant": True if any_of is None else is_relevant(sn, any_of)})
    return out


def snapshot(video_ids: list[str], today: dt.date | None = None, hints: Iterable[str] = (),
             any_of: Iterable[str] | None = None) -> tuple[pd.DataFrame, list[dict]]:
    """(관련 영상의 조회수 스냅샷, 받은 영상 전체의 원문 행). 원문 행의 relevant로 걸러진 영상을 볼 수 있다."""
    today = today or dt.date.today()
    frames, raw = [], []
    for i in range(0, len(video_ids), 50):
        r = get_json(f"{BASE}/videos", "youtube videos", {
            "part": "snippet,statistics", "id": ",".join(video_ids[i:i + 50]), "key": _key()})
        frames.append(parse_videos(r, today, env("YOUTUBE_OFFICIAL_CHANNEL_ID"), hints, any_of))
        raw += raw_rows(r, any_of)
    df = pd.concat(frames, ignore_index=True) if frames else parse_videos({}, today, None)
    return df, raw


def parse_comment_dates(resp: dict) -> list[dt.date]:
    out = []
    for it in resp.get("items", []):
        d = kst_date(it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {}).get("publishedAt", ""))
        if d:
            out.append(d)
    return out


def comment_dates(video_id: str, max_pages: int = 5) -> tuple[list[dt.date], int]:
    """영상 하나의 댓글 작성일 (최신순, 100개씩). 댓글이 꺼진 영상은 빈 목록. (작성일들, 호출 수)"""
    dates, token, calls = [], None, 0
    for _ in range(max_pages):
        params = {"part": "snippet", "videoId": video_id, "maxResults": 100, "order": "time",
                  "textFormat": "plainText", "key": _key()}
        if token:
            params["pageToken"] = token
        try:
            r = get_json(f"{BASE}/commentThreads", "youtube comments", params)
        except ApiError as e:
            if "commentsDisabled" in str(e) or "HTTP 403" in str(e):
                break
            raise
        calls += 1
        dates += parse_comment_dates(r)
        token = r.get("nextPageToken")
        if not token:
            break
    return dates, calls


def comments_daily(dates: Iterable[dt.date], keyword: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """reaction_daily 형식: 날짜별 댓글 수 (본문 없이 작성일만 센 값)."""
    cnt = Counter(d for d in dates if start <= d <= end)
    return pd.DataFrame([(d, "youtube", keyword, "comments", float(cnt[d])) for d in sorted(cnt)],
                        columns=["date", "source", "keyword", "metric", "value"])


def prune(df: pd.DataFrame, today: dt.date | None = None) -> pd.DataFrame:
    """30일 지난 스냅샷을 지우고, 같은 날 두 번 수집했으면 그 날 영상별로 마지막 것만 남긴다."""
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=RETENTION_DAYS)
    df = df.assign(date=pd.to_datetime(df["date"]).dt.date)
    df = df[df["date"] > cutoff].drop_duplicates(subset=["date", "video_id"], keep="last")
    return df.reset_index(drop=True)
