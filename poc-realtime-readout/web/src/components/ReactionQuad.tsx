import type { Day } from "../types";
import { fmt, md, pct } from "../format";
import { Verdict } from "./bits";

// 신제품 반응: 무엇을 말하나(주제·긍부정) + 어떤 콘텐츠가 끌었나 + 판매로 이어지나
export function ReactionQuad({ day }: { day: Day }) {
  const tp = day.topics;
  const max = tp ? Math.max(...tp.rows.map((x) => x.mentions), 1) : 1;
  return (
    <section className="panel quad" aria-labelledby="q1">
      <div className="panel-h"><h2 id="q1">신제품 반응</h2><span className="note">매일</span></div>
      <Verdict c={day.reaction_status} />
      <h3 className="h3">무엇을 말하나 <span className="note">최근 3일 블로그 주제별 언급 · 초록 긍정 · 빨강 부정 · 회색 판단 안 됨 · % = 판단된 글 중 긍정</span></h3>
      {!tp ? <div className="empty">주제 데이터 없음</div> : (
        <div className="topics">
          {tp.rows.map((t) => (
            <div className="trow" key={t.topic}>
              <span className="tname">{t.topic}</span>
              <div className="tbar" style={{ width: `${(t.mentions / max) * 100}%` }}
                title={`긍정 ${t.positive} · 부정 ${t.negative} · 판단 안 됨 ${t.mentions - t.positive - t.negative}`}>
                <div className="tpos" style={{ width: `${t.mentions ? (t.positive / t.mentions) * 100 : 0}%` }} />
                <div className="tneg" style={{ width: `${t.mentions ? (t.negative / t.mentions) * 100 : 0}%` }} />
              </div>
              <span className="tval">
                {fmt(t.mentions)} · {t.pos != null ? pct(t.pos) : "-"}
                {t.surge && <span className="chip crit">급증</span>}
                {t.neg_up && <span className="chip warn">부정↑</span>}
              </span>
            </div>
          ))}
        </div>
      )}
      <h3 className="h3">어떤 콘텐츠가 끌었나 <span className="note">유튜브 조회수{day.youtube && day.youtube.asof > day.date ? ` · ${md(day.youtube.asof)} 수집 기준` : ""}</span></h3>
      {!day.youtube ? <div className="empty">티저 공개 전</div> : (
        <div className="yt">
          {day.youtube.videos.slice(0, 3).map((y) => (
            <div className="row" key={y.title}>
              <span><span className={`chip ${y.channel_type === "official" ? "blue" : "pink"}`}>{y.channel_type === "official" ? "공식" : "소비자"}</span> {y.title.replace(/^(공식|소비자 쇼츠|먹방) · /, "")}</span>
              <span>{fmt(y.views)}회</span>
            </div>
          ))}
        </div>
      )}
      {day.conversion && (
        <div className="conv">
          <h3 className="h3">판매로 이어지나 <span className="note">출시 첫 주 = 100, 최근 7일</span></h3>
          <div className="convrow"><span>판매</span><div className="cbar" style={{ width: `${Math.min(day.conversion.sales_idx, 120) / 1.2}%`, background: "var(--s1)" }} /><b>{day.conversion.sales_idx.toFixed(0)}</b></div>
          <div className="convrow"><span>검색</span><div className="cbar" style={{ width: `${Math.min(day.conversion.search_idx, 120) / 1.2}%`, background: "var(--s2)" }} /><b>{day.conversion.search_idx.toFixed(0)}</b></div>
        </div>
      )}
    </section>
  );
}
