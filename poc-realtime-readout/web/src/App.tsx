import { useCallback, useEffect, useState } from "react";
import type { Readout } from "./types";
import { TopBar } from "./components/TopBar";
import { Kpis } from "./components/Kpis";
import { Timeline } from "./components/Timeline";
import { ReactionQuad } from "./components/ReactionQuad";
import { FlavorTable } from "./components/FlavorTable";
import { StorePanel } from "./components/StorePanel";
import { PromoPanel } from "./components/PromoPanel";
import { AlertFeed } from "./components/AlertFeed";

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
        const want = hashDate() ?? d.meta.milestones.find((m) => m.label.startsWith("1주"))?.date;
        const i = d.days.findIndex((x) => x.date === want);
        setCur(i >= 0 ? i : d.days.length - 1);
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

  if (err) return <div className="wrap"><div className="empty">데이터를 불러오지 못했습니다. ({err})</div></div>;
  if (!data) return <div className="wrap"><div className="empty">불러오는 중…</div></div>;

  const day = data.days[cur];
  return (
    <>
      <TopBar data={data} cur={cur} playing={playing} onPick={(i) => { setPlaying(false); pick(i); }} onPlay={togglePlay} />
      <div className="wrap">
        <Kpis day={day} />
        <div className="layout">
          <main className="main">
            <Timeline data={data} day={day} theme={theme} />
            <div className="quads">
              <ReactionQuad day={day} />
              <FlavorTable day={day} />
              <StorePanel data={data} day={day} />
              <PromoPanel data={data} day={day} />
            </div>
          </main>
          <AlertFeed alerts={data.alerts} day={day} />
        </div>
        <footer>SDIC × 넥스트페이먼츠 산학 PoC · 화면의 수치는 시연용 예시 데이터입니다.</footer>
      </div>
    </>
  );
}
