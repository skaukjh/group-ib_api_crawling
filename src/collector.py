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
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

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


class RateLimitError(GroupIBAPIError):
  """Rate Limit 초과 예외 (HTTP 429)"""
  pass


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

    # 기본 URL 설정
    self.baseUrl = "https://tap.group-ib.com"

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
      response = requests.get(authUrl, headers=headers, timeout=30)

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
    """
    if not os.path.exists(self.csvFile):
      raise FileNotFoundError(f"list.csv 파일을 찾을 수 없습니다: {self.csvFile}")

    # pandas로 CSV 읽기
    df = pd.read_csv(self.csvFile)

    endpointsList = []

    for _, row in df.iterrows():
      url = row['endpoint']
      paramsStr = row['params']

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

    self.endpoints = endpointsList
    self.logger.info(f"✓ {len(endpointsList)}개 엔드포인트 로드 완료")

    return endpointsList

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
    """data/seq_update.json에 seqUpdate 값 저장

    Args:
      seqUpdates: 엔드포인트별 seqUpdate 딕셔너리

    Returns:
      저장 성공 시 True, 실패 시 False
    """
    try:
      with open(self.seqUpdateFile, 'w', encoding='utf-8') as f:
        json.dump(seqUpdates, f, indent=2, ensure_ascii=False)
      self.logger.info(f"✓ seqUpdate 저장 완료: {self.seqUpdateFile}")
      return True
    except Exception as e:
      self.logger.error(f"✗ seqUpdate 저장 실패: {e}")
      return False

  def fetchApi(self, url: str, params: Dict[str, str],
               retryCount: int = 0) -> Optional[Dict]:
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
      response = requests.get(url, headers=headers, params=params, timeout=30)

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

  def extractDataAndSeqUpdate(self, response: Dict,
                               endpoint: str) -> Tuple[List, int]:
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

  def saveToJsonl(self, endpoint: str, items: List[Dict],
                  seqUpdate: int) -> bool:
    """데이터를 JSON Lines 형식으로 저장

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

    try:
      with open(filepath, 'a', encoding='utf-8') as f:
        for item in items:
          record = {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'source': 'groupib-api',
            'endpoint': endpoint,
            'seqUpdate': seqUpdate,
            'data': item
          }
          f.write(json.dumps(record, ensure_ascii=False) + '\n')

      self.logger.info(f"  ✓ 저장 완료: {filepath} ({len(items)}건)")
      return True

    except Exception as e:
      self.logger.error(f"  ✗ 파일 저장 실패: {filepath} - {e}")
      return False

  def collectSingleEndpoint(self, endpointConfig: Dict,
                            seqUpdates: Dict) -> Tuple[bool, int]:
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
    """모든 엔드포인트 순차 수집

    Returns:
      업데이트된 seqUpdate 딕셔너리
    """
    if not self.endpoints:
      self.logger.error("엔드포인트가 로드되지 않았습니다. loadEndpoints()를 먼저 호출하세요.")
      return {}

    # seqUpdate 로드
    seqUpdates = self.loadSeqUpdate()

    totalEndpoints = len(self.endpoints)
    self.logger.info("")
    self.logger.info("=" * 40)
    self.logger.info(f"수집 사이클 시작 ({totalEndpoints}개 엔드포인트)")
    self.logger.info("=" * 40)

    successCount = 0
    totalRecords = 0

    for idx, endpointConfig in enumerate(self.endpoints, 1):
      endpoint = endpointConfig['endpoint']

      self.logger.info(f"\n[{idx}/{totalEndpoints}] {endpoint}")

      success, recordCount = self.collectSingleEndpoint(endpointConfig, seqUpdates)

      if success:
        successCount += 1
        totalRecords += recordCount

      # Rate Limit 방지를 위한 엔드포인트 간 1초 대기
      if idx < totalEndpoints:
        time.sleep(1)

    self.logger.info("")
    self.logger.info("=" * 40)
    self.logger.info(f"수집 사이클 완료")
    self.logger.info(f"  성공: {successCount}/{totalEndpoints} 엔드포인트")
    self.logger.info(f"  총 수집: {totalRecords}건")
    self.logger.info("=" * 40)

    return seqUpdates
