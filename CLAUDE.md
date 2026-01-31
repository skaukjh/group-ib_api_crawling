# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Group-IB Threat Intelligence API 크롤러 - 19개 엔드포인트에서 위협 인텔리전스 데이터를 30분 간격으로 자동 수집하는 Python 애플리케이션.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py

# 테스트 실행 (pytest 설치 필요)
pip install pytest pytest-mock
pytest tests/ -v

# 타입 체킹 (mypy 설치 필요)
pip install mypy
mypy src/ --strict
```

## Architecture

```
main.py                    # 엔트리 포인트, 30분 무한 루프 실행
    ↓
src/collector.py           # GroupIBCollector 클래스 (핵심 수집 로직)
    - authenticate()       # Basic Auth로 API 인증
    - loadEndpoints()      # list.csv에서 엔드포인트 로드
    - collectAllEndpoints()# 모든 엔드포인트 순차 수집
    - saveToJsonl()        # JSON Lines 형식으로 저장
    ↓
src/config.py              # 환경 변수 기반 설정 관리 (Config 클래스)
```

### Key Mechanisms

- **seqUpdate**: Group-IB API의 증분 수집 메커니즘. 응답의 최상위 `seqUpdate` 필드 값을 저장하여 다음 요청 시 사용 → 신규 데이터만 수집
- **재시도 로직**: `retryOnError` 데코레이터로 네트워크 오류/5xx/429 자동 재시도 (최대 3회)
- **원자적 파일 쓰기**: `saveSeqUpdate()`는 `.tmp` 파일에 먼저 쓰고 rename (데이터 손실 방지)

### Data Flow

1. `list.csv` → 엔드포인트 URL + 파라미터 로드
2. `data/seq_update.json` → 마지막 seqUpdate 값 로드
3. API 호출 → 응답의 `items`/`data`/`results` 추출
4. `data/outputs/*.jsonl` → JSON Lines 형식으로 저장

## Coding Conventions

- **들여쓰기**: 2칸 스페이스
- **네이밍**: camelCase (Python PEP8과 다름)
- **주석/로그**: 한국어
- **타입 힌트**: 모든 함수에 명시 (`Dict[str, Any]` 등 구체적 타입 사용)

## Environment Variables

`.env` 파일 필수 설정:
```
GROUPIB_USERNAME=your_email@example.com
GROUPIB_API_KEY=your_api_key
```

선택적 오버라이드:
```
GROUPIB_BASE_URL=https://tap.group-ib.com
REQUEST_TIMEOUT=30
RATE_LIMIT_WAIT=1
MAX_RETRIES=3
WAIT_MINUTES=30
```

## Adding New Endpoints

`list.csv`에 행 추가:
```csv
https://tap.group-ib.com/api/v2/새로운/엔드포인트/updated,limit=100
```
