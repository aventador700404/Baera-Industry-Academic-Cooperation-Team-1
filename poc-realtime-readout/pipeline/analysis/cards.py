"""판독 → 마케팅이 할 일. 두 층.

매일 모니터링 (카드 1장, 매일 바뀜)
  오늘의 모니터링  최근 3일 알림 중 가장 급한 것(모든 모듈), 없으면 반응 상태 요약.
                  품절처럼 급한 건 주간 판독을 기다리지 않고 여기서 바로 뜬다.
주간 판독 (카드 3장, 매주 월요일 아침 일요일까지의 데이터로 확정 — 팀 장표 7번의 결정 3축)
  증산 · 재출시  (모듈 2 맛별 판매)  할인 효과를 뺀 맛 수요 vs 목표 (첫 주 목표 대비)
  매장 지원      (모듈 3 매장 순위)  주변 반응으로 판독한 점검·바이럴 매장
  판촉 조정      (모듈 4 판촉 효과)  끝난 행사의 증분 ROI 판정
"""
from __future__ import annotations

import datetime as dt

from ..config import LAUNCH, RULES
from . import fmt
from .alerts import PROMO_ACTION, TONE_RANK, pick_for_card

PILL = {"crit": ("crit", "즉시 대응"), "warn": ("warn", "대응 검토"), "good": ("good", "확산 활용"), "info": ("info", "관찰")}


def card(key: str, module: str, title: str, pill: tuple[str, str], head: str, items: list, tags: list[str]) -> dict:
    return {"key": key, "module": module, "title": title, "pill": {"tone": pill[0], "label": pill[1]},
            "head": head, "items": [i for i in items if i], "tags": tags}


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _most_urgent(alerts: list[dict], d: dt.date, days: int = 3) -> dict | None:
    recent = [a for a in alerts if 0 <= (d - _d(a["date"])).days < days]
    if not recent:
        return None
    return sorted(recent, key=lambda a: (TONE_RANK[a["tone"]], -_d(a["date"]).toordinal()))[0]


def monitor_card(d: dt.date, c: dict) -> dict:
    r = c["reaction"]
    status = None
    if r.get("last_x") is not None:
        status = (f"검색지수 출시 전 한 달 평균의 {fmt.times(r['last_x'])}"
                  + (f" (정점 대비 {fmt.pct(r['from_peak'])})" if d > LAUNCH.launch and r.get("from_peak") else "")
                  + (f" · 긍정률 {fmt.pct(r['positive_7d'])}" if r.get("positive_7d") is not None else ""))
    a = _most_urgent(c["alerts"], d)
    if a:
        when = "오늘" if a["date"] == d.isoformat() else fmt.md(_d(a["date"]))
        return card("monitor", a["module"], "오늘의 모니터링", PILL[a["tone"]], a["title"],
                    [f"{when} 감지 · {a['detail']}", f"할 일: {a['action']}", status],
                    ["reaction"] if a["module"] == "reaction" else ["sales", "reaction"])
    return card("monitor", "reaction", "오늘의 모니터링", ("info", "관찰"),
                "특이 신호 없음" if d >= LAUNCH.teaser else "출시 전 평소 수준",
                [status, "검색·언급·주제·영상 신호를 매일 아침 모니터링", "할 일: 현행 유지"], ["reaction"])


def reaction_status(d: dt.date, c: dict) -> dict:
    """신제품 반응 패널 머리: 최근 3일 반응 알림 중 가장 급한 것, 없으면 상태 요약 (매일)."""
    r = c["reaction"]
    a = pick_for_card(c["alerts"], d, "reaction")
    status = None
    if r.get("last_x") is not None:
        status = (f"검색지수 출시 전 한 달 평균의 {fmt.times(r['last_x'])}"
                  + (f" · 긍정률 {fmt.pct(r['positive_7d'])}" if r.get("positive_7d") is not None else ""))
    if a:
        return card("reaction", "reaction", "신제품 반응", PILL[a["tone"]], a["title"],
                    [f"할 일: {a['action']}", status], ["reaction"])
    return card("reaction", "reaction", "신제품 반응", ("info", "안정"),
                "특이 신호 없음" if d >= LAUNCH.teaser else "출시 전 평소 수준", [status], ["reaction"])


