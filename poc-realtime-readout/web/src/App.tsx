import { useEffect, useState } from "react";
import type { Readout } from "./types";
import { ViewPicker } from "./components/ViewPicker";
import { Cards } from "./components/Cards";
import { ReactionSales } from "./components/ReactionSales";
import { FlavorTable } from "./components/FlavorTable";
import { StorePanel } from "./components/StorePanel";
import { PromoPanel } from "./components/PromoPanel";
import { SchemaPanel } from "./components/SchemaPanel";
import { LagPanel } from "./components/LagPanel";

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

const initialView = () => {
  const h = new URLSearchParams(location.hash.slice(1)).get("view");
  return h ?? "w1";
};

export default function App() {
  const [data, setData] = useState<Readout | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cur, setCur] = useState(1);
  const theme = useThemeTick();

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/readout.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d: Readout) => {
        setData(d);
        const i = d.views.findIndex((v) => v.id === initialView());
        if (i >= 0) setCur(i);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  const pick = (i: number) => {
    setCur(i);
    if (data) history.replaceState(null, "", `#view=${data.views[i].id}`);
  };

  if (err) return <div className="wrap"><div className="notice"><b>데이터를 못 읽었습니다.</b> {err} · 먼저 <code>make data</code></div></div>;
  if (!data) return <div className="wrap"><div className="empty">불러오는 중…</div></div>;

  const view = data.views[cur];
  const allMock = Object.values(data.meta.provenance_raw).every((p) => p === "mock");
  return (
    <div className="wrap">
      <header>
        <div className="eyebrow">SDIC × 넥스트페이먼츠 산학 · 마케팅 AX PoC</div>
        <h1>{data.meta.title}</h1>
        <p className="sub">
          2026년 3월 이달의 맛 「{data.meta.flavor}」 출시를 재현한 시연 화면입니다. 판매, 행사, SNS 반응을 같은 날짜 축에 올려
          매주 읽고, 그 주에 내릴 결정 세 가지로 연결합니다.
        </p>
      </header>

      <div className="notice" role="note">
        <span className={`tag ${allMock ? "mock" : "api"}`}>{allMock ? "시연 데이터" : "일부 실데이터"}</span>
        <div>
          <b>{allMock ? "실제 데이터가 아닙니다." : "데이터 출처가 섞여 있습니다."}</b>{" "}
          각 패널의 배지가 출처입니다(본사 · 공개 API · 목). 판매 목 데이터는 공개된 누적 판매(출시 15일 100만 개, 22일 142만 개)에
          맞춰 보정했고, 반응 지표는 공개 API로 받을 수 있는 형식입니다.
        </div>
      </div>

      <ViewPicker views={data.views} cur={cur} onPick={pick} />
      <Cards cards={view.cards} data={data} />
      <ReactionSales data={data} view={view} theme={theme} />
      <div className="grid2">
        <FlavorTable data={data} view={view} />
        <LagPanel data={data} view={view} />
      </div>
      <StorePanel data={data} view={view} />
      <PromoPanel data={data} view={view} />
      <SchemaPanel data={data} />
      <footer>{data.meta.assumptions} · 생성 {data.meta.generated_at.replace("T", " ")}</footer>
    </div>
  );
}
