"""분석이 목 데이터에 심어 둔 사건을 '그 날' 찾아내는지, 미래 데이터를 쓰지 않는지."""
import datetime as dt
import json

from pipeline.config import LAUNCH, asof_dates, weekly_asofs

D = dt.date.fromisoformat


def day(readout, d):
    return next(x for x in readout["days"] if x["date"] == d)


def alerts(readout, kind_prefix):
    return [a for a in readout["alerts"] if a["kind"].startswith(kind_prefix)]


def test_one_snapshot_per_day(readout):
    assert [x["date"] for x in readout["days"]] == [d.isoformat() for d in asof_dates()]
    for x in readout["days"]:
        assert x["monitor"]["key"] == "monitor"
        if x["weekly"]:
            assert [c["key"] for c in x["weekly"]["cards"]] == ["demand", "store", "promo"]


def test_weekly_cards_change_only_on_read_days(readout):
    reads = {d.isoformat() for d in weekly_asofs()}
    prev = None
    for x in readout["days"]:
        w = x["weekly"]
        if prev is not None and w is not None and x["date"] not in reads:
            assert w == {**prev, "new_alerts": w["new_alerts"]}, x["date"]
        prev = w
    assert {x["weekly"]["asof"] for x in readout["days"] if x["weekly"]} == reads


def test_weekly_store_card_keeps_midweek_alerts(readout, truth):
    """주중(3/11)에 뜬 품절 매장이 다음 주간 판독(3/16 월)에 빠지지 않아야 한다."""
    sid = truth["stores"]["stockout_a"]["store_id"]
    alert = next(a for a in readout["alerts"] if a.get("ref") == sid)
    name = alert["title"].split(": ", 1)[-1]
    nxt = min(w for w in weekly_asofs() if w.isoformat() >= alert["date"]).isoformat()
    card = next(c for c in day(readout, nxt)["weekly"]["cards"] if c["key"] == "store")
    assert name in card["head"] and card["pill"]["tone"] == "crit"


def test_promo_incremental_close_to_truth(readout, truth):
    """정답 증분이 화면에 내는 범위 안에 있고, 점 추정도 15% 안."""
    for p in day(readout, LAUNCH.month_end.isoformat())["promos"]:
        true_inc = truth["promos"][p["id"]]["incremental"]
        assert p["inc_lo"] <= true_inc <= p["inc_hi"], (p["id"], p["inc_lo"], true_inc, p["inc_hi"])
        assert abs(p["inc"] - true_inc) / true_inc < 0.15, (p["id"], p["inc"], true_inc)


def test_promo_verdicts(readout):
    got = {p["id"]: (p["verdict_label"], p["firm"]) for p in day(readout, "2026-03-31")["promos"]}
    # 출시 기념 행사는 정답 ROI가 1.0 근처라 범위가 기준을 걸친다 → 잠정으로 남아야 맞다
    assert got == {"launch500": ("중단 검토", False), "barawk": ("중단 검토", True), "d31": ("지속", False)}


def test_first_promo_read_is_tentative(readout):
    first = alerts(readout, "promo")[0]
    p = next(p for p in day(readout, first["date"])["promos"] if p["id"] == "launch500")
    assert p["firm"] is False and p["tentative_reason"] == "few_days"


def test_promo_before_launch_is_listed_not_judged(readout):
    """2월 배라위크는 출시 전이라 이달의 맛 증분이 없다: 행사 목록에는 있고 판정 대상은 아님."""
    feb = next(p for p in readout["promos"] if p["id"] == "barawk_feb")
    assert feb["before_launch"] is True and feb["evidence"].startswith("규칙 추정")
    assert all(p["id"] != "barawk_feb" for p in day(readout, "2026-03-31")["promos"])


def test_promos_carry_evidence(readout):
    for p in readout["promos"]:
        assert p["evidence"] and p["source"].startswith("https://"), p["id"]


