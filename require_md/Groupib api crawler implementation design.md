---
## 1. 프로젝트 개요

### 1.1 배경 및 목적
Group-IB는 위협 인텔리전스 전문 플랫폼으로, REST API를 통해 다양한 위협 정보를 제공합니다. 본 프로젝트는 이 API를 활용하여 위협 정보를 자동으로 수집하는 크롤링 모듈을 구축하는 것을 목표로 합니다.

**핵심 목표:**
- Group-IB API로부터 위협 정보 자동 수집
- seqUpdate 메커니즘을 활용한 증분 데이터 수집
- 수집된 데이터를 JSON Lines 형식으로 저장
- 30분 간격 주기적 수집
- 향후 대규모 시스템의 한 모듈로 통합 가능한 구조

### 1.2 범위
**포함 사항:**
- Basic 인증 방식 API 연결
- 19개 엔드포인트 데이터 수집
- seqUpdate 기반 증분 수집
- JSON Lines 형식 데이터 저장
- 30분 간격 반복 수집
- 에러 핸들링 및 재시도 로직

**제외 사항 (향후 확장):**
- Kafka Producer 통합
- 데이터베이스 직접 연동
- 웹 대시보드
- 알림 시스템

---

## 2. 시스템 설계

### 2.1 아키텍처 개요
```
┌─────────────────┐
│  Group-IB API   │ (19개 엔드포인트)
└────────┬────────┘
         │ HTTPS/REST (Basic Auth)
         ▼
┌─────────────────┐
│   Collector     │ (인증, 요청, seqUpdate 관리)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  JSON Storage   │ (.jsonl 파일)
└────────┬────────┘
         │
         │ 30분 간격 반복
         └──────────┐
                    ▼
              (다음 수집 사이클)
```

### 2.2 디렉토리 구조
```
groupib-crawler/
├── .env                    # API 인증 정보
├── .gitignore
├── README.md
├── requirements.txt
├── main.py                 # 메인 실행 파일
├── list.csv                # 엔드포인트 설정 (URL, 파라미터)
│
├── src/
│   ├── __init__.py
│   └── collector.py        # 핵심 수집 로직 (단일 모듈)
│
├── data/
│   ├── outputs/            # 수집 데이터 저장
│   │   └── *.jsonl         # JSON Lines 파일
│   └── seq_update.json     # seqUpdate 값 저장
│
└── logs/
    └── app.log             # 애플리케이션 로그
```

### 2.3 모듈 책임

#### collector.py (단일 모듈)
- API Basic 인증 관리
- list.csv 파싱
- HTTP 요청 및 응답 처리
- seqUpdate 값 관리 (저장/로드)
- 데이터 추출 및 JSON Lines 저장
- 30분 간격 반복 수집
- 에러 핸들링 및 재시도
- 로깅

#### main.py
- Collector 초기화 및 실행
- 무한 루프로 30분 간격 수집

---

## 3. 기능 요구사항 (Functional Requirements)

### 3.1 FR-1: API 인증

#### FR-1.1 환경 변수 관리
- `.env` 파일에서 인증 정보 로드
- 필요 정보:
  ```
  username=skaukjh@fsec.or.kr
  api_key=duYbH1cICqGWaOuMGEyiQMOQp719mDQM
  ```
- `python-dotenv` 라이브러리 사용

#### FR-1.2 Basic 인증 구현
**인증 방식**: HTTP Basic Authentication
```python
# 구현 예시 (실제 구현은 Claude Code가 수행)
auth_byte = f"{username}:{api_key}".encode("ascii")
auth_b64 = base64.b64encode(auth_byte)
auth_b64_str = auth_b64.decode("ascii")
auth_result = f"Basic {auth_b64_str}"

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54",
    "Authorization": auth_result,
    "Accept": "*/*"
}
```

#### FR-1.3 인증 검증
- **검증 엔드포인트**: `GET https://tap.group-ib.com/api/v2/user/granted_collections`
- **성공 조건**: HTTP 200 응답
- **실패 처리**: 에러 로깅 및 프로그램 종료

