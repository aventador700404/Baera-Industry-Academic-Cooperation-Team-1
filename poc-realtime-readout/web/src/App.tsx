import { useCallback, useEffect, useState } from "react";
import type { Readout } from "./types";
import { TimeBar } from "./components/TimeBar";
import { AlertFeed } from "./components/AlertFeed";
import { Cards } from "./components/Cards";
import { ReactionPanel } from "./components/ReactionPanel";
import { FlavorTable } from "./components/FlavorTable";
import { StorePanel } from "./components/StorePanel";
import { PromoPanel } from "./components/PromoPanel";
import { SchemaPanel } from "./components/SchemaPanel";

const STEP_MS = 1300; // 재생 속도: 하루당

// 다크/라이트 전환 시 차트를 다시 그리기 위한 카운터
function useThemeTick() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = () => setTick((t) => t + 1);
    mq.addEventListener("change", on);
    const mo = new MutationObserver(on);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { mq.removeEventListener("change", on); mo.disconnect(); };
  }, []);
  return tick;
}

const hashDate = () => new URLSearchParams(location.hash.slice(1)).get("d");

export default function App() {
  const [data, setData] = useState<Readout | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cur, setCur] = useState(0);
  const [playing, setPlaying] = useState(false);
  const theme = useThemeTick();

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/readout.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d: Readout) => {
        setData(d);
        const want = hashDate() ?? d.meta.milestones.find((m) => m.label === "티저")?.date;
        const i = d.days.findIndex((x) => x.date === want);
        setCur(i >= 0 ? i : 0);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  const pick = useCallback((i: number) => {
    setCur(i);
    if (data) history.replaceState(null, "", `#d=${data.days[i].date}`);
  }, [data]);

  // 재생: 하루씩 앞으로. 끝에 닿으면 멈춤
  useEffect(() => {
    if (!playing || !data) return;
    if (cur >= data.days.length - 1) { setPlaying(false); return; }
    const t = setTimeout(() => pick(cur + 1), STEP_MS);
    return () => clearTimeout(t);
  }, [playing, cur, data, pick]);

  const togglePlay = () => {
    if (!data) return;
    if (!playing && cur >= data.days.length - 1) pick(0);
    setPlaying((p) => !p);
  };

  if (err) return <div className="wrap"><div className="notice"><b>데이터를 못 읽었습니다.</b> {err} · 먼저 <code>make data</code></div></div>;
  if (!data) return <div className="wrap"><div className="empty">불러오는 중…</div></div>;

  const day = data.days[cur];
  const allMock = Object.values(data.meta.provenance_raw).every((p) => p === "mock");
  return (
    <div className="wrap">
      <header>
        <div className="eyebrow">SDIC × 넥스트페이먼츠 산학 · 마케팅 AX PoC</div>
        <h1>{data.meta.title}</h1>
        <p className="sub">
          판매, 광고, SNS 반응을 같은 날짜 축에 올려 매일 아침 판독하고, 튀는 신호는 그 날 바로 알림으로 띄웁니다.
          2026년 3월 이달의 맛 「{data.meta.flavor}」 출시를 날짜 순서대로 다시 재생합니다.
        </p>
      </header>

      <div className="notice" role="note">
        <span className={`tag ${allMock ? "mock" : "api"}`}>{allMock ? "시연 데이터" : "일부 실데이터"}</span>
        <div>
          <b>{allMock ? "실제 데이터가 아닙니다." : "데이터 출처가 섞여 있습니다."}</b>{" "}
          패널마다 배지로 출처를 표시합니다(본사 · 공개 API · 목). 반응 지표는 공개 API로 받을 수 있는 형식이고,
          판매 목 데이터는 공개된 누적 판매(출시 15일 100만 개, 22일 142만 개)에 맞췄습니다.
        </div>
      </div>

      <TimeBar data={data} cur={cur} playing={playing} onPick={(i) => { setPlaying(false); pick(i); }} onPlay={togglePlay} />

      <div className="layout">
        <main className="main">
          <Cards cards={day.cards} data={data} />
          <ReactionPanel data={data} day={day} theme={theme} />
          <div className="grid2">
            <FlavorTable data={data} day={day} />
            <StorePanel data={data} day={day} />
          </div>
          <PromoPanel data={data} day={day} />
        </main>
        <AlertFeed alerts={data.alerts} day={day} />
      </div>

      <SchemaPanel data={data} />
      <footer>{data.meta.assumptions} · 생성 {data.meta.generated_at.replace("T", " ")}</footer>
    </div>
  );
}
