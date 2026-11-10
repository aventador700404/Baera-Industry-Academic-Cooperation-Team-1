import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Day, Readout } from "../types";
import { makeCharts, type Charts } from "../charts";
import { md } from "../format";

const FOCUS_BEFORE_TEASER = 28; // 기본 화면: 예고 4주 전 ~ 월말 (출시 전후)

function shiftDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// 판매 · 광고 · SNS 반응을 같은 날짜 축에 (세 줄이 같은 x축을 공유).
// 수집 기간이 길면(예: 두쫀쿠 유행이 시작된 11월부터) 출시 전후가 화면 폭에 맞게 보이고, 그 앞은 옆으로 넘겨서 본다.
export function Timeline({ data, day, theme }: { data: Readout; day: Day; theme: number }) {
  const r = useRef<HTMLCanvasElement>(null), a = useRef<HTMLCanvasElement>(null), s = useRef<HTMLCanvasElement>(null);
  const charts = useRef<Charts | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const dayRef = useRef(day);
  dayRef.current = day;
  const [width, setWidth] = useState<number | null>(null);

  const dates = data.dates;
  const focusStart = shiftDays(data.meta.product.teaser, -FOCUS_BEFORE_TEASER);
  const focusIdx = Math.max(0, dates.findIndex((d) => d >= focusStart));
  const scrollable = focusIdx > 0;
  // 업계 키워드 정점이 기본 화면보다 앞이면 알려 준다
  const trendPeak = useMemo(() => {
    const t = data.series.trend;
    if (!t) return null;
    let best = -1;
    t.forEach((v, i) => { if (v != null && (best < 0 || v > (t[best] ?? -1))) best = i; });
    return best >= 0 && best < focusIdx ? dates[best] : null;
  }, [data, focusIdx, dates]);

  useLayoutEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const fit = () => {
      const cw = el.clientWidth;
      const total = scrollable ? Math.round((cw * dates.length) / (dates.length - focusIdx)) : cw;
      setWidth(total);
      requestAnimationFrame(() => { el.scrollLeft = el.scrollWidth; });   // 처음엔 출시 전후 (오른쪽 끝)
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [dates.length, focusIdx, scrollable]);

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
          {scrollable && <span className="note">← 옆으로 넘기면 {md(dates[0])}부터{trendPeak ? ` · 업계 키워드 정점 ${md(trendPeak)}` : ""}</span>}
          <span className="key"><span className="sw band" />행사 기간</span>
          <span className="key"><span className="sw dotk" />알림</span>
        </div>
      </div>
      <div className="tl-scroll" ref={scroller} tabIndex={scrollable ? 0 : -1} aria-label="타임라인 (옆으로 넘겨 이전 기간 보기)">
        <div className="tl-inner" style={{ width: width ?? "100%" }}>
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
        </div>
      </div>
    </section>
  );
}