---

### 3.2 FR-2: 엔드포인트 설정 로드

#### FR-2.1 CSV 파일 파싱
- **파일 위치**: `list.csv` (main.py와 동일 디렉토리)
- **파일 형식**:
  ```csv
  API_PATH,input_param
  https://tap.group-ib.com/api/v2/apt/threat_actor/updated,limit=100
  https://tap.group-ib.com/api/v2/apt/threat/updated,limit=10
  ...
  ```
- **총 엔드포인트 수**: 19개

#### FR-2.2 파라미터 파싱
- `input_param` 형식: `key1=value1&key2=value2` 또는 `key=value`
- 딕셔너리로 변환: `{"limit": "100"}` 또는 `{"limit": "10"}`
- 추가 파라미터 `seqUpdate`는 동적으로 관리

#### FR-2.3 엔드포인트 리스트
```
1. /api/v2/apt/threat_actor/updated (limit=100)
2. /api/v2/apt/threat/updated (limit=10)
3. /api/v2/hi/threat_actor/updated (limit=100)
4. /api/v2/hi/threat/updated (limit=10)
5. /api/v2/hi/open_threats/updated (limit=100)
6. /api/v2/hi/analytic/updated (limit=500)
7. /api/v2/ioc/common/updated (limit=5000)
8. /api/v2/malware/cnc/updated (limit=1000)
9. /api/v2/malware/malware/malware/updated (limit=100)
10. /api/v2/osi/vulnerability/updated (limit=200)
11. /api/v2/compromised/discord/updated (limit=100)
12. /api/v2/compromised/messenger/updated (limit=100)
13. /api/v2/compromised/access/updated (limit=500)
14. /api/v2/compromised/account_group/updated (limit=500)
15. /api/v2/osi/git_repository/updated (limit=500)
16. /api/v2/osi/public_leak/updated (limit=100)
17. /api/v2/attacks/ddos/updated (limit=5000)
18. /api/v2/attacks/phishing_group/updated (limit=1000)
19. /api/v2/suspicious_ip/scanner/updated (limit=500)
```
---

### 3.3 FR-3: seqUpdate 메커니즘

#### FR-3.1 seqUpdate 개념
**공식 설명**:
> Sequence update number to get the next data chunk. Use this parameter to iterate through feeds. The value should be obtained from the previous response's top-level seqUpdate field or from /api/v2/sequence_list endpoint. Important: Always use the top-level seqUpdate field for iteration. (Default: 0)

**동작 방식**:
- 첫 요청: `seqUpdate=0` (또는 파라미터 없음, 기본값 0)
- API 응답의 최상위 `seqUpdate` 필드 값 추출
- 다음 요청 시 이전 `seqUpdate` 값 사용
- 신규 데이터만 증분 수집

#### FR-3.2 seqUpdate 저장 및 로드
- **저장 위치**: `data/seq_update.json`
- **저장 형식**:
  ```json
  {
    "/api/v2/apt/threat_actor/updated": 12345,
    "/api/v2/apt/threat/updated": 67890,
    ...
  }
  ```
- **초기값**: 각 엔드포인트별 `0`
- **업데이트 시점**: API 응답 성공 후 즉시 저장

#### FR-3.3 seqUpdate 사용 예시
```
1차 요청: GET /api/v2/apt/threat_actor/updated?limit=100&seqUpdate=0
응답: {"seqUpdate": 12345, "count": 100, "items": [...]}
→ seq_update.json에 12345 저장

2차 요청 (30분 후): GET /api/v2/apt/threat_actor/updated?limit=100&seqUpdate=12345
응답: {"seqUpdate": 12350, "count": 5, "items": [...]}  (신규 5건만)
→ seq_update.json에 12350 저장
```
---

### 3.4 FR-4: 데이터 수집

