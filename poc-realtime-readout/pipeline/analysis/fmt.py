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


def times(x: float) -> str:
    """배수: 10배 미만은 소수 한 자리."""
    return f"{x:.1f}배" if x < 10 else f"{x:.0f}배"
