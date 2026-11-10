# 자주 쓰는 명령 모음. `make help`
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: help setup mock collect check-apis build-data publish data live test dev web shoot clean

help:
	@echo "make setup       파이썬 가상환경 + 웹 패키지 설치 (처음 한 번)"
	@echo "make data        목 데이터 생성 → 판독 JSON 빌드 (키 없이 바로 됨)"
	@echo "make collect     .env 키로 공개 API 수집 → data/collected"
	@echo "make live        목 데이터 + 공개 API 수집 → 판독 JSON (실데이터로 화면 갱신)"
	@echo "make check-apis  키마다 1회 호출 테스트"
	@echo "make test        파이썬 테스트"
	@echo "make dev         data 빌드 후 웹 개발 서버 (http://127.0.0.1:5173)"
	@echo "make web         웹 정적 빌드 → web/dist (배포용)"
	@echo "make shoot       빌드 화면 캡처 + 콘솔 오류 확인 (vite preview 켜 둔 상태에서)"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd web && npm ci

mock:
	$(PY) -m pipeline.mock.generate

collect:
	$(PY) -m pipeline.collect.run

check-apis:
	$(PY) -m pipeline.collect.run --check

build-data:
	$(PY) -m pipeline.build

publish:  ## 배포용 readout.json 갱신 (커밋하면 Vercel 반영)
	$(PY) -m pipeline.build --publish

data: mock build-data

live: mock collect build-data

test:
	$(PY) -m pytest

dev: data
	cd web && npm run dev

web: publish
	cd web && npm run build

shoot:
	cd web && node scripts/shoot.mjs ../shots

clean:
	rm -rf data/generated/*.csv data/generated/_truth.json data/collected/*.csv web/dist shots