#### FR-4.1 API 요청
- **메서드**: GET
- **타임아웃**: 30초
- **헤더**: Basic Auth 포함
- **파라미터**: 
  - CSV에서 로드한 파라미터 (예: `limit=100`)
  - `seqUpdate` 값 (저장된 값 또는 0)

#### FR-4.2 응답 처리
- **성공 조건**: HTTP 200
- **응답 구조 (예상)**:
  ```json
  {
    "seqUpdate": 12345,
    "count": 100,
    "items": [...]  // 또는 "data", "results" 등
  }
  ```
- **데이터 추출**: `items`, `data`, `results` 필드 우선 확인
- **seqUpdate 추출**: 최상위 `seqUpdate` 필드 값

#### FR-4.3 재시도 로직
- **최대 재시도**: 3회
- **재시도 대상**: 
  - 네트워크 오류
  - 5xx 서버 오류
  - 타임아웃
- **Rate Limit (429) 처리**: 
  - 1차: 5초 대기 후 재시도
  - 2차: 10초 대기 후 재시도
  - 3차: 15초 대기 후 재시도
- **재시도 제외**: 4xx 클라이언트 오류 (401, 404 등)

---

### 3.5 FR-5: 데이터 저장

#### FR-5.1 JSON Lines 형식
- **파일명 규칙**: URL 경로를 파일명으로 변환
  - 예: `/api/v2/apt/threat_actor/updated` → `apt_threat_actor_updated.jsonl`
  - 특수문자 제거, 슬래시를 언더스코어로 변환
- **파일 위치**: `data/outputs/`
- **저장 모드**: append (누적 저장)

#### FR-5.2 데이터 포맷
```json
{"timestamp": "2025-01-31T10:30:45.123Z", "source": "groupib-api", "endpoint": "/api/v2/apt/threat_actor/updated", "seqUpdate": 12345, "data": {...원본_데이터...}}
```

**필드 설명**:
- `timestamp`: 수집 시각 (UTC, ISO 8601)
- `source`: 데이터 출처 (고정값: "groupib-api")
- `endpoint`: API 엔드포인트 경로
- `seqUpdate`: 현재 응답의 seqUpdate 값
- `data`: API 응답 원본 데이터 (필터링 없이 전체)

---

### 3.6 FR-6: 반복 수집 (30분 간격)

#### FR-6.1 수집 사이클
1. 19개 엔드포인트 순차 수집
2. 각 엔드포인트별 seqUpdate 값 로드
3. API 요청 및 데이터 수집
4. 새로운 seqUpdate 값 저장
5. JSON Lines 파일에 데이터 저장
6. 다음 엔드포인트로 이동
7. 모든 엔드포인트 완료 후 30분 대기
8. 1번으로 돌아가서 반복

#### FR-6.2 엔드포인트 간 간격
- **각 요청 간 간격**: 1초 (Rate Limit 방지)
- **사이클 간 대기**: 30분

#### FR-6.3 무한 루프
- 프로그램은 수동 종료 전까지 계속 실행
- `Ctrl+C` (KeyboardInterrupt)로 종료 가능
- 종료 시 현재 seqUpdate 값 저장 확인

---

## 4. 비기능 요구사항 (Non-Functional Requirements)

### 4.1 로깅 (NFR-1)
**요구사항:**
- 모든 주요 작업에 대한 로깅
- 파일 및 콘솔 동시 출력
- 로그 레벨: INFO, WARNING, ERROR
- 타임스탬프 포함

**로그 출력 형식:**
```
[2025-01-31 10:30:45] [INFO] API 인증 성공
[2025-01-31 10:30:46] [INFO] 엔드포인트 수집: /api/v2/apt/threat_actor/updated
[2025-01-31 10:30:47] [INFO] seqUpdate: 12345 → 12350 (신규 5건)
[2025-01-31 10:30:48] [ERROR] 요청 실패: /api/v2/test - Status 404
```

**로그 파일 위치:**
- `logs/app.log`

