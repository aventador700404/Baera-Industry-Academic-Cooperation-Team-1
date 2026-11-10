"""공개 API 수집 → data/collected/*.csv + _collect_log.json. 키가 없는 API는 건너뛰고 목 데이터가 그 자리를 채운다.

실행: python -m pipeline.collect.run            (기본: config.COLLECT 기간, 2025-11-01 ~ 2026-03-31)
      python -m pipeline.collect.run --check    (키마다 1회 호출만 해 보고 끝)

API 하나가 실패해도 나머지는 계속 모은다. 무엇을 몇 건 모았는지, 실패했으면 왜인지는
_collect_log.json 에 남고 화면의 '데이터 출처' 탭이 그대로 보여 준다. 키 값은 어디에도 남기지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

import pandas as pd

from ..config import COLLECT, COLLECTED, LAUNCH
from . import events, instagram, naver, youtube
from ._http import env, load_env, redact

LOG = COLLECTED / "_collect_log.json"


# ---------------------------------------------------------------- 원문 보관 (raw 층)
def raw_dir():
    return COLLECTED / "raw"


def save_raw(name: str, rows: list[dict], today: dt.date) -> int:
    """수집한 원문을 그대로 남긴다: data/collected/raw/{name}_{수집일}.jsonl (깃에 안 올라감).
    집계값이 왜 그렇게 나왔는지 나중에 글 단위로 다시 볼 수 있게. 보관 기간은 COLLECT.raw_retention_days."""
    d = raw_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}_{today.isoformat()}.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows), encoding="utf-8")
    return len(rows)


def prune_raw(today: dt.date) -> None:
    for f in raw_dir().glob("*.jsonl") if raw_dir().exists() else []:
        try:
            day = dt.date.fromisoformat(f.stem.rsplit("_", 1)[-1])
        except ValueError:
            continue
        if (today - day).days > COLLECT.raw_retention_days:
            f.unlink()


def _post_raw(it: dict, relevant: bool | None = None) -> dict:
    row = {"date": naver.post_date(it), "title": naver.clean(it.get("title", "")),
           "description": naver.clean(it.get("description", "")),
           "link": it.get("originallink") or it.get("link", ""), "author": it.get("bloggername", "")}
    if relevant is not None:
        row["relevant"] = relevant
    return row


def _err(e: Exception) -> str:
    return redact(f"{type(e).__name__}: {e}")


def competitors() -> list[str]:
    """IG_ACCOUNTS=계정1,계정2 (배라·요아정·설빙·하겐다즈 공식 계정명은 팀이 확인해서 넣는다)."""
    return [a.strip() for a in (env("IG_ACCOUNTS") or "").split(",") if a.strip()]


def check() -> int:
    """키가 있는 API마다 가장 싼 호출 한 번. 실패해도 계속하고 마지막에 요약."""
    load_env()
    today = dt.date.today()
    q = COLLECT.blog_queries[0]
    tests = {
        "네이버 데이터랩": (("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"), lambda: naver.datalab(
            today - dt.timedelta(days=7), today - dt.timedelta(days=1), {"bra": ["배스킨라빈스"]})),
        "네이버 블로그 검색": (("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"),
                         lambda: naver.fetch_items(q, max_items=100, sort="sim")),
        "네이버 카페 검색": (("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"), lambda: [naver.cafe_total(q)]),
        "네이버 뉴스 검색": (("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"),
                         lambda: naver.fetch_items("배스킨라빈스", max_items=100, sort="sim", kind="news")),
        "유튜브 Data API": (("YOUTUBE_API_KEY",), lambda: youtube.search_ids(
            "배스킨라빈스", today - dt.timedelta(days=7), max_results=1)),
        "인스타 Business Discovery": (("IG_USER_ID", "IG_ACCESS_TOKEN", "IG_ACCOUNTS"),
                                       lambda: instagram.discover(competitors()[0], n_media=1)),
    }
    if env("NAVER_CLIENT_ID"):
        print(f"  네이버 호출 방식: {naver.mode()} ({naver.url('blog').split('/search')[0]})")
    bad = 0
    for name, (keys, fn) in tests.items():
        if not all(env(k) for k in keys):
            print(f"  -  {name}: 키 없음 → 목 데이터 사용 ({', '.join(keys)})")
            continue
        try:
            out = fn()
            size = len(out) if hasattr(out, "__len__") else 1
            print(f"  OK {name}: 응답 {size}건")
        except Exception as e:  # noqa: BLE001 - 점검용이라 전부 잡아서 보여준다
            bad += 1
            print(f"  !! {name}: {_err(e)}")
    return 1 if bad else 0


def _naver(start: dt.date, end: dt.date, log: dict) -> list[pd.DataFrame]:
    frames = []
    today = dt.date.today()
    try:
        dl = naver.datalab(start, end, LAUNCH.keyword_groups)
        frames.append(dl)
        log["naver_datalab"] = {"ok": True, "rows": len(dl), "calls": 1, "groups": LAUNCH.keyword_groups,
                                "first": str(dl["date"].min()) if len(dl) else None,
                                "last": str(dl["date"].max()) if len(dl) else None}
        print(f"  네이버 데이터랩: {len(dl)}행")
    except Exception as e:  # noqa: BLE001
        log["naver_datalab"] = {"ok": False, "error": _err(e)}
        print(f"  !! 네이버 데이터랩: {_err(e)}")
    try:
        # 행사명 검색지수: 브랜드 전체와 한 요청에 넣어 행사 기간에 얼마나 올랐는지 본다 (키워드 이름 앞에 promo_)
        pdl = naver.datalab(start, end, COLLECT.promo_keyword_groups)
        pdl["keyword"] = "promo_" + pdl["keyword"]
        frames.append(pdl)
        log["naver_datalab_promo"] = {"ok": True, "rows": len(pdl), "calls": 1, "groups": COLLECT.promo_keyword_groups}
        print(f"  네이버 데이터랩 (행사명): {len(pdl)}행")
    except Exception as e:  # noqa: BLE001
        log["naver_datalab_promo"] = {"ok": False, "error": _err(e)}
        print(f"  !! 네이버 데이터랩 (행사명): {_err(e)}")
    try:
        items, st = naver.collect_posts(COLLECT.blog_queries, start, end)
        rel_flags = [naver.relevant(it, COLLECT.must_have, COLLECT.any_of) for it in items]
        rel = [it for it, ok in zip(items, rel_flags) if ok]
        save_raw("blog", [_post_raw(it, ok) for it, ok in zip(items, rel_flags)], today)
        frames.append(naver.parse_blog(rel, COLLECT.blog_keyword, start, end))
        topics = naver.parse_topics(rel, start, end)
        if len(topics):
            topics.to_csv(COLLECTED / "reaction_topics_daily.csv", index=False)
        in_period = sum(1 for d in map(naver.post_date, rel) if d and start <= d <= end)
        log["naver_blog"] = {"ok": True, **st, "relevant": len(rel), "relevant_in_period": in_period}
        print(f"  네이버 블로그: 받은 글 {st['unique']}건, 신제품 글 {len(rel)}건 (기간 안 {in_period}건)")
    except Exception as e:  # noqa: BLE001
        log["naver_blog"] = {"ok": False, "error": _err(e)}
        print(f"  !! 네이버 블로그: {_err(e)}")
    try:
        totals = {q: naver.cafe_total(q) for q in COLLECT.cafe_queries}
        log["naver_cafe"] = {"ok": True, "total_by_query": totals, "calls": len(totals),
                             "note": "카페글은 작성일이 없어 날짜별 집계 대신 검색 결과 전체 건수만 기록"}
        print(f"  네이버 카페: {totals}")
    except Exception as e:  # noqa: BLE001
        log["naver_cafe"] = {"ok": False, "error": _err(e)}
        print(f"  !! 네이버 카페: {_err(e)}")
    try:
        # 뉴스: 행사 일정·혜택과 발표된 성과 수치. 성과 기사는 기간이 끝난 뒤에도 나오므로 지금까지의 기사를 다 본다
        nstart = start - dt.timedelta(days=COLLECT.news_lookback_days)
        items, st = naver.collect_posts(COLLECT.news_queries, nstart, end, kind="news")
        save_raw("news", [_post_raw(it) for it in items], today)
        ev, cl = events.extract(items, start, end)
        ev.to_csv(COLLECTED / "news_events.csv", index=False)
        cl.to_csv(COLLECTED / "news_claims.csv", index=False)
        log["naver_news"] = {"ok": True, **st, "events": len(ev), "claims": len(cl)}
        print(f"  네이버 뉴스: 기사 {st['unique']}건 → 행사 {len(ev)}개, 발표 수치 {len(cl)}개")
    except Exception as e:  # noqa: BLE001
        log["naver_news"] = {"ok": False, "error": _err(e)}
        print(f"  !! 네이버 뉴스: {_err(e)}")
    return frames


def _youtube(start: dt.date, end: dt.date, log: dict) -> list[pd.DataFrame]:
    try:
        ids: list[str] = []
        for q in COLLECT.youtube_queries:
            ids += [i for i in youtube.search_ids(q, COLLECT.youtube_after, end, COLLECT.youtube_max_videos)
                    if i not in ids]
        snap, raw = youtube.snapshot(ids, hints=COLLECT.official_channel_hint, any_of=COLLECT.youtube_any_of)
        save_raw("youtube", raw, dt.date.today())
        dropped = [r["title"] for r in raw if not r["relevant"]]
        path = COLLECTED / "youtube_videos_daily.csv"
        old = pd.read_csv(path) if path.exists() else snap.iloc[0:0]
        if len(old) and "published_at" not in old.columns:   # 예전 형식 파일은 버리고 새로
            old = snap.iloc[0:0]
        youtube.prune(pd.concat([old, snap], ignore_index=True)).to_csv(path, index=False)
        top = snap.sort_values("views", ascending=False)["video_id"].head(COLLECT.comment_videos).tolist()
        dates, c_calls = [], 0
        for vid in top:
            ds, n = youtube.comment_dates(vid, COLLECT.comment_pages)
            dates += ds
            c_calls += n
        cm = youtube.comments_daily(dates, COLLECT.blog_keyword, start, end)
        units = 100 * len(COLLECT.youtube_queries) + -(-len(ids) // 50) + c_calls
        log["youtube"] = {"ok": True, "videos": len(snap), "official": int((snap["channel_type"] == "official").sum()),
                          "dropped_irrelevant": len(dropped), "dropped_examples": dropped[:3],
                          "comment_videos": len(top), "comments": len(dates),
                          "comments_in_period": int(cm["value"].sum()) if len(cm) else 0,
                          "units": units, "snapshot_date": dt.date.today().isoformat()}
        print(f"  유튜브: 영상 {len(snap)}개 (관련 없는 영상 {len(dropped)}개 제외), 댓글 {len(dates)}개 (약 {units} units)")
        return [cm]
    except Exception as e:  # noqa: BLE001
        log["youtube"] = {"ok": False, "error": _err(e)}
        print(f"  !! 유튜브: {_err(e)}")
        return []


def collect(start: dt.date, end: dt.date) -> dict:
    load_env()
    COLLECTED.mkdir(parents=True, exist_ok=True)
    log: dict = {"collected_at": dt.datetime.now().isoformat(timespec="seconds"),
                 "period": [start.isoformat(), end.isoformat()], "sources": {}}
    frames: list[pd.DataFrame] = []
    prune_raw(dt.date.today())
    if env("NAVER_CLIENT_ID") and env("NAVER_CLIENT_SECRET"):
        log["naver_mode"] = naver.mode()
        frames += _naver(start, end, log["sources"])
    else:
        print("  -  네이버: 키 없음 → 목 데이터 사용")
    if env("YOUTUBE_API_KEY"):
        frames += _youtube(start, end, log["sources"])
    else:
        print("  -  유튜브: 키 없음 → 목 데이터 사용")
    frames = [f for f in frames if len(f)]
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(COLLECTED / "reaction_daily.csv", index=False)

    if env("IG_USER_ID") and env("IG_ACCESS_TOKEN") and competitors():
        try:
            accs, media = [], []
            for a in competitors():
                acc, m = instagram.discover(a)
                accs.append(acc)
                media.append(m)
            pd.DataFrame(accs).to_csv(COLLECTED / "instagram_accounts_daily.csv", index=False)
            pd.concat(media, ignore_index=True).to_csv(COLLECTED / "instagram_media_daily.csv", index=False)
            log["sources"]["instagram"] = {"ok": True, "accounts": len(accs)}
            print("  인스타 Business Discovery 수집 완료 (화면 반영은 다음 단계)")
        except Exception as e:  # noqa: BLE001
            log["sources"]["instagram"] = {"ok": False, "error": _err(e)}
            print(f"  !! 인스타: {_err(e)}")

    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"→ {LOG.relative_to(LOG.parents[2])}")
    return log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--start", default=COLLECT.start.isoformat())
    ap.add_argument("--end", default=COLLECT.end.isoformat())
    a = ap.parse_args()
    if a.check:
        sys.exit(check())
    collect(dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end))


if __name__ == "__main__":
    main()
