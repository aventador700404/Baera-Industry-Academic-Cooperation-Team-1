import { useEffect, useRef } from "react";
import type { Day, Readout } from "../types";
import { makeCharts, type Charts } from "../charts";

// 판매 · 광고 · SNS 반응을 같은 날짜 축에 (세 줄이 같은 x축을 공유)
export function Timeline({ data, day, theme }: { data: Readout; day: Day; theme: number }) {
  const r = useRef<HTMLCanvasElement>(null), a = useRef<HTMLCanvasElement>(null), s = useRef<HTMLCanvasElement>(null);
  const charts = useRef<Charts | null>(null);
  const dayRef = useRef(day);
  dayRef.current = day;

  useEffect(() => {
    if (!r.current || !a.current || !s.current) return;
    charts.current = makeCharts(r.current, a.current, s.current, data, () => dayRef.current);
    charts.current.update(dayRef.current);
    return () => charts.current?.destroy();
  }, [data, theme]);
  useEffect(() => { charts.current?.update(day); }, [day]);

  return (
    <section className="panel timeline" aria-labelledby="tl-h">
      <div className="panel-h">
        <h2 id="tl-h">통합 타임라인</h2>
        <div className="legend">
          <span className="key"><span className="sw band" />행사 기간</span>
          <span className="key"><span className="sw dotk" />알림</span>
        </div>
      </div>
      <div className="lane">
        <div className="lane-h">
          <b>SNS 반응</b>
          <span className="key"><span className="sw" style={{ background: "var(--s2)" }} />{data.meta.keyword_labels.bra}</span>
          <span className="key"><span className="sw dash" style={{ color: "var(--trend)" }} />{data.meta.keyword_labels.trend}</span>
          <span className="note">네이버 검색지수 0~100</span>
        </div>
        <div className="chartbox r"><canvas ref={r} role="img" aria-label="일별 검색지수와 알림" /></div>
      </div>
      <div className="lane">
        <div className="lane-h">
          <b>광고</b>
          <span className="key"><span className="sw bar" style={{ background: "var(--s3)" }} />일별 노출 (캠페인·클릭·비용은 마우스를 올리면)</span>
        </div>
        <div className="chartbox a"><canvas ref={a} role="img" aria-label="일별 광고 노출" /></div>
      </div>
      <div className="lane">
        <div className="lane-h">
          <b>판매</b>
          <span className="key"><span className="sw bar" style={{ background: "var(--s1)" }} />일별 판매 (개)</span>
          <span className="key"><span className="sw dash" style={{ color: "var(--muted)" }} />행사가 없었을 때 (추정)</span>
          <span className="key"><span className="sw range" />추정 범위</span>
        </div>
        <div className="chartbox s"><canvas ref={s} role="img" aria-label="일별 판매와 기준선" /></div>
      </div>
    </section>
  );
}
