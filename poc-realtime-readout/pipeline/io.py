"""테이블 읽기. 우선순위: data/raw (본사) > data/collected (공개 API) > data/generated (목).

테이블마다 어디서 왔는지(provenance)를 같이 돌려줘서 화면에 '목 / 공개 API / 본사' 표시를 붙인다.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import COLLECTED, GENERATED, RAW
from .schema import OPTIONAL, TABLES, coerce

SOURCES = (("raw", RAW), ("api", COLLECTED), ("mock", GENERATED))


@dataclass
class Tables:
    frames: dict[str, pd.DataFrame]
    provenance: dict[str, str]

    def __getitem__(self, name: str) -> pd.DataFrame:
        return self.frames[name]

    def has(self, name: str) -> bool:
        return name in self.frames and len(self.frames[name]) > 0


def read_csv(path) -> pd.DataFrame:
    """CSV 읽기. 엑셀에서 저장한 본사 파일은 BOM 붙은 utf-8이거나 cp949일 수 있어 둘 다 받는다."""
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949")


def load_all() -> Tables:
    frames, prov = {}, {}
    for name in TABLES:
        for tag, folder in SOURCES:
            path = folder / f"{name}.csv"
            if path.exists():
                frames[name] = coerce(name, read_csv(path))
                prov[name] = tag
                break
        else:
            if name not in OPTIONAL:
                raise FileNotFoundError(
                    f"{name}.csv 가 data/raw, data/collected, data/generated 어디에도 없음. "
                    "먼저 `make mock` 실행")
    # 반응 데이터는 API 수집분과 목을 섞을 수 있다: 수집된 source만 덮어쓴다
    api_path = COLLECTED / "reaction_daily.csv"
    mock_path = GENERATED / "reaction_daily.csv"
    if prov.get("reaction_daily") == "api" and mock_path.exists():
        api = coerce("reaction_daily", read_csv(api_path))
        mock = coerce("reaction_daily", read_csv(mock_path))
        got = set(zip(api["source"], api["keyword"], api["metric"]))
        keep = mock[[k not in got for k in zip(mock["source"], mock["keyword"], mock["metric"])]]
        if len(keep):
            frames["reaction_daily"] = pd.concat([api, keep], ignore_index=True)
            prov["reaction_daily"] = "mixed"
    return Tables(frames, prov)
