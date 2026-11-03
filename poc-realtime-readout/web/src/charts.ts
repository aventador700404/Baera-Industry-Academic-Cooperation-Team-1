import {
  BarController, BarElement, CategoryScale, Chart, Filler, LinearScale, LineController, LineElement,
  PointElement, Tooltip, type ChartConfiguration, type ChartOptions, type Plugin,
} from "chart.js";
import type { Readout, View } from "./types";
import { man, md } from "./format";

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

// 행사 기간 음영, 티저·출시 표시선, 판독 시점 이후 흐리게
function bandsPlugin(data: Readout, getView: () => View, labels: boolean): Plugin<"bar" | "line"> {
  const dates = data.dates;
  const half = (chart: Chart) => {
    const x = chart.scales.x;
    return (x.getPixelForValue(1) - x.getPixelForValue(0)) / 2;
  };
  return {
    id: "bands",
    beforeDatasetsDraw(chart) {
      const { ctx, chartArea: a, scales: { x } } = chart;
      if (!a) return;
      ctx.save();
      const h = half(chart);
      for (const p of data.promos) {
        const i0 = dates.indexOf(p.start), i1 = dates.indexOf(p.end);
        if (i0 < 0) continue;
        ctx.fillStyle = css("--band");
        ctx.fillRect(x.getPixelForValue(i0) - h, a.top, x.getPixelForValue(i1) - x.getPixelForValue(i0) + 2 * h, a.bottom - a.top);
      }
      for (const m of data.markers) {
        const i = dates.indexOf(m.date);
        if (i < 0) continue;
        const px = x.getPixelForValue(i);
        ctx.strokeStyle = css("--muted"); ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke(); ctx.setLineDash([]);
        if (labels) {
          ctx.fillStyle = css("--ink-2"); ctx.font = `11px ${css("--font")}`; ctx.textAlign = "left";
          ctx.fillText(m.label, px + 4, a.top + 11);
        }
      }
      ctx.restore();
    },
    afterDatasetsDraw(chart) {
      const { ctx, chartArea: a, scales: { x } } = chart;
      const v = getView();
      const i = dates.indexOf(v.to);
      if (!a || i < 0) return;
      const px = x.getPixelForValue(i) + half(chart);
      ctx.save();
      ctx.fillStyle = css("--dim"); ctx.fillRect(px, a.top, a.right - px, a.bottom - a.top);
      ctx.strokeStyle = css("--s1"); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      const right = px > a.right - 80;
      ctx.fillStyle = css("--s1"); ctx.font = `600 11px ${css("--font")}`; ctx.textAlign = right ? "right" : "left";
      ctx.fillText(`판독 ${md(v.read)}`, px + (right ? -6 : 6), a.bottom - 6);
      ctx.restore();
    },
  };
}

function baseOptions(data: Readout, fmtY: (v: number) => string): ChartOptions<"bar" | "line"> {
  const dates = data.dates, line = css("--line"), ink2 = css("--ink-2"), font = css("--font");
  const promoOf = (d: string) => data.promos.find((p) => d >= p.start && d <= p.end);
  return {
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: "index", intersect: false }, layout: { padding: { top: 4 } },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: ink2, borderColor: line, borderWidth: 1,
        padding: 10, titleFont: { family: font, weight: 600 }, bodyFont: { family: font },
        filter: (it) => it.raw != null && !(it.dataset as { hideInTooltip?: boolean }).hideInTooltip,
        callbacks: {
          title: (it) => { const d = dates[it[0].dataIndex]; const p = promoOf(d); return md(d) + (p ? ` · ${p.name}` : ""); },
          label: (it) => ` ${it.dataset.label}: ${fmtY(it.raw as number)}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false }, border: { color: line },
        ticks: {
          color: ink2, font: { family: font, size: 11 }, autoSkip: false, maxRotation: 0,
          callback: (_v, idx) => { const d = dates[idx]; return /-(01|08|15|22)$/.test(d) ? md(d) : ""; },
        },
      },
      y: {
        beginAtZero: true, grid: { color: line, lineWidth: 1 }, border: { display: false },
        ticks: { color: ink2, font: { family: font, size: 11 }, maxTicksLimit: 5, callback: (v) => fmtY(Number(v)) },
      },
    },
  };
}

export interface ChartPair { update: (v: View) => void; destroy: () => void }

export function makeCharts(cr: HTMLCanvasElement, cs: HTMLCanvasElement, data: Readout, getView: () => View): ChartPair {
  const s1 = css("--s1"), s2 = css("--s2"), muted = css("--muted");
  const rangeFill = alpha(muted, 0.22);
  const dates = data.dates;
  const ri = make(cr, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        { label: data.meta.keyword_labels.bra, data: [], borderColor: s1, backgroundColor: s1, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.25 },
        { label: data.meta.keyword_labels.trend, data: [], borderColor: s2, backgroundColor: s2, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.25 },
      ],
    },
    options: baseOptions(data, (v) => String(Math.round(v))),
    plugins: [bandsPlugin(data, getView, true)],
  });
  const sa = make(cs, {
    type: "bar",
    data: {
      labels: dates,
      datasets: [
        { type: "bar", label: "일별 판매", data: [], backgroundColor: s1, borderRadius: { topLeft: 3, topRight: 3 }, borderSkipped: "bottom", categoryPercentage: 0.9, barPercentage: 0.85, order: 3 },
        { type: "line", label: "기준선 하한", data: [], borderWidth: 0, pointRadius: 0, fill: false, order: 2, hideInTooltip: true },
        { type: "line", label: "기준선 범위", data: [], borderWidth: 0, pointRadius: 0, backgroundColor: rangeFill, fill: "-1", order: 2, hideInTooltip: true },
        { type: "line", label: "기준선 (추정)", data: [], borderColor: muted, borderDash: [5, 4], borderWidth: 2, pointRadius: 0, pointHoverRadius: 3, tension: 0.2, order: 1 },
      ],
    },
    options: baseOptions(data, man),
    plugins: [bandsPlugin(data, getView, false)],
  });

  const onAxis = (arr: number[] | undefined, v: View) =>
    dates.map((d) => {
      const i = data.launch_dates.indexOf(d);
      return arr && i >= 0 && d <= v.to ? arr[i] : null;
    });

  const update = (v: View) => {
    ri.data.datasets[0].data = (data.series.bra ?? []).map((x, i) => (dates[i] <= v.to ? x : null));
    ri.data.datasets[1].data = (data.series.trend ?? []).map((x, i) => (dates[i] <= v.to ? x : null));
    sa.data.datasets[0].data = data.series.sales.map((x, i) => (dates[i] <= v.to ? x : null));
    sa.data.datasets[1].data = onAxis(v.baseline?.lo, v);
    sa.data.datasets[2].data = onAxis(v.baseline?.hi, v);
    sa.data.datasets[3].data = onAxis(v.baseline?.base, v);
    ri.update("none"); sa.update("none");
  };
  return { update, destroy: () => { ri.destroy(); sa.destroy(); } };
}

