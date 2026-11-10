"""데이터 계약: 이 열 구조만 맞으면 목 데이터 대신 본사 데이터가 그대로 들어간다.

docs/DATA.md 의 표와 같은 내용. 바꾸면 둘 다 고친다.
"""
from __future__ import annotations

import pandas as pd

# 테이블 이름 → {열: 타입}. 타입은 date / int / float / str
TABLES: dict[str, dict[str, str]] = {
    "sales_daily": {"date": "date", "store_id": "str", "flavor": "str", "qty": "int"},
    "store_master": {"store_id": "str", "store_name": "str", "region": "str"},
    "promo_calendar": {
        "promo_id": "str", "name": "str", "start": "date", "end": "date",
        "discount_rate": "float", "desc": "str",
    },
    "reaction_daily": {"date": "date", "source": "str", "keyword": "str", "metric": "str", "value": "float"},
    "reaction_topics_daily": {"date": "date", "topic": "str", "mentions": "int", "positive": "int", "negative": "int"},
    "youtube_videos_daily": {
        "date": "date", "video_id": "str", "channel_type": "str", "title": "str", "views": "int",
        "published_at": "date",
    },
    "store_reaction_daily": {"date": "date", "store_id": "str", "mentions": "int"},
    "ad_daily": {"date": "date", "campaign": "str", "channel": "str", "impressions": "int", "clicks": "int",
                 "spend": "int"},
}

# 없어도 화면이 도는 테이블 (해당 열·문구만 빠짐)
OPTIONAL = {"youtube_videos_daily", "reaction_topics_daily", "store_reaction_daily", "ad_daily"}

# 있으면 쓰고 없으면 빈 값으로 채우는 열. 행사표의 근거 표시는 본사 캘린더에는 없을 수 있다
#   evidence: 확인 / 규칙 추정 / 가정 같은 확인 수준,  source: 근거 링크
OPTIONAL_COLS: dict[str, dict[str, str]] = {
    "promo_calendar": {"evidence": "str", "source": "str"},
}


class SchemaError(ValueError):
    pass


def coerce(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """열 확인 + 타입 변환. 빠진 열이 있으면 SchemaError."""
    extra = OPTIONAL_COLS.get(name, {})
    df = df.assign(**{c: "" for c in extra if c not in df.columns})
    spec = {**TABLES[name], **extra}
    missing = [c for c in spec if c not in df.columns]
    if missing:
        raise SchemaError(f"{name}: 빠진 열 {missing} (필요: {list(TABLES[name])})")
    out = df[list(spec)].copy()
    for col, typ in spec.items():
        if typ == "date":
            out[col] = pd.to_datetime(out[col]).dt.date
        elif typ == "int":
            out[col] = pd.to_numeric(out[col], errors="raise").round().astype("int64")
        elif typ == "float":
            out[col] = pd.to_numeric(out[col], errors="raise").astype("float64")
        else:
            out[col] = out[col].fillna("").astype(str)
    if name == "sales_daily" and (out["qty"] < 0).any():
        raise SchemaError("sales_daily: qty 음수")
    if name == "promo_calendar" and (out["start"] > out["end"]).any():
        raise SchemaError("promo_calendar: start > end")
    return out
