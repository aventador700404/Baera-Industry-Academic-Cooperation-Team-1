# 데이터

## 테이블 계약 (`pipeline/schema.py`와 같음)

| 테이블 | 열 | 지금 | 실제 운영 | 주기 |
|---|---|---|---|---|
| `sales_daily` | date, store_id, flavor, qty | 목 (매장 1,713 × 맛 9 × 일) | POS·점주 앱 매출관리·플레이버 관리, 해피오더 | 매일 |
| `store_master` | store_id, store_name, type, region | 목 (유형 5종, 지역 예시) | 본사 매장 마스터 | 분기 |
| `promo_calendar` | promo_id, name, start, end, discount_rate, desc | 목 (배라데이·배라위크·31데이) | 본사 마케팅 캘린더, 점주 분담 약정 | 행사별 |
| `reaction_daily` | date, source, keyword, metric, value | 목 (공개 API 형식) | 네이버 데이터랩·블로그 검색 | 매일 |
| `youtube_videos_daily` | date, video_id, channel_type, title, views | 목 | YouTube Data API 스냅샷 | 매일 |
| `store_reaction_weekly` | week_start, store_id, mentions | 목 | '배스킨라빈스 + 지점명' 블로그 검색 결과 수 | 매주 |
| `store_context_weekly` | week_start, store_id, kind, value, note | 목 (심어 둔 2건) | 카카오 로컬(경쟁점), 서울 생활인구 | 매주 |

`reaction_daily`는 long 형식이다. 지금 쓰는 키: `naver_datalab/bra|trend/search_index`, `naver_blog/bra/mentions`, `naver_blog/bra/positive_ratio`.
마지막 세 테이블은 없어도 화면이 돈다(해당 열·문구만 빠짐).

## 공개 API (파트 1 리서치, 접근 2026-10-30 기준)

| API | 무료 한도 | 지켜야 할 것 | 이 레포에서 |
|---|---|---|---|
| 네이버 데이터랩 검색어트렌드 | 월 5만 건 | 상대지수(0~100). 비교할 키워드는 한 요청에 묶음(최대 5그룹) | `bra`, `trend` 두 그룹을 한 요청으로 |
| 네이버 검색(블로그) | API HUB 검색 합산 월 77.5만 건 | 본문이 아니라 요약만. 최신순 최대 1,000건 | 언급 수는 하한값. 감성은 요약문 단어 사전 방식 |
| YouTube Data API | 일 10,000 units (search 100 units) | **API 수치로 새 지표(좋아요율 등) 계산 금지, 30일 넘게 저장 금지** | 영상별 조회수 원값만, 합계·비율도 안 만듦. `prune()`이 30일 지난 행 삭제 |
| 인스타 Business Discovery | 무료 | 팀 비즈니스 계정 + 페이스북 페이지 + Meta 앱 필요. 상대 계정 인사이트(도달)는 불가 | 수집만 구현, 화면 반영은 다음 단계 |

- **NAVER API HUB**: 2026-07-31부터 신규 신청은 HUB에서만. 기존 개발자센터 키는 HUB에서 못 쓴다(기존 앱은 2027-06-30까지 사용 가능).
  HUB 엔드포인트·인증 방식은 확인 못 해서 `.env`의 `NAVER_DATALAB_URL`, `NAVER_SEARCH_URL`로 바꿀 수 있게 열어 뒀다. 결제수단 등록 필수 여부도 확인 필요.
- **과거 기간의 한계**: 데이터랩은 2016년부터 과거 추이를 받을 수 있어 2026년 3월 출시도 실제 값으로 채울 수 있다.
  블로그는 최신 1,000건까지라 3월 글은 못 닿고, 유튜브는 과거 일별 조회수를 주지 않는다 → 이 둘은 **다음 이달의 맛부터 매일 쌓아야** 한다.
- 배달앱(배민·쿠팡이츠·요기요), 네이버 플레이스 리뷰, 커뮤니티: 공식 API 없음, 약관상 자동 수집 금지 → 본사 계정 연동 경로로 제안.

## 목 데이터 보정 (`pipeline/mock/generate.py`)

- 브랜드 합계: 행사 없는 수요 = 바닥 + 지수 감소, 행사일은 정해 둔 상승률만큼 증가. 감소 속도는
  `(22일 누적 − 15일 누적) ÷ 15일 누적 = 0.42`가 되도록 찾고, 노이즈를 넣은 뒤 두 앵커에 **정확히** 다시 맞춘다.
- 매장 배분: 매장 규모(로그정규) × 유형별 '몰리는 날' 곡선 × 노이즈. 일별 합계가 브랜드 합계와 정확히 같도록 최대 잉여 배분.
- 기존 맛: 원조는 잠식(−15% → −6%), 딸기는 시즌 상승(+3% → +13%), 나머지 −3.5%.
- 심어 둔 정답(`_truth.json`, 분석 코드는 읽지 않음): 행사별 실제 증분, 2주차·3주차 품절 매장, 3주차 유동인구 증가 매장, 4주차 경쟁점 개점 매장.
- 매장 수 1,713은 2025 정보공개서 가맹점 수. 지역·매장명은 예시다.
