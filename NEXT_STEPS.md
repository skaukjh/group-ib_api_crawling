# 다음 단계 안내

설계 분석이 완료되었습니다. 이 문서는 코드 구현을 위한 다음 단계를 안내합니다.

---

## 현재 상태

### 완료된 작업

- [x] 설계 문서 분석 (778줄, 30KB)
- [x] 요구사항 분석 및 분류
- [x] 모듈 설계 및 인터페이스 정의
- [x] 데이터 구조 정의
- [x] 에러 처리 전략 수립
- [x] 문서화 완성
  - README.md (사용자 가이드)
  - IMPLEMENTATION_SPEC.md (상세 명세)
  - IMPLEMENTATION_SUMMARY.md (구현 요약)
  - DESIGN_ANALYSIS_REPORT.md (분석 보고서)
  - CHANGELOG.md (변경 이력)
- [x] 프로젝트 구조 생성
  - src/ 디렉토리 생성
  - data/outputs/ 디렉토리 생성
  - logs/ 디렉토리 생성
  - src/__init__.py 생성
- [x] 설정 파일 준비
  - .env (인증 정보 포함)
  - .env.example (템플릿)
  - .gitignore (제외 설정)
  - requirements.txt (의존성)
  - list.csv (19개 엔드포인트)

### 구현 대기 중 (api-crawler-builder 담당)

- [ ] src/collector.py 구현
- [ ] main.py 구현
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성

---

## 코드 구현 가이드

### Step 1: api-crawler-builder 에이전트 호출

```bash
# 다음 정보를 api-crawler-builder에 전달하세요:

프로젝트 경로: C:\Users\skauk\Desktop\OSINT 자료\GroupIB_Crawling

필수 참고 문서:
1. IMPLEMENTATION_SUMMARY.md (빠른 개요)
2. IMPLEMENTATION_SPEC.md (상세 명세)

선택 참고 문서:
3. README.md (배경 이해)
4. DESIGN_ANALYSIS_REPORT.md (상세 분석)

기존 준비물:
- src/__init__.py (생성됨)
- .env (인증 정보 포함)
- .env.example (템플릿)
- .gitignore (제외 설정)
- list.csv (19개 엔드포인트)
- requirements.txt (의존성)
```

### Step 2: 구현 순서 (api-crawler-builder용)

#### Phase 1: src/collector.py (500-700 라인)

**우선순위 1 - 핵심 초기화**
```python
class GroupIBCollector:
    def __init__(self):
        # .env 로드, 로거 설정, 디렉토리 생성

    def authenticate(self) -> bool:
        # GET /api/v2/user/granted_collections
        # HTTP 200 확인

    def load_endpoints(self) -> List[Dict]:
        # list.csv 파싱 (pandas)
        # URL, 엔드포인트 경로, 파라미터 추출
```

**우선순위 2 - API 통신**
```python
    def build_auth_header(self) -> Dict[str, str]:
        # Base64 인코딩된 Basic Auth 헤더

    def fetch_api(self, url, params, retry_count=0):
        # HTTP GET 요청
        # 재시도 로직 (3회, exponential backoff)
        # Rate Limit 처리 (429)
```

**우선순위 3 - 상태 관리**
```python
    def load_seq_update(self) -> Dict:
        # data/seq_update.json 로드

    def save_seq_update(self, seq_updates: Dict) -> bool:
        # data/seq_update.json 저장
```

**우선순위 4 - 데이터 처리**
```python
    def extract_data_and_seq_update(self, response, endpoint):
        # 응답에서 items/data/results 필드 추출
        # seqUpdate 필드 추출

    def url_to_filename(self, endpoint: str) -> str:
        # /api/v2/apt/threat_actor/updated
        # → apt_threat_actor_updated.jsonl

    def save_to_jsonl(self, endpoint, items, seq_update) -> bool:
        # JSON Lines 형식으로 저장 (append)
        # timestamp, source, endpoint, seqUpdate, data 필드
```

