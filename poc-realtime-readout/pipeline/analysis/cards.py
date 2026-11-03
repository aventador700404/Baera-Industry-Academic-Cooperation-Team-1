"""그 주에 내릴 결정 세 가지: 증산·재출시 / 판촉 지속·조정·중단 / 매장 지원 우선순위.

입력은 build.py가 계산한 숫자 묶음(dict). 판정 기준은 config.RULES.
"""
from __future__ import annotations

import datetime as dt

from ..config import LAUNCH, RULES, VIEWS, View
from . import fmt

PROMO_MSG = {
    "good": "증분이 할인 비용을 넘김 → 유지하되 사이즈업·대상 품목 점검",
    "warn": "할인 대부분이 원래 살 손님에게 돌아감 → 할인 폭 축소 또는 일정 분리",
    "crit": "할인 비용보다 늘어난 매출이 작음 → 대상 품목·채널 축소 또는 중단 검토",
}


def card(key: str, title: str, pill: tuple[str, str], head: str, items: list[str], tags: list[str]) -> dict:
    return {"key": key, "title": title, "pill": {"tone": pill[0], "label": pill[1]},
            "head": head, "items": [i for i in items if i], "tags": tags}


def demand_card(v: View, c: dict) -> dict:
    L = LAUNCH
    title = "이달의 맛 증산 · 재출시"
    r = c["reaction"]
    if v.id == "pre":
        mult = r.get("last_x") or 0
        items = [
            f"출시 전 평소(티저 전) 일평균 대비 {fmt.md(v.to)} 검색지수 {mult:.0f}배",
            (f"블로그·카페 언급 최근 7일 {fmt.n(r['mentions_7d'])}건 (평소 7일 {fmt.n(r['mentions_pre_7d'])}건)"
             if r.get("mentions_pre_7d") else None),
            ("업계 키워드 '두바이 쫀득쿠키'는 3주 전보다 "
             f"{fmt.pct(abs(c['trend_change']))} 낮아 유행 수명 점검 필요"
             if (c.get("trend_change") or 0) < -0.2 else None),
        ]
        return card("demand", title, ("warn", "초도 물량 검토"),
                    f"티저 이틀 만에 검색지수가 평소의 {mult:.0f}배", items, ["reaction"])
    if v.id == VIEWS[-1].id:
        pos = r.get("positive_7d")
        ok = pos is not None and pos >= RULES.rerelease_positive
        items = [
            f"{L.launch.month}월 누적 {fmt.n(c['cum'])}개, 원조 '{L.parent_flavor}' 목표보다 일평균 "
            f"{fmt.pct(c['month_avg'] / L.target_daily - 1)} 많음",
            f"긍정률 {int(RULES.rerelease_positive * 100)}% 이상 유지 → 재출시 후보로 등록" if ok
            else f"긍정률 {int(RULES.rerelease_positive * 100)}% 미만 → 재출시 보류",
            "반응 둔화 속도를 다음 이달의 맛 물량 계획에 반영",
        ]
        head = (f"월 판매 {c['month_rank']}위, 최근 7일 긍정률 {fmt.pct(pos)}" if pos is not None
                else f"월 판매 {c['month_rank']}위")
        return card("demand", title, ("good", "재출시 후보") if ok and c["month_rank"] == 1 else ("info", "재출시 보류"),
                    head, items, ["sales", "reaction"])
    ratio = round(c["w_demand"] / L.target_daily, 2)  # 표시값과 판정값을 같게
    pill = (("good", "증산 검토") if ratio >= RULES.demand_up else
            ("info", "유지") if ratio >= RULES.demand_hold else ("warn", "감산 검토"))
    anchor = next((f" · 공개 앵커 {(d - L.launch).days + 1}일 {val // 10_000:,}만 개와 일치"
                   for d, val in L.anchors if d == v.to), "")
    items = [
        f"이번 판독 주간 일평균 판매 {fmt.n(c['w_avg'])}개 중 맛 수요(기준선) {fmt.n(c['w_demand'])}개",
        f"목표: 원조 '{L.parent_flavor}' 일평균 {fmt.n(L.target_daily)}개 (가정)",
        f"누적 {fmt.n(c['cum'])}개{anchor}",
    ]
    return card("demand", title, pill, f"할인 효과를 뺀 맛 수요가 목표의 {ratio:.2f}배", items, ["sales", "reaction"])


