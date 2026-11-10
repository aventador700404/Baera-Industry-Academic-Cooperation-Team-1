"""HTTP + .env 공통. 키는 .env에서만 읽고 코드·로그에 남기지 않는다."""
from __future__ import annotations

import os
import re
from pathlib import Path

import requests

from ..config import ROOT

TIMEOUT = 20


def load_env(path: Path = ROOT / ".env") -> None:
    """간단한 .env 로더 (python-dotenv 없이). 이미 있는 환경변수는 덮지 않는다."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name, default)
    return v if v else None


class ApiError(RuntimeError):
    pass


_SECRET = re.compile(r"(key|access_token|client_secret)=[^&\s'\"]+", re.I)


def redact(text: str) -> str:
    """오류 문구에 주소가 섞여 키가 남지 않게 지운다."""
    return _SECRET.sub(r"\1=***", text)


def _check(r: requests.Response, what: str) -> dict:
    if r.status_code >= 400:
        # 응답 본문 앞부분만 (키가 섞여 나올 수 있는 URL은 남기지 않음)
        raise ApiError(redact(f"{what}: HTTP {r.status_code} {r.text[:200]}"))
    return r.json()


def get_json(url: str, what: str, params: dict | None = None, headers: dict | None = None) -> dict:
    try:
        r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:   # 연결 오류 문구에는 키가 든 주소가 섞인다 → 종류만 남김
        raise ApiError(f"{what}: {type(e).__name__}") from None
    return _check(r, what)


def post_json(url: str, what: str, body: dict, headers: dict | None = None) -> dict:
    try:
        r = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ApiError(f"{what}: {type(e).__name__}") from None
    return _check(r, what)
