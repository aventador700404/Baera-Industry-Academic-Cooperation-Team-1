import json

import pytest

from pipeline.config import GENERATED, RAW


@pytest.fixture(scope="session", autouse=True)
def mock_data(tmp_path_factory):
    """목 데이터가 없으면 만든다. data/raw에 본사 데이터가 있으면 목 기준 테스트는 건너뛴다.

    레포에 올라간 공개 API 수집분(data/collected)은 테스트에서 빼고 목 데이터만으로 돌린다
    (목에 심어 둔 정답과 비교하는 테스트라서)."""
    if any(RAW.glob("*.csv")):
        pytest.skip("data/raw 에 본사 데이터가 있어 목 데이터 기준 테스트를 건너뜀")
    if not (GENERATED / "_truth.json").exists() or not (GENERATED / "reaction_topics_daily.csv").exists():
        from pipeline.mock import generate
        generate.main()
    from pipeline import build, io
    empty = tmp_path_factory.mktemp("collected_empty")
    mp = pytest.MonkeyPatch()
    mp.setattr(io, "SOURCES", (("raw", RAW), ("api", empty), ("mock", GENERATED)))
    mp.setattr(io, "COLLECTED", empty)
    mp.setattr(build, "COLLECTED", empty)
    yield json.loads((GENERATED / "_truth.json").read_text(encoding="utf-8"))
    mp.undo()


@pytest.fixture(scope="session")
def truth(mock_data):
    return mock_data


@pytest.fixture(scope="session")
def readout():
    from pipeline.build import build
    return build()
