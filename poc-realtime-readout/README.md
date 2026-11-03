# 이달의 맛 주간 판독 (배라 마케팅 AX PoC)

SDIC × 넥스트페이먼츠 산학 「AI 전환(AX)을 통한 배스킨라빈스 마케팅 강화 전략」 PoC.

**판매, 행사, SNS 반응을 같은 날짜 축에 올려 매주 읽고, 그 주에 내릴 결정 세 가지로 연결하는 화면.**
2026년 3월 이달의 맛 「두바이에서 온 엄마는 외계인」 출시를 재현한다.

| 결정 | 화면이 답하는 질문 |
|---|---|
| 증산 · 재출시 | 할인 효과를 뺀 맛 수요가 목표 대비 몇 배인가 |
| 판촉 지속 · 조정 · 중단 | 행사 덕분에 늘어난 판매(증분)가 할인 비용을 넘었나 |
| 매장 지원 우선순위 | 어느 매장이 왜 오르고 떨어졌나 (품절 의심, 상권 변화, 유형 흐름) |

판독 시점(출시 전 → 1~4주차 → 월말)을 고르면 **그 날까지의 데이터만으로** 다시 계산한 결과가 나온다.
지금 방식(월말 정산 후 4/6 판독, 가정)보다 며칠 앞당겨지는지도 같이 보여 준다.

> 판매·매장·행사 데이터는 **목 데이터**다. 브랜드 합계는 공개 보도된 누적 판매(출시 15일 100만 개, 22일 142만 개)에
> 정확히 맞췄다. 반응 데이터는 공개 API 형식이며 키를 넣으면 실제 값으로 바뀐다. 화면의 배지가 출처를 표시한다.

## 바로 실행

```bash
make setup     # 처음 한 번: .venv + pip, web npm ci
make dev       # 목 데이터 생성 → 판독 JSON 빌드 → http://127.0.0.1:5173
make test      # 분석이 목 데이터에 심어 둔 정답을 찾는지 확인
```

키 없이 바로 돈다. 공개 API를 붙이려면 `.env.example`을 `.env`로 복사해 키를 넣고 `make check-apis` → `make collect` → `make build-data`.

## 구조

```
pipeline/            파이썬: 데이터 → 계산 → JSON (로직은 전부 여기)
  config.py          출시일·목표·단가·판정 기준 등 가정을 한곳에
  schema.py          데이터 계약 (테이블·열). 본사 데이터는 이 모양으로 넣는다
  io.py              읽기 우선순위: data/raw(본사) > data/collected(API) > data/generated(목)
  mock/generate.py   목 데이터 (매장 1,713개 × 맛 × 일, 공개 앵커에 맞춤, 정답은 _truth.json)
  collect/           네이버 데이터랩·블로그, 유튜브, 인스타 Business Discovery 수집기
  analysis/          기준선 추정, 판촉 ROI, 맛 순위, 매장 순위·신호·이유, 반응 요약, 결정 카드
  build.py           판독 시점별로 전부 계산 → web/public/data/readout.json
web/                 React 19 + Vite + TypeScript + Chart.js. JSON만 읽어서 그린다
tests/               pytest (정답 복원, 데이터 계약, 수집기 파싱)
docs/                ARCHITECTURE · DATA · CONTEXT
```

팀 이전 PoC(sdic-persona-team1)와 같은 패턴: **파이썬으로 미리 계산해 JSON으로 떨구고, 웹은 정적으로 그린다.**
서버가 없어서 `make web` 결과(`web/dist`)를 GitHub Pages, Vercel, Netlify 어디에 올려도 된다(`base: "./"`).

## 본사 데이터로 바꾸기

`docs/DATA.md`의 열 구조대로 CSV를 `data/raw/`에 넣고 `make build-data`. 그 테이블만 목 대신 본사 데이터로 바뀌고 배지도 바뀐다.
`data/raw/`의 CSV는 git에 올라가지 않는다.

## 문서

- [docs/CONTEXT.md](docs/CONTEXT.md) — 왜 이 화면인가 (파트 3 현황 → 파트 1 수집 → PoC), 본사에 확인할 것
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 데이터 흐름, 계산 방법(기준선·ROI·매장 신호), 확장 지점
- [docs/DATA.md](docs/DATA.md) — 테이블 계약, API 한도와 정책, 목 데이터 보정 방법
