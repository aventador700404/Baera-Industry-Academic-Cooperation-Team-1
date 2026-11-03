"""화면 문구용 숫자 표기."""
from __future__ import annotations

import datetime as dt


def n(x: float) -> str:
    return f"{round(x):,}"


def pct(x: float, digits: int = 0) -> str:
    return f"{x * 100:.{digits}f}%"


def md(d: dt.date) -> str:
    return f"{d.month}/{d.day}"


def signed(x: float) -> str:
    return f"+{round(x):,}" if x >= 0 else f"−{abs(round(x)):,}"


def million_won(x: float) -> str:
    return f"{x / 1e6:,.0f}백만 원"
