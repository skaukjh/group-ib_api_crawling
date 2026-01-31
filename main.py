"""
Group-IB API 크롤러 - 메인 엔트리 포인트

이 프로그램은 Group-IB Threat Intelligence API로부터 데이터를 수집합니다.
- 30분 간격으로 반복 수집
- seqUpdate 메커니즘으로 증분 데이터만 수집
- Ctrl+C로 정상 종료 가능

사용법:
  python main.py
"""

import time
import sys
from src.collector import GroupIBCollector, AuthenticationError


def main():
  """메인 함수

  1. Collector 초기화
  2. API 인증 확인
  3. 엔드포인트 로드
  4. 무한 루프:
     - 모든 엔드포인트 수집
     - seqUpdate 저장
     - 30분 대기
  5. KeyboardInterrupt 처리 (Ctrl+C)
  """
  try:
    # 1. Collector 초기화
    collector = GroupIBCollector()

    # 2. API 인증 확인
    if not collector.authenticate():
      collector.logger.error("API 인증에 실패했습니다. 프로그램을 종료합니다.")
      sys.exit(1)

    # 3. 엔드포인트 로드
    collector.loadEndpoints()

    # 4. 무한 루프 (30분 간격 수집)
    cycleNumber = 0

    while True:
      cycleNumber += 1

      try:
        # 모든 엔드포인트 수집
        seqUpdates = collector.collectAllEndpoints()

        # seqUpdate 저장
        collector.saveSeqUpdate(seqUpdates)

        # 30분 대기
        waitMinutes = 30
        waitSeconds = waitMinutes * 60

        collector.logger.info("")
        collector.logger.info(f"다음 사이클까지 {waitMinutes}분 대기...")
        collector.logger.info(f"(Ctrl+C를 눌러 종료할 수 있습니다)")
        collector.logger.info("")

        # 1분마다 로그 출력하며 대기
        for minute in range(waitMinutes):
          time.sleep(60)
          remainingMinutes = waitMinutes - minute - 1
          if remainingMinutes > 0:
            collector.logger.info(f"  대기 중... (남은 시간: {remainingMinutes}분)")

      except KeyboardInterrupt:
        # Ctrl+C 입력 시 즉시 종료
        raise

      except AuthenticationError as e:
        # 인증 오류 시 프로그램 종료
        collector.logger.error(f"인증 오류 발생: {e}")
        collector.logger.error("프로그램을 종료합니다.")
        sys.exit(1)

      except Exception as e:
        # 예상치 못한 에러 발생 시 로그 남기고 1분 대기 후 재시도
        collector.logger.error(f"예상치 못한 에러 발생: {e}")
        collector.logger.error("1분 후 다시 시도합니다...")
        time.sleep(60)

  except KeyboardInterrupt:
    # 5. KeyboardInterrupt 처리 (Ctrl+C)
    print("\n")
    if 'collector' in locals():
      collector.logger.info("=" * 40)
      collector.logger.info("사용자가 프로그램 종료를 요청했습니다 (Ctrl+C)")

      # seqUpdate 최종 저장
      if 'seqUpdates' in locals():
        collector.logger.info("seqUpdate 최종 저장 중...")
        collector.saveSeqUpdate(seqUpdates)

      collector.logger.info("프로그램을 정상 종료합니다.")
      collector.logger.info("=" * 40)
    else:
      print("프로그램을 종료합니다.")

    sys.exit(0)

  except AuthenticationError as e:
    # 인증 에러로 인한 종료
    if 'collector' in locals():
      collector.logger.error(f"인증 실패: {e}")
    else:
      print(f"인증 실패: {e}")
    sys.exit(1)

  except Exception as e:
    # 기타 예상치 못한 에러
    if 'collector' in locals():
      collector.logger.error(f"치명적 오류 발생: {e}")
      collector.logger.error("프로그램을 종료합니다.")
    else:
      print(f"치명적 오류 발생: {e}")
    sys.exit(1)


if __name__ == '__main__':
  main()
