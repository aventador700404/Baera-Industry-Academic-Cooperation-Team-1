"""분석이 목 데이터에 심어 둔 정답을 찾아내는지."""
import json
import math

from pipeline.config import VIEWS


def view(readout, vid):
    return next(v for v in readout["views"] if v["id"] == vid)


def test_promo_incremental_close_to_truth(readout, truth):
    last = view(readout, VIEWS[-1].id)
    for p in last["promos"]:
        true_inc = truth["promos"][p["id"]]["incremental"]
        assert abs(p["inc"] - true_inc) / true_inc < 0.10, (p["id"], p["inc"], true_inc)


def test_promo_verdicts(readout):
    got = {p["id"]: p["verdict_label"] for p in view(readout, "w5")["promos"]}
    assert got == {"baraday": "조정", "barawk": "중단 검토", "d31": "지속"}


def test_early_read_is_tentative(readout):
    p = next(p for p in view(readout, "w1")["promos"] if p["id"] == "baraday")
    assert p["firm"] is False and p["tentative_reason"] == "few_days"


def test_stockouts_flagged_in_their_week(readout, truth):
    for vid, key in (("w2", "stockout_w2"), ("w3", "stockout_w3")):
        rows = view(readout, vid)["stores"]["rows"]
        hit = [r for r in rows if r["store_id"] == truth["planted"][key]]
        assert hit and hit[0]["flag"] == "check", (vid, rows[:2])


def test_store_context_explains_moves(readout, truth):
    for vid, key, word in (("w3", "popup_w3", "유동인구"), ("w4", "competitor_w4", "개점")):
        rows = view(readout, vid)["stores"]["rows"]
        hit = [r for r in rows if r["store_id"] == truth["planted"][key]]
        assert hit and word in (hit[0]["why"] or ""), (vid, key)


def test_type_peak_order(readout):
    peaks = view(readout, "w5")["peaks"]
    assert peaks[0]["type"] == "대학가" and peaks[-1]["type"] == "주거"


def test_every_view_has_three_cards(readout):
    assert [v["id"] for v in readout["views"]] == [v.id for v in VIEWS]
    for v in readout["views"]:
        assert [c["key"] for c in v["cards"]] == ["demand", "promo", "store"]


def test_json_has_no_nan(readout):
    text = json.dumps(readout, ensure_ascii=False, allow_nan=False)  # NaN이면 ValueError
    assert "NaN" not in text
