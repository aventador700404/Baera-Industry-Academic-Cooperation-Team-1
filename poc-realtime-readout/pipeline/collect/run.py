"""공개 API 수집 → data/collected/*.csv. 키가 없는 API는 건너뛰고 목 데이터가 그 자리를 채운다.

실행: python -m pipeline.collect.run            (기본: 티저 4주 전 ~ 월말)
      python -m pipeline.collect.run --check    (키마다 1회 호출만 해 보고 끝)
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys

import pandas as pd

from ..config import COLLECTED, LAUNCH
from . import instagram, naver, youtube
from ._http import env, load_env


def competitors() -> list[str]:
    """IG_ACCOUNTS=계정1,계정2 (배라·요아정·설빙·하겐다즈 공식 계정명은 팀이 확인해서 넣는다)."""
    return [a.strip() for a in (env("IG_ACCOUNTS") or "").split(",") if a.strip()]


def check() -> int:
    """키가 있는 API마다 가장 싼 호출 한 번. 실패해도 계속하고 마지막에 요약."""
    load_env()
    today = dt.date.today()
    tests = {
        "네이버 데이터랩": (("NAVER_CLIENT_ID",), lambda: naver.datalab(
            today - dt.timedelta(days=7), today - dt.timedelta(days=1), {"bra": ["배스킨라빈스"]})),
        "네이버 블로그 검색": (("NAVER_CLIENT_ID",), lambda: naver.blog(
            "배스킨라빈스", "bra", today - dt.timedelta(days=3), today, max_items=100)),
        "유튜브 Data API": (("YOUTUBE_API_KEY",), lambda: youtube.search_ids(
            "배스킨라빈스", today - dt.timedelta(days=7), max_results=1)),
        "인스타 Business Discovery": (("IG_USER_ID", "IG_ACCESS_TOKEN", "IG_ACCOUNTS"),
                                       lambda: instagram.discover(competitors()[0], n_media=1)),
    }
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
            print(f"  !! {name}: {type(e).__name__}: {e}")
    return 1 if bad else 0


def collect(start: dt.date, end: dt.date) -> None:
    load_env()
    COLLECTED.mkdir(parents=True, exist_ok=True)
    frames = []
    if env("NAVER_CLIENT_ID"):
        frames.append(naver.datalab(start, end, LAUNCH.keyword_groups))
        frames.append(naver.blog(" ".join(LAUNCH.keyword_groups["bra"][:1]), "bra", start, end))
        print("네이버 데이터랩·블로그 수집 완료")
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(COLLECTED / "reaction_daily.csv", index=False)

    if env("YOUTUBE_API_KEY"):
        path = COLLECTED / "youtube_videos_daily.csv"
        ids = youtube.search_ids(LAUNCH.flavor, LAUNCH.teaser - dt.timedelta(days=3))
        snap = youtube.snapshot(ids)
        old = pd.read_csv(path) if path.exists() else snap.iloc[0:0]
        youtube.prune(pd.concat([old, snap], ignore_index=True)).to_csv(path, index=False)
        print(f"유튜브 스냅샷 {len(snap)}개 영상 (30일 지난 행은 삭제)")

    if env("IG_USER_ID") and env("IG_ACCESS_TOKEN") and competitors():
        accs, media = [], []
        for a in competitors():
            acc, m = instagram.discover(a)
            accs.append(acc)
            media.append(m)
        pd.DataFrame(accs).to_csv(COLLECTED / "instagram_accounts_daily.csv", index=False)
        pd.concat(media, ignore_index=True).to_csv(COLLECTED / "instagram_media_daily.csv", index=False)
        print("인스타 Business Discovery 수집 완료 (화면 반영은 다음 단계)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--start", default=(LAUNCH.teaser - dt.timedelta(days=26)).isoformat())
    ap.add_argument("--end", default=LAUNCH.month_end.isoformat())
    a = ap.parse_args()
    if a.check:
        sys.exit(check())
    collect(dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end))


if __name__ == "__main__":
    main()
