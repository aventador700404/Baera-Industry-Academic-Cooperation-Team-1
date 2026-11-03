# 이달의 맛 실시간 반응 판독 (배라 마케팅 AX PoC)

SDIC × 넥스트페이먼츠 산학 「AI 전환(AX)을 통한 배스킨라빈스 마케팅 강화 전략」 PoC.

**판매, 광고, SNS 반응을 같은 날짜 축에 올려 매일 아침 판독하고, 평소와 다르게 튀는 신호는 그 날 바로 알림으로 띄우는 마케팅 의사결정 화면.**
배라가 이달의 맛 반응을 판독하는 데 약 1개월이 걸리는 문제를 '판독·보고 구조' 문제로 보고, 그 간격을 하루 단위로 줄이는 것을 보여 준다.

시연은 2026년 3월 이달의 맛 「두바이에서 온 엄마는 외계인」 출시를 **날짜 순서대로 다시 재생**한다. 슬라이더의 하루는
'그 날 밤까지 쌓인 데이터를 다음 날 아침에 본 판독'이고, 계산은 그 날까지의 데이터만 쓴다(테스트로 확인).

## 화면 (파트 1 스토리라인 4장 'PoC 화면 설계' 기준)

공통 날짜 슬라이더(▶ 재생) + 오늘의 판독 카드 4장 + 실시간 알림 피드 + 4모듈.

| 모듈 | 총괄 질문 | 보는 것 | 데이터 |
|---|---|---|---|
| 1 신제품 반응 | Q1 즉시 반응, Q3 SNS·인플루언서 | 검색·언급 급등, 주제별 언급과 긍부정(맛·비교·가격·품절·사이즈·매장), 반응을 끈 콘텐츠, 반응 대비 판매(전환) | 공개 API |
| 2 맛별 판매 순위 | Q2 | 7일 일평균 순위, 원조 잠식, 첫 주 목표 대비 | 목 |
| 3 매장 순위 급등 | Q4 | 순위 변화를 매장 주변 SNS 반응으로 판독 (언급↑ 판매↓ = 품절 의심, 언급↑ 판매↑ = 바이럴) | 목 + 공개 API |
| 4 판촉 행사 효과 | — | 기준선을 뺀 증분, 증분 ROI → 지속·조정·중단 | 목 |

판독 지표는 업계 공개 사례의 공통 언어인 **첫 주 목표 대비**, **출시 전 한 달 일평균 대비**를 쓴다.

> 판매·매장·행사 데이터는 **목 데이터**다. 브랜드 합계는 공개 보도된 누적 판매(출시 15일 100만 개, 22일 142만 개)에 정확히 맞췄다.
> 반응 데이터는 공개 API 형식이고 키를 넣으면 실제 값으로 바뀐다. 패널마다 배지로 출처를 표시한다.

## 바로 실행

```bash
make setup     # 처음 한 번: .venv + pip, web npm ci
make dev       # 목 데이터 생성 → 판독 JSON 빌드 → http://127.0.0.1:5173
make test      # 심어 둔 사건을 그 날 잡는지, 미래 데이터를 안 쓰는지
```

키 없이 바로 돈다. 공개 API를 붙이려면 `.env.example`을 `.env`로 복사해 키를 넣고 `make check-apis` → `make collect` → `make build-data`.

## 구조

```
pipeline/            파이썬: 데이터 → 하루씩 판독 → JSON (계산 로직은 전부 여기)
  config.py          출시일·목표·단가·판정 기준·알림 기준 등 가정을 한곳에
  schema.py          데이터 계약 (테이블·열). 본사 데이터는 이 모양으로 넣는다
  io.py              읽기 우선순위: data/raw(본사) > data/collected(API) > data/generated(목)
  mock/generate.py   목 데이터 (공개 앵커에 맞춤, 감지돼야 할 사건을 심어 둠, 정답은 _truth.json)
  collect/           네이버 데이터랩·블로그(언급·주제), 유튜브, 인스타 Business Discovery 수집기
  analysis/          alerts(실시간 감지) · reaction · flavor · stores · promo · baseline · cards
  build.py           슬라이더의 하루마다 전부 계산 → web/public/data/readout.json
web/                 React + Vite + TypeScript + Chart.js. JSON만 읽어서 그린다 (정적 파일)
tests/               pytest
docs/                ARCHITECTURE · DATA · CONTEXT
```

`make web` 결과(`web/dist`)는 서버 없이 어디에 올려도 된다.

## 문서

- [docs/CONTEXT.md](docs/CONTEXT.md) — 왜 이 화면인가, 시연 흐름, 본사에 확인할 것
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 감지 규칙, 계산 방법, 실제 운영으로 넘어갈 때
- [docs/DATA.md](docs/DATA.md) — 테이블 계약, API 한도와 정책, 목 데이터와 심어 둔 사건
