# Group-IB API 크롤러 - 구현 요약

api-crawler-builder 에이전트가 코드를 구현할 때 참고할 요약 문서입니다.
상세한 명세는 `IMPLEMENTATION_SPEC.md` 를 참고하세요.

---

## 핵심 목표

Group-IB API의 19개 엔드포인트로부터 seqUpdate 메커니즘을 활용하여 증분 데이터를 자동으로 수집하고, JSON Lines 형식으로 저장하며, 30분 간격으로 반복 수집하는 시스템 구현.

---

## 기술 스택

- **언어**: Python 3.8+
- **HTTP 클라이언트**: requests==2.31.0
- **CSV 처리**: pandas==2.1.4
- **환경 변수**: python-dotenv==1.0.0
- **내장 라이브러리**: base64, json, time, logging, os

---

## 구현할 항목 (Priority Order)

### 1. src/collector.py - GroupIBCollector 클래스

**책임**: API 인증, 요청, 데이터 저장, seqUpdate 관리

#### 주요 메서드

| 메서드 | 기능 | 중요도 |
|--------|------|--------|
| `__init__()` | 환경 변수 로드, 로거 설정, 디렉토리 생성 | ★★★ |
| `authenticate()` | API 인증 확인 (/api/v2/user/granted_collections) | ★★★ |
| `load_endpoints()` | list.csv 파싱, 엔드포인트 추출 | ★★★ |
| `load_seq_update()` | data/seq_update.json 로드 | ★★★ |
| `save_seq_update()` | seqUpdate 값 저장 | ★★★ |
| `build_auth_header()` | Base64 인코딩된 Basic Auth 헤더 생성 | ★★★ |
| `fetch_api()` | HTTP GET 요청, 재시도 로직 포함 | ★★★ |
| `extract_data_and_seq_update()` | 응답에서 데이터와 seqUpdate 추출 | ★★★ |
| `url_to_filename()` | 엔드포인트 경로 → JSON Lines 파일명 변환 | ★★ |
| `save_to_jsonl()` | 데이터를 JSON Lines 형식으로 저장 | ★★★ |
| `collect_single_endpoint()` | 단일 엔드포인트 수집 | ★★★ |
| `collect_all_endpoints()` | 19개 엔드포인트 순차 수집 | ★★★ |

#### 커스텀 예외 클래스

```python
class GroupIBAPIError(Exception):
    """기본 API 에러"""

class AuthenticationError(GroupIBAPIError):
    """인증 실패 (401)"""

class RateLimitError(GroupIBAPIError):
    """Rate Limit (429)"""
```

---

### 2. main.py - 엔트리 포인트

**책임**: 프로그램 초기화, 무한 루프, KeyboardInterrupt 처리

#### 구조

```python
def main():
    # 1. Collector 초기화
    # 2. 인증 확인
    # 3. 엔드포인트 로드
    # 4. 무한 루프:
    #    - collect_all_endpoints() 호출
    #    - seqUpdate 저장
    #    - 30분 대기
    # 5. KeyboardInterrupt 처리
    #    - seqUpdate 최종 저장
    #    - 종료 메시지

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # 정상 종료 처리
```

---

## 데이터 구조

### 입력 데이터

#### .env 파일
```
username=skaukjh@fsec.or.kr
api_key=duYbH1cICqGWaOuMGEyiQMOQp719mDQM
```

#### list.csv
```csv
endpoint,params
https://tap.group-ib.com/api/v2/apt/threat_actor/updated,limit=100
https://tap.group-ib.com/api/v2/apt/threat/updated,limit=10
...
```

### 중간 데이터

#### data/seq_update.json
```json
{
  "/api/v2/apt/threat_actor/updated": 12345,
  "/api/v2/apt/threat/updated": 67890
}
```

### 출력 데이터

#### data/outputs/*.jsonl (각 줄)
```json
{
  "timestamp": "2025-01-31T10:30:45.123Z",
  "source": "groupib-api",
  "endpoint": "/api/v2/apt/threat_actor/updated",
  "seqUpdate": 12345,
  "data": {...원본_API_응답...}
}
```

---

## 비즈니스 로직

### 수집 주기 (30분 간격)

1. 19개 엔드포인트 순차 처리
2. 각 엔드포인트별 저장된 seqUpdate 로드 (초기값: 0)
3. API 요청 (GET /api/v2/{endpoint}?limit={limit}&seqUpdate={seqUpdate})
4. 응답에서 데이터 및 새로운 seqUpdate 추출
5. JSON Lines 파일에 데이터 저장 (append 모드)
6. seqUpdate 값 업데이트 (성공한 경우만)
7. **30분 대기**
8. 1번으로 돌아가서 반복

### seqUpdate 메커니즘

- **목적**: 중복 데이터 방지, 증분 수집
- **초기값**: 0 (또는 파라미터 없음)
- **저장 위치**: data/seq_update.json (엔드포인트별)
- **사용 방식**: 매 요청에 seqUpdate 파라미터 포함
- **업데이트**: API 응답의 최상위 seqUpdate 필드로 업데이트

### 재시도 로직

