import type { Day, Readout } from "../types";
import { fmt, md } from "../format";

const host = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };

// 판촉 탭의 근거: 뉴스에서 찾은 행사 일정·혜택과 회사가 발표한 성과 수치 (기준일까지 나온 기사만)
export function PublicEvidence({ data, day }: { data: Readout; day: Day }) {
  // 최근 행사부터. 출시 전 행사는 '매달·매년 반복되는 행사인지' 확인용이라 연도를 붙이고 흐리게
  const { teaser } = data.meta.product;
  const yr = teaser.slice(0, 4);
  const ymd = (d: string) => (d.slice(0, 4) === yr ? md(d) : `'${d.slice(2, 4)}.${md(d).replace("/", ".")}`);
  const span = (a: string, b: string | null) => (!b || a === b ? ymd(a) : `${ymd(a)}~${ymd(b)}`);
  const events = (data.meta.public_events ?? []).filter((e) => !e.first_pub || e.first_pub <= day.date)
    .slice().sort((x, y) => (y.start > x.start ? 1 : y.start < x.start ? -1 : 0));
  const claims = (data.meta.public_claims ?? []).filter((c) => c.pub <= day.date);
  const promoName = (id: string | null) => data.promos.find((p) => p.id === id)?.name;
  return (
    <section className="panel" aria-labelledby="pe-h">
      <div className="panel-h"><h2 id="pe-h">공개 자료 근거</h2><span className="note">네이버 뉴스 검색 · 기준일까지 나온 기사</span></div>
      {!data.meta.public_events && !data.meta.public_claims ? (
        <div className="empty">뉴스를 수집하면 행사 일정과 발표 성과가 여기에 나옵니다.</div>
      ) : (
        <>
          <h3 className="h3">뉴스에서 찾은 행사</h3>
          {events.length === 0 ? <div className="empty">기준일까지 찾은 행사가 없습니다.</div> : (
            <div className="tablewrap">
              <table className="compact">
                <thead><tr><th className="l">행사</th><th className="l">기간</th><th className="l">날짜 근거</th><th className="l">혜택</th><th>기사</th><th className="l">행사표</th><th className="l">출처</th></tr></thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.event_id} className={(e.end ?? e.start) < teaser ? "past" : ""}>
                      <td className="l name">{e.name}</td>
                      <td className="l">{span(e.start, e.end)}</td>
                      <td className="l"><span className={`chip ${e.evidence === "기사 날짜" ? "good" : e.evidence.startsWith("기사") ? "blue" : "warn"}`}>{e.evidence}</span></td>
                      <td className="l why">{e.benefits || "-"}</td>
                      <td>{fmt(e.n_articles)} <span className="note">({fmt(e.n_outlets)}곳)</span></td>
                      <td className="l">{e.in_calendar ? <span className="chip good">{promoName(e.in_calendar)}</span> : <span className="flat">없음</span>}</td>
                      <td className="l">{e.sources.slice(0, 2).map((u) => <a key={u} href={u} target="_blank" rel="noreferrer" className="src">{host(u)}</a>)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <h3 className="h3">회사가 발표한 성과 <span className="note">잘된 것만 보도되는 수치라 판정에는 쓰지 않고, 설정의 공개 앵커와 맞춰 보는 데만 씀</span></h3>
          {claims.length === 0 ? <div className="empty">기준일까지 나온 발표 수치가 없습니다.</div> : (
            <div className="tablewrap">
              <table className="compact">
                <thead><tr><th className="l">기사</th><th className="l">내용</th><th className="l">출시일 기준</th><th className="l">공개 앵커</th></tr></thead>
                <tbody>
                  {claims.map((c) => (
                    <tr key={`${c.pub}-${c.text}`}>
                      <td className="l">{md(c.pub)} <a href={c.link} target="_blank" rel="noreferrer" className="src">{host(c.link)}</a></td>
                      <td className="l why">{c.days && c.count ? `${c.days}일 만에 ${fmt(c.count / 10000)}만 개` : c.text}</td>
                      <td className="l">{c.date ? md(c.date) : "-"}</td>
                      <td className="l">{c.matches_anchor == null ? <span className="flat">-</span> :
                        c.matches_anchor ? <span className="chip good">일치</span> : <span className="chip warn">다름</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
