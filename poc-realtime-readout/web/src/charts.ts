import {
  BarController, BarElement, CategoryScale, Chart, Filler, LinearScale, LineController, LineElement,
  PointElement, Tooltip, type ChartConfiguration, type ChartOptions, type Plugin,
} from "chart.js";
import type { Day, Readout } from "./types";
import { fmt, man, md } from "./format";

// 막대+선 혼합 차트라 타입을 느슨하게 하나로 묶는다
type Series = (number | null)[];
type Loose = Chart<"bar" | "line", Series, string>;
const make = (el: HTMLCanvasElement, cfg: object) =>
  new Chart(el, cfg as ChartConfiguration<"bar" | "line", Series, string>) as Loose;

Chart.register(BarController, BarElement, CategoryScale, Filler, LinearScale, LineController, LineElement, PointElement, Tooltip);

const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const alpha = (hex: string, a: number) => {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};
const Y_WIDTH = 46; // 세 차트의 y축 폭을 맞춰 날짜 축을 정확히 정렬

interface Role { top: boolean; bottom: boolean }

// 행사 기간 음영, 티저·출시 표시선, 기준일 이후 흐리게, (맨 위 차트) 알림 점
function overlay(data: Readout, dates: string[], getDay: () => Day, role: Role): Plugin<"bar" | "line"> {
  // 보이는 기간 밖에서 시작·끝나는 행사는 기간 끝에 맞춰 자른다
  const clampIdx = (d: string, side: "start" | "end") => {
    const i = dates.indexOf(d);
    if (i >= 0) return i;
    if (side === "start" && d < dates[0]) return 0;
    if (side === "end" && d > dates[dates.length - 1]) return dates.length - 1;
    return -1;
  };
  const half = (chart: Chart) => (chart.scales.x.getPixelForValue(1) - chart.scales.x.getPixelForValue(0)) / 2;
  return {
    id: "overlay",
    beforeDatasetsDraw(chart) {
      const { ctx, chartArea: a, scales: { x } } = chart;
      if (!a) return;
      ctx.save();
      const h = half(chart);
      let labelEnd = -Infinity;
      for (const p of [...data.promos].sort((u, v) => (u.start < v.start ? -1 : 1))) {
        if (p.end < dates[0] || p.start > dates[dates.length - 1]) continue;
        const i0 = clampIdx(p.start, "start"), i1 = clampIdx(p.end, "end");
        if (i0 < 0 || i1 < 0) continue;
        ctx.fillStyle = css("--band");
        ctx.fillRect(x.getPixelForValue(i0) - h, a.top, x.getPixelForValue(i1) - x.getPixelForValue(i0) + 2 * h, a.bottom - a.top);
        if (role.top) {
          // 이름은 그래프 안쪽에 들어오게: 기간 앞이 잘렸으면 왼쪽 끝, 오른쪽 끝에 걸리면 안쪽으로 당긴다
          ctx.fillStyle = css("--band-ink"); ctx.font = `600 10px ${css("--font")}`; ctx.textAlign = "left";
          // 좁은 화면에서 앞 행사 이름과 겹치면 생략 (마우스를 올리면 툴팁에 행사명이 나온다)
          const w = ctx.measureText(p.name).width;
          const tx = Math.max(a.left + 2, Math.min(x.getPixelForValue(i0) - h + 3, a.right - w - 2));
          if (tx >= labelEnd + 6) { ctx.fillText(p.name, tx, a.bottom - 4); labelEnd = tx + w; }
        }
      }
      data.markers.forEach((m, k) => {
        const i = dates.indexOf(m.date);
        if (i < 0) return;
        const px = x.getPixelForValue(i);
        ctx.strokeStyle = css("--muted"); ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke(); ctx.setLineDash([]);
        if (role.top) {
          // 예고(2/23)와 출시(2/24)처럼 붙어 있으면 첫 표시는 선 왼쪽, 다음 표시는 선 오른쪽에
          const left = k === 0;
          ctx.fillStyle = css("--ink-2"); ctx.font = `11px ${css("--font")}`; ctx.textAlign = left ? "right" : "left";
          ctx.fillText(m.label, px + (left ? -4 : 4), a.top + 11);
        }
      });
      ctx.restore();
    },
    afterDatasetsDraw(chart) {
      const { ctx, chartArea: a, scales: { x } } = chart;
      const v = getDay();
      const i = dates.indexOf(v.date);
      if (!a || i < 0) return;
      const px = x.getPixelForValue(i) + half(chart);
      ctx.save();
      if (role.top) {
        const tone: Record<string, string> = { crit: css("--crit"), warn: css("--warn"), good: css("--good"), info: css("--s1") };
        const stack: Record<string, number> = {};
        for (const al of data.alerts) {
          if (al.date > v.date) continue;
          const j = dates.indexOf(al.date);
          if (j < 0) continue;
          const k = (stack[al.date] = (stack[al.date] ?? 0) + 1);
          ctx.fillStyle = tone[al.tone];
          ctx.beginPath(); ctx.arc(x.getPixelForValue(j) + (k - 1) * 7, a.top - 9, 3.5, 0, Math.PI * 2); ctx.fill();
        }
      }
      ctx.fillStyle = css("--dim"); ctx.fillRect(px, a.top, a.right - px, a.bottom - a.top);
      ctx.strokeStyle = css("--s1"); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      if (role.bottom) {
        const right = px > a.right - 70;
        const txt = `기준일 ${md(v.date)}`;
        ctx.font = `600 11px ${css("--font")}`; ctx.textAlign = right ? "right" : "left";
        const w = ctx.measureText(txt).width, tx = px + (right ? -6 : 6);
        ctx.fillStyle = css("--surface"); ctx.fillRect(right ? tx - w - 3 : tx - 3, a.bottom - 19, w + 6, 16);
        ctx.fillStyle = css("--s1"); ctx.fillText(txt, tx, a.bottom - 6);
      }
      ctx.restore();
    },
  };
}