def demand_card(d: dt.date, c: dict) -> dict:
    L, title = LAUNCH, "증산 · 재출시"
    r = c["reaction"]
    if d < L.launch:
        if d >= L.teaser and r.get("last_x"):
            return card("demand", "flavor", title, ("warn", "초도 물량 검토"),
                        f"티저 후 검색지수가 평소의 {fmt.times(r['last_x'])}",
                        ["판매 전이라 반응으로만 판단: 출시 첫 주 수요가 목표를 넘을 가능성",
                         f"목표: 원조 '{L.parent_flavor}' 일평균 {fmt.n(L.target_daily)}개 (가정)"], ["reaction"])
        return card("demand", "flavor", title, ("info", "출시 전"), "출시 전 반응 대기",
                    [f"출시 {fmt.md(L.launch)} · 티저 {fmt.md(L.teaser)}"], ["reaction"])
    if d == L.month_end:
        pos = r.get("positive_7d")
        ok = pos is not None and pos >= RULES.rerelease_positive and c["month_rank"] == 1
        return card("demand", "flavor", title, ("good", "재출시 후보") if ok else ("info", "재출시 보류"),
                    f"판매 기간 맛 순위 {c['month_rank']}위, 최근 7일 긍정률 {fmt.pct(pos)}" if pos is not None
                    else f"판매 기간 맛 순위 {c['month_rank']}위",
                    # 이달의 맛 판매 기간 = 출시일 ~ 월말 (2/24 출시 '3월 이달의 맛'이면 2/24~3/31)
                    [f"출시({fmt.md(L.launch)}) 후 누적 {fmt.n(c['cum'])}개, 목표보다 일평균 "
                     f"{fmt.pct(abs(c['month_avg'] / L.target_daily - 1))} {'많음' if c['month_avg'] >= L.target_daily else '적음'}",
                     f"긍정률 {int(RULES.rerelease_positive * 100)}% 이상 유지 → 재출시 후보로 등록" if ok
                     else "재출시 기준 미달 → 보류", "반응이 식는 속도를 다음 이달의 맛 물량 계획에 반영"],
                    ["sales", "reaction"])
    ratio = round(c["demand_ratio"], 2)
    pill = (("good", "증산 검토") if ratio >= RULES.demand_up else
            ("info", "유지") if ratio >= RULES.demand_hold else ("warn", "감산 검토"))
    first_week = (d - L.launch).days < 6
    anchor = next((f" · 공개 앵커 {(a - L.launch).days + 1}일 {v // 10_000:,}만 개와 일치"
                   for a, v in L.anchors if a == d), "")
    span = f"출시 후 {(d - L.launch).days + 1}일" if first_week else "최근 7일"
    items = [
        f"{span} 일평균 판매 {fmt.n(c['sales_avg'])}개 중 맛 수요 {fmt.n(c['demand_avg'])}개" if c["baseline_ready"]
        else f"{span} 일평균 판매 {fmt.n(c['sales_avg'])}개 (행사 없는 날이 아직 부족해 할인 효과 미분리)",
        f"목표: 원조 '{L.parent_flavor}' 일평균 {fmt.n(L.target_daily)}개 (가정)",
        f"누적 {fmt.n(c['cum'])}개{anchor}",
        f"원조 '{L.parent_flavor}' {c['cannib']}" if c.get("cannib") else None,
    ]
    if first_week:
        pill = (pill[0], pill[1] + " (잠정)")
    head = (f"할인 효과를 뺀 맛 수요가 목표의 {ratio:.2f}배" if c["baseline_ready"]
            else f"판매가 목표의 {ratio:.2f}배 (할인 효과 포함)")
    return card("demand", "flavor", title, pill, head, items, ["sales"])