**필수 로깅 항목:**
- 인증 성공/실패
- 각 엔드포인트 수집 시작/완료
- seqUpdate 값 변화 (이전 → 현재)
- 수집된 데이터 개수
- API 요청 성공/실패 (URL, 상태 코드)
- 파일 저장 성공/실패
- 에러 발생 시 스택 트레이스
- 30분 대기 시작/종료

---

### 4.2 에러 처리 (NFR-2)

#### 커스텀 예외 클래스
```python
class GroupIBAPIError(Exception):
    """API 요청 기본 에러"""

class AuthenticationError(GroupIBAPIError):
    """인증 실패"""

class RateLimitError(GroupIBAPIError):
    """API 호출 제한"""
```

#### 에러 처리 전략
- **네트워크 오류**: 재시도 (최대 3회, exponential backoff)
- **인증 오류 (401)**: 즉시 중단, 사용자에게 알림
- **Rate Limit (429)**: 대기 후 재시도 (5초, 10초, 15초)
- **클라이언트 오류 (4xx)**: 로깅 후 다음 엔드포인트 진행
- **서버 오류 (5xx)**: 재시도
- **파싱 오류**: 로깅 후 스킵 (전체 중단하지 않음)
- **seqUpdate 저장 실패**: 로깅 후 계속 진행 (다음 사이클에서 재시도)

---

### 4.3 성능 및 리소스 관리 (NFR-3)

**Rate Limiting:**
- API 요청 간 최소 1초 간격
- 429 응답 시 지수 백오프
- 사이클 간 30분 대기

**메모리 관리:**
- seqUpdate 기반 증분 수집으로 필요한 데이터만 가져옴
- JSON Lines append 모드 (메모리 효율적)
- 각 엔드포인트별 독립 처리

**디스크 공간:**
- 로그 파일 자동 로테이션 (권장)
- 데이터 파일 주기적 정리 (수동)

---

### 4.4 보안 (NFR-4)

**인증 정보 보호:**
- `.env` 파일 사용
- `.gitignore`에 `.env` 추가
- 소스 코드에 하드코딩 금지

**로그 보안:**
- API 키 로그에 출력 금지
- username은 로그 가능, api_key는 마스킹

---

### 4.5 확장성 (NFR-5)

**모듈화:**
- collector.py: 독립적으로 사용 가능
- 단일 파일로 간결한 구조

**데이터 포맷:**
- JSON Lines 형식으로 스트리밍 처리 가능
- Kafka Producer 추가 용이
- seqUpdate 값 포함으로 추적 가능

**설정 관리:**
- CSV 기반 설정으로 엔드포인트 추가/수정 용이
- 코드 수정 없이 설정 변경 가능

---

## 5. 사용자 시나리오

### 5.1 시나리오: 초기 실행 및 무한 수집

**목적**: 시스템 시작 및 지속적 데이터 수집

**사전 조건:**
- `.env` 파일에 username, api_key 설정
- `list.csv` 파일에 19개 엔드포인트 설정

**실행:**
```bash
python main.py
```