function options(data: Readout, dates: string[], fmtY: (v: number) => string, role: Role,
                 tip: (i: number) => string[] = () => [], label?: (it: { dataset: { label?: string }; raw: unknown; dataIndex: number }) => string):
  ChartOptions<"bar" | "line"> {
  const line = css("--line"), ink2 = css("--ink-2"), font = css("--font");
  // 보이는 날짜 수에 따라 눈금 간격: 두 달 남짓이면 매주, 길면 매달 1일
  const tickRe = dates.length > 100 ? /-01$/ : dates.length > 45 ? /-(01|15)$/ : /-(01|08|15|22)$/;
  const promoOf = (d: string) => data.promos.find((p) => d >= p.start && d <= p.end);
  return {
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: "index", intersect: false },
    layout: { padding: { top: role.top ? 18 : 4 } },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: ink2, borderColor: line, borderWidth: 1,
        padding: 10, titleFont: { family: font, weight: 600 }, bodyFont: { family: font },
        filter: (it) => it.raw != null && !(it.dataset as { hideInTooltip?: boolean }).hideInTooltip,
        callbacks: {
          title: (it) => { const d = dates[it[0].dataIndex]; const p = promoOf(d); return md(d) + (p ? ` · ${p.name}` : ""); },
          label: (it) => label ? label(it) : ` ${it.dataset.label}: ${fmtY(it.raw as number)}`,
          afterBody: (it) => tip(it[0].dataIndex),
        },
      },
    },
    scales: {
      x: {
        // 막대(광고·판매)와 선(SNS)이 같은 자리에 오도록 세 차트 모두 칸 가운데에 점을 찍는다
        offset: true, grid: { display: false }, border: { color: line },
        ticks: {
          display: role.bottom, color: ink2, font: { family: font, size: 11 }, autoSkip: false, maxRotation: 0,
          callback: (_v, idx) => { const d = dates[idx]; return d && tickRe.test(d) ? md(d) : ""; },
        },
      },
      // 타임라인을 옆으로 넘길 때 기본 화면(오른쪽 끝 = 출시 전후)에서 눈금이 보이게 오른쪽에 둔다
      y: {
        position: "right", beginAtZero: true, grid: { color: line, lineWidth: 1 }, border: { display: false },
        afterFit: (scale) => { scale.width = Y_WIDTH; },
        ticks: { color: ink2, font: { family: font, size: 10 }, maxTicksLimit: 4, callback: (v) => fmtY(Number(v)) },
      },
    },
  };
}

export interface Charts { update: (v: Day) => void; destroy: () => void }

// 검색지수 한 줄의 기간 안(그 날까지) 정점. 화면 옆에 원래 지수와 날짜를 같이 보여 준다
export interface Peak { date: string; raw: number }
export function peakOf(series: (number | null)[] | null, dates: string[], from: number, to: number, upto: string): Peak | null {
  if (!series) return null;
  let best = -1;
  for (let i = from; i <= to; i++) {
    const v = series[i];
    if (v == null || dates[i] > upto) continue;
    if (best < 0 || v > (series[best] as number)) best = i;
  }
  return best >= 0 && (series[best] as number) > 0 ? { date: dates[best], raw: series[best] as number } : null;
}

