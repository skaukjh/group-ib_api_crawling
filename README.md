# Group-IB Threat Intelligence API 크롤러

Group-IB의 위협 인텔리전스 데이터를 30분 간격으로 자동 수집하는 Python 애플리케이션입니다. 19개 엔드포인트에서 신규 데이터를 효율적으로 수집하고 JSON Lines 형식으로 저장하며, 관련 PDF 자동 다운로드합니다.

## 주요 기능

- **자동 수집**: 30분 간격으로 무한 반복 수집
- **증분 수집**: `seqUpdate` 메커니즘으로 신규 데이터만 효율적으로 수집
- **PDF 다운로드**: 각 항목의 포탈 링크에서 PDF 자동 다운로드
- **안정적인 저장**: 원자적 파일 쓰기로 데이터 손실 방지
- **자동 재시도**: 네트워크 오류/서버 오류 시 자동 재시도 (최대 3회)
- **상세한 로깅**: 수집 진행 상황을 파일과 콘솔에 기록

## 설치

### 필수 요구사항
- Python 3.8 이상
- pip

### 의존성 설치

```bash
pip install -r requirements.txt
```

## 설정

### 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
# 필수 설정
GROUPIB_USERNAME=your_email@example.com
GROUPIB_API_KEY=your_api_key

# 선택적 설정 (기본값 사용)
GROUPIB_BASE_URL=https://tap.group-ib.com
REQUEST_TIMEOUT=30
RATE_LIMIT_WAIT=1
MAX_RETRIES=3
WAIT_MINUTES=30
```

## 사용법

### 기본 실행

```bash
python main.py
```

메인 프로세스가 시작되며, 30분 간격으로 무한 반복 수집합니다.

### 단일 수집 (테스트)

```python
from src.collector import GroupIBCollector

collector = GroupIBCollector()
collector.authenticate()
collector.loadEndpoints()
seqUpdates = collector.collectAllEndpoints()
collector.saveSeqUpdate(seqUpdates)
```

## 개발 및 테스트

### 테스트 실행

```bash
# 모든 테스트 실행
pytest tests/ -v

# 특정 파일 테스트
pytest tests/test_collector.py -v
```

### 타입 체킹

```bash
mypy src/ --strict
```

### 데이터 검증

```bash
# 수집 데이터에서 중복 ID 검사
python check_duplicates.py
```

## 디렉토리 구조

```
.
├── main.py                      # 엔트리 포인트
├── list.csv                     # 수집 대상 엔드포인트 목록
├── CLAUDE.md                    # 개발자 가이드
├── requirements.txt             # 파이썬 의존성
├── src/
│   ├── collector.py             # 핵심 수집 로직 (GroupIBCollector 클래스)
│   └── config.py                # 설정 관리
├── tests/
│   └── test_collector.py        # 단위 테스트
├── data/
│   ├── seq_update.json          # 마지막 seqUpdate 값 저장
│   ├── seq_update.json.bak      # 백업 파일
│   ├── outputs/                 # 수집 데이터 (JSON Lines 형식)
│   └── pdfs/                    # 다운로드된 PDF
└── logs/
    └── app.log                  # 실행 로그
```

## 엔드포인트 추가

`list.csv`에 새로운 엔드포인트 행 추가:

```csv
https://tap.group-ib.com/api/v2/새로운/엔드포인트/updated,limit=100
```

포맷: `URL,파라미터`

## 주요 메커니즘

### seqUpdate
Group-IB API의 증분 수집 메커니즘. API 응답의 최상위 `seqUpdate` 필드 값을 저장하여 다음 요청 시 파라미터로 전달하면, 마지막 seqUpdate 이후의 신규 데이터만 반환받습니다.

### 재시도 로직
네트워크 타임아웃, 5xx 서버 오류, 429 Rate Limit 오류 시 자동으로 재시도합니다. 기본 설정은 최대 3회입니다.

### 원자적 파일 쓰기
seqUpdate 저장 시 먼저 임시 파일(`.tmp`)에 쓴 후, rename 연산으로 실제 파일로 교체합니다. 프로세스 중단 시에도 데이터 손실을 방지합니다.

## 데이터 초기화

처음부터 다시 수집하려면:

```bash
# data 폴더 전체 삭제
rm -rf data

# main.py 실행 (새로운 data 폴더 자동 생성, 전체 데이터 수집)
python main.py
```

## 로그 확인

```bash
# 실시간 로그 확인
tail -f logs/app.log

# 전체 로그 조회
cat logs/app.log
```

## 개발자 가이드

자세한 아키텍처, 코딩 컨벤션, 개발 팁은 [CLAUDE.md](./CLAUDE.md) 참조.

## 라이센스

[라이센스 정보]

## 지원

문제나 제안사항이 있으면 이슈를 등록해주세요.