def promo_card(v: View, c: dict) -> dict:
    title = "판촉 행사 지속 · 조정 · 중단"
    done = [p for p in c["promos"] if p["status"] == "done"]
    if not done:
        first = c["promos"][0] if c["promos"] else None
        sched = ", ".join(f"{p['name']} {fmt.md(_d(p['start']))}"
                          + (f"~{fmt.md(_d(p['end']))}" if p['start'] != p['end'] else "") for p in c["promos"])
        head = (f"출시일({fmt.md(LAUNCH.launch)})이 {first['name']}"
                f"({fmt.md(_d(first['start']))}~{fmt.md(_d(first['end']))})와 겹침"
                if first and _d(first["start"]) <= LAUNCH.launch <= _d(first["end"]) else "행사 일정 확인")
        items = ["출시 첫 주 판매에 맛 효과와 할인 효과가 섞임",
                 "행사 없는 날 판매로 기준선을 먼저 잡아 두고 증분만 셈",
                 f"예정 행사: {sched}"]
        return card("promo", title, ("warn", "효과 분리 필요"), head, items, ["sales"])
    p = done[-1]
    label = p["verdict_label"] + ("" if p["firm"] else " (잠정)")
    overlap = _d(p["start"]) <= LAUNCH.launch <= _d(p["end"])
    items = [
        PROMO_MSG[p["verdict"]],
        "출시일과 겹친 행사라 출시 수요와 섞임 → 출시 주간 할인은 분리 권장" if overlap and p["verdict"] != "good" else None,
        f"행사 기간 판매 {fmt.n(p['act'])}개 중 행사 덕분 {fmt.n(p['inc'])}개 "
        f"(범위 {fmt.n(p['inc_lo'])}~{fmt.n(p['inc_hi'])})",
        f"할인 비용 {fmt.million_won(p['cost_won'])} (가정)",
        None if p["firm"] else (
            f"행사 없는 날 {p['n_fit']}일로 기준선을 잡아 잠정 → 다음 판독에서 확정"
            if p["tentative_reason"] == "few_days" else
            f"ROI 범위 {p['roi_lo']:.2f}~{p['roi_hi']:.2f}가 판정 기준을 걸침 → 다음 판독에서 확정"),
    ]
    return card("promo", title, (p["verdict"], label),
                f"{p['name']} 증분 {fmt.pct(p['inc_pct'])}, 증분 ROI {p['roi']:.2f}", items, ["sales", "cost"])


def store_card(v: View, c: dict) -> dict:
    title = "매장 지원 우선순위"
    if v.id == "pre":
        return card("store", title, ("info", "출시 후 판독"), "출시 첫 주부터 매장별 순위와 주변 반응을 같이 봄",
                    ["순위가 오르는 매장: 재고 선배치·POP 우선",
                     "주변 반응은 높은데 순위가 떨어지는 매장: 품절·운영 점검",
                     "매장 유형별 반응 속도로 초도 물량 배분"], ["sales", "reaction"])
    st = c["stores"]
    alert, riser = st["alert"], st["riser"]
    items = []
    if alert:
        pill = ("crit", "점검 우선")
        head = f"{alert['type']} · {alert['name']}: 반응↑ 판매↓"
        items += [f"주변 SNS 언급 {alert['sns_prev']}→{alert['sns']}건인데 순위 {alert['rank_prev']}위 → {alert['rank']}위",
                  "품절·재고·운영 문제 의심 → 현장 점검 우선"]
    else:
        pill = ("good", "확산 매장 지원")
        head = f"{riser['type']} · {riser['name']} 순위 +{riser['delta']}"
    items.append(f"가장 많이 오른 매장: {riser['type']} · {riser['name']} "
                 f"({riser['rank_prev']}위 → {riser['rank']}위)" + (f", {riser['why']}" if riser.get("why") else "")
                 + " → 재고 선배치")
    peaks = [p for p in c["peaks"] if p["firm"]]
    if len(peaks) >= 2:
        items.append(f"판매가 몰린 날: {peaks[0]['type']} {peaks[0]['day']}일차 → {peaks[-1]['type']} "
                     f"{peaks[-1]['day']}일차 → 다음 맛 초도 물량은 {peaks[0]['type']}부터")
    return card("store", title, pill, head, items, ["sales", "reaction"])


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def build(v: View, c: dict) -> list[dict]:
    return [demand_card(v, c), promo_card(v, c), store_card(v, c)]
