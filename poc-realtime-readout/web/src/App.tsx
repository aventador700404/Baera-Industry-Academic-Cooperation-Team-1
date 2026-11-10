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
import { ModuleCards, TABS, type Tab } from "./components/ModuleCards";
import { PublicEvidence } from "./components/PublicEvidence";

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

// 푸터: 어떤 테이블이 실제 수집값이고 어떤 게 예시인지
const TABLE_KO: Record<string, string> = { sales_daily: "판매", store_master: "매장", promo_calendar: "행사 일정", reaction_daily: "SNS 반응",
  reaction_topics_daily: "언급 주제", youtube_videos_daily: "유튜브", store_reaction_daily: "매장 반응", ad_daily: "광고" };
function footNote(prov: Record<string, string>) {
  const by = (p: string) => Object.keys(prov).filter((k) => prov[k] === p).map((k) => TABLE_KO[k] ?? k);
  const api = [...by("공개 API"), ...by("공개 API + 목").map((t) => `${t}(일부 예시)`)], mock = by("목"), raw = by("본사 데이터");
  if (!api.length && !raw.length) return "화면의 수치는 시연용 예시 데이터입니다.";
  return [raw.length && `본사 데이터: ${raw.join("·")}`, api.length && `공개 API 실제 수집: ${api.join("·")}`,
          mock.length && `예시 데이터: ${mock.join("·")}`].filter(Boolean).join(" · ");
}

const hashParam = (k: string) => new URLSearchParams(location.hash.slice(1)).get(k);
const hashDate = () => hashParam("d");
const TAB_MODULE: Record<Tab, string | undefined> = { overview: undefined, reaction: "reaction", flavor: "flavor", store: "store", promo: "promo" };

export default function App() {
  const [data, setData] = useState<Readout | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cur, setCur] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [tab, setTab] = useState<Tab>(() => (TABS.find((t) => t.key === hashParam("t"))?.key ?? "overview"));
  const theme = useThemeTick();

  useEffect(() => {
    // 로컬 빌드 결과(readout.local.json, 레포에 안 올라감)가 있으면 그걸, 없으면 배포용(readout.json)을 읽는다
    const base = `${import.meta.env.BASE_URL}data/`;
    const get = (name: string) => fetch(base + name).then((r) => {
      if (!r.ok || !(r.headers.get("content-type") ?? "").includes("json")) throw new Error(`HTTP ${r.status}`);
      return r.json();
    });
    get("readout.local.json").catch(() => get("readout.json"))
      .then((d: Readout) => {
        setData(d);
        const want = hashDate() ?? d.meta.milestones.find((m) => m.label.startsWith("1주"))?.date;
        const i = d.days.findIndex((x) => x.date === want);
        setCur(i >= 0 ? i : d.days.length - 1);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  const syncHash = useCallback((d: string, t: Tab) => {
    history.replaceState(null, "", `#d=${d}${t === "overview" ? "" : `&t=${t}`}`);
  }, []);
  const pick = useCallback((i: number) => {
    setCur(i);
    if (data) syncHash(data.days[i].date, tab);
  }, [data, tab, syncHash]);
  const open = (t: Tab) => {
    setTab(t);
    if (data) syncHash(data.days[cur].date, t);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

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
        <nav className="tabs" aria-label="화면">
          {TABS.map((t) => (
            <button type="button" key={t.key} className={tab === t.key ? "on" : ""} aria-current={tab === t.key ? "page" : undefined}
                    onClick={() => open(t.key)}>{t.label}</button>
          ))}
        </nav>
        <div className="layout">
          {tab === "overview" ? (
            <main className="main">
              <ModuleCards day={day} onOpen={open} />
              <Timeline data={data} day={day} theme={theme} />
              <div className="kpis-wrap">
                <div className="h3">세부 지표 <span className="note">{day.date.slice(5).replace("-", "/")} 기준</span></div>
                <Kpis day={day} />
              </div>
            </main>
          ) : (
            <main className="main detail">
              {tab === "reaction" && <>
                <ReactionQuad day={day} />
                <Kpis day={day} only={["검색지수 (출시 전 한 달 대비)", "블로그 언급 (최근 7일)", "긍정률 (최근 7일)", "반응 대비 판매 (전환)"]} />
              </>}
              {tab === "flavor" && <>
                <FlavorTable day={day} />
                <Kpis day={day} only={["누적 판매", "첫 주 목표 대비 (맛 수요)"]} />
              </>}
              {tab === "store" && <StorePanel data={data} day={day} />}
              {tab === "promo" && <>
                <PromoPanel data={data} day={day} />
                <PublicEvidence data={data} day={day} />
                <Kpis day={day} only={["누적 판매", "광고 노출 (최근 7일)"]} />
              </>}
            </main>
          )}
          <AlertFeed alerts={data.alerts} day={day} module={TAB_MODULE[tab]} />
        </div>
        <footer>SDIC × 넥스트페이먼츠 산학 PoC · {footNote(data.meta.provenance)}</footer>
      </div>
    </>
  );
}
