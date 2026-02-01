"""
Group-IB API 크롤러 설정 모듈

환경 변수를 통한 중앙 집중식 설정 관리
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class Config:
  """설정 클래스

  환경 변수로부터 설정값을 로드하고, 기본값을 제공합니다.
  """

  # API 자격증명 (필수)
  GROUPIB_USERNAME: str = os.getenv('GROUPIB_USERNAME', '')
  GROUPIB_API_KEY: str = os.getenv('GROUPIB_API_KEY', '')

  # API 엔드포인트
  GROUPIB_BASE_URL: str = os.getenv('GROUPIB_BASE_URL', 'https://tap.group-ib.com')

  # 타임아웃 설정 (초)
  REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))

  # Rate Limit 설정
  RATE_LIMIT_WAIT: int = int(os.getenv('RATE_LIMIT_WAIT', '1'))
  MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))

  # 수집 사이클 설정 (분)
  WAIT_MINUTES: int = int(os.getenv('WAIT_MINUTES', '30'))

  # 로그 레벨
  LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

  # 파일 경로
  PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  DATA_DIR: str = os.path.join(PROJECT_ROOT, 'data')
  OUTPUTS_DIR: str = os.path.join(DATA_DIR, 'outputs')
  LOGS_DIR: str = os.path.join(PROJECT_ROOT, 'logs')
  SEQ_UPDATE_FILE: str = os.path.join(DATA_DIR, 'seq_update.json')
  CSV_FILE: str = os.path.join(PROJECT_ROOT, 'list.csv')

  @classmethod
  def validate(cls) -> bool:
    """필수 설정값 검증

    Returns:
      모든 필수 설정이 있으면 True, 없으면 False
    """
    if not cls.GROUPIB_USERNAME:
      raise ValueError("GROUPIB_USERNAME 환경 변수가 설정되어 있지 않습니다.")

    if not cls.GROUPIB_API_KEY:
      raise ValueError("GROUPIB_API_KEY 환경 변수가 설정되어 있지 않습니다.")

    return True

  @classmethod
  def getAll(cls) -> dict:
    """모든 설정값 반환 (디버깅용)

    Returns:
      설정 딕셔너리 (민감한 정보는 마스킹)
    """
    return {
      'GROUPIB_USERNAME': cls.GROUPIB_USERNAME,
      'GROUPIB_API_KEY': '***' if cls.GROUPIB_API_KEY else '',
      'GROUPIB_BASE_URL': cls.GROUPIB_BASE_URL,
      'REQUEST_TIMEOUT': cls.REQUEST_TIMEOUT,
      'RATE_LIMIT_WAIT': cls.RATE_LIMIT_WAIT,
      'MAX_RETRIES': cls.MAX_RETRIES,
      'WAIT_MINUTES': cls.WAIT_MINUTES,
      'LOG_LEVEL': cls.LOG_LEVEL,
      'PROJECT_ROOT': cls.PROJECT_ROOT,
    }


# 전역 설정 인스턴스
config = Config()