**예상 동작:**
```
[2025-01-31 10:00:00] [INFO] ========================================
[2025-01-31 10:00:00] [INFO] Group-IB API 크롤러 시작
[2025-01-31 10:00:00] [INFO] ========================================
[2025-01-31 10:00:00] [INFO] API 인증 중...
[2025-01-31 10:00:01] [INFO] ✓ API 인증 성공
[2025-01-31 10:00:01] [INFO] 19개 엔드포인트 로드 완료
[2025-01-31 10:00:01] [INFO] seqUpdate 파일 로드: data/seq_update.json

=== 수집 사이클 1 시작 ===
[2025-01-31 10:00:02] [INFO] [1/19] /api/v2/apt/threat_actor/updated
[2025-01-31 10:00:02] [INFO]   seqUpdate: 0 (최초 수집)
[2025-01-31 10:00:03] [INFO]   ✓ 수집 완료: 100건
[2025-01-31 10:00:03] [INFO]   새로운 seqUpdate: 12345
[2025-01-31 10:00:03] [INFO]   저장: data/outputs/apt_threat_actor_updated.jsonl

[2025-01-31 10:00:04] [INFO] [2/19] /api/v2/apt/threat/updated
[2025-01-31 10:00:04] [INFO]   seqUpdate: 0 (최초 수집)
[2025-01-31 10:00:05] [INFO]   ✓ 수집 완료: 10건
[2025-01-31 10:00:05] [INFO]   새로운 seqUpdate: 6789
[2025-01-31 10:00:05] [INFO]   저장: data/outputs/apt_threat_updated.jsonl

... (19개 엔드포인트 모두 수집)

[2025-01-31 10:05:00] [INFO] === 수집 사이클 1 완료 (총 5분 소요) ===
[2025-01-31 10:05:00] [INFO] 다음 사이클까지 30분 대기...

... (30분 대기)

=== 수집 사이클 2 시작 ===
[2025-01-31 10:35:00] [INFO] [1/19] /api/v2/apt/threat_actor/updated
[2025-01-31 10:35:00] [INFO]   seqUpdate: 12345 (증분 수집)
[2025-01-31 10:35:01] [INFO]   ✓ 수집 완료: 5건 (신규)
[2025-01-31 10:35:01] [INFO]   새로운 seqUpdate: 12350
[2025-01-31 10:35:01] [INFO]   저장: data/outputs/apt_threat_actor_updated.jsonl

... (계속 반복)
```

**종료:**
```
^C
[2025-01-31 11:00:00] [INFO] 종료 신호 수신
[2025-01-31 11:00:00] [INFO] seqUpdate 값 최종 저장 중...
[2025-01-31 11:00:00] [INFO] ✓ 프로그램 종료
```

---

### 5.2 시나리오: 백그라운드 실행 (Linux)

**목적**: 서버에서 지속적으로 실행

**실행:**
```bash
nohup python main.py > output.log 2>&1 &
```
---

### 5.3 시나리오: 에러 복구

**상황**: 네트워크 일시적 장애

**동작:**
```
[2025-01-31 10:15:00] [INFO] [5/19] /api/v2/hi/analytic/updated
[2025-01-31 10:15:01] [ERROR] 요청 실패: Connection timeout
[2025-01-31 10:15:01] [INFO] 재시도 1/3 (5초 후)...
[2025-01-31 10:15:06] [INFO] ✓ 재시도 성공: 500건
[2025-01-31 10:15:06] [INFO] 저장: data/outputs/hi_analytic_updated.jsonl
```

**상황**: Rate Limit 초과

**동작:**
```
[2025-01-31 10:20:00] [INFO] [10/19] /api/v2/osi/vulnerability/updated
[2025-01-31 10:20:01] [WARNING] Rate Limit 도달 (429)
[2025-01-31 10:20:01] [INFO] 5초 대기 후 재시도...
[2025-01-31 10:20:06] [INFO] ✓ 재시도 성공: 200건
```

---

## 6. 데이터 명세

### 6.1 입력 데이터

#### .env 파일
```
username=skaukjh@fsec.or.kr
api_key=duYbH1cICqGWaOuMGEyiQMOQp719mDQM
```

#### list.csv 파일 (main.py와 동일 디렉토리)
```csv
API_PATH,input_param
https://tap.group-ib.com/api/v2/apt/threat_actor/updated,limit=100
https://tap.group-ib.com/api/v2/apt/threat/updated,limit=10
.......
```

**필드 설명:**
- `API_PATH`: 전체 API URL (필수)
- `input_param`: 쿼리 파라미터 (형식: `key=value` 또는 `key1=value1&key2=value2`)

---

### 6.2 중간 데이터 (seqUpdate 저장)

#### data/seq_update.json
```json
{
  "/api/v2/apt/threat_actor/updated": 12345,
  "/api/v2/apt/threat/updated": 67890,
  "/api/v2/hi/threat_actor/updated": 11111,
  ...
}
```