**우선순위 5 - 수집 로직**
```python
    def collect_single_endpoint(self, config, seq_updates):
        # 단일 엔드포인트 수집
        # seqUpdate 로드 → API 요청 → 데이터 저장 → 업데이트

    def collect_all_endpoints(self) -> Dict:
        # 19개 엔드포인트 순차 처리
        # 각 요청 간 1초 간격
        # 로깅
```

#### Phase 2: main.py (100-150 라인)

```python
from src.collector import GroupIBCollector

def main():
    # 1. Collector 초기화
    collector = GroupIBCollector()

    # 2. 인증 확인
    if not collector.authenticate():
        exit(1)

    # 3. 엔드포인트 로드
    endpoints = collector.load_endpoints()

    # 4. seqUpdate 로드
    seq_updates = collector.load_seq_update()

    # 5. 무한 루프
    while True:
        try:
            # seqUpdate 업데이트
            seq_updates = collector.collect_all_endpoints()

            # seqUpdate 저장
            collector.save_seq_update(seq_updates)

            # 30분 대기
            time.sleep(1800)

        except KeyboardInterrupt:
            # seqUpdate 최종 저장
            collector.save_seq_update(seq_updates)
            print("\n프로그램 종료")
            exit(0)

        except Exception as e:
            # 예상치 못한 에러 처리
            logger.error(f"예상치 못한 에러: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
```

#### Phase 3: 테스트

```bash
# 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python main.py

# 로그 확인 (다른 터미널)
tail -f logs/app.log

# 데이터 확인 (30분 후 또는 더 일찍)
ls -la data/outputs/
cat data/seq_update.json
head -1 data/outputs/apt_threat_actor_updated.jsonl
```

---

## 검증 체크리스트

### 구현 완료 후 확인사항

#### 기능 검증
- [ ] python main.py 실행 성공
- [ ] 콘솔에 시작 메시지 출력
- [ ] logs/app.log 파일 생성
- [ ] API 인증 성공 ("✓ API 인증 성공" 로그)
- [ ] 19개 엔드포인트 로드 확인
- [ ] 첫 번째 엔드포인트 수집 시작
- [ ] data/seq_update.json 파일 생성
- [ ] data/outputs/apt_threat_actor_updated.jsonl 등 파일 생성

#### seqUpdate 메커니즘
- [ ] 첫 실행: seqUpdate=0으로 시작 (로그 확인)
- [ ] API 응답에서 새로운 seqUpdate 추출
- [ ] data/seq_update.json에 저장됨
- [ ] 두 번째 사이클에서 저장된 값 사용 (로그 확인)

#### 데이터 저장
- [ ] JSON Lines 파일 생성됨
- [ ] 각 줄이 유효한 JSON (테스트: `cat file.jsonl | jq .`)
- [ ] 필수 필드 확인: timestamp, source, endpoint, seqUpdate, data
- [ ] append 모드로 누적 저장됨 (파일 크기 증가 확인)

#### 로깅
- [ ] logs/app.log 파일에 로그 기록됨
- [ ] 타임스탬프 포함 ([YYYY-MM-DD HH:MM:SS] 형식)
- [ ] 로그 레벨 포함 ([INFO], [WARNING], [ERROR])
- [ ] 주요 이벤트 로깅 (인증, 엔드포인트, 저장, 대기)

#### 30분 대기
- [ ] 모든 엔드포인트 수집 완료 후 "다음 사이클까지 30분 대기" 메시지
- [ ] 30분 경과 후 자동으로 다시 수집 시작
- [ ] 로그에 대기 시간 기록

#### 에러 처리
- [ ] 네트워크 오류 발생 시 재시도 로그 (최대 3회)
- [ ] Rate Limit (429) 발생 시 대기 후 재시도 (5초, 10초, 15초)
- [ ] 인증 실패 (401) 시 프로그램 종료
- [ ] 개별 엔드포인트 실패 시에도 다음 엔드포인트 계속 진행

#### 종료 처리
- [ ] Ctrl+C 입력 시 정상 종료
- [ ] 종료 전 seqUpdate 최종 저장
- [ ] 종료 메시지 출력

