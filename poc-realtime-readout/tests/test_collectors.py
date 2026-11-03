"""수집기 응답 파싱 (네트워크 없이 고정 응답으로)."""
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from pipeline.collect import instagram, naver, youtube

FIX = Path(__file__).parent / "fixtures"
D = dt.date.fromisoformat


def test_datalab_parse():
    df = naver.parse_datalab(json.loads((FIX / "naver_datalab.json").read_text()))
    assert set(df["keyword"]) == {"bra", "trend"}
    assert df[(df["keyword"] == "bra")]["value"].max() == 100.0


def test_blog_parse_counts_and_sentiment():
    items = json.loads((FIX / "naver_blog.json").read_text())["items"]
    df = naver.parse_blog(items, "bra", D("2026-03-01"), D("2026-03-02"))
    m = df[df["metric"] == "mentions"].set_index("date")["value"]
    assert m[D("2026-03-01")] == 4 and m[D("2026-03-02")] == 1   # 범위 밖 글은 제외
    pos = df[df["metric"] == "positive_ratio"].set_index("date")["value"]
    assert abs(pos[D("2026-03-01")] - 0.75) < 1e-9                # 긍정 3, 부정 1
    assert D("2026-03-02") not in pos.index                        # 판단할 글이 적으면 비움


def test_topic_classification():
    items = json.loads((FIX / "naver_blog.json").read_text())["items"]
    df = naver.parse_topics(items, D("2026-03-01"), D("2026-03-02")).set_index(["date", "topic"])
    assert df.loc[(D("2026-03-01"), "맛"), "mentions"] >= 3
    assert df.loc[(D("2026-03-01"), "맛"), "negative"] >= 1          # '너무 달기만 해서 실망'
    assert list(df.reset_index().columns) == ["date", "topic", "mentions", "positive", "negative"]


def test_sentiment_strips_tags():
    assert naver.sentiment("<b>두바이</b> 진짜 존맛") == 1
    assert naver.sentiment("품절이라 실망") == -1
    assert naver.sentiment("오늘 다녀옴") == 0


def test_youtube_parse_and_retention():
    resp = json.loads((FIX / "youtube_videos.json").read_text())
    df = youtube.parse_videos(resp, D("2026-03-05"), official_channel="UC_official")
    assert dict(zip(df["video_id"], df["channel_type"])) == {"v1": "official", "v2": "consumer"}
    assert list(df.columns) == ["date", "video_id", "channel_type", "title", "views"]  # 원값만
    old = df.assign(date=D("2026-01-01"))
    kept = youtube.prune(pd.concat([old, df]), today=D("2026-03-05"))
    assert set(kept["date"]) == {D("2026-03-05")}


def test_instagram_parse():
    resp = {"business_discovery": {"followers_count": 1200, "media_count": 3,
                                   "media": {"data": [{"timestamp": "2026-03-01T10:00:00+0000",
                                                       "like_count": 50, "comments_count": 4}]}}}
    acc, media = instagram.parse(resp, "brand_a", D("2026-03-02"))
    assert acc["followers"] == 1200 and media["likes"].tolist() == [50]