**용도**: 각 엔드포인트별 마지막 seqUpdate 값 저장

---

### 6.3 출력 데이터

#### JSON Lines 파일 형식
**파일명**: `{엔드포인트_경로}.jsonl`
- 예: `/api/v2/apt/threat_actor/updated` → `apt_threat_actor_updated.jsonl`

**파일 위치**: `data/outputs/`

**각 줄 형식**:
```json
{"timestamp": "2025-01-31T10:30:45.123Z", "source": "groupib-api", "endpoint": "/api/v2/apt/threat_actor/updated", "seqUpdate": 12345, "data": {...원본_API_응답_데이터...}}
```

**필드 설명:**
- `timestamp`: 수집 시각 (UTC, ISO 8601)
- `source`: 데이터 출처 (고정값: "groupib-api")
- `endpoint`: API 엔드포인트 경로
- `seqUpdate`: 현재 응답의 seqUpdate 값
- `data`: API 응답 원본 데이터 (전체)

---

## 7. 기술 스택

### 7.1 필수 라이브러리
```
python-dotenv==1.0.0    # 환경 변수 관리
requests==2.31.0        # HTTP 클라이언트
pandas==2.1.4           # CSV 처리
```

### 7.2 Python 버전
- Python 3.8 이상

### 7.3 내장 라이브러리 활용
- `base64`: Basic Auth 인코딩
- `json`: JSON 파싱 및 저장
- `time`: sleep, 타임스탬프
- `logging`: 로깅
- `os`: 파일/디렉토리 관리

---

## 8. 제약사항 및 고려사항

### 8.1 API 제약사항
- **인증 방식**: HTTP Basic Authentication (username:api_key)
- **Rate Limit**: API 제공자의 호출 제한 준수 필요 (1초 간격)
- **타임아웃**: 30초 내 응답 없으면 실패 처리
- **seqUpdate 메커니즘**: 반드시 응답의 최상위 seqUpdate 필드 사용

### 8.2 시스템 제약사항
- **디스크 공간**: JSON Lines 파일이 누적되므로 정기적 정리 필요
- **메모리**: seqUpdate 기반 증분 수집으로 효율적
- **네트워크**: 안정적인 인터넷 연결 필요

### 8.3 보안 고려사항
- API 인증 정보를 `.env` 파일로 관리
- `.env` 파일은 절대 버전 관리 시스템에 포함하지 않음
- 로그에 api_key 출력 금지

### 8.4 운영 고려사항
- 30분 간격 수집으로 최신 데이터 유지
- seqUpdate 값 자동 관리로 중복 수집 방지
- 무한 루프 실행으로 지속적 모니터링

---

## 9. 테스트 계획

### 9.1 단위 테스트 항목
- [ ] 환경 변수 로드 (.env)
- [ ] CSV 파일 파싱 (list.csv)
- [ ] Basic Auth 헤더 생성
- [ ] API 요청 성공/실패 처리
- [ ] seqUpdate 값 저장/로드
- [ ] JSON Lines 저장
- [ ] 재시도 로직

### 9.2 통합 테스트 시나리오
1. **인증 테스트**
   - 유효한 인증 정보로 성공
   - 잘못된 인증 정보로 실패

2. **seqUpdate 테스트**
   - 초기 수집 (seqUpdate=0)
   - 증분 수집 (저장된 seqUpdate 사용)
   - seqUpdate 값 저장 확인

3. **데이터 수집 테스트**
   - 19개 엔드포인트 순차 수집
   - JSON Lines 파일 생성 확인
   - seqUpdate 값 업데이트 확인

4. **반복 수집 테스트**
   - 30분 대기 확인
   - 다음 사이클 정상 실행
   - Ctrl+C 종료 확인

5. **에러 처리 테스트**
   - Rate Limit 429 응답
   - 네트워크 타임아웃
   - 5xx 서버 오류
   - 파일 저장 실패

---

