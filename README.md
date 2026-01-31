# Group-IB API 크롤러 (GroupIB Crawler)

Group-IB 위협 인텔리전스 API로부터 자동으로 데이터를 수집하는 크롤링 시스템입니다.

## 프로젝트 개요

- **목적**: Group-IB API의 19개 엔드포인트로부터 위협 정보 자동 수집
- **수집 방식**: seqUpdate 메커니즘을 활용한 증분 수집 (중복 방지)
- **저장 형식**: JSON Lines (.jsonl) 형식으로 스트리밍 저장
- **수집 주기**: 30분 간격 반복 수집
- **인증 방식**: HTTP Basic Authentication (username:api_key)

## 시스템 아키텍처

```
Group-IB API (19개 엔드포인트)
         ↓ HTTPS/REST (Basic Auth)
   Collector (인증, 요청, seqUpdate 관리)
         ↓
   JSON Storage (.jsonl 파일)
         ↓
   30분 간격 반복
```

## 디렉토리 구조

```
groupib-crawler/
├── .env                      # API 인증 정보 (username, api_key)
├── .gitignore               # git 제외 설정
├── README.md                # 이 파일
├── requirements.txt         # Python 의존성
├── main.py                  # 메인 실행 파일
├── list.csv                 # 19개 엔드포인트 설정
│
├── src/
│   ├── __init__.py
│   └── collector.py         # 핵심 수집 로직
│
├── data/
│   ├── outputs/             # 수집 데이터 저장 (*.jsonl)
│   └── seq_update.json      # seqUpdate 값 저장
│
└── logs/
    └── app.log              # 애플리케이션 로그
```

## 설치 및 설정

### 1단계: 저장소 클론 및 디렉토리 이동

```bash
cd groupib-crawler
```

### 2단계: 의존성 설치

```bash
pip install -r requirements.txt
```

필요한 패키지:
- `python-dotenv==1.0.0` - 환경 변수 관리
- `requests==2.31.0` - HTTP 클라이언트
- `pandas==2.1.4` - CSV 처리

### 3단계: 인증 정보 설정

`.env` 파일에 Group-IB API 인증 정보 입력:

```
username=your-email@example.com
api_key=your-api-key-here
```

### 4단계: 엔드포인트 확인

`list.csv` 파일에 19개 엔드포인트가 설정되어 있습니다. 필요시 엔드포인트를 추가/수정할 수 있습니다.

```csv
endpoint,params
https://tap.group-ib.com/api/v2/apt/threat_actor/updated,limit=100
https://tap.group-ib.com/api/v2/apt/threat/updated,limit=10
...
```

## 실행 방법

### 기본 실행

```bash
python main.py
```

### 백그라운드 실행 (Linux/macOS)

```bash
nohup python main.py > output.log 2>&1 &
```

### 종료 방법

```
Ctrl+C (프로그램이 현재 seqUpdate 값을 저장한 후 종료)
```

## seqUpdate 메커니즘 설명

### seqUpdate란?

seqUpdate는 Group-IB API의 증분 수집 메커니즘입니다. API 응답에서 다음 데이터를 가져올 때 사용할 시퀀스 번호입니다.

### 작동 방식

1. **첫 번째 요청**: seqUpdate=0 (또는 파라미터 없음)
   ```
   GET /api/v2/apt/threat_actor/updated?limit=100&seqUpdate=0
   응답: {"seqUpdate": 12345, "count": 100, "items": [...]}
   ```

2. **seqUpdate 저장**: data/seq_update.json에 12345 저장

3. **두 번째 요청** (30분 후): seqUpdate=12345 사용
   ```
   GET /api/v2/apt/threat_actor/updated?limit=100&seqUpdate=12345
   응답: {"seqUpdate": 12350, "count": 5, "items": [...]}  (신규 5건만)
   ```

4. **반복**: 새로운 seqUpdate 값 저장 후 반복

**이점**:
- 중복 데이터 수집 방지
- 신규 데이터만 증분 수집
- 네트워크 및 API 트래픽 절감

## 데이터 저장 형식

### JSON Lines 파일 (.jsonl)

각 줄이 하나의 JSON 객체로 저장됩니다.

**파일명 규칙**: `/api/v2/apt/threat_actor/updated` → `apt_threat_actor_updated.jsonl`

**저장 위치**: `data/outputs/`

**데이터 형식**:
```json
{"timestamp": "2025-01-31T10:30:45.123Z", "source": "groupib-api", "endpoint": "/api/v2/apt/threat_actor/updated", "seqUpdate": 12345, "data": {...원본_API_응답_데이터...}}
```

**필드 설명**:
- `timestamp` - 수집 시각 (UTC, ISO 8601)
- `source` - 데이터 출처 (고정값: "groupib-api")
- `endpoint` - API 엔드포인트 경로
- `seqUpdate` - 현재 응답의 seqUpdate 값
- `data` - API 응답 원본 데이터 (전체)

## 수집 사이클 및 로깅

### 수집 주기

1. 19개 엔드포인트 순차 수집 (약 5~10분 소요)
2. 각 엔드포인트별 seqUpdate 값 로드
3. API 요청 및 데이터 수집
4. 새로운 seqUpdate 값 저장
5. JSON Lines 파일에 데이터 저장
6. **30분 대기**
7. 1번으로 돌아가서 반복

### 로그 파일

`logs/app.log` 에 다음 정보가 기록됩니다:

