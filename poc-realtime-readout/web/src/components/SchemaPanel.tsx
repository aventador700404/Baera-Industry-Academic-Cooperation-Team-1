import type { Readout } from "../types";
import { Prov } from "./bits";

// 본사 데이터로 바꿔 끼우는 지점. 열 이름은 pipeline/schema.py 에서 그대로 온다.
const DESC: Record<string, [string, string]> = {
  sales_daily: ["POS·점주 앱 매출관리·플레이버 관리, 해피오더 주문 (계정 연동)", "매일"],
  store_master: ["본사 매장 마스터", "분기"],
  promo_calendar: ["본사 마케팅 캘린더, 점주 분담 약정", "행사별"],
  reaction_daily: ["네이버 데이터랩 검색어트렌드, 블로그 검색 API", "매일"],
  reaction_topics_daily: ["블로그·카페 요약문 주제 분류 (계정 연동 시 배달앱·플레이스 리뷰)", "매일"],
  youtube_videos_daily: ["YouTube Data API (원값만, 30일 보관)", "매일 (시간 단위 가능)"],
  store_reaction_daily: ["'배스킨라빈스 + 지점명' 블로그 검색 결과 수", "매일"],
};

export function SchemaPanel({ data }: { data: Readout }) {
  const p = data.meta.provenance_raw;
  return (
    <section className="panel" aria-labelledby="m5">
      <div className="panel-h">
        <div>
          <h2 id="m5">본사 데이터로 바꿔 끼우는 지점</h2>
          <div className="q">같은 열 구조의 CSV를 data/raw 에 넣고 다시 빌드하면 이 화면이 그대로 동작합니다</div>
        </div>
      </div>
      <div className="tablewrap">
        <table className="schema">
          <thead><tr><th className="l">테이블</th><th className="l">열</th><th className="l">지금</th><th className="l">실제 운영</th><th className="l">주기</th></tr></thead>
          <tbody>
            {Object.entries(data.schema).map(([name, cols]) => (
              <tr key={name}>
                <td><code>{name}</code></td>
                <td><code>{cols.join(", ")}</code></td>
                <td>{p[name] ? <Prov p={p[name]} what="출처" /> : <span className="flat">없음</span>}</td>
                <td>{DESC[name]?.[0]}</td>
                <td>{DESC[name]?.[1]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
