import json

import pytest

from pipeline.config import GENERATED, RAW


@pytest.fixture(scope="session", autouse=True)
def mock_data():
    """목 데이터가 없으면 만든다. data/raw에 본사 데이터가 있으면 목 기준 테스트는 건너뛴다."""
    if any(RAW.glob("*.csv")):
        pytest.skip("data/raw 에 본사 데이터가 있어 목 데이터 기준 테스트를 건너뜀")
    if not (GENERATED / "_truth.json").exists() or not (GENERATED / "reaction_topics_daily.csv").exists():
        from pipeline.mock import generate
        generate.main()
    return json.loads((GENERATED / "_truth.json").read_text())


@pytest.fixture(scope="session")
def truth(mock_data):
    return mock_data


@pytest.fixture(scope="session")
def readout():
    from pipeline.build import build
    return build()
