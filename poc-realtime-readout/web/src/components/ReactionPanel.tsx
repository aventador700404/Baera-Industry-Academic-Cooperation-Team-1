import { useEffect, useRef } from "react";
import type { Day, Readout } from "../types";
import { makeCharts, type ChartPair } from "../charts";
import { fmt, md, pct, period } from "../format";
import { Prov } from "./bits";

// 모듈 1 · 신제품 반응 (Q1 즉시 반응 + Q3 SNS·인플루언서 반응)
export function ReactionPanel({ data, day, theme }: { data: Readout; day: Day; theme: number }) {
  const r = useRef<HTMLCanvasElement>(null), s = useRef<HTMLCanvasElement>(null);
  const charts = useRef<ChartPair | null>(null);
  const dayRef = useRef(day);
  dayRef.current = day;

  useEffect(() => {
    if (!r.current || !s.current) return;
    charts.current = makeCharts(r.current, s.current, data, () => dayRef.current);
    charts.current.update(dayRef.current);
    return () => charts.current?.destroy();
  }, [data, theme]);

  useEffect(() => { charts.current?.update(day); }, [day]);

  const p = data.meta.provenance_raw;
  const tp = day.topics;
  const maxTopic = tp ? Math.max(...tp.rows.map((x) => x.mentions), 1) : 1;
  return (
    <section className="panel" aria-labelledby="m1">
      <div className="panel-h">
        <div>
          <div className="eyebrow">모듈 1</div>
          <h2 id="m1">신제품 반응</h2>
          <div className="q">검색·언급이 얼마나 튀었나, 사람들이 무엇을 말하나, 어떤 콘텐츠가 끌었나, 판매로 이어지나</div>
        </div>
        <div className="tags"><Prov p={p.reaction_daily} what="검색·언급" /><Prov p={p.reaction_topics_daily} what="주제" /><Prov p={p.sales_daily} what="판매" /></div>
      </div>
      <div className="kpis">
        {day.kpis.map((k) => (
          <div className="kpi" key={k.k}><div className="k">{k.k}</div><div className="v">{k.v}</div><div className="d">{k.d}</div></div>
        ))}
      </div>
      <div className="chartlabel">
        <span className="key"><span className="sw" style={{ background: "var(--s1)" }} />{data.meta.keyword_labels.bra}</span>
        <span className="key"><span className="sw" style={{ background: "var(--s2)" }} />{data.meta.keyword_labels.trend}</span>
        <span className="key"><span className="sw band" />행사 기간</span>
        <span className="key"><span className="sw dotk" />알림</span>
        <span className="note">네이버 데이터랩 상대지수 (0~100)</span>
      </div>
      <div className="chartbox"><canvas ref={r} aria-label="일별 검색지수와 알림" role="img" /></div>
      <div className="chartlabel">
        <span className="key"><span className="sw bar" style={{ background: "var(--s1)" }} />일별 판매 (개)</span>
        <span className="key"><span className="sw dash" />행사가 없었을 때 기준선 (추정)</span>
        <span className="key"><span className="sw range" />기준선 범위</span>
      </div>
      <div className="chartbox"><canvas ref={s} aria-label="일별 판매와 기준선" role="img" /></div>
      {day.baseline && (
        <p className="note">기준선은 이 날까지의 행사 없는 날 {day.baseline.n_fit}일과 기존 맛의 요일 패턴으로 매일 다시 추정합니다.</p>
      )}

      <div className="grid2 sub">
        <div>
          <h3 className="h3">무엇을 말하나 <span className="note">{tp ? `최근 3일 ${period(tp.window.start, tp.window.end)} · 블로그·카페 요약문 주제 분류` : ""}</span></h3>
          {!tp ? <div className="empty">주제 데이터 없음</div> : (
            <div className="topics">
              {tp.rows.map((t) => {
                return (
                  <div className="trow" key={t.topic}>
                    <span className="tname">{t.topic}</span>
                    <div className="tbar" style={{ width: `${(t.mentions / maxTopic) * 100}%` }} title={`긍정 ${t.positive} · 부정 ${t.negative}`}>
                      <div className="tpos" style={{ width: `${t.mentions ? (t.positive / t.mentions) * 100 : 0}%` }} />
                    </div>
                    <span className="tval">
                      {fmt(t.mentions)}건 · 긍정 {t.pos != null ? pct(t.pos) : "-"}
                      {t.surge && <span className="chip crit">급증</span>}
                      {t.neg_up && <span className="chip warn">부정↑</span>}
                    </span>
                  </div>
                );
              })}
              <div className="note"><span className="sw bar" style={{ background: "var(--good)" }} /> 긍정 비중 · 나머지 부정. 급증 = 비중이 그 전 14일의 2배 이상</div>
            </div>
          )}
        </div>
        <div>
          <h3 className="h3">어떤 콘텐츠가 끌었나 <span className="note">유튜브 조회수 원값 · {day.youtube ? `${md(day.youtube.asof)} 기준` : ""}</span></h3>
          {!day.youtube ? <div className="empty">티저 공개 전</div> : (
            <div className="yt">
              {day.youtube.videos.map((y) => (
                <div className="row" key={y.title}>
                  <span><span className={`chip ${y.channel_type === "official" ? "" : "new"}`}>{y.channel_type === "official" ? "공식" : "소비자"}</span> {y.title}</span>
                  <span>{fmt(y.views)}회</span>
                </div>
              ))}
              <div className="note">API 정책상 조회수로 합계·비율 같은 새 지표를 만들지 않고 원값만 보여줍니다. <Prov p={p.youtube_videos_daily} what="유튜브" /></div>
            </div>
          )}
          {day.conversion && (
            <div className="conv">
              <h3 className="h3">판매로 이어지나 <span className="note">출시 첫 주 = 100, 최근 7일 평균</span></h3>
              <div className="convrow"><span>판매 지수</span><div className="cbar" style={{ width: `${Math.min(day.conversion.sales_idx, 120) / 1.2}%`, background: "var(--s1)" }} /><b>{day.conversion.sales_idx.toFixed(0)}</b></div>
              <div className="convrow"><span>검색 지수</span><div className="cbar" style={{ width: `${Math.min(day.conversion.search_idx, 120) / 1.2}%`, background: "var(--s2)" }} /><b>{day.conversion.search_idx.toFixed(0)}</b></div>
              <div className="note">
                {day.conversion.ratio >= 1.2 ? "관심이 식는 속도보다 판매가 덜 빠짐 → 화제성보다 맛 수요가 판매를 끎"
                  : day.conversion.ratio <= 0.8 ? "관심은 남았는데 판매가 빠짐 → 품절·가격·접근성 점검"
                  : "관심과 판매가 비슷하게 움직임"}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
