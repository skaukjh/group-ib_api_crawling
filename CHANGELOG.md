# 변경 이력 (CHANGELOG)

이 파일은 Group-IB API 크롤러의 모든 변경사항을 기록합니다.

## [개발 중 - 2025-01-31]

### 초기 설계 및 명세

#### 추가됨
- 프로젝트 기본 구조 설계
- Group-IB API 크롤러 시스템 아키텍처 정의
- 19개 엔드포인트 명세 작성
- seqUpdate 메커니즘 설계
- 에러 처리 및 재시도 로직 정의
- 로깅 및 모니터링 전략 수립

#### 예정 항목
- src/collector.py 구현 (GroupIBCollector 클래스)
- main.py 구현 (무한 루프, 30분 간격 수집)
- 단위 테스트 작성
- 통합 테스트 시나리오

### 문서화

#### 생성된 파일
- `README.md` - 사용자 설명서 및 설정 가이드
- `IMPLEMENTATION_SPEC.md` - 개발자용 상세 명세서
- `CHANGELOG.md` - 변경 이력 (이 파일)
- `.gitignore` - git 제외 설정
- `.env.example` - 환경 변수 템플릿
- `requirements.txt` - Python 의존성

#### 업데이트된 파일
- `list.csv` - 19개 엔드포인트 확인
- `.env` - 인증 정보 설정 완료

---

## 향후 예정

### v0.2.0 (2025-02-01 예정)
- [ ] src/collector.py 완성
- [ ] main.py 완성
- [ ] 기본 기능 테스트 통과

### v0.3.0 (2025-02-08 예정)
- [ ] 전체 통합 테스트 완료
- [ ] 문서화 완성
- [ ] Production 배포 준비

### v1.0.0 (2025-02-15 예정)
- [ ] 공식 릴리스
- [ ] 안정성 검증
- [ ] 운영 모드 시작

### 향후 확장 (TBD)
- Kafka Producer 통합
- 웹 대시보드
- 알림 시스템
- Docker 컨테이너화

---

## 커밋 규칙

모든 커밋 메시지는 다음 형식을 따릅니다:

```
[태그] 간단한 설명

상세 설명 (필요시)

Related: #이슈번호 (해당시)
```

### 커밋 태그

- `[INIT]` - 초기 설정
- `[FEAT]` - 새로운 기능
- `[FIX]` - 버그 수정
- `[REFACTOR]` - 리팩토링
- `[DOCS]` - 문서 추가/수정
- `[TEST]` - 테스트 추가
- `[CHORE]` - 기타 변경

---

## 버전 관리

이 프로젝트는 [Semantic Versioning](https://semver.org/) 을 따릅니다.

```
MAJOR.MINOR.PATCH
```

- `MAJOR`: 호환되지 않는 API 변경
- `MINOR`: 호환되는 새로운 기능
- `PATCH`: 버그 수정

---

**마지막 업데이트**: 2025년 1월 31일
