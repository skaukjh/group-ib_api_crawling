# Group-IB API 크롤러 구현 명세서

이 문서는 api-crawler-builder 에이전트가 코드를 구현할 때 참고할 상세한 기술 명세입니다.

---

## 목차

1. [구현 개요](#1-구현-개요)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [핵심 모듈 명세](#3-핵심-모듈-명세)
4. [데이터 구조 및 인터페이스](#4-데이터-구조-및-인터페이스)
5. [API 명세](#5-api-명세)
6. [비즈니스 로직](#6-비즈니스-로직)
7. [에러 처리](#7-에러-처리)
8. [구현 체크리스트](#8-구현-체크리스트)

---

## 1. 구현 개요

### 목표
Group-IB API의 19개 엔드포인트로부터 seqUpdate 메커니즘을 활용한 증분 데이터 수집 시스템 구축

### 기술 스택
- **언어**: Python 3.8+
- **HTTP 클라이언트**: requests==2.31.0
- **CSV 처리**: pandas==2.1.4
- **환경 변수**: python-dotenv==1.0.0
- **내장 라이브러리**: base64, json, time, logging, os

### 핵심 특징
- Basic Authentication (username:api_key)
- seqUpdate 기반 증분 수집
- JSON Lines 형식 저장
- 30분 간격 반복 수집
- 재시도 로직 (3회, exponential backoff)
- 포괄적 로깅 및 에러 처리

---

## 2. 프로젝트 구조

### 디렉토리 레이아웃

```
groupib-crawler/
├── .env                           # 인증 정보 (git 제외)
├── .gitignore                    # git 제외 설정
├── README.md                     # 사용자 문서
├── requirements.txt              # 의존성
├── IMPLEMENTATION_SPEC.md        # 이 파일
├── main.py                       # 엔트리 포인트
├── list.csv                      # 19개 엔드포인트 설정
│
├── src/
│   ├── __init__.py
│   └── collector.py              # 핵심 수집 로직 (단일 모듈)
│
├── data/
│   ├── outputs/                  # JSON Lines 파일 저장
│   │   └── *.jsonl              # 엔드포인트별 데이터 파일
│   └── seq_update.json           # seqUpdate 상태 저장
│
└── logs/
    └── app.log                   # 애플리케이션 로그
```

### 파일별 책임

| 파일 | 책임 | 라인 수 예상 |
|------|------|-----------|
| main.py | Collector 초기화, 무한 루프, KeyboardInterrupt 처리 | 100-150 |
| src/collector.py | API 인증, 요청, seqUpdate 관리, 데이터 저장, 로깅 | 500-700 |
| list.csv | 19개 엔드포인트 URL, 파라미터 설정 | 20행 |
| .env | API 인증 정보 | 2행 |

---

## 3. 핵심 모듈 명세

### 3.1 src/collector.py

#### 클래스: GroupIBCollector

```python
class GroupIBCollector:
    """Group-IB API 데이터 수집 클래스"""

    def __init__(self):
        """초기화
        - 환경 변수 로드 (.env)
        - 로거 설정
        - 디렉토리 생성 (data/, data/outputs/, logs/)
        """

    def authenticate(self) -> bool:
        """API 인증 확인
        - 엔드포인트: GET https://tap.group-ib.com/api/v2/user/granted_collections
        - 성공 조건: HTTP 200
        - 반환: True (성공) / False (실패)
        """

    def load_endpoints(self) -> List[Dict[str, str]]:
        """list.csv에서 엔드포인트 로드
        - 파일 위치: main.py와 동일 디렉토리의 list.csv
        - 반환: [
            {
              'url': 'https://tap.group-ib.com/api/v2/apt/threat_actor/updated',
              'endpoint': '/api/v2/apt/threat_actor/updated',
              'params': {'limit': '100'}
            },
            ...
          ]
        """

    def load_seq_update(self) -> Dict[str, int]:
        """data/seq_update.json에서 seqUpdate 값 로드
        - 파일 위치: data/seq_update.json
        - 파일 없으면: 빈 딕셔너리 반환
        - 반환: {'/api/v2/apt/threat_actor/updated': 12345, ...}
        """

    def save_seq_update(self, seq_updates: Dict[str, int]) -> bool:
        """seqUpdate 값을 data/seq_update.json에 저장
        - 입력: {'/api/v2/apt/threat_actor/updated': 12345, ...}
        - 성공 시: True, 실패 시: False
        - 실패해도 프로그램 계속 진행
        """

    def build_auth_header(self) -> Dict[str, str]:
        """Basic Auth 헤더 생성
        - 형식: f"{username}:{api_key}" → Base64 인코딩
        - 반환: {
            'User-Agent': 'Mozilla/5.0...',
            'Authorization': 'Basic xyz==',
            'Accept': '*/*'
          }
        """

    def fetch_api(self, url: str, params: Dict[str, str],
                  retry_count: int = 0) -> Dict or None:
        """API 요청 및 응답 처리
        - 메서드: GET
        - 타임아웃: 30초
        - 파라미터: CSV 파라미터 + seqUpdate
        - 반환: 응답 JSON (dict) 또는 None (실패)
        - 재시도: 최대 3회 (네트워크 오류, 5xx, 타임아웃)
        - Rate Limit (429): 5초, 10초, 15초 대기 후 재시도
        """

    def extract_data_and_seq_update(self, response: Dict,
                                    endpoint: str) -> Tuple[List, int]:
        """응답에서 데이터와 seqUpdate 추출
        - 데이터 필드 우선순위: items → data → results
        - seqUpdate: 응답의 최상위 seqUpdate 필드
        - 반환: (데이터_리스트, seqUpdate_값)
        """

    def url_to_filename(self, endpoint: str) -> str:
        """엔드포인트 경로를 JSON Lines 파일명으로 변환
        - 입력: '/api/v2/apt/threat_actor/updated'
        - 처리:
          1. '/api/v2/' 제거
          2. 슬래시를 언더스코어로 변환
          3. '.jsonl' 확장자 추가
        - 반환: 'apt_threat_actor_updated.jsonl'
        """

    def save_to_jsonl(self, endpoint: str, items: List[Dict],
                      seq_update: int) -> bool:
        """데이터를 JSON Lines 형식으로 저장
        - 파일 위치: data/outputs/{파일명}.jsonl
        - 모드: append
        - 각 줄 형식: {
            'timestamp': '2025-01-31T10:30:45.123Z',
            'source': 'groupib-api',
            'endpoint': '/api/v2/apt/threat_actor/updated',
            'seqUpdate': 12345,
            'data': {...원본_API_응답...}
          }
        - 성공: True, 실패: False
        """

    def collect_single_endpoint(self, endpoint_config: Dict,
                                seq_updates: Dict) -> Tuple[bool, int]:
        """단일 엔드포인트 수집
        - 입력: endpoint_config, 현재 seq_updates
        - 처리:
          1. 저장된 seqUpdate 로드
          2. API 요청
          3. 응답에서 데이터, seqUpdate 추출
          4. JSON Lines 저장
          5. seqUpdate 업데이트
        - 반환: (성공_여부, 수집된_건수)
        """

    def collect_all_endpoints(self) -> Dict[str, int]:
        """모든 엔드포인트 순차 수집
        - 엔드포인트 간 1초 간격
        - 각 엔드포인트마다 로깅
        - 실패한 엔드포인트도 계속 진행
        - 반환: 최종 seq_updates 딕셔너리
        """
```

#### 예외 클래스

```python
class GroupIBAPIError(Exception):
    """API 요청 기본 예외"""

class AuthenticationError(GroupIBAPIError):
    """인증 실패 (401)"""

class RateLimitError(GroupIBAPIError):
    """Rate Limit 초과 (429)"""
```

#### 로깅 설정

```python
# 파일과 콘솔 동시 출력
# 형식: [2025-01-31 10:30:45] [INFO] 메시지
# 파일: logs/app.log
```

---

## 4. 데이터 구조 및 인터페이스

### 4.1 환경 변수 (.env)

```
username=skaukjh@fsec.or.kr
api_key=duYbH1cICqGWaOuMGEyiQMOQp719mDQM
```

### 4.2 엔드포인트 설정 (list.csv)

```csv
endpoint,params
https://tap.group-ib.com/api/v2/apt/threat_actor/updated,limit=100
https://tap.group-ib.com/api/v2/apt/threat/updated,limit=10
...
```

**파라미터 형식**:
- 단일: `limit=100`
- 다중: `key1=value1&key2=value2`

### 4.3 seqUpdate 저장 (data/seq_update.json)

```json
{
  "/api/v2/apt/threat_actor/updated": 12345,
  "/api/v2/apt/threat/updated": 67890,
  "/api/v2/hi/threat_actor/updated": 11111
}
```

**특징**:
- 각 엔드포인트별 독립 관리
- 파일 없으면 자동 생성
- 초기값: 각 엔드포인트 0

### 4.4 JSON Lines 출력 (data/outputs/*.jsonl)

각 줄의 형식:

```json
{
  "timestamp": "2025-01-31T10:30:45.123Z",
  "source": "groupib-api",
  "endpoint": "/api/v2/apt/threat_actor/updated",
  "seqUpdate": 12345,
  "data": {...원본_API_응답_전체...}
}
```

---

## 5. API 명세

### 5.1 Group-IB API 엔드포인트

**기본 URL**: `https://tap.group-ib.com`

**인증**: HTTP Basic Authentication
- Header: `Authorization: Basic {base64(username:api_key)}`

**요청 예시**:
```
GET /api/v2/apt/threat_actor/updated?limit=100&seqUpdate=12345
Headers:
  User-Agent: Mozilla/5.0...
  Authorization: Basic xyz==
  Accept: */*
```

**응답 형식** (예상):
```json
{
  "seqUpdate": 12350,
  "count": 5,
  "items": [
    {...},
    {...}
  ]
}
```

**주요 특성**:
- 메서드: GET
- 타임아웃: 30초
- seqUpdate 필드 반드시 포함
- items, data, results 중 하나가 데이터 필드

### 5.2 인증 검증 엔드포인트

```
GET https://tap.group-ib.com/api/v2/user/granted_collections
```

- 성공: HTTP 200
- 실패: HTTP 401 또는 타임아웃

---

## 6. 비즈니스 로직

### 6.1 수집 사이클

```
루프:
  1. 19개 엔드포인트 순차 처리
  2. 각 엔드포인트:
     a. 저장된 seqUpdate 로드 (기본값: 0)
     b. API 요청 (seqUpdate 포함)
     c. 응답에서 데이터 및 seqUpdate 추출
     d. JSON Lines 파일에 저장 (append)
     e. seqUpdate 업데이트 (성공한 경우만)
  3. 모든 엔드포인트 완료 후 30분 대기
  4. 1번으로 돌아가서 반복

무한 루프이므로 KeyboardInterrupt (Ctrl+C)로만 종료 가능
```

### 6.2 seqUpdate 메커니즘

```
첫 번째 사이클:
  요청: seqUpdate=0
  응답: seqUpdate=12345, items=[...100건...]
  저장: seq_update.json에 12345 저장

두 번째 사이클 (30분 후):
  요청: seqUpdate=12345
  응답: seqUpdate=12350, items=[...5건...] (신규만)
  저장: seq_update.json에 12350 저장

장점:
  - 중복 수집 방지
  - 증분 데이터만 수집
  - 네트워크 효율성
```

### 6.3 재시도 로직

```
요청 실패 시:
  - 네트워크 오류 (ConnectionError, Timeout)
  - 5xx 서버 오류 (500, 502, 503, ...)
  → 최대 3회 재시도
  → 매 재시도마다 1초 증가 (1초, 2초, 3초)

Rate Limit (429):
  → 1차: 5초 대기 후 재시도
  → 2차: 10초 대기 후 재시도
  → 3차: 15초 대기 후 재시도

클라이언트 오류 (4xx):
  - 401 (인증 실패): 즉시 중단
  - 404, 400 등: 로깅 후 다음 엔드포인트 진행
```

### 6.4 엔드포인트 간 간격

- 각 요청 간: 1초 (Rate Limit 방지)
- 사이클 간: 30분

---

## 7. 에러 처리

### 7.1 에러 전략

| 에러 종류 | 처리 방식 | 재시도 |
|---------|---------|--------|
| 네트워크 오류 (ConnectionError, Timeout) | 로그 + 재시도 | ○ (3회) |
| 5xx 서버 오류 | 로그 + 재시도 | ○ (3회) |
| 429 Rate Limit | 로그 + exponential backoff + 재시도 | ○ (3회) |
| 401 인증 오류 | 로그 + 프로그램 종료 | ✗ |
| 404, 400 등 4xx | 로그 + 다음 엔드포인트 진행 | ✗ |
| 파일 저장 실패 | 로그 + 계속 진행 | ✗ |
| seqUpdate 저장 실패 | 로그 + 계속 진행 | ✗ |

### 7.2 로깅 레벨

```
[INFO]   - 정상 작동 (인증 성공, 데이터 수집, 대기 시작 등)
[WARNING] - 복구 가능한 에러 (Rate Limit, 재시도)
[ERROR]   - 복구 불가능한 에러 (인증 실패, 파일 저장 실패)
```

### 7.3 로그 항목

```
✓ 인증 성공/실패
✓ 엔드포인트 수집 시작/완료
✓ seqUpdate 값 변화 (이전 → 현재)
✓ 수집된 데이터 개수
✓ API 요청 성공/실패 (URL, 상태 코드)
✓ 파일 저장 성공/실패 (파일명)
✓ 재시도 시도 (횟수, 대기 시간)
✓ 30분 대기 시작/종료
✓ 프로그램 시작/종료
```

---

## 8. 구현 체크리스트

### Phase 1: 프로젝트 구조 및 설정

- [ ] .gitignore 생성 (.env, __pycache__, logs/, data/)
- [ ] requirements.txt 생성 (3가지 의존성)
- [ ] 디렉토리 구조 생성
  - [ ] src/
  - [ ] data/outputs/
  - [ ] logs/

### Phase 2: collector.py 구현

- [ ] GroupIBCollector 클래스 생성
- [ ] __init__ 메서드
  - [ ] .env 파일 로드 (python-dotenv)
  - [ ] 로거 설정
  - [ ] 디렉토리 생성
- [ ] authenticate() 메서드
  - [ ] GET /api/v2/user/granted_collections 요청
  - [ ] 인증 성공 여부 확인
  - [ ] 실패 시 예외 발생
- [ ] load_endpoints() 메서드
  - [ ] list.csv 파싱 (pandas)
  - [ ] 엔드포인트 URL 추출
  - [ ] 파라미터 파싱 (key=value 형식)
- [ ] load_seq_update() 메서드
  - [ ] data/seq_update.json 로드
  - [ ] 파일 없으면 빈 딕셔너리 반환
- [ ] save_seq_update() 메서드
  - [ ] data/seq_update.json 저장
  - [ ] 실패 시 로그만 남기고 계속 진행
- [ ] build_auth_header() 메서드
  - [ ] Base64 인코딩
  - [ ] Authorization 헤더 생성
  - [ ] User-Agent, Accept 헤더 추가
- [ ] fetch_api() 메서드
  - [ ] HTTP GET 요청
  - [ ] 타임아웃 30초 설정
  - [ ] 응답 JSON 파싱
  - [ ] 재시도 로직 (3회)
  - [ ] Rate Limit 처리 (429)
  - [ ] 에러 처리 및 로깅
- [ ] extract_data_and_seq_update() 메서드
  - [ ] items/data/results 필드 확인
  - [ ] seqUpdate 필드 추출
  - [ ] 데이터 리스트 반환
- [ ] url_to_filename() 메서드
  - [ ] /api/v2/ 제거
  - [ ] 슬래시를 언더스코어로 변환
  - [ ] .jsonl 확장자 추가
- [ ] save_to_jsonl() 메서드
  - [ ] JSON Lines 형식으로 저장
  - [ ] append 모드
  - [ ] timestamp (UTC, ISO 8601)
  - [ ] source, endpoint, seqUpdate, data 필드 포함
- [ ] collect_single_endpoint() 메서드
  - [ ] seqUpdate 로드
  - [ ] API 요청
  - [ ] 응답 처리
  - [ ] 파일 저장
  - [ ] seqUpdate 업데이트
- [ ] collect_all_endpoints() 메서드
  - [ ] 19개 엔드포인트 순차 처리
  - [ ] 각 요청 간 1초 간격
  - [ ] 로깅
  - [ ] 실패 시에도 계속 진행

### Phase 3: main.py 구현

- [ ] GroupIBCollector 임포트
- [ ] main() 함수
  - [ ] Collector 초기화
  - [ ] 인증 확인
  - [ ] 엔드포인트 로드
  - [ ] seqUpdate 로드
  - [ ] 무한 루프
    - [ ] collect_all_endpoints() 호출
    - [ ] seqUpdate 저장
    - [ ] 30분 대기 (로깅)
  - [ ] KeyboardInterrupt 처리
    - [ ] seqUpdate 최종 저장
    - [ ] 종료 메시지 출력
- [ ] __name__ == '__main__' 확인

### Phase 4: 테스트 및 검증

- [ ] .env 파일 설정 확인
- [ ] list.csv 19개 엔드포인트 확인
- [ ] python main.py 실행
- [ ] 인증 성공 확인
- [ ] 19개 엔드포인트 수집 확인
- [ ] data/outputs/ 파일 생성 확인
- [ ] data/seq_update.json 업데이트 확인
- [ ] logs/app.log 로그 확인
- [ ] 30분 대기 확인
- [ ] Ctrl+C 종료 확인
- [ ] 에러 처리 테스트 (Rate Limit, 타임아웃 등)

---

## 부록: 19개 엔드포인트 목록

| # | 엔드포인트 | Limit |
|---|-----------|-------|
| 1 | /api/v2/apt/threat_actor/updated | 100 |
| 2 | /api/v2/apt/threat/updated | 10 |
| 3 | /api/v2/hi/threat_actor/updated | 100 |
| 4 | /api/v2/hi/threat/updated | 10 |
| 5 | /api/v2/hi/open_threats/updated | 100 |
| 6 | /api/v2/hi/analytic/updated | 500 |
| 7 | /api/v2/ioc/common/updated | 5000 |
| 8 | /api/v2/malware/cnc/updated | 1000 |
| 9 | /api/v2/malware/malware/malware/updated | 100 |
| 10 | /api/v2/osi/vulnerability/updated | 200 |
| 11 | /api/v2/compromised/discord/updated | 100 |
| 12 | /api/v2/compromised/messenger/updated | 100 |
| 13 | /api/v2/compromised/access/updated | 500 |
| 14 | /api/v2/compromised/account_group/updated | 500 |
| 15 | /api/v2/osi/git_repository/updated | 500 |
| 16 | /api/v2/osi/public_leak/updated | 100 |
| 17 | /api/v2/attacks/ddos/updated | 5000 |
| 18 | /api/v2/attacks/phishing_group/updated | 1000 |
| 19 | /api/v2/suspicious_ip/scanner/updated | 500 |
