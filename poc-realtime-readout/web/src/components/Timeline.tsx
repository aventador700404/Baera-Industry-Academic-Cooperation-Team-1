import { useEffect, useMemo, useRef, useState } from "react";
import type { Day, Readout } from "../types";
import { makeCharts, peakOf, type Charts } from "../charts";
import { md } from "../format";

function shiftDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
const idxOnOrAfter = (dates: string[], d: string) => {
  const i = dates.findIndex((x) => x >= d);
  return i < 0 ? dates.length - 1 : i;
};
const idxOnOrBefore = (dates: string[], d: string) => {
  let i = dates.length - 1;
  while (i > 0 && dates[i] > d) i--;
  return i;
};
const rawIdx = (v: number) => (v < 10 ? v.toFixed(1) : String(Math.round(v)));

// 판매 · 광고 · SNS 반응을 같은 날짜 축에 (세 줄이 같은 x축을 공유).
// 보이는 기간을 고를 수 있고, 검색지수는 그 기간 안(그 날까지)의 최고치를 100으로 다시 맞춘다.
// 업계 키워드처럼 크기가 다른 줄이 있어도 신제품 줄이 바닥에 깔리지 않게. 원래 지수와 정점 날짜는 옆에 따로 보여 준다.
export function Timeline({ data, day, theme }: { data: Readout; day: Day; theme: number }) {
  const r = useRef<HTMLCanvasElement>(null), a = useRef<HTMLCanvasElement>(null), s = useRef<HTMLCanvasElement>(null);
  const charts = useRef<Charts | null>(null);
  const dayRef = useRef(day);
  dayRef.current = day;

  const dates = data.dates;
  const last = dates.length - 1;
  const { teaser, launch } = data.meta.product;
  const presets = useMemo(() => [
    { key: "around", label: "출시 전후", range: [idxOnOrAfter(dates, shiftDays(teaser, -28)), last] as [number, number] },
    { key: "after", label: "출시 후", range: [idxOnOrAfter(dates, shiftDays(launch, -3)), last] as [number, number] },
    { key: "all", label: "전체 수집 기간", range: [0, last] as [number, number] },
  ].filter((p, i, arr) => arr.findIndex((q) => q.range[0] === p.range[0] && q.range[1] === p.range[1]) === i),  // 같은 기간이면 하나만
  [dates, teaser, launch, last]);
  const [range, setRange] = useState<[number, number]>(presets[0].range);
  const [r0, r1] = range;

  useEffect(() => {
    if (!r.current || !a.current || !s.current) return;
    charts.current = makeCharts(r.current, a.current, s.current, data, () => dayRef.current, range);
    charts.current.update(dayRef.current);
    return () => charts.current?.destroy();
  }, [data, theme, range]);
  useEffect(() => { charts.current?.update(day); }, [day]);

  const bra = peakOf(data.series.bra, dates, r0, r1, day.date);
  const trend = peakOf(data.series.trend, dates, r0, r1, day.date);
  const trendAll = peakOf(data.series.trend, dates, 0, last, day.date);
  const setFrom = (d: string) => { if (d) setRange([Math.min(idxOnOrAfter(dates, d), r1 - 6), r1]); };
  const setTo = (d: string) => { if (d) setRange([r0, Math.max(idxOnOrBefore(dates, d), r0 + 6)]); };

  return (
    <section className="panel timeline" aria-labelledby="tl-h">
      <div className="panel-h">
        <h2 id="tl-h">통합 타임라인</h2>
        <div className="legend">
          <span className="key"><span className="sw band" />행사 기간</span>
          <span className="key"><span className="sw dotk" />알림</span>
        </div>
      </div>
      <div className="tl-range" role="group" aria-label="보이는 기간">
        {presets.map((p) => (
          <button type="button" key={p.key} className={p.range[0] === r0 && p.range[1] === r1 ? "on" : ""}
                  onClick={() => setRange(p.range)}>{p.label}</button>
        ))}
        <label>
          <input type="date" value={dates[r0]} min={dates[0]} max={dates[r1]} onChange={(e) => setFrom(e.target.value)} aria-label="시작일" />
        </label>
        <span className="note">~</span>
        <label>
          <input type="date" value={dates[r1]} min={dates[r0]} max={dates[last]} onChange={(e) => setTo(e.target.value)} aria-label="끝일" />
        </label>
      </div>
      <div className="lane">
        <div className="lane-h">
          <b>SNS 반응</b>
          <span className="key"><span className="sw" style={{ background: "var(--s2)" }} />{data.meta.keyword_labels.bra}
            {bra && <span className="peak">정점 {md(bra.date)} · 원래 지수 {rawIdx(bra.raw)}</span>}</span>
          <span className="key"><span className="sw dash" style={{ color: "var(--trend)" }} />{data.meta.keyword_labels.trend}
            {trend && <span className="peak">정점 {md(trend.date)} · 원래 지수 {rawIdx(trend.raw)}
              {trendAll && trendAll.date !== trend.date ? ` (전체 기간 정점 ${md(trendAll.date)})` : ""}</span>}</span>
          <span className="note">네이버 검색지수 · 각 줄을 보이는 기간의 최고치 = 100으로</span>
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
