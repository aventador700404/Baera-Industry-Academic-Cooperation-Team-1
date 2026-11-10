"""Windows 기본 인코딩(cp949)에서도 깨지지 않는지."""
import json
import re
from pathlib import Path

import pandas as pd

from pipeline import build, io

ROOT = Path(__file__).resolve().parents[1]


def test_text_io_names_encoding():
    """read_text / write_text 는 인코딩을 꼭 적는다 (없으면 Windows에서 cp949로 저장됨)."""
    bad = []
    for p in list((ROOT / "pipeline").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.(read_text|write_text)\(", line) and "encoding=" not in line and "re.search" not in line:
                bad.append(f"{p.relative_to(ROOT)}:{i}")
    assert not bad, bad


def test_collect_log_reads_old_cp949(tmp_path, monkeypatch):
    log = tmp_path / "_collect_log.json"
    log.write_bytes(json.dumps({"note": "블로그 수집 실패"}, ensure_ascii=False).encode("cp949"))
    monkeypatch.setattr(build, "COLLECTED", tmp_path)
    assert build.collect_log() == {"note": "블로그 수집 실패"}


def test_read_csv_accepts_excel_exports(tmp_path):
    df = pd.DataFrame({"store_id": ["S1"], "store_name": ["혜화점"], "region": ["서울"]})
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        f = tmp_path / f"m_{enc}.csv"
        df.to_csv(f, index=False, encoding=enc)
        assert io.read_csv(f).equals(df), enc
