"""뉴스 기사(제목·요약)에서 행사 일정·혜택과 회사가 발표한 성과 수치를 뽑는다.

네이버 뉴스 검색 API는 기사 본문을 주지 않고 요약 1~2문장만 준다. 그래서
- 날짜는 요약에 있는 것만 쓴다. 없으면 행사 규칙(배라위크 = 매월 셋째 월요일부터 7일, 31데이 = 31일,
  이달의 맛 = 그달 1일)으로 채우고 근거를 '규칙 추정'으로 표시한다.
- 같은 보도자료를 여러 매체가 받아 쓴다. 행사 하나에 기사 수와 매체 수를 따로 센다.
- 성과 수치는 회사가 발표한 것만 나온다 (잘된 행사만 보도되는 선택 편향). 판매 증분·ROI는 본사 데이터로 본다.
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from collections import Counter
from urllib.parse import urlparse

import pandas as pd

from .naver import clean, post_date

# 행사 종류: id 접두어 → (표시 이름, 찾을 말). promo_calendar의 promo_id 접두어와 맞춘다
EVENTS = {
    "barawk": ("배라위크", ("배라위크",)),
    "d31": ("31데이", ("31데이", "31DAY", "31 DAY")),
    "flavor": ("이달의 맛 출시", ("이달의 맛",)),
    "party": ("파티데이", ("파티데이",)),
}
BRAND = ("배스킨", "베스킨", "배라", "라빈스")

# 혜택 문구: (정규식, 표시 함수)
BENEFITS = [
    (re.compile(r"([가-힣A-Za-z]{2,6})\s*(\d)\s*\+\s*(\d)"), lambda m: f"{m.group(1)} {m.group(2)}+{m.group(3)}"),
    (re.compile(r"(\d{1,2})\s*%\s*할인"), lambda m: f"{m.group(1)}% 할인"),
    (re.compile(r"패밀리[^.]{0,20}?하프\s*갤론"), lambda m: "패밀리 → 하프갤론"),
    (re.compile(r"사이즈\s*(?:업그레이드|업|UP)", re.I), lambda m: "사이즈업"),
    (re.compile(r"(\d{3,5})\s*원[^.]{0,10}?더블"), lambda m: f"{m.group(1)}원 더블"),
    (re.compile(r"사전\s*예약"), lambda m: "사전예약"),
    (re.compile(r"네이버\s*페이"), lambda m: "네이버페이 추가 혜택"),
]

# 날짜 문구 (요약에 있는 것만). '15일 만에'는 성과 문구라 날짜에서 뺀다
_CLAIM_DAYS = re.compile(r"\d{1,3}\s*일\s*만에")
_RANGE_MD = re.compile(r"(\d{1,2})월\s*(\d{1,2})일\s*(?:부터|~|-|–)\s*(?:(\d{1,2})월\s*)?(\d{1,2})일")
_RANGE_D = re.compile(r"(?<![\d월])(\d{1,2})일\s*(?:부터|~|-|–)\s*(\d{1,2})일")
_UNTIL = re.compile(r"(?<![\d~\-–])(\d{1,2})일\s*까지")
_SINGLE_MD = re.compile(r"(\d{1,2})월\s*(\d{1,2})일")
_EXPLICIT_MONTH = re.compile(r"(\d{1,2})월\s*(?:['‘\"“]?\s*)?(?:이달의 맛|슈퍼\s*배라위크|배라위크|31데이)")

# 성과 문구: "출시 15일 만에 (누적 판매) 100만 개", "판매량 44% 증가"
_CLAIM_COUNT = re.compile(r"(\d{1,3})\s*일\s*만에[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*만\s*개")
_CLAIM_PCT = re.compile(r"(판매(?:량)?|매출|영업이익|이달의 맛)[^0-9.]{0,15}?(\d+(?:\.\d+)?)\s*%\s*(?:증가|성장|늘|↑|상승)")


def _resolve(day: int, month: int | None, pub: dt.date) -> dt.date | None:
    """월이 없으면 기사 날짜에 가까운 달로 (기사보다 1주 전 ~ 6주 뒤)."""
    cands = []
    months = [month] if month else [pub.month, pub.month % 12 + 1, (pub.month - 2) % 12 + 1]
    for m in months:
        for y in (pub.year - 1, pub.year, pub.year + 1):
            if 1 <= day <= calendar.monthrange(y, m)[1]:
                d = dt.date(y, m, day)
                if pub - dt.timedelta(days=10) <= d <= pub + dt.timedelta(days=45):
                    cands.append(d)
    return min(cands, key=lambda d: abs((d - pub).days)) if cands else None


def extract_dates(text: str, pub: dt.date) -> tuple[dt.date | None, dt.date | None]:
    """(시작, 끝). 하루짜리면 시작 = 끝. 못 찾으면 None."""
    t = _CLAIM_DAYS.sub(" ", text)
    m = _RANGE_MD.search(t)
    if m:
        s = _resolve(int(m.group(2)), int(m.group(1)), pub)
        e = _resolve(int(m.group(4)), int(m.group(3) or m.group(1)), pub)
        return s, e
    m = _RANGE_D.search(t)
    if m:
        s = _resolve(int(m.group(1)), None, pub)
        e = _resolve(int(m.group(2)), s.month if s else None, pub) if s else None
        if s and e and e < s:
            e = _resolve(int(m.group(2)), s.month % 12 + 1, pub)
        return s, e
    m = _SINGLE_MD.search(t)
    if m:
        d = _resolve(int(m.group(2)), int(m.group(1)), pub)
        return d, d
    m = _UNTIL.search(t)
    if m:
        return None, _resolve(int(m.group(1)), None, pub)
    return None, None


def third_monday(y: int, m: int) -> dt.date:
    first = dt.date(y, m, 1)
    return first + dt.timedelta(days=(7 - first.weekday()) % 7 + 14)


def rule_dates(etype: str, y: int, m: int) -> tuple[dt.date | None, dt.date | None]:
    if etype == "barawk":
        s = third_monday(y, m)
        return s, s + dt.timedelta(days=6)
    if etype == "d31":
        return (dt.date(y, m, 31), dt.date(y, m, 31)) if calendar.monthrange(y, m)[1] == 31 else (None, None)
    if etype == "flavor":
        return dt.date(y, m, 1), None
    return None, None


def benefits(text: str) -> list[str]:
    out = []
    for rx, fn in BENEFITS:
        out += [fn(m) for m in rx.finditer(text)]
    return out


def classify(text: str) -> list[str]:
    return [k for k, (_, words) in EVENTS.items() if any(w in text for w in words)]


def event_month(etype: str, text: str, start: dt.date | None, pub: dt.date) -> tuple[int, int]:
    """행사가 속한 달: 요약에 '3월 이달의 맛'처럼 적혀 있으면 그 달, 아니면 찾은 날짜, 아니면 기사 날짜."""
    m = _EXPLICIT_MONTH.search(text)
    if m:
        mo = int(m.group(1))
        y = pub.year + (1 if mo < pub.month - 6 else 0)
        return y, mo
    if start:
        return start.year, start.month
    if etype == "flavor" and pub.day >= 24:   # 말일 무렵 '이달의 맛' 기사는 다음 달 출시 예고
        nxt = pub + dt.timedelta(days=10)
        return nxt.year, nxt.month
    return pub.year, pub.month


def _mode(xs: list):
    xs = [x for x in xs if x is not None]
    return Counter(xs).most_common(1)[0][0] if xs else None


def _quoted(text: str) -> str | None:
    m = re.search(r"[‘'\"“]([^’'\"”]{2,24})[’'\"”]", text)
    return m.group(1).strip() if m else None


def extract(items: list[dict], start: dt.date, end: dt.date) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(행사 후보표, 발표 성과표). 기간은 행사 날짜(없으면 기사 날짜) 기준."""
    groups: dict[tuple, list[dict]] = {}
    claims = []
    for it in items:
        pub = post_date(it)
        if pub is None:
            continue
        title, desc = clean(it.get("title", "")), clean(it.get("description", ""))
        text = f"{title} {desc}"
        if not any(b in text for b in BRAND):
            continue
        link = it.get("originallink") or it.get("link") or ""
        for m in _CLAIM_COUNT.finditer(text):
            claims.append({"pub": pub, "kind": "누적 판매", "days": int(m.group(1)),
                           "count": int(round(float(m.group(2)) * 10_000)),
                           "product": "두바이" if ("두바이" in text or "외계인" in text) else "",
                           "text": text[max(0, m.start() - 30): m.end() + 10].strip(), "link": link})
        for m in _CLAIM_PCT.finditer(text):
            claims.append({"pub": pub, "kind": f"{m.group(1)} 증가율", "days": None, "count": None,
                           "pct": float(m.group(2)), "product": "두바이" if "두바이" in text else "",
                           "text": text[max(0, m.start() - 20): m.end() + 10].strip(), "link": link})
        for etype in classify(text):
            s, e = extract_dates(text, pub)
            y, mo = event_month(etype, text, s, pub)
            groups.setdefault((etype, y, mo), []).append({
                "pub": pub, "title": title, "text": text, "start": s, "end": e, "link": link,
                "outlet": urlparse(link).netloc.replace("www.", ""), "benefits": benefits(text),
                "super": "슈퍼" in text, "product": _quoted(text) if etype == "flavor" else None})

    rows = []
    for (etype, y, mo), arts in groups.items():
        s, e = _mode([a["start"] for a in arts]), _mode([a["end"] for a in arts])
        rs, re_ = rule_dates(etype, y, mo)
        if etype == "d31":
            # 31데이 기사의 'N일까지'는 사전예약 마감이다. 날짜는 규칙(31일)으로, 요약에 31일이 있으면 기사 확인
            said = any(re.search(r"(?<!\d)31일", a["text"]) for a in arts)
            s, e, evidence = rs, rs, "기사 + 규칙" if said else "규칙 추정"
        else:
            evidence = "기사 날짜" if s and (e or etype == "flavor") else "기사 + 규칙" if (s or e) else "규칙 추정"
            if s is None and e is not None and rs and rs <= e:
                s = rs
            s, e = s or rs, e or re_
        if s is None or not (start - dt.timedelta(days=7) <= s <= end):
            continue
        name = EVENTS[etype][0]
        if etype == "barawk" and any(a["super"] for a in arts):
            name = "슈퍼 배라위크"
        if etype == "flavor":
            prod = _mode([a["product"] for a in arts])
            name = f"{mo}월 이달의 맛" + (f": {prod}" if prod else "")
        ben = [b for b, _ in Counter(b for a in arts for b in set(a["benefits"])).most_common(4)]
        arts = sorted(arts, key=lambda a: a["pub"])
        rows.append({"event_id": f"{etype}_{y}{mo:02d}", "type": etype, "name": name,
                     "start": s, "end": e, "evidence": evidence, "benefits": " · ".join(ben),
                     "n_articles": len(arts), "n_outlets": len({a["outlet"] for a in arts if a["outlet"]}),
                     "first_pub": arts[0]["pub"], "title": arts[0]["title"],
                     "sources": " ".join(list(dict.fromkeys(a["link"] for a in arts if a["link"]))[:3])})
    ev_cols = ["event_id", "type", "name", "start", "end", "evidence", "benefits", "n_articles", "n_outlets",
               "first_pub", "title", "sources"]
    ev = pd.DataFrame(rows, columns=ev_cols).sort_values("start").reset_index(drop=True) if rows \
        else pd.DataFrame(columns=ev_cols)
    cl_cols = ["pub", "kind", "days", "count", "pct", "product", "text", "link"]
    cl = pd.DataFrame(claims).reindex(columns=cl_cols) if claims else pd.DataFrame(columns=cl_cols)
    if len(cl):
        cl = cl.sort_values("pub").drop_duplicates(subset=["kind", "days", "count", "pct", "product"])
    return ev, cl.reset_index(drop=True)
