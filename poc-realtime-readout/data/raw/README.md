# data/raw — 본사 데이터 넣는 곳

여기에 넣은 CSV가 목 데이터보다 먼저 쓰입니다(`pipeline/io.py`). **이 폴더의 CSV는 git에 올라가지 않습니다.**

파일 이름과 열은 `docs/DATA.md`의 표와 정확히 같아야 합니다. 예: `sales_daily.csv`

```
date,store_id,flavor,qty
2026-03-01,S0001,두바이에서 온 엄마는 외계인,41
```

넣은 뒤 `make build-data` → 화면 배지가 '본사 데이터'로 바뀝니다. 열이 빠졌으면 어떤 열이 없는지 알려 주고 멈춥니다.