def test_small_samples_do_not_alert():
    """글이 적은 날의 비율 차이는 우연일 수 있다: 같은 차이라도 건수가 적으면 안 울린다."""
    from pipeline.analysis.reaction import topic_flags, z_two_prop
    assert z_two_prop(30, 100, 60, 100) < -4 and abs(z_two_prop(3, 10, 6, 10)) < 2
    big = topic_flags(60, 20, 40, 300, 30, 20, 10, 600)      # 비중 0.2 vs 0.05, 긍정률 0.33 vs 0.67
    small = topic_flags(6, 2, 4, 30, 3, 2, 1, 60)           # 같은 비율, 건수 10분의 1
    assert big["surge"] and big["neg_up"] and not small["surge"] and not small["neg_up"]


def test_teaser_spike_caught_same_day(readout):
    a = alerts(readout, "search_spike")
    assert a and a[0]["date"] == LAUNCH.teaser.isoformat()


def test_topic_events_caught_inside_window(readout, truth):
    s, e = map(D, truth["topic_events"]["품절·재고"])
    hit = [a for a in alerts(readout, "topic_surge") if "품절" in a["title"]]
    assert hit and s <= D(hit[0]["date"]) <= e
    s, e = map(D, truth["topic_events"]["맛_부정"])
    hit = [a for a in alerts(readout, "topic_neg") if "'맛'" in a["title"]]
    assert hit and s <= D(hit[0]["date"]) <= e


def test_planted_stores_caught_and_nothing_else(readout, truth):
    store_alerts = alerts(readout, "store")
    found = {a["kind"]: [] for a in store_alerts}
    for key, ev in truth["stores"].items():
        kind = "store_viral" if key == "viral" else "store_check"
        hit = [a for a in store_alerts if a["kind"] == kind and ev["store_id"] in json.dumps(day(readout, a["date"])["stores"], ensure_ascii=False)
               and D(ev["start"]) <= D(a["date"]) <= D(ev["end"]) + dt.timedelta(days=2)]
        assert hit, key
    assert len(store_alerts) == len(truth["stores"]), [a["title"] for a in store_alerts]


def test_conversion_holds_at_month_end(readout):
    c = day(readout, "2026-03-31")["conversion"]
    assert c and c["ratio"] > 1.2   # 검색은 빨리 식고 판매는 버팀 (목 데이터 설계)


def test_no_future_data(readout):
    """3/12까지로 자른 데이터로 다시 돌려도 3/12까지의 알림·카드가 같아야 한다."""
    from pipeline.build import build
    from pipeline.io import Tables, load_all
    cut = D("2026-03-12")
    T = load_all()
    frames = {k: (v[v["date"] <= cut] if "date" in v.columns else v) for k, v in T.frames.items()}
    short = build(Tables(frames, T.provenance))
    keep = lambda r: [a for a in r["alerts"] if a["date"] <= cut.isoformat()]
    assert keep(short) == keep(readout)
    for k in ("monitor", "weekly"):
        assert day(short, "2026-03-12")[k] == day(readout, "2026-03-12")[k]


def test_json_has_no_nan(readout):
    text = json.dumps(readout, ensure_ascii=False, allow_nan=False)
    assert "NaN" not in text


def test_youtube_top_for_a_period_collected_later():
    """지나간 기간을 나중에 수집하면 그 날까지 올라온 영상만, 조회수는 수집일 기준으로 보여 준다."""
    import pandas as pd
    from pipeline.analysis import reaction
    D = dt.date.fromisoformat
    yt = pd.DataFrame([
        {"date": D("2026-11-10"), "video_id": "a", "channel_type": "official", "title": "출시 영상", "views": 300,
         "published_at": D("2026-02-26")},
        {"date": D("2026-11-10"), "video_id": "b", "channel_type": "consumer", "title": "후기", "views": 900,
         "published_at": D("2026-03-10")}])
    out = reaction.youtube_top(yt, D("2026-03-05"))
    assert out["asof"] == "2026-11-10" and [v["title"] for v in out["videos"]] == ["출시 영상"]
    assert reaction.youtube_top(yt, D("2026-02-20")) is None