## 10. 성공 기준

### 10.1 기능적 성공 기준
- [ ] API 인증 성공
- [ ] 19개 엔드포인트 모두 수집 가능
- [ ] seqUpdate 메커니즘 정상 작동
- [ ] JSON Lines 파일 정상 생성
- [ ] 30분 간격 반복 수집 안정적 작동

### 10.2 품질 기준
- [ ] 데이터 수집 성공률 > 95%
- [ ] API 요청 재시도 정상 작동
- [ ] 에러 발생 시 적절한 로깅
- [ ] seqUpdate 값 정확히 관리
- [ ] 메모리 사용량 안정적 유지

### 10.3 운영 기준
- [ ] 로그 파일 정상 생성
- [ ] 백그라운드 실행 가능
- [ ] Ctrl+C 정상 종료

---

## 11. 향후 확장 계획

### 11.1 Kafka 통합 (예정)
- Kafka Producer 구현
- JSON Lines 데이터를 Kafka 메시지로 전송
- 토픽 명명 규칙: `groupib.{category}.{type}`
  - 예: `groupib.apt.threat_actor`

### 11.2 추가 기능 (검토)
- 웹 대시보드 (수집 상태 모니터링)
- 알림 시스템 (Slack, Email)
- 데이터 검증 및 품질 체크
- Docker 컨테이너화

---

## 부록: Claude Code 구현 가이드

### A.1 구현 순서

**Step 1: 프로젝트 구조 생성**
```
작업:
1. 디렉토리 구조 생성
2. .gitignore 생성 (.env, __pycache__, logs/, data/)
3. requirements.txt 생성
```

**Step 2: collector.py 구현**
```
작업:
1. GroupIBCollector 클래스 생성
2. Basic Auth 구현
3. list.csv 로드 기능
4. seqUpdate 저장/로드 (JSON 파일)
5. API 요청 함수 (재시도 로직 포함)
6. JSON Lines 저장 함수
7. 로깅 설정
```

**Step 3: main.py 구현**
```
작업:
1. Collector 초기화
2. 인증 확인
3. 무한 루프:
   - 19개 엔드포인트 순차 수집
   - 각 엔드포인트별 seqUpdate 로드
   - API 요청 및 데이터 수집
   - seqUpdate 업데이트 및 저장
   - JSON Lines 저장
   - 30분 대기
4. KeyboardInterrupt 처리
```

**Step 4: 테스트**
```
검증:
- python main.py 실행
- 인증 성공 확인
- 19개 엔드포인트 수집 확인
- seqUpdate 값 저장 확인
- JSON Lines 파일 생성 확인
- 30분 대기 확인
- Ctrl+C 종료 확인
```

---

### A.2 구현 시 주의사항

**Basic Auth 구현:**
- username:api_key 형식
- Base64 인코딩
- Authorization 헤더에 "Basic {encoded}" 형식

**seqUpdate 관리:**
- 응답의 **최상위** seqUpdate 필드만 사용
- 각 엔드포인트별로 독립적으로 관리
- 파일 저장 실패 시에도 로그 남기고 계속 진행

**파일명 생성:**
- URL 경로에서 /api/v2/ 제거
- 슬래시(/)를 언더스코어(_)로 변환
- 예: `/api/v2/apt/threat_actor/updated` → `apt_threat_actor_updated.jsonl`

**에러 처리:**
- 개별 엔드포인트 실패 시 전체 중단하지 않음
- 로그 남기고 다음 엔드포인트 진행
- seqUpdate 값은 성공 시에만 업데이트

---

### A.3 README.md 작성 가이드

**포함 내용:**
1. 프로젝트 개요
2. 설치 방법
   ```bash
   pip install -r requirements.txt
   ```
3. 설정 방법
   - .env 파일 생성 (username, api_key)
   - list.csv 확인
4. 실행 방법
   ```bash
   python main.py
   ```
5. seqUpdate 메커니즘 설명
6. 디렉토리 구조 설명