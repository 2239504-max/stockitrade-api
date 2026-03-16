## 주요 포트폴리오 API
- `POST /uploads/shinhan?filename=...`
  - `application/octet-stream` 바디에 `.xlsx` 바이너리를 넣어 전송
  - 거래를 파싱해서 SQLite에 저장
- `POST /trades/manual`
  - 수동 거래 1건 저장
- `GET /portfolio/summary`
  - 누적 거래 기반 포지션/현금 요약

## Shinhan 업로드 파일 포맷
첫 행(header)에 아래 컬럼을 포함해야 합니다.
- 필수: `date`, `ticker`, `side`, `quantity`, `price`
- 선택: `fee`, `account`, `memo`

`side` 값은 `buy` 또는 `sell`.

데이터는 `data/trades.db`에 저장됩니다.
