"""
Group-IB API 데이터 수집 모듈

이 모듈은 Group-IB Threat Intelligence API로부터 데이터를 수집하고,
seqUpdate 메커니즘을 활용하여 증분 데이터만 효율적으로 수집합니다.
"""

import os
import json
import time
import base64
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Callable
from urllib.parse import urlparse
from functools import wraps

import requests
import pandas as pd
from dotenv import load_dotenv


# ===== 예외 클래스 정의 =====

class GroupIBAPIError(Exception):
  """Group-IB API 기본 예외 클래스"""
  pass


class AuthenticationError(GroupIBAPIError):
  """인증 실패 예외 (HTTP 401)"""
  pass


# RateLimitError는 현재 미사용이지만 향후 확장성을 위해 보존
class RateLimitError(GroupIBAPIError):
  """Rate Limit 초과 예외 (HTTP 429)"""
  pass


# ===== 유틸리티 함수 =====

def retryOnError(maxAttempts: int = 3,
                 baseWaitTime: int = 1,
                 exponentialBackoff: bool = False) -> Callable:
  """재시도 데코레이터

  네트워크 오류, 타임아웃, 서버 오류 발생 시 자동으로 재시도합니다.

  Args:
    maxAttempts: 최대 재시도 횟수 (기본값: 3)
    baseWaitTime: 기본 대기 시간(초) (기본값: 1)
    exponentialBackoff: 지수 백오프 사용 여부 (기본값: False)

  Returns:
    데코레이터 함수
  """
  def decorator(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
      lastException = None

      for attempt in range(maxAttempts):
        try:
          return func(*args, **kwargs)
        except (requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
          lastException = e

          if attempt < maxAttempts - 1:
            if exponentialBackoff:
              waitTime = baseWaitTime * (2 ** attempt)
            else:
              waitTime = baseWaitTime * (attempt + 1)

            # 로거가 있으면 사용
            if args and hasattr(args[0], 'logger'):
              args[0].logger.warning(
                f"⚠ 재시도 {attempt + 1}/{maxAttempts - 1}: {e}. "
                f"{waitTime}초 대기 중..."
              )

            time.sleep(waitTime)
          else:
            if args and hasattr(args[0], 'logger'):
              args[0].logger.error(
                f"✗ {maxAttempts}회 재시도 실패: {e}"
              )

      # 모든 재시도 실패 시 마지막 예외 발생
      raise lastException

    return wrapper
  return decorator


# ===== Collector 클래스 =====

class GroupIBCollector:
  """Group-IB API 데이터 수집 클래스

  주요 기능:
  - Basic Authentication 기반 인증
  - 19개 엔드포인트로부터 데이터 수집
  - seqUpdate 메커니즘을 통한 증분 수집
  - JSON Lines 형식으로 데이터 저장
  - 재시도 로직 및 Rate Limit 처리
  """

  def __init__(self):
    """초기화 메서드

    - .env 파일에서 환경 변수 로드
    - 로거 설정 (파일 + 콘솔)
    - 필요한 디렉토리 생성
    """
    # 환경 변수 로드
    load_dotenv()
    self.username = os.getenv('GROUPIB_USERNAME')
    self.apiKey = os.getenv('GROUPIB_API_KEY')

    if not self.username or not self.apiKey:
      raise ValueError(".env 파일에 GROUPIB_USERNAME과 GROUPIB_API_KEY가 설정되어 있어야 합니다.")

    # 기본 URL 설정 (환경 변수로 오버라이드 가능)
    self.baseUrl = os.getenv('GROUPIB_BASE_URL', 'https://tap.group-ib.com')

    # 설정 가능한 파라미터들
    self.requestTimeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
    self.rateLimitWait = int(os.getenv('RATE_LIMIT_WAIT', '1'))
    self.maxRetries = int(os.getenv('MAX_RETRIES', '3'))

    # 경로 설정
    self.projectRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    self.dataDir = os.path.join(self.projectRoot, "data")
    self.outputsDir = os.path.join(self.dataDir, "outputs")
    self.logsDir = os.path.join(self.projectRoot, "logs")
    self.seqUpdateFile = os.path.join(self.dataDir, "seq_update.json")
    self.csvFile = os.path.join(self.projectRoot, "list.csv")

    # 디렉토리 생성
    os.makedirs(self.dataDir, exist_ok=True)
    os.makedirs(self.outputsDir, exist_ok=True)
    os.makedirs(self.logsDir, exist_ok=True)

    # 로거 설정
    self._setupLogger()

    # 엔드포인트 리스트 (나중에 load_endpoints()로 로드)
    self.endpoints = []

    # 실패한 엔드포인트 추적
    self.failedEndpoints = []

    self.logger.info("=" * 40)
    self.logger.info("Group-IB API 크롤러 초기화 완료")
    self.logger.info("=" * 40)

  def _setupLogger(self):
    """로거 설정 (파일 + 콘솔 동시 출력)

    형식: [2025-01-31 10:30:45] [INFO] 메시지
    파일: logs/app.log
    """
    self.logger = logging.getLogger("GroupIBCollector")
    self.logger.setLevel(logging.INFO)

    # 기존 핸들러 제거 (중복 방지)
    if self.logger.handlers:
      self.logger.handlers.clear()

    # 파일 핸들러
    logFile = os.path.join(self.logsDir, "app.log")
    fileHandler = logging.FileHandler(logFile, encoding='utf-8')
    fileHandler.setLevel(logging.INFO)

    # 콘솔 핸들러
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    fileHandler.setFormatter(formatter)
    consoleHandler.setFormatter(formatter)

    # 핸들러 추가
    self.logger.addHandler(fileHandler)
    self.logger.addHandler(consoleHandler)

  def buildAuthHeader(self) -> Dict[str, str]:
    """Basic Authentication 헤더 생성

    Returns:
      HTTP 헤더 딕셔너리 (Authorization, User-Agent, Accept)
    """
    # username:api_key 형식으로 조합
    authString = f"{self.username}:{self.apiKey}"

    # ASCII로 인코딩 후 Base64 인코딩
    authBytes = authString.encode("ascii")
    authB64 = base64.b64encode(authBytes)
    authB64Str = authB64.decode("ascii")

    # Authorization 헤더 생성
    authHeader = f"Basic {authB64Str}"

    return {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54",
      "Authorization": authHeader,
      "Accept": "*/*"
    }

  def authenticate(self) -> bool:
    """API 인증 확인

    GET /api/v2/user/granted_collections 엔드포인트로 인증 테스트

    Returns:
      인증 성공 시 True, 실패 시 False

    Raises:
      AuthenticationError: 인증 실패 시
    """
    self.logger.info("API 인증 중...")

    authUrl = f"{self.baseUrl}/api/v2/user/granted_collections"
    headers = self.buildAuthHeader()

    try:
      response = requests.get(authUrl, headers=headers, timeout=self.requestTimeout)

      if response.status_code == 200:
        self.logger.info("✓ API 인증 성공")
        return True
      elif response.status_code == 401:
        self.logger.error("✗ API 인증 실패 (HTTP 401 Unauthorized)")
        raise AuthenticationError("인증 정보가 올바르지 않습니다.")
      else:
        self.logger.error(f"✗ 예상치 못한 응답: HTTP {response.status_code}")
        return False

    except requests.exceptions.Timeout:
      self.logger.error("✗ API 인증 타임아웃 (30초 초과)")
      return False
    except requests.exceptions.RequestException as e:
      self.logger.error(f"✗ API 인증 중 네트워크 오류: {e}")
      return False

  def loadEndpoints(self) -> List[Dict[str, str]]:
    """list.csv 파일에서 엔드포인트 로드

    Returns:
      엔드포인트 설정 리스트
      [
        {
          'url': 'https://tap.group-ib.com/api/v2/apt/threat_actor/updated',
          'endpoint': '/api/v2/apt/threat_actor/updated',
          'params': {'limit': '100'}
        },
        ...
      ]

    Raises:
      FileNotFoundError: CSV 파일이 존재하지 않을 때
      ValueError: CSV 형식이 잘못되었을 때
    """
    if not os.path.exists(self.csvFile):
      raise FileNotFoundError(f"list.csv 파일을 찾을 수 없습니다: {self.csvFile}")

    try:
      # pandas로 CSV 읽기
      df = pd.read_csv(self.csvFile)

      # 필수 컬럼 검증
      requiredColumns = ['endpoint', 'params']
      missingColumns = [col for col in requiredColumns if col not in df.columns]
      if missingColumns:
        raise ValueError(f"CSV 파일에 필수 컬럼이 누락되었습니다: {', '.join(missingColumns)}")

      endpointsList = []

      for index, row in df.iterrows():
        try:
          url = row['endpoint']
          paramsStr = row['params']

          # URL 검증
          if pd.isna(url) or not isinstance(url, str):
            self.logger.warning(f"라인 {index + 2}: URL이 유효하지 않습니다. 건너뜁니다.")
            continue

          # URL에서 엔드포인트 경로 추출
          parsed = urlparse(url)
          endpointPath = parsed.path

          # 파라미터 파싱 (key=value 형식)
          params = {}
          if pd.notna(paramsStr):
            for param in paramsStr.split('&'):
              if '=' in param:
                key, value = param.split('=', 1)
                params[key.strip()] = value.strip()

          endpointsList.append({
            'url': url,
            'endpoint': endpointPath,
            'params': params
          })

        except Exception as e:
          self.logger.warning(f"라인 {index + 2} 파싱 실패: {e}. 건너뜁니다.")
          continue

      if not endpointsList:
        raise ValueError("유효한 엔드포인트가 하나도 로드되지 않았습니다.")

      self.endpoints = endpointsList
      self.logger.info(f"✓ {len(endpointsList)}개 엔드포인트 로드 완료")

      return endpointsList

    except pd.errors.EmptyDataError:
      raise ValueError("CSV 파일이 비어 있습니다.")
    except pd.errors.ParserError as e:
      raise ValueError(f"CSV 파일 파싱 오류: {e}")

  def loadSeqUpdate(self) -> Dict[str, int]:
    """data/seq_update.json에서 seqUpdate 값 로드

    Returns:
      엔드포인트별 seqUpdate 딕셔너리
      {'/api/v2/apt/threat_actor/updated': 12345, ...}
    """
    if not os.path.exists(self.seqUpdateFile):
      self.logger.info("seqUpdate 파일이 없습니다. 빈 상태로 시작합니다.")
      return {}

    try:
      with open(self.seqUpdateFile, 'r', encoding='utf-8') as f:
        seqUpdates = json.load(f)
      self.logger.info(f"✓ seqUpdate 파일 로드: {self.seqUpdateFile}")
      return seqUpdates
    except Exception as e:
      self.logger.warning(f"seqUpdate 파일 로드 실패: {e}. 빈 상태로 시작합니다.")
      return {}

  def saveSeqUpdate(self, seqUpdates: Dict[str, int]) -> bool:
    """data/seq_update.json에 seqUpdate 값 저장 (원자적 쓰기 + 백업)

    Args:
      seqUpdates: 엔드포인트별 seqUpdate 딕셔너리

    Returns:
      저장 성공 시 True, 실패 시 False
    """
    try:
      # 1. 백업 파일 생성 (기존 파일이 있는 경우)
      if os.path.exists(self.seqUpdateFile):
        backupFile = self.seqUpdateFile + '.bak'
        try:
          with open(self.seqUpdateFile, 'r', encoding='utf-8') as src:
            with open(backupFile, 'w', encoding='utf-8') as dst:
              dst.write(src.read())
        except Exception as e:
          self.logger.warning(f"백업 파일 생성 실패: {e}")

      # 2. 임시 파일에 먼저 쓰기 (원자적 쓰기)
      tempFile = self.seqUpdateFile + '.tmp'
      with open(tempFile, 'w', encoding='utf-8') as f:
        json.dump(seqUpdates, f, indent=2, ensure_ascii=False)

      # 3. 임시 파일을 실제 파일로 교체
      if os.path.exists(self.seqUpdateFile):
        os.remove(self.seqUpdateFile)
      os.rename(tempFile, self.seqUpdateFile)

      self.logger.info(f"✓ seqUpdate 저장 완료: {self.seqUpdateFile}")
      return True

    except Exception as e:
      self.logger.error(f"✗ seqUpdate 저장 실패: {e}")
      # 임시 파일 정리
      tempFile = self.seqUpdateFile + '.tmp'
      if os.path.exists(tempFile):
        try:
          os.remove(tempFile)
        except:
          pass
      return False

  def fetchApi(self, url: str, params: Dict[str, str],
               retryCount: int = 0) -> Optional[Dict[str, Any]]:
    """API 요청 및 응답 처리 (재시도 로직 포함)

    Args:
      url: 요청 URL
      params: 쿼리 파라미터
      retryCount: 현재 재시도 횟수 (내부 사용)

    Returns:
      응답 JSON 딕셔너리 또는 None (실패 시)
    """
    headers = self.buildAuthHeader()

    try:
      response = requests.get(url, headers=headers, params=params, timeout=self.requestTimeout)

      # HTTP 200 성공
      if response.status_code == 200:
        return response.json()

      # HTTP 401 인증 실패 (즉시 중단)
      elif response.status_code == 401:
        self.logger.error(f"✗ 인증 실패 (401): {url}")
        raise AuthenticationError("API 인증이 실패했습니다.")

      # HTTP 429 Rate Limit
      elif response.status_code == 429:
        if retryCount < 3:
          waitTime = 5 * (retryCount + 1)  # 5초, 10초, 15초
          self.logger.warning(f"⚠ Rate Limit 도달 (429). {waitTime}초 대기 후 재시도 ({retryCount+1}/3)")
          time.sleep(waitTime)
          return self.fetchApi(url, params, retryCount + 1)
        else:
          self.logger.error(f"✗ Rate Limit 재시도 3회 실패: {url}")
          return None

      # HTTP 5xx 서버 오류
      elif 500 <= response.status_code < 600:
        if retryCount < 3:
          waitTime = retryCount + 1  # 1초, 2초, 3초
          self.logger.warning(f"⚠ 서버 오류 ({response.status_code}). {waitTime}초 대기 후 재시도 ({retryCount+1}/3)")
          time.sleep(waitTime)
          return self.fetchApi(url, params, retryCount + 1)
        else:
          self.logger.error(f"✗ 서버 오류 재시도 3회 실패: {url} (HTTP {response.status_code})")
          return None

      # 기타 4xx 클라이언트 오류
      else:
        self.logger.error(f"✗ 요청 실패 (HTTP {response.status_code}): {url}")
        return None

    except requests.exceptions.Timeout:
      if retryCount < 3:
        waitTime = retryCount + 1
        self.logger.warning(f"⚠ 타임아웃. {waitTime}초 대기 후 재시도 ({retryCount+1}/3)")
        time.sleep(waitTime)
        return self.fetchApi(url, params, retryCount + 1)
      else:
        self.logger.error(f"✗ 타임아웃 재시도 3회 실패: {url}")
        return None

    except requests.exceptions.RequestException as e:
      if retryCount < 3:
        waitTime = retryCount + 1
        self.logger.warning(f"⚠ 네트워크 오류: {e}. {waitTime}초 대기 후 재시도 ({retryCount+1}/3)")
        time.sleep(waitTime)
        return self.fetchApi(url, params, retryCount + 1)
      else:
        self.logger.error(f"✗ 네트워크 오류 재시도 3회 실패: {url} - {e}")
        return None

  def extractDataAndSeqUpdate(self, response: Dict[str, Any],
                               endpoint: str) -> Tuple[List[Dict[str, Any]], int]:
    """응답에서 데이터와 seqUpdate 추출

    Args:
      response: API 응답 JSON
      endpoint: 엔드포인트 경로

    Returns:
      (데이터 리스트, seqUpdate 값) 튜플
    """
    # seqUpdate 추출 (응답의 최상위 필드)
    seqUpdate = response.get('seqUpdate', 0)

    # 데이터 필드 우선순위: items → data → results
    dataList = []
    if 'items' in response:
      dataList = response['items']
    elif 'data' in response:
      dataList = response['data']
    elif 'results' in response:
      dataList = response['results']
    else:
      self.logger.warning(f"⚠ 응답에 데이터 필드가 없습니다 (items/data/results): {endpoint}")
      dataList = []

    # 리스트가 아닌 경우 처리
    if not isinstance(dataList, list):
      dataList = [dataList]

    return dataList, seqUpdate

  def urlToFilename(self, endpoint: str) -> str:
    """엔드포인트 경로를 JSON Lines 파일명으로 변환

    Args:
      endpoint: 엔드포인트 경로 (예: '/api/v2/apt/threat_actor/updated')

    Returns:
      파일명 (예: 'apt_threat_actor_updated.jsonl')
    """
    # '/api/v2/' 제거
    filename = endpoint.replace('/api/v2/', '')

    # 슬래시를 언더스코어로 변환
    filename = filename.replace('/', '_')

    # .jsonl 확장자 추가
    filename = filename + '.jsonl'

    return filename

  def saveToJsonl(self, endpoint: str, items: List[Dict[str, Any]],
                  seqUpdate: int) -> bool:
    """데이터를 JSON Lines 형식으로 저장 (에러 핸들링 강화)

    Args:
      endpoint: 엔드포인트 경로
      items: 저장할 데이터 리스트
      seqUpdate: 현재 seqUpdate 값

    Returns:
      저장 성공 시 True, 실패 시 False
    """
    if not items:
      self.logger.info(f"  저장할 데이터가 없습니다: {endpoint}")
      return True

    filename = self.urlToFilename(endpoint)
    filepath = os.path.join(self.outputsDir, filename)

    successCount = 0
    failCount = 0

    try:
      with open(filepath, 'a', encoding='utf-8') as f:
        for index, item in enumerate(items):
          try:
            record = {
              'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
              'source': 'groupib-api',
              'endpoint': endpoint,
              'seqUpdate': seqUpdate,
              'data': item
            }
            # JSON 직렬화 테스트
            jsonLine = json.dumps(record, ensure_ascii=False)
            f.write(jsonLine + '\n')
            successCount += 1

          except (TypeError, ValueError) as e:
            failCount += 1
            self.logger.warning(f"  항목 {index + 1} JSON 직렬화 실패: {e}")
            continue

      if failCount > 0:
        self.logger.warning(f"  ⚠ 저장 완료: {filepath} (성공: {successCount}건, 실패: {failCount}건)")
      else:
        self.logger.info(f"  ✓ 저장 완료: {filepath} ({successCount}건)")

      return successCount > 0  # 최소 1건 이상 성공 시 True

    except IOError as e:
      self.logger.error(f"  ✗ 파일 I/O 오류: {filepath} - {e}")
      return False
    except Exception as e:
      self.logger.error(f"  ✗ 파일 저장 실패: {filepath} - {e}")
      return False

  def collectSingleEndpoint(self, endpointConfig: Dict[str, Any],
                            seqUpdates: Dict[str, int]) -> Tuple[bool, int]:
    """단일 엔드포인트 데이터 수집

    Args:
      endpointConfig: 엔드포인트 설정
      seqUpdates: 현재 seqUpdate 딕셔너리

    Returns:
      (성공 여부, 수집된 건수) 튜플
    """
    url = endpointConfig['url']
    endpoint = endpointConfig['endpoint']
    params = endpointConfig['params'].copy()

    # 저장된 seqUpdate 로드 (기본값: 0)
    currentSeqUpdate = seqUpdates.get(endpoint, 0)

    # seqUpdate 파라미터 추가 (0이 아닌 경우만)
    if currentSeqUpdate > 0:
      params['seqUpdate'] = str(currentSeqUpdate)
      self.logger.info(f"  seqUpdate: {currentSeqUpdate} (증분 수집)")
    else:
      self.logger.info(f"  seqUpdate: 0 (최초 수집)")

    # API 요청
    response = self.fetchApi(url, params)

    if response is None:
      self.logger.error(f"  ✗ 수집 실패: {endpoint}")
      return False, 0

    # 데이터 및 seqUpdate 추출
    dataList, newSeqUpdate = self.extractDataAndSeqUpdate(response, endpoint)

    # 데이터 저장
    saveSuccess = self.saveToJsonl(endpoint, dataList, newSeqUpdate)

    if saveSuccess:
      # seqUpdate 업데이트
      seqUpdates[endpoint] = newSeqUpdate

      if newSeqUpdate != currentSeqUpdate:
        self.logger.info(f"  새로운 seqUpdate: {currentSeqUpdate} → {newSeqUpdate}")

      self.logger.info(f"  ✓ 수집 완료: {len(dataList)}건")
      return True, len(dataList)
    else:
      return False, 0

  def collectAllEndpoints(self) -> Dict[str, int]:
    """모든 엔드포인트 순차 수집 (실패한 엔드포인트 우선 재시도)

    Returns:
      업데이트된 seqUpdate 딕셔너리
    """
    if not self.endpoints:
      self.logger.error("엔드포인트가 로드되지 않았습니다. loadEndpoints()를 먼저 호출하세요.")
      return {}

    # seqUpdate 로드
    seqUpdates = self.loadSeqUpdate()

    # 수집할 엔드포인트 목록 (실패한 엔드포인트 우선)
    endpointsToCollect = []

    # 1. 이전에 실패한 엔드포인트 우선 추가
    if self.failedEndpoints:
      self.logger.info(f"이전 사이클에서 실패한 {len(self.failedEndpoints)}개 엔드포인트를 우선 재시도합니다.")
      endpointsToCollect.extend(self.failedEndpoints)

    # 2. 나머지 엔드포인트 추가 (중복 제거)
    failedEndpointPaths = {ep['endpoint'] for ep in self.failedEndpoints}
    for ep in self.endpoints:
      if ep['endpoint'] not in failedEndpointPaths:
        endpointsToCollect.append(ep)

    totalEndpoints = len(endpointsToCollect)
    self.logger.info("")
    self.logger.info("=" * 40)
    self.logger.info(f"수집 사이클 시작 ({totalEndpoints}개 엔드포인트)")
    self.logger.info("=" * 40)

    successCount = 0
    totalRecords = 0
    newFailedEndpoints = []

    for idx, endpointConfig in enumerate(endpointsToCollect, 1):
      endpoint = endpointConfig['endpoint']

      self.logger.info(f"\n[{idx}/{totalEndpoints}] {endpoint}")

      success, recordCount = self.collectSingleEndpoint(endpointConfig, seqUpdates)

      if success:
        successCount += 1
        totalRecords += recordCount
      else:
        # 실패한 엔드포인트 기록
        newFailedEndpoints.append(endpointConfig)

      # Rate Limit 방지를 위한 엔드포인트 간 대기
      if idx < totalEndpoints:
        time.sleep(self.rateLimitWait)

    # 실패한 엔드포인트 목록 업데이트
    self.failedEndpoints = newFailedEndpoints

    self.logger.info("")
    self.logger.info("=" * 40)
    self.logger.info(f"수집 사이클 완료")
    self.logger.info(f"  성공: {successCount}/{totalEndpoints} 엔드포인트")
    self.logger.info(f"  실패: {len(newFailedEndpoints)}/{totalEndpoints} 엔드포인트")
    self.logger.info(f"  총 수집: {totalRecords}건")
    if newFailedEndpoints:
      self.logger.warning(f"  다음 사이클에서 실패한 엔드포인트를 재시도합니다.")
    self.logger.info("=" * 40)

    return seqUpdates
