"""수집기 응답 파싱 (네트워크 없이 고정 응답으로)."""
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from pipeline.collect import instagram, naver, youtube

FIX = Path(__file__).parent / "fixtures"
D = dt.date.fromisoformat


def test_datalab_parse():
    df = naver.parse_datalab(json.loads((FIX / "naver_datalab.json").read_text(encoding="utf-8")))
    assert set(df["keyword"]) == {"bra", "trend"}
    assert df[(df["keyword"] == "bra")]["value"].max() == 100.0


def test_blog_parse_counts_and_sentiment():
    items = json.loads((FIX / "naver_blog.json").read_text(encoding="utf-8"))["items"]
    df = naver.parse_blog(items, "bra", D("2026-03-01"), D("2026-03-02"))
    m = df[df["metric"] == "mentions"].set_index("date")["value"]
    assert m[D("2026-03-01")] == 4 and m[D("2026-03-02")] == 1   # 범위 밖 글은 제외
    pos = df[df["metric"] == "positive_ratio"].set_index("date")["value"]
    assert abs(pos[D("2026-03-01")] - 0.75) < 1e-9                # 긍정 3, 부정 1
    assert D("2026-03-02") not in pos.index                        # 판단할 글이 적으면 비움


def test_topic_classification():
    items = json.loads((FIX / "naver_blog.json").read_text(encoding="utf-8"))["items"]
    df = naver.parse_topics(items, D("2026-03-01"), D("2026-03-02")).set_index(["date", "topic"])
    assert df.loc[(D("2026-03-01"), "맛"), "mentions"] >= 3
    assert df.loc[(D("2026-03-01"), "맛"), "negative"] >= 1          # '너무 달기만 해서 실망'
    assert list(df.reset_index().columns) == ["date", "topic", "mentions", "positive", "negative"]


def test_sentiment_strips_tags():
    assert naver.sentiment("<b>두바이</b> 진짜 존맛") == 1
    assert naver.sentiment("품절이라 실망") == -1
    assert naver.sentiment("오늘 다녀옴") == 0


def test_youtube_parse_and_retention():
    resp = json.loads((FIX / "youtube_videos.json").read_text(encoding="utf-8"))
    df = youtube.parse_videos(resp, D("2026-03-05"), official_channel="UC_official")
    assert dict(zip(df["video_id"], df["channel_type"])) == {"v1": "official", "v2": "consumer"}
    assert list(df.columns) == ["date", "video_id", "channel_type", "title", "views", "published_at"]  # 원값만
    old = df.assign(date=D("2026-01-01"))
    kept = youtube.prune(pd.concat([old, df]), today=D("2026-03-05"))
    assert set(kept["date"]) == {D("2026-03-05")}


def test_instagram_parse():
    resp = {"business_discovery": {"followers_count": 1200, "media_count": 3,
                                   "media": {"data": [{"timestamp": "2026-03-01T10:00:00+0000",
                                                       "like_count": 50, "comments_count": 4}]}}}
    acc, media = instagram.parse(resp, "brand_a", D("2026-03-02"))
    assert acc["followers"] == 1200 and media["likes"].tolist() == [50]