| 상황 | 처리 | 재시도 |
|------|------|--------|
| 네트워크 오류 | 로그 + 재시도 | ○ (최대 3회, 1-2-3초) |
| 5xx 서버 오류 | 로그 + 재시도 | ○ (최대 3회, 1-2-3초) |
| 429 Rate Limit | 로그 + exponential backoff | ○ (5초, 10초, 15초) |
| 401 인증 오류 | 로그 + 프로그램 종료 | ✗ |
| 404, 400 등 4xx | 로그 + 다음 엔드포인트 진행 | ✗ |

---

## API 명세

### Group-IB API

**기본 정보**:
- 기본 URL: `https://tap.group-ib.com`
- 인증: HTTP Basic Authentication
- 메서드: GET
- 타임아웃: 30초

**헤더**:
```python
{
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54",
    "Authorization": "Basic {base64(username:api_key)}",
    "Accept": "*/*"
}
```

**인증 검증**:
```
GET /api/v2/user/granted_collections
→ 성공: HTTP 200
→ 실패: HTTP 401 또는 타임아웃
```

**요청 예시**:
```
GET /api/v2/apt/threat_actor/updated?limit=100&seqUpdate=12345
```

**응답 예시**:
```json
{
  "seqUpdate": 12350,
  "count": 5,
  "items": [...]  // 또는 "data", "results"
}
```

---

## 주의사항

### 1. Basic Auth 구현

```python
auth_byte = f"{username}:{api_key}".encode("ascii")
auth_b64 = base64.b64encode(auth_byte)
auth_b64_str = auth_b64.decode("ascii")
auth_result = f"Basic {auth_b64_str}"
```

### 2. seqUpdate 관리

- **응답의 최상위 seqUpdate 필드만 사용** (nested 필드 아님)
- 각 엔드포인트별로 독립 관리
- 파일 저장 실패 시에도 로그 남기고 계속 진행

### 3. 파일명 생성

```
/api/v2/apt/threat_actor/updated
→ apt_threat_actor_updated.jsonl

규칙:
1. "/api/v2/" 제거
2. "/" → "_" 변환
3. ".jsonl" 확장자 추가
```

### 4. 데이터 추출

응답에서 데이터 필드 우선순위:
1. items
2. data
3. results

첫 번째로 존재하는 필드를 사용

### 5. JSON Lines 형식

- 각 줄이 독립적인 JSON 객체
- 반드시 append 모드로 저장 (누적)
- 한 줄에 하나의 레코드

### 6. 에러 처리

- 개별 엔드포인트 실패 시 전체 중단 금지
- 로그 남기고 다음 엔드포인트 진행
- seqUpdate는 성공 시에만 업데이트

### 7. 엔드포인트 간 간격

- 각 요청 간: 1초 (Rate Limit 방지)
- 사이클 간: 30분

---

## 로깅

### 설정

- 파일: `logs/app.log`
- 콘솔 + 파일 동시 출력
- 형식: `[2025-01-31 10:30:45] [INFO] 메시지`
- 레벨: INFO, WARNING, ERROR

### 필수 로그 항목

```
✓ 프로그램 시작/종료
✓ 인증 성공/실패
✓ 19개 엔드포인트 로드 완료
✓ seqUpdate 파일 로드
✓ 수집 사이클 시작/완료
✓ [N/19] 엔드포인트명
✓ seqUpdate: 이전값 → 새로운값
✓ 수집 완료: N건
✓ 파일 저장: 경로
✓ 재시도 시도 (횟수, 대기 시간)
✓ 에러 메시지 (URL, 상태 코드, 예외)
✓ 30분 대기 시작/종료
```

---

## 19개 엔드포인트

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

## 구현 순서 권장사항

1. **src/collector.py 핵심 메서드** (우선순위)
   - `__init__()` → `load_endpoints()` → `build_auth_header()`
   - `fetch_api()` (재시도 로직 포함)
   - `authenticate()`
   - `load_seq_update()` → `save_seq_update()`
   - `extract_data_and_seq_update()`
   - `save_to_jsonl()`
   - `collect_single_endpoint()` → `collect_all_endpoints()`

2. **main.py**
   - Collector 초기화 및 실행

3. **테스트**
   - 인증 확인
   - 19개 엔드포인트 수집
   - seqUpdate 저장/로드
   - JSON Lines 파일 생성
   - 30분 대기 및 반복 수집

---

## 주요 파일 위치

- `.env` - API 인증 정보 (프로젝트 루트)
- `list.csv` - 엔드포인트 설정 (프로젝트 루트)
- `src/collector.py` - Collector 클래스
- `main.py` - 엔트리 포인트
- `data/seq_update.json` - seqUpdate 값 저장
- `data/outputs/*.jsonl` - 수집 데이터
- `logs/app.log` - 애플리케이션 로그

---

## 코딩 규칙

- **들여쓰기**: 2칸 스페이스
- **네이밍**: camelCase (변수, 함수)
- **주석**: 한국어
- **문서**: 한국어
- **타입**: type hints 사용, any 금지

---

## 성공 기준

- [ ] python main.py 실행 성공
- [ ] API 인증 성공 (로그 확인)
- [ ] 19개 엔드포인트 모두 수집 가능
- [ ] seqUpdate 메커니즘 정상 작동
- [ ] JSON Lines 파일 생성 및 데이터 저장
- [ ] 30분 간격 반복 수집 안정적 작동
- [ ] Ctrl+C 정상 종료
- [ ] 로그 파일 정상 생성
- [ ] 에러 발생 시 적절한 로깅 및 재시도

---

**최종 업데이트**: 2025년 1월 31일 10:34
