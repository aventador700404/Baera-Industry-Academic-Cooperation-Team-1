import { useEffect, useRef } from "react";
import type { Readout, View } from "../types";
import { makeCharts, type ChartPair } from "../charts";
import { fmt, md } from "../format";
import { Prov } from "./bits";

export function ReactionSales({ data, view, theme }: { data: Readout; view: View; theme: number }) {
  const r = useRef<HTMLCanvasElement>(null), s = useRef<HTMLCanvasElement>(null);
  const charts = useRef<ChartPair | null>(null);
  const viewRef = useRef(view);
  viewRef.current = view;

  useEffect(() => {
    if (!r.current || !s.current) return;
    charts.current = makeCharts(r.current, s.current, data, () => viewRef.current);
    charts.current.update(viewRef.current);
    return () => charts.current?.destroy();
  }, [data, theme]);

  useEffect(() => { charts.current?.update(view); }, [view]);

  const p = data.meta.provenance_raw;
  const bl = view.baseline;
  return (
    <section className="panel" aria-labelledby="m1">
      <div className="panel-h">
        <div>
          <h2 id="m1">신제품 반응과 판매</h2>
          <div className="q">같은 날짜 축에서 반응이 판매보다 먼저 움직이는지, 판매 중 할인 덕분은 얼마인지</div>
        </div>
        <div className="tags"><Prov p={p.reaction_daily} what="반응" /><Prov p={p.sales_daily} what="판매" /></div>
      </div>
      <div className="kpis">
        {view.kpis.map((k) => (
          <div className="kpi" key={k.k}><div className="k">{k.k}</div><div className="v">{k.v}</div><div className="d">{k.d}</div></div>
        ))}
      </div>
      <div className="chartlabel">
        <span className="key"><span className="sw" style={{ background: "var(--s1)" }} />{data.meta.keyword_labels.bra}</span>
        <span className="key"><span className="sw" style={{ background: "var(--s2)" }} />{data.meta.keyword_labels.trend}</span>
        <span className="key"><span className="sw band" />행사 기간</span>
        <span className="note">네이버 데이터랩 상대지수 (0~100)</span>
      </div>
      <div className="chartbox"><canvas ref={r} aria-label="일별 검색지수 추이" role="img" /></div>
      <div className="chartlabel">
        <span className="key"><span className="sw bar" style={{ background: "var(--s1)" }} />일별 판매 (개)</span>
        <span className="key"><span className="sw dash" />행사가 없었을 때 기준선 (추정)</span>
        <span className="key"><span className="sw range" />기준선 범위</span>
        <span className="key"><span className="sw band" />행사 기간</span>
      </div>
      <div className="chartbox"><canvas ref={s} aria-label="일별 판매와 기준선" role="img" /></div>
      {bl && (
        <p className="note">
          기준선은 이 판독 시점까지의 행사 없는 날 {bl.n_fit}일과 기존 맛의 요일 패턴으로 다시 추정합니다.
          판독 주가 바뀌면 기준선도 바뀝니다.
        </p>
      )}
      {view.youtube && (
        <div className="yt">
          <div className="note">유튜브 영상 조회수 ({md(view.youtube.asof)} 기준 원값 · API 정책상 파생 지표는 만들지 않음) <Prov p={p.youtube_videos_daily} what="유튜브" /></div>
          {view.youtube.videos.map((y) => (
            <div className="row" key={y.title}>
              <span><span className={`chip ${y.channel_type === "official" ? "" : "new"}`}>{y.channel_type === "official" ? "공식" : "소비자"}</span> {y.title}</span>
              <span>{fmt(y.views)}회</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
