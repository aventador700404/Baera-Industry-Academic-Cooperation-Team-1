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
function overlay(data: Readout, getDay: () => Day, role: Role): Plugin<"bar" | "line"> {
  const dates = data.dates;
  const half = (chart: Chart) => (chart.scales.x.getPixelForValue(1) - chart.scales.x.getPixelForValue(0)) / 2;
  return {
    id: "overlay",
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
        if (role.top) {
          ctx.fillStyle = css("--band-ink"); ctx.font = `600 10px ${css("--font")}`; ctx.textAlign = "left";
          ctx.fillText(p.name, x.getPixelForValue(i0) - h + 3, a.bottom - 4);
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
        ctx.fillStyle = css("--s1"); ctx.font = `600 11px ${css("--font")}`; ctx.textAlign = right ? "right" : "left";
        ctx.fillText(`기준일 ${md(v.date)}`, px + (right ? -6 : 6), a.bottom - 6);
      }
      ctx.restore();
    },
  };
}

function options(data: Readout, fmtY: (v: number) => string, role: Role, tip: (i: number) => string[] = () => []):
  ChartOptions<"bar" | "line"> {
  const dates = data.dates, line = css("--line"), ink2 = css("--ink-2"), font = css("--font");
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
          label: (it) => ` ${it.dataset.label}: ${fmtY(it.raw as number)}`,
          afterBody: (it) => tip(it[0].dataIndex),
        },
      },
    },
    scales: {
      x: {
        grid: { display: false }, border: { color: line },
        ticks: {
          display: role.bottom, color: ink2, font: { family: font, size: 11 }, autoSkip: false, maxRotation: 0,
          callback: (_v, idx) => { const d = dates[idx]; return /-(01|08|15|22)$/.test(d) ? md(d) : ""; },
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

// 같은 날짜 축의 세 줄: SNS 반응 / 광고 / 판매
export function makeCharts(cr: HTMLCanvasElement, ca: HTMLCanvasElement, cs: HTMLCanvasElement,
                           data: Readout, getDay: () => Day): Charts {
  const s1 = css("--s1"), s2 = css("--s2"), s3 = css("--s3"), trend = css("--trend"), muted = css("--muted");
  const dates = data.dates, S = data.series;

  const reaction = make(cr, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        { label: data.meta.keyword_labels.bra, data: [], borderColor: s2, backgroundColor: s2, borderWidth: 2.2, pointRadius: 0, pointHoverRadius: 4, tension: 0.25 },
        { label: data.meta.keyword_labels.trend, data: [], borderColor: trend, backgroundColor: trend, borderWidth: 1.6, borderDash: [4, 3], pointRadius: 0, pointHoverRadius: 3, tension: 0.25 },
      ],
    },
    options: options(data, (v) => String(Math.round(v)), { top: true, bottom: false }),
    plugins: [overlay(data, getDay, { top: true, bottom: false })],
  });

  const adTip = (i: number) => {
    const c = S.ad_campaign[i], sp = S.ad_spend[i], ck = S.ad_clicks[i], im = S.ad_impressions[i];
    return c ? [` 캠페인: ${c}`, ` 클릭: ${fmt(ck ?? 0)} (${im ? ((100 * (ck ?? 0)) / im).toFixed(2) : "-"}%)`, ` 비용: ${fmt((sp ?? 0) / 10000)}만 원`] : [];
  };
  const ads = make(ca, {
    type: "bar",
    data: { labels: dates, datasets: [
      { label: "광고 노출", data: [], backgroundColor: s3, borderRadius: { topLeft: 2, topRight: 2 }, borderSkipped: "bottom", categoryPercentage: 0.9, barPercentage: 0.85 },
    ] },
    options: options(data, man, { top: false, bottom: false }, adTip),
    plugins: [overlay(data, getDay, { top: false, bottom: false })],
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
    options: options(data, man, { top: false, bottom: true }),
    plugins: [overlay(data, getDay, { top: false, bottom: true })],
  });

  const onAxis = (arr: number[] | undefined, v: Day) =>
    dates.map((d) => {
      const i = data.launch_dates.indexOf(d);
      return arr && i >= 0 && d <= v.date ? arr[i] : null;
    });
  const upto = (arr: (number | null)[] | null, v: Day) => (arr ?? []).map((x, i) => (dates[i] <= v.date ? x : null));

  const update = (v: Day) => {
    reaction.data.datasets[0].data = upto(S.bra, v);
    reaction.data.datasets[1].data = upto(S.trend, v);
    ads.data.datasets[0].data = upto(S.ad_impressions, v);
    sales.data.datasets[0].data = upto(S.sales, v);
    sales.data.datasets[1].data = onAxis(v.baseline?.lo, v);
    sales.data.datasets[2].data = onAxis(v.baseline?.hi, v);
    sales.data.datasets[3].data = onAxis(v.baseline?.base, v);
    for (const c of [reaction, ads, sales]) c.update("none");
  };
  return { update, destroy: () => { reaction.destroy(); ads.destroy(); sales.destroy(); } };
}