---

## 예상 실행 결과

### 초기 실행 로그

```
[2025-01-31 10:30:45] [INFO] ========================================
[2025-01-31 10:30:45] [INFO] Group-IB API 크롤러 시작
[2025-01-31 10:30:45] [INFO] ========================================
[2025-01-31 10:30:45] [INFO] API 인증 중...
[2025-01-31 10:30:46] [INFO] ✓ API 인증 성공
[2025-01-31 10:30:46] [INFO] 19개 엔드포인트 로드 완료
[2025-01-31 10:30:46] [INFO] seqUpdate 파일 로드: data/seq_update.json

=== 수집 사이클 1 시작 ===
[2025-01-31 10:30:47] [INFO] [1/19] /api/v2/apt/threat_actor/updated
[2025-01-31 10:30:47] [INFO]   seqUpdate: 0 (최초 수집)
[2025-01-31 10:30:48] [INFO]   ✓ 수집 완료: 100건
[2025-01-31 10:30:48] [INFO]   새로운 seqUpdate: 12345
[2025-01-31 10:30:48] [INFO]   저장: data/outputs/apt_threat_actor_updated.jsonl

[2025-01-31 10:30:49] [INFO] [2/19] /api/v2/apt/threat/updated
[2025-01-31 10:30:49] [INFO]   seqUpdate: 0 (최초 수집)
[2025-01-31 10:30:50] [INFO]   ✓ 수집 완료: 10건
[2025-01-31 10:30:50] [INFO]   새로운 seqUpdate: 6789
[2025-01-31 10:30:50] [INFO]   저장: data/outputs/apt_threat_updated.jsonl

... (19개 엔드포인트 모두)

[2025-01-31 10:35:00] [INFO] === 수집 사이클 1 완료 (총 5분 소요) ===
[2025-01-31 10:35:00] [INFO] 다음 사이클까지 30분 대기...

... (30분 경과)

=== 수집 사이클 2 시작 ===
[2025-01-31 11:05:00] [INFO] [1/19] /api/v2/apt/threat_actor/updated
[2025-01-31 11:05:00] [INFO]   seqUpdate: 12345 (증분 수집)
[2025-01-31 11:05:01] [INFO]   ✓ 수집 완료: 5건 (신규)
[2025-01-31 11:05:01] [INFO]   새로운 seqUpdate: 12350
[2025-01-31 11:05:01] [INFO]   저장: data/outputs/apt_threat_actor_updated.jsonl

... (계속 반복)
```

---

## 문제 해결 가이드

### 문제: 인증 실패 (401 에러)

**증상**: "[ERROR] 요청 실패: 401 Unauthorized"

**해결 방법**:
1. `.env` 파일에서 username과 api_key 확인
2. Group-IB 포털에서 API 키 확인
3. API 키가 만료되지 않았는지 확인
4. Base64 인코딩이 올바른지 확인 (단위 테스트)

### 문제: CSV 파일을 찾을 수 없음

**증상**: "FileNotFoundError: list.csv not found"

**해결 방법**:
1. list.csv가 main.py와 동일 디렉토리에 있는지 확인
2. 파일명이 정확히 "list.csv"인지 확인 (대소문자)
3. 경로가 상대 경로가 아닌 절대 경로로 설정되어 있는지 확인

### 문제: 디렉토리 생성 실패

**증상**: "Permission denied: data/outputs"

**해결 방법**:
1. 프로젝트 디렉토리에 대한 쓰기 권한 확인
2. 수동으로 디렉토리 생성:
   ```bash
   mkdir -p data/outputs
   mkdir -p logs
   ```

### 문제: 네트워크 타임아웃

**증상**: "[WARNING] 요청 실패: Connection timeout"

**해결 방법**:
1. 인터넷 연결 확인
2. 방화벽 설정 확인
3. Group-IB API 서버 상태 확인
4. 재시도 로직이 작동하는지 확인 (로그에서 "재시도" 메시지)

### 문제: Rate Limit 도달

**증상**: "[WARNING] Rate Limit 도달 (429)"

**정상 동작**:
- 이는 정상 동작입니다
- 프로그램은 자동으로 5초, 10초, 15초 대기 후 재시도합니다
- 로그에서 "재시도" 메시지 확인

---

## 성능 및 모니터링

### 모니터링 명령어

```bash
# 로그 실시간 모니터링
tail -f logs/app.log

# 특정 엔드포인트 수집 건수 확인
wc -l data/outputs/apt_threat_actor_updated.jsonl

# seqUpdate 현재 값 확인
cat data/seq_update.json | jq .

# 저장된 데이터 샘플 확인 (첫 번째 줄)
head -1 data/outputs/apt_threat_actor_updated.jsonl | jq .

# 모든 JSONL 파일 목록
ls -la data/outputs/*.jsonl
```

### 성능 지표

| 항목 | 예상값 | 측정 방법 |
|------|--------|----------|
| 19개 엔드포인트 수집 시간 | 5-10분 | 로그에서 "수집 완료" 시간 차이 |
| 메모리 사용량 | <100MB | `ps aux \| grep python` |
| 디스크 증가량 (일일) | 100KB-10MB | `du -sh data/outputs/` |
| CPU 사용률 | <5% (대기 중) | `top` 또는 작업 관리자 |

---

## 배포 및 운영

### 로컬 테스트

```bash
# 1. 설치
pip install -r requirements.txt

# 2. 실행
python main.py

# 3. 모니터링 (다른 터미널)
tail -f logs/app.log

# 4. 종료 (Ctrl+C)
```

### 백그라운드 실행 (Linux/macOS)

```bash
# nohup으로 실행
nohup python main.py > output.log 2>&1 &

# 프로세스 ID 확인
ps aux | grep main.py

# 로그 확인
tail -f output.log

# 프로세스 종료
kill <PID>
```

### Windows 백그라운드 실행

```bash
# PowerShell에서 백그라운드 실행
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden

# 또는 Task Scheduler에서 예약 작업 설정
```

### Docker 컨테이너화 (향후)

```dockerfile
# 기본 구조 (참고용)
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## 다음 다음 단계 (향후 확장)

### Phase 2: Kafka Producer 추가

```python
# KafkaProducer를 이용한 실시간 메시지 전송
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
topic = f"groupib.{category}.{type}"
producer.send(topic, value=json.dumps(record).encode())
```

### Phase 3: 웹 대시보드

- 수집 현황 모니터링
- 엔드포인트별 통계
- 에러 로그 조회
- 수집 일정 조정

### Phase 4: 알림 시스템

- Slack 알림 (에러 발생 시)
- Email 리포트 (일일 요약)
- SMS 긴급 알림 (중대 에러)

---

## 참고 자료

### 내부 문서

- [README.md](./README.md) - 사용자 설명서
- [IMPLEMENTATION_SPEC.md](./IMPLEMENTATION_SPEC.md) - 상세 기술 명세
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - 빠른 참고
- [DESIGN_ANALYSIS_REPORT.md](./DESIGN_ANALYSIS_REPORT.md) - 분석 보고서
- [CHANGELOG.md](./CHANGELOG.md) - 변경 이력

### 외부 자료

- [Group-IB API 문서](https://api.group-ib.com)
- [Requests 라이브러리](https://docs.python-requests.org/)
- [JSON Lines 포맷](https://jsonlines.org)
- [Python 로깅](https://docs.python.org/3/library/logging.html)

---

## 문의 및 피드백

문제가 발생하거나 개선사항이 있으면 다음을 확인하세요:

1. **IMPLEMENTATION_SPEC.md** - 기술 세부사항
2. **README.md** - 사용자 가이드
3. **logs/app.log** - 에러 메시지
4. **DESIGN_ANALYSIS_REPORT.md** - 전체 설계 분석

---

**문서 작성**: 2025년 1월 31일
**상태**: 최종 완료
**다음 단계**: api-crawler-builder 에이전트의 코드 구현
