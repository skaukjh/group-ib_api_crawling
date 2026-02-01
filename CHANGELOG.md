# 변경 이력 (Changelog)

이 파일은 Group-IB API 크롤러의 주요 변경 사항을 기록합니다.

---

## [0.2.0] - 2026-01-31

### 🚨 보안 (Security)
- **추가**: `.gitignore` 파일 생성으로 민감한 파일 보호
- **추가**: `.env.example` 템플릿 파일 제공
- **개선**: README에 보안 가이드 섹션 추가
- **수정**: API 자격증명 관리 체계 개선

### ✨ 새로운 기능 (Features)
- **추가**: 실패한 엔드포인트 자동 재시도 메커니즘
- **추가**: 환경 변수 기반 설정 관리 (`src/config.py`)
- **추가**: `retryOnError` 데코레이터로 재시도 로직 통합
- **추가**: seqUpdate 파일 백업 메커니즘 (`.bak`)
- **추가**: 원자적 파일 쓰기 (`.tmp` → rename)
- **추가**: 환경 변수로 모든 설정값 오버라이드 가능
  - `GROUPIB_BASE_URL`
  - `REQUEST_TIMEOUT`
  - `RATE_LIMIT_WAIT`
  - `MAX_RETRIES`
  - `WAIT_MINUTES`

### 🐛 버그 수정 (Bug Fixes)
- **수정**: `main.py`의 `seqUpdates` 변수 스코프 문제 해결
- **수정**: KeyboardInterrupt 시 안전한 종료 로직 구현
- **수정**: CSV 파싱 에러 처리 강화
  - 필수 컬럼 검증
  - 행별 에러 핸들링
  - 빈 CSV 파일 처리
- **수정**: JSON Lines 저장 시 항목별 에러 핸들링

### 🔧 개선 (Improvements)
- **개선**: 타입 힌팅 완성 (`Dict[str, Any]`, `List[Dict[str, Any]]` 등)
- **개선**: 실패/성공 건수 추적 및 로깅
- **개선**: 재시도 로직 데코레이터 패턴으로 리팩토링
- **개선**: 하드코딩된 값들 환경 변수로 이동
- **개선**: 설정 중앙 집중 관리

### 📚 문서화 (Documentation)
- **추가**: `README.md` - 프로젝트 전체 가이드
- **추가**: `CODE_REVIEW_REPORT.md` - 코드 리뷰 보고서
- **추가**: `FINAL_VERIFICATION_REPORT.md` - 최종 검증 보고서
- **추가**: `CHANGELOG.md` - 변경 이력 (본 문서)
- **개선**: `requirements.txt`에 주석 추가
- **개선**: 모든 함수 docstring 개선

### 🧪 테스트 (Tests)
- **추가**: `tests/test_collector.py` - 단위 테스트 12개
- **추가**: pytest 기반 테스트 프레임워크
- **추가**: Mock을 활용한 API 테스트
- **추가**: 환경 변수 테스트
- **추가**: 파일 I/O 테스트

### 📦 의존성 (Dependencies)
- **추가**: pytest (개발 환경, 주석 처리)
- **추가**: pytest-mock (개발 환경, 주석 처리)
- **추가**: mypy (개발 환경, 주석 처리)

### 🗂️ 파일 구조 (File Structure)
```
신규 파일:
+ .gitignore
+ .env.example
+ README.md
+ CODE_REVIEW_REPORT.md
+ FINAL_VERIFICATION_REPORT.md
+ CHANGELOG.md
+ src/config.py
+ tests/__init__.py
+ tests/test_collector.py

수정 파일:
* main.py
* src/collector.py
* requirements.txt
```

---

## [0.1.0] - 초기 버전

### ✨ 초기 기능
- Group-IB API 데이터 수집 기능
- seqUpdate 메커니즘 구현
- JSON Lines 형식 저장
- Basic Authentication 인증
- 19개 엔드포인트 지원
- 재시도 로직 (Rate Limit, 서버 오류)
- 30분 간격 자동 수집
- 파일 및 콘솔 로깅

### 📁 초기 파일
- `main.py` - 메인 엔트리 포인트
- `src/__init__.py` - 패키지 초기화
- `src/collector.py` - 수집 로직
- `list.csv` - 엔드포인트 설정
- `.env` - 환경 변수 (보안 주의!)
- `requirements.txt` - 의존성

---

## 버전 규칙

이 프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

**형식**: MAJOR.MINOR.PATCH

- **MAJOR**: 하위 호환성이 없는 API 변경
- **MINOR**: 하위 호환성이 있는 기능 추가
- **PATCH**: 하위 호환성이 있는 버그 수정

---

## 변경 유형 아이콘

- 🚨 **보안** (Security): 보안 관련 수정
- ✨ **새로운 기능** (Features): 새로운 기능 추가
- 🐛 **버그 수정** (Bug Fixes): 버그 수정
- 🔧 **개선** (Improvements): 기존 기능 개선
- 📚 **문서화** (Documentation): 문서 추가/수정
- 🧪 **테스트** (Tests): 테스트 추가/수정
- 📦 **의존성** (Dependencies): 의존성 업데이트
- 🗑️ **제거** (Removed): 기능 제거
- ⚠️ **사용 중단** (Deprecated): 곧 제거될 기능

---

**마지막 업데이트**: 2026-01-31