```
[2025-01-31 10:00:00] [INFO] ========================================
[2025-01-31 10:00:00] [INFO] Group-IB API 크롤러 시작
[2025-01-31 10:00:00] [INFO] API 인증 중...
[2025-01-31 10:00:01] [INFO] ✓ API 인증 성공
[2025-01-31 10:00:01] [INFO] 19개 엔드포인트 로드 완료
[2025-01-31 10:00:02] [INFO] [1/19] /api/v2/apt/threat_actor/updated
[2025-01-31 10:00:02] [INFO]   seqUpdate: 0 (최초 수집)
[2025-01-31 10:00:03] [INFO]   ✓ 수집 완료: 100건
[2025-01-31 10:00:03] [INFO]   새로운 seqUpdate: 12345
[2025-01-31 10:00:03] [INFO]   저장: data/outputs/apt_threat_actor_updated.jsonl
...
```

## 에러 처리 및 재시도

### 재시도 로직

- **최대 재시도**: 3회
- **재시도 대상**:
  - 네트워크 오류
  - 5xx 서버 오류
  - 타임아웃 (30초)

### Rate Limit 처리 (429)

API 호출 제한에 도달한 경우:
- 1차 재시도: 5초 대기
- 2차 재시도: 10초 대기
- 3차 재시도: 15초 대기

### 클라이언트 오류 (4xx)

401, 404 등의 클라이언트 오류는 재시도하지 않고 로깅 후 다음 엔드포인트로 진행합니다.

## 19개 엔드포인트 목록

| 순번 | 엔드포인트 | Limit | 설명 |
|------|-----------|-------|------|
| 1 | /api/v2/apt/threat_actor/updated | 100 | APT 위협 행위자 |
| 2 | /api/v2/apt/threat/updated | 10 | APT 위협 |
| 3 | /api/v2/hi/threat_actor/updated | 100 | 해킹 인텔리전스 위협 행위자 |
| 4 | /api/v2/hi/threat/updated | 10 | 해킹 인텔리전스 위협 |
| 5 | /api/v2/hi/open_threats/updated | 100 | 공개 위협 |
| 6 | /api/v2/hi/analytic/updated | 500 | 해킹 인텔리전스 분석 |
| 7 | /api/v2/ioc/common/updated | 5000 | 일반 IoC |
| 8 | /api/v2/malware/cnc/updated | 1000 | 멀웨어 C&C 서버 |
| 9 | /api/v2/malware/malware/malware/updated | 100 | 멀웨어 정보 |
| 10 | /api/v2/osi/vulnerability/updated | 200 | 취약점 |
| 11 | /api/v2/compromised/discord/updated | 100 | 손상된 Discord |
| 12 | /api/v2/compromised/messenger/updated | 100 | 손상된 Messenger |
| 13 | /api/v2/compromised/access/updated | 500 | 손상된 접근 정보 |
| 14 | /api/v2/compromised/account_group/updated | 500 | 손상된 계정 그룹 |
| 15 | /api/v2/osi/git_repository/updated | 500 | Git 저장소 |
| 16 | /api/v2/osi/public_leak/updated | 100 | 공개 유출 정보 |
| 17 | /api/v2/attacks/ddos/updated | 5000 | DDoS 공격 |
| 18 | /api/v2/attacks/phishing_group/updated | 1000 | 피싱 그룹 |
| 19 | /api/v2/suspicious_ip/scanner/updated | 500 | 의심 IP 스캐너 |

## 보안 주의사항

- `.env` 파일에는 API 키 등 민감 정보가 포함되어 있습니다.
- `.gitignore`에 `.env`가 추가되어 있으므로 git에 커밋되지 않습니다.
- 로그 파일에는 API 키가 기록되지 않습니다.
- API 인증 정보는 절대 소스 코드에 하드코딩하지 마세요.

## 성능 및 리소스

### Rate Limiting

- API 요청 간 최소 1초 간격
- 429 응답 시 지수 백오프 (5초, 10초, 15초)
- 사이클 간 30분 대기

### 메모리 관리

- seqUpdate 기반 증분 수집으로 필요한 데이터만 수집
- JSON Lines append 모드로 메모리 효율적 저장
- 각 엔드포인트별 독립 처리

### 디스크 공간

JSON Lines 파일이 누적되므로 정기적 정리 권장:

```bash
# 예: 30일 이상 된 파일 삭제
find data/outputs -name "*.jsonl" -mtime +30 -delete
```

## 트러블슈팅

### 인증 실패 (401 에러)

- `.env` 파일에 올바른 username과 api_key 입력 확인
- API 키 만료 여부 확인
- Group-IB 계정 상태 확인

### 네트워크 오류

- 인터넷 연결 상태 확인
- 방화벽 설정 확인
- Group-IB API 서버 상태 확인

### 데이터가 저장되지 않음

- `data/outputs/` 디렉토리 존재 및 쓰기 권한 확인
- 로그 파일 (`logs/app.log`) 확인하여 에러 메시지 확인

## 향후 확장 계획

### 예정된 기능

- Kafka Producer 통합 (JSON Lines 데이터를 Kafka로 전송)
- 웹 대시보드 (수집 상태 모니터링)
- 알림 시스템 (Slack, Email)
- Docker 컨테이너화

## 라이선스 및 문의

- 프로젝트: Group-IB API 크롤러
- 개발자: [개발자 정보]
- 문의: [문의 정보]

## 참고 자료

- [Group-IB API 공식 문서](https://api.group-ib.com)
- [seqUpdate 메커니즘 설명](https://api.group-ib.com/docs/sequpdate)
- [JSON Lines 포맷](https://jsonlines.org)

---

**마지막 업데이트**: 2025년 1월 31일