def store_card(d: dt.date, c: dict) -> dict:
    """주간 판독: 이번 주(지난 판독 이후)에 뜬 매장 알림을 모아 판독 시점 상태와 같이 본다."""
    title = "매장 지원"
    st = c["stores"]
    if st is None:
        return card("store", "store", title, ("info", "첫 주 이후"), "출시 7일이 지나면 매장 순위 변화가 쌓임",
                    ["주변 언급↑ 판매↓ 매장 → 품절·운영 점검", "주변 언급↑ 판매↑ 매장 → 재고 선배치·콘텐츠 확산"],
                    ["sales", "reaction"])
    week = [a for a in c.get("week_alerts", []) if a["module"] == "store"]
    checks = [a for a in week if a["kind"] == "store_check"]
    virals = [a for a in week if a["kind"] == "store_viral"]

    def now(a: dict) -> str | None:
        r = st.get("watch", {}).get(a.get("ref"))
        return (f"판독 시점: 순위 {fmt.n(r['rank_prev'])}→{fmt.n(r['rank'])}위(7일 전 대비), 주변 언급 {r['sns']}건(7일)"
                if r else None)

    items = []
    if checks:
        a = checks[0]
        name = a["title"].split(": ", 1)[-1]
        pill = ("crit", "점검 우선")
        head = f"이번 주 점검 신호 {len(checks)}곳: {name}" if len(checks) > 1 else f"{name}: 반응↑ 판매↓"
        items += [f"{fmt.md(_d(a['date']))} 감지 · {a['detail']}", now(a),
                  "할 일: 재고·운영 확인 → 품절이면 공지·대체 맛 안내, 다음 맛 초도 배분에 반영"]
        if virals:
            items.append(f"바이럴 매장도 있음: {virals[0]['title'].split(': ', 1)[-1]}")
    elif virals:
        a = virals[0]
        name = a["title"].split(": ", 1)[-1]
        pill, head = ("good", "확산 지원"), f"{name}: 반응↑ 판매↑"
        items += [f"{fmt.md(_d(a['date']))} 감지 · {a['detail']}", now(a),
                  "할 일: 재고 선배치, 매장 언급 콘텐츠를 공식 채널에서 확산"]
    else:
        a = st["riser"]
        pill, head = ("info", "관찰"), "이번 주 반응과 연결된 매장 신호 없음"
        items.append(f"가장 많이 오른 매장: {a['name']} ({fmt.n(a['rank_prev'])}→{fmt.n(a['rank'])}위), "
                     + (a["why"] if a.get("why") else "주변 반응 변화 없음"))
    return card("store", "store", title, pill, head, items, ["sales", "reaction"])


def promo_card(d: dt.date, c: dict) -> dict:
    title = "판촉 조정"
    done = [p for p in c["promos"] if p["status"] == "done"]
    if not done:
        first = c["promos"][0] if c["promos"] else None
        overlap = first and _d(first["start"]) <= LAUNCH.launch <= _d(first["end"])
        pend = [p for p in c["promos"] if p["status"] in ("running", "pending")]
        head = (f"출시일({fmt.md(LAUNCH.launch)})이 {first['name']} 기간({fmt.md(_d(first['start']))}~"
                f"{fmt.md(_d(first['end']))})과 겹침" if overlap else "행사 판독 대기")
        items = ["출시 첫 주 판매에 맛 효과와 할인 효과가 섞임",
                 "행사 없는 날 판매로 기준선을 먼저 잡고 증분만 셈",
                 f"{pend[0]['name']}: {'진행 중' if pend[0]['status'] == 'running' else '종료, 기준선 데이터 쌓는 중'}"
                 if pend else None]
        return card("promo", "promo", title, ("warn", "효과 분리 필요"), head, items, ["sales"])
    p = done[-1]
    label = p["verdict_label"] + ("" if p["firm"] else " (잠정)")
    items = [
        f"할 일: {PROMO_ACTION[p['verdict']]}",
        f"행사 기간 판매 {fmt.n(p['act'])}개 중 행사 덕분 {fmt.n(p['inc'])}개 (범위 {fmt.n(p['inc_lo'])}~{fmt.n(p['inc_hi'])})",
        f"할인 비용 {fmt.million_won(p['cost_won'])} (가정)",
        None if p["firm"] else (f"행사 없는 날 {p['n_fit']}일로 기준선을 잡아 잠정" if p["tentative_reason"] == "few_days"
                                else f"ROI 범위 {p['roi_lo']:.2f}~{p['roi_hi']:.2f}가 판정 기준을 걸쳐 잠정"),
    ]
    return card("promo", "promo", title, (p["verdict"], label),
                f"{p['name']} 증분 {fmt.pct(p['inc_pct'])}, 증분 ROI {p['roi']:.2f}", items, ["sales", "cost"])


def decisions(d: dt.date, c: dict) -> list[dict]:
    """주간 판독의 결정 3축."""
    return [demand_card(d, c), store_card(d, c), promo_card(d, c)]