# ---------------------------------------------------------------- 키만 넣으면 돌도록: 호출 방식·수집 흐름
def _env(monkeypatch, **kv):
    for k in ("NAVER_API_MODE", "NAVER_SEARCH_URL", "NAVER_DATALAB_URL", "NAVER_CAFE_URL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in kv.items():
        monkeypatch.setenv(k, v)


def test_naver_hub_is_default_and_openapi_is_switchable(monkeypatch):
    _env(monkeypatch, NAVER_CLIENT_ID="id", NAVER_CLIENT_SECRET="sec")
    assert naver.url("blog") == "https://naverapihub.apigw.ntruss.com/search/v1/blog"
    assert naver.url("datalab") == "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
    assert naver.url("cafe").endswith("/search/v1/cafearticle")
    assert naver._headers() == {"X-NCP-APIGW-API-KEY-ID": "id", "X-NCP-APIGW-API-KEY": "sec"}
    monkeypatch.setenv("NAVER_API_MODE", "openapi")
    assert naver.url("blog") == "https://openapi.naver.com/v1/search/blog.json"
    assert set(naver._headers()) == {"X-Naver-Client-Id", "X-Naver-Client-Secret"}


def _fake_search(pages_by_sort):
    """sort별로 미리 정한 글 목록을 100개씩 잘라 돌려주는 가짜 검색."""
    def get_json(url, what, params=None, headers=None):
        if "cafe" in url:
            return {"total": 321, "items": []}
        items = pages_by_sort[params["sort"]]
        s = params["start"] - 1
        return {"total": len(items), "items": items[s:s + params["display"]]}
    return get_json


def _post(i, day, title="배라 두바이 존맛 추천"):
    return {"title": title, "description": "", "link": f"https://blog/{i}", "postdate": day}


def test_collect_posts_merges_sorts_and_keeps_only_new_product_posts(monkeypatch):
    _env(monkeypatch, NAVER_CLIENT_ID="id", NAVER_CLIENT_SECRET="sec")
    sim = [_post(i, "20260305") for i in range(150)] + [_post(999, "20260305", "두바이 여행 후기")]
    date = [_post(i, "20260320") for i in range(100, 260)]          # 100~149는 sim과 겹침
    monkeypatch.setattr(naver, "get_json", _fake_search({"sim": sim, "date": date}))
    items, st = naver.collect_posts(["배라 두바이"], D("2026-03-01"), D("2026-03-31"))
    assert st["fetched"] == 151 + 160 and st["unique"] == 261          # 링크 기준 중복 제거
    assert st["first"] == "2026-03-05" and st["last"] == "2026-03-20"
    rel = [it for it in items if naver.relevant(it, ("두바이",), ("배라", "배스킨"))]
    assert len(rel) == 260                                             # '두바이 여행'은 빠짐
    assert naver.cafe_total("배라 두바이") == 321


def test_youtube_comments_and_channel_hint():
    resp = {"items": [{"snippet": {"topLevelComment": {"snippet": {"publishedAt": "2026-03-02T09:00:00Z"}}}},
                      {"snippet": {"topLevelComment": {"snippet": {"publishedAt": "2026-03-02T21:00:00Z"}}}},
                      {"snippet": {"topLevelComment": {"snippet": {"publishedAt": "2026-04-10T01:00:00Z"}}}}]}
    dates = youtube.parse_comment_dates(resp)
    df = youtube.comments_daily(dates, "bra", D("2026-03-01"), D("2026-03-31"))
    assert df.to_dict("records") == [{"date": D("2026-03-02"), "source": "youtube", "keyword": "bra",
                                      "metric": "comments", "value": 2.0}]   # 기간 밖 댓글은 제외
    sn = {"channelTitle": "배스킨라빈스 Baskin Robbins Korea", "channelId": "X"}
    assert youtube.channel_type(sn, None, ("배스킨라빈스",)) == "official"
    assert youtube.channel_type(sn, "UC_other", ("배스킨라빈스",)) == "consumer"   # 채널 ID가 있으면 그걸 따름


def test_errors_never_carry_keys():
    from pipeline.collect._http import redact
    msg = redact("ConnectionError: url: /youtube/v3/search?part=id&key=AIzaSECRET123&q=x")
    assert "AIzaSECRET123" not in msg and "key=***" in msg


def test_collect_runs_end_to_end_without_network(monkeypatch, tmp_path):
    from pipeline.collect import run
    _env(monkeypatch, NAVER_CLIENT_ID="CID_X1", NAVER_CLIENT_SECRET="SEC_X2", YOUTUBE_API_KEY="YK_X3")
    monkeypatch.delenv("IG_USER_ID", raising=False)
    monkeypatch.setattr(run, "COLLECTED", tmp_path)
    monkeypatch.setattr(run, "LOG", tmp_path / "_collect_log.json")
    monkeypatch.setattr(run, "load_env", lambda: None)
    sim = [_post(i, "20260305") for i in range(30)]
    monkeypatch.setattr(naver, "get_json", _fake_search({"sim": sim, "date": sim}))
    monkeypatch.setattr(naver, "post_json", lambda *a, **k: json.loads((FIX / "naver_datalab.json").read_text(encoding="utf-8")))

    def yt_get(url, what, params=None, headers=None):
        if url.endswith("/search"):
            return {"items": [{"id": {"videoId": "v1"}}, {"id": {"videoId": "v2"}}]}
        if url.endswith("/videos"):
            return json.loads((FIX / "youtube_videos.json").read_text(encoding="utf-8"))
        return {"items": [{"snippet": {"topLevelComment": {"snippet": {"publishedAt": "2026-03-03T00:00:00Z"}}}}]}
    monkeypatch.setattr(youtube, "get_json", yt_get)

    log = run.collect(D("2026-02-01"), D("2026-03-31"))
    src = log["sources"]
    assert all(src[k]["ok"] for k in ("naver_datalab", "naver_blog", "naver_cafe", "youtube"))
    dumped = json.dumps(log)
    assert log["naver_mode"] == "hub" and not any(k in dumped for k in ("CID_X1", "SEC_X2", "YK_X3"))
    reac = pd.read_csv(tmp_path / "reaction_daily.csv")
    assert {"naver_datalab", "naver_blog", "youtube"} <= set(reac["source"])
    assert (tmp_path / "reaction_topics_daily.csv").exists()
    yt = pd.read_csv(tmp_path / "youtube_videos_daily.csv")
    assert "published_at" in yt.columns and len(yt) == 2
    assert json.loads((tmp_path / "_collect_log.json").read_text(encoding="utf-8"))["period"] == ["2026-02-01", "2026-03-31"]


def test_one_api_failing_does_not_stop_the_others(monkeypatch, tmp_path):
    from pipeline.collect import run
    from pipeline.collect._http import ApiError
    _env(monkeypatch, NAVER_CLIENT_ID="id", NAVER_CLIENT_SECRET="sec")
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("IG_USER_ID", raising=False)
    monkeypatch.setattr(run, "COLLECTED", tmp_path)
    monkeypatch.setattr(run, "LOG", tmp_path / "_collect_log.json")
    monkeypatch.setattr(run, "load_env", lambda: None)

    def boom(*a, **k):
        raise ApiError("naver datalab: HTTP 401 unauthorized")
    monkeypatch.setattr(naver, "post_json", boom)
    monkeypatch.setattr(naver, "get_json", _fake_search({"sim": [_post(1, "20260305")], "date": []}))
    log = run.collect(D("2026-03-01"), D("2026-03-31"))
    assert log["sources"]["naver_datalab"]["ok"] is False and "401" in log["sources"]["naver_datalab"]["error"]
    assert log["sources"]["naver_blog"]["ok"] is True


def test_spelling_variants_are_searched_and_kept():
    """배라·베라, 배스킨라빈스·베스킨라빈스·배스킨라벤스 같은 섞어 쓴 표기도 검색하고 거르지 않는다."""
    from pipeline.config import COLLECT, LAUNCH
    bra = " ".join(LAUNCH.keyword_groups["bra"])
    for w in ("베라 두바이", "베스킨라빈스 두바이", "배스킨라벤스 두바이"):
        assert w in bra
    assert len(LAUNCH.keyword_groups["bra"]) <= 20 and len(LAUNCH.keyword_groups) <= 5   # 데이터랩 제한
    assert "베라 두바이" in COLLECT.blog_queries
    keep = lambda t: naver.relevant({"title": t, "description": ""}, COLLECT.must_have, COLLECT.any_of)
    for t in ("베스킨라벤스 두바이 맛 후기", "베라 두바이 엄외 먹어봄", "배스킨 라빈스 두바이 신상", "두바이 엄마는 외계인 존맛"):
        assert keep(t), t
    assert not keep("두바이 여행 3박 4일 후기")