// 같은 날짜 축의 세 줄: SNS 반응 / 광고 / 판매. range = 보이는 기간 [시작, 끝] (data.dates 인덱스)
export function makeCharts(cr: HTMLCanvasElement, ca: HTMLCanvasElement, cs: HTMLCanvasElement,
                           data: Readout, getDay: () => Day, range: [number, number]): Charts {
  const s1 = css("--s1"), s2 = css("--s2"), s3 = css("--s3"), trend = css("--trend"), muted = css("--muted");
  const [r0, r1] = range;
  const dates = data.dates.slice(r0, r1 + 1);
  const cut = <T,>(arr: T[] | null | undefined) => (arr ?? []).slice(r0, r1 + 1);
  const S = data.series;
  const raw = { bra: cut(S.bra), trend: cut(S.trend) };

  // 검색지수: 두 줄을 각각 '보이는 기간 안, 그 날까지의 최고치 = 100'으로 맞춘다 (원래 지수는 툴팁에)
  const reactionLabel = (it: { dataset: { label?: string }; raw: unknown; dataIndex: number }) => {
    const r = (it.dataset.label === data.meta.keyword_labels.bra ? raw.bra : raw.trend)[it.dataIndex];
    return ` ${it.dataset.label}: ${Math.round(it.raw as number)} (원래 지수 ${r == null ? "-" : r < 10 ? r.toFixed(1) : Math.round(r)})`;
  };
  const reaction = make(cr, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        { label: data.meta.keyword_labels.bra, data: [], borderColor: s2, backgroundColor: s2, borderWidth: 2.2, pointRadius: 0, pointHoverRadius: 4, tension: 0.25 },
        { label: data.meta.keyword_labels.trend, data: [], borderColor: trend, backgroundColor: trend, borderWidth: 1.6, borderDash: [4, 3], pointRadius: 0, pointHoverRadius: 3, tension: 0.25 },
      ],
    },
    options: options(data, dates, (v) => String(Math.round(v)), { top: true, bottom: false }, () => [], reactionLabel),
    plugins: [overlay(data, dates, getDay, { top: true, bottom: false })],
  });

  const adImp = cut(S.ad_impressions), adSpend = cut(S.ad_spend), adClicks = cut(S.ad_clicks), adCamp = cut(S.ad_campaign);
  const adTip = (i: number) => {
    const c = adCamp[i], sp = adSpend[i], ck = adClicks[i], im = adImp[i];
    return c ? [` 캠페인: ${c}`, ` 클릭: ${fmt(ck ?? 0)} (${im ? ((100 * (ck ?? 0)) / im).toFixed(2) : "-"}%)`, ` 비용: ${fmt((sp ?? 0) / 10000)}만 원`] : [];
  };
  const ads = make(ca, {
    type: "bar",
    data: { labels: dates, datasets: [
      { label: "광고 노출", data: [], backgroundColor: s3, borderRadius: { topLeft: 2, topRight: 2 }, borderSkipped: "bottom", categoryPercentage: 0.9, barPercentage: 0.85 },
    ] },
    options: options(data, dates, man, { top: false, bottom: false }, adTip),
    plugins: [overlay(data, dates, getDay, { top: false, bottom: false })],
  });

  const sales = make(cs, {
    type: "bar",
    data: {
      labels: dates,
      datasets: [
        { type: "bar", label: "판매", data: [], backgroundColor: s1, borderRadius: { topLeft: 3, topRight: 3 }, borderSkipped: "bottom", categoryPercentage: 0.9, barPercentage: 0.85, order: 3 },
        { type: "line", label: "기준선 하한", data: [], borderWidth: 0, pointRadius: 0, fill: false, order: 2, hideInTooltip: true },
        { type: "line", label: "기준선 범위", data: [], borderWidth: 0, pointRadius: 0, backgroundColor: alpha(muted, 0.22), fill: "-1", order: 2, hideInTooltip: true },
        { type: "line", label: "행사 없었을 때 (추정)", data: [], borderColor: muted, borderDash: [5, 4], borderWidth: 2, pointRadius: 0, pointHoverRadius: 3, tension: 0.2, order: 1 },
      ],
    },
    options: options(data, dates, man, { top: false, bottom: true }),
    plugins: [overlay(data, dates, getDay, { top: false, bottom: true })],
  });

  const onAxis = (arr: number[] | undefined, v: Day) =>
    dates.map((d) => {
      const i = data.launch_dates.indexOf(d);
      return arr && i >= 0 && d <= v.date ? arr[i] : null;
    });
  const upto = (arr: (number | null)[], v: Day) => arr.map((x, i) => (dates[i] <= v.date ? x : null));
  const scaled = (arr: (number | null)[], v: Day) => {
    const shown = upto(arr, v);
    const mx = Math.max(0, ...shown.filter((x): x is number => x != null));
    return shown.map((x) => (x == null || mx <= 0 ? x : (100 * x) / mx));
  };

  const update = (v: Day) => {
    reaction.data.datasets[0].data = scaled(raw.bra, v);
    reaction.data.datasets[1].data = scaled(raw.trend, v);
    ads.data.datasets[0].data = upto(adImp, v);
    sales.data.datasets[0].data = upto(cut(S.sales), v);
    sales.data.datasets[1].data = onAxis(v.baseline?.lo, v);
    sales.data.datasets[2].data = onAxis(v.baseline?.hi, v);
    sales.data.datasets[3].data = onAxis(v.baseline?.base, v);
    for (const c of [reaction, ads, sales]) c.update("none");
  };
  return { update, destroy: () => { reaction.destroy(); ads.destroy(); sales.destroy(); } };
}
