"""행사가 없었을 때의 기준선 추정.

이달의 맛은 출시 전 판매 이력이 없다. 그래서 두 가지를 따로 잡는다.
  1) 요일 패턴: 기존 맛의 출시 전 판매에서 추정 (이력이 충분함)
  2) 추세: 이달의 맛의 '행사 없는 날' 판매로 바닥 + 지수 감소 곡선을 맞춤
     qty_t / dow_t = c0 + c1 * exp(-t / k)

k는 격자 탐색, c0와 c1은 최소제곱. 비슷하게 잘 맞는 k가 여러 개면 그 범위 전체로
기준선의 위아래 범위를 같이 낸다. 여기에 하루하루의 변동(sigma)에서 오는 오차도 더한다 (promo.py). 범위가 판정 기준을 걸치거나, 맞추는 데 쓴 행사 없는 날이
적으면(초반 판독) 판촉 판정은 '잠정'으로 표시한다 (promo.py).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

# k < 3 은 출시 반응이 사흘 안에 거의 다 빠진다는 뜻이라 제외.
# 초반 판독(행사 없는 날 5일)에서 그런 곡선이 행사일 기준선을 마음대로 키우는 것을 막는다.
# 위쪽은 넉넉히 둔다: 실제 공개 앵커(15일 100만 → 22일 142만)는 3주 동안 수요가 거의 안 빠진 모양이다.
K_GRID = np.round(np.concatenate([np.arange(3.0, 80.0, 0.25), np.arange(80.0, 300.0, 2.0)]), 2)
CHI2_95 = 3.84


def estimate_dow(daily_total: pd.Series, before: dt.date) -> np.ndarray:
    """요일 지수 (월..일, 기하평균 1). daily_total: index=date, 기존 맛 브랜드 합계."""
    s = daily_total[[d < before for d in daily_total.index]]
    if len(s) < 14:
        return np.ones(7)
    df = pd.DataFrame({"y": np.log(s.to_numpy(dtype=float))}, index=s.index)
    # 주 단위 추세를 빼고 요일 효과만 남긴다
    df["trend"] = pd.Series(df["y"].to_numpy()).rolling(7, center=True, min_periods=4).mean().to_numpy()
    df["res"] = df["y"] - df["trend"]
    df["dow"] = [d.weekday() for d in df.index]
    eff = df.groupby("dow")["res"].mean().reindex(range(7)).fillna(0).to_numpy(copy=True)
    eff -= eff.mean()
    return np.exp(eff)


@dataclass
class Baseline:
    base: np.ndarray       # 점 추정
    lo: np.ndarray
    hi: np.ndarray
    k: float
    k_band: tuple[float, float]
    n_fit: int             # 맞추는 데 쓴 행사 없는 날 수
    sigma: float = 0.0     # 행사 없는 날의 하루 변동 (로그 잔차 표준편차)


def _fit_k(t: np.ndarray, y: np.ndarray, k: float):
    X = np.column_stack([np.ones_like(t, dtype=float), np.exp(-t / k)])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    if coef[0] < 0 or coef[1] < 0:  # 음수면 한쪽만 쓰는 모형으로
        c0 = max(np.mean(y), 1e-9)
        coef = np.array([c0, 0.0])
    pred = np.clip(X @ coef, 1e-9, None)
    sse = float(np.sum((np.log(y) - np.log(pred)) ** 2))
    return coef, sse


def fit_baseline(dates: list[dt.date], qty: np.ndarray, promo_mask: np.ndarray,
                 dow: np.ndarray, launch: dt.date, asof: dt.date | None = None) -> Baseline | None:
    """dates 전체에 대해 기준선을 낸다. 맞추는 데는 asof까지의 행사 없는 날만 쓴다."""
    dates = list(dates)
    qty = np.asarray(qty, dtype=float)
    t = np.array([(d - launch).days for d in dates], dtype=float)
    dw = dow[[d.weekday() for d in dates]]
    use = (~promo_mask) & (qty > 0)
    if asof is not None:
        use &= np.array([d <= asof for d in dates])
    n = int(use.sum())
    if n < 3:
        return None
    ty, yy = t[use], qty[use] / dw[use]
    fits = [(k, *_fit_k(ty, yy, k)) for k in K_GRID]
    sses = np.array([f[2] for f in fits])
    i_best = int(np.argmin(sses))
    sse_min = max(sses[i_best], 1e-12)
    band = sses <= sse_min * (1 + CHI2_95 / max(n - 3, 1))
    curves = []
    for (k, coef, _), ok in zip(fits, band):
        if ok:
            curves.append((coef[0] + coef[1] * np.exp(-t / k)) * dw)
    curves = np.array(curves)
    k_best, coef_best, _ = fits[i_best]
    base = (coef_best[0] + coef_best[1] * np.exp(-t / k_best)) * dw
    ks = K_GRID[band]
    sigma = float(np.sqrt(sse_min / max(n - 3, 1)))
    return Baseline(base=base, lo=curves.min(axis=0), hi=curves.max(axis=0),
                    k=float(k_best), k_band=(float(ks.min()), float(ks.max())), n_fit=n, sigma=sigma)
