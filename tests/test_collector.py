"""
GroupIBCollector 클래스 단위 테스트

실행 방법:
  pytest tests/test_collector.py -v
"""

import os
import json
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.collector import (
  GroupIBCollector,
  GroupIBAPIError,
  AuthenticationError,
  RateLimitError
)


@pytest.fixture
def mockEnv(monkeypatch):
  """환경 변수 Mock 설정"""
  monkeypatch.setenv('GROUPIB_USERNAME', 'test@example.com')
  monkeypatch.setenv('GROUPIB_API_KEY', 'test_api_key_12345')
  monkeypatch.setenv('GROUPIB_BASE_URL', 'https://test.group-ib.com')
  monkeypatch.setenv('REQUEST_TIMEOUT', '10')
  monkeypatch.setenv('RATE_LIMIT_WAIT', '0')  # 테스트 시 대기 시간 제거
  monkeypatch.setenv('MAX_RETRIES', '2')


@pytest.fixture
def tempDir():
  """임시 디렉토리 생성"""
  with tempfile.TemporaryDirectory() as tmpdir:
    yield tmpdir


class TestGroupIBCollector:
  """GroupIBCollector 클래스 테스트"""

  def testInitialization(self, mockEnv):
    """초기화 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()

      assert collector.username == 'test@example.com'
      assert collector.apiKey == 'test_api_key_12345'
      assert collector.baseUrl == 'https://test.group-ib.com'
      assert collector.requestTimeout == 10
      assert collector.rateLimitWait == 0
      assert collector.maxRetries == 2
      assert isinstance(collector.endpoints, list)
      assert isinstance(collector.failedEndpoints, list)

  def testInitializationWithoutCredentials(self, monkeypatch):
    """자격증명 없이 초기화 시 에러 발생"""
    monkeypatch.delenv('GROUPIB_USERNAME', raising=False)
    monkeypatch.delenv('GROUPIB_API_KEY', raising=False)

    with pytest.raises(ValueError) as excinfo:
      GroupIBCollector()

    assert "GROUPIB_USERNAME" in str(excinfo.value)

  def testBuildAuthHeader(self, mockEnv):
    """인증 헤더 생성 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()
      headers = collector.buildAuthHeader()

      assert 'Authorization' in headers
      assert headers['Authorization'].startswith('Basic ')
      assert 'User-Agent' in headers
      assert 'Accept' in headers

  def testUrlToFilename(self, mockEnv):
    """URL을 파일명으로 변환 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()

      # 테스트 케이스
      testCases = [
        ('/api/v2/apt/threat_actor/updated', 'apt_threat_actor_updated.jsonl'),
        ('/api/v2/hi/threat/updated', 'hi_threat_updated.jsonl'),
        ('/api/v2/ioc/common/updated', 'ioc_common_updated.jsonl'),
      ]

      for endpoint, expectedFilename in testCases:
        result = collector.urlToFilename(endpoint)
        assert result == expectedFilename

  def testExtractDataAndSeqUpdate(self, mockEnv):
    """응답에서 데이터 추출 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()

      # items 필드 테스트
      response1 = {
        'seqUpdate': 12345,
        'items': [{'id': 1}, {'id': 2}]
      }
      dataList1, seqUpdate1 = collector.extractDataAndSeqUpdate(response1, '/test')
      assert len(dataList1) == 2
      assert seqUpdate1 == 12345

      # data 필드 테스트
      response2 = {
        'seqUpdate': 67890,
        'data': [{'id': 3}]
      }
      dataList2, seqUpdate2 = collector.extractDataAndSeqUpdate(response2, '/test')
      assert len(dataList2) == 1
      assert seqUpdate2 == 67890

      # results 필드 테스트
      response3 = {
        'seqUpdate': 111,
        'results': [{'id': 4}, {'id': 5}, {'id': 6}]
      }
      dataList3, seqUpdate3 = collector.extractDataAndSeqUpdate(response3, '/test')
      assert len(dataList3) == 3
      assert seqUpdate3 == 111

      # 데이터 필드 없음
      response4 = {'seqUpdate': 0}
      dataList4, seqUpdate4 = collector.extractDataAndSeqUpdate(response4, '/test')
      assert len(dataList4) == 0
      assert seqUpdate4 == 0

  @patch('src.collector.requests.get')
  def testAuthenticateSuccess(self, mockGet, mockEnv):
    """인증 성공 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()

      # Mock 응답 설정
      mockResponse = Mock()
      mockResponse.status_code = 200
      mockGet.return_value = mockResponse

      result = collector.authenticate()
      assert result is True

  @patch('src.collector.requests.get')
  def testAuthenticateFailure(self, mockGet, mockEnv):
    """인증 실패 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()

      # Mock 응답 설정 (401 Unauthorized)
      mockResponse = Mock()
      mockResponse.status_code = 401
      mockGet.return_value = mockResponse

      with pytest.raises(AuthenticationError):
        collector.authenticate()

  def testLoadSeqUpdate(self, mockEnv, tempDir):
    """seqUpdate 로드 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()
      collector.seqUpdateFile = os.path.join(tempDir, 'seq_update.json')

      # 파일이 없는 경우
      result1 = collector.loadSeqUpdate()
      assert result1 == {}

      # 파일이 있는 경우
      testData = {'/api/v2/test': 12345}
      with open(collector.seqUpdateFile, 'w') as f:
        json.dump(testData, f)

      result2 = collector.loadSeqUpdate()
      assert result2 == testData

  def testSaveSeqUpdate(self, mockEnv, tempDir):
    """seqUpdate 저장 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()
      collector.seqUpdateFile = os.path.join(tempDir, 'seq_update.json')

      testData = {'/api/v2/test': 99999}
      result = collector.saveSeqUpdate(testData)

      assert result is True
      assert os.path.exists(collector.seqUpdateFile)

      # 저장된 데이터 확인
      with open(collector.seqUpdateFile, 'r') as f:
        savedData = json.load(f)
      assert savedData == testData

      # 백업 파일 확인
      backupFile = collector.seqUpdateFile + '.bak'
      # 두 번째 저장 시 백업 파일 생성됨
      collector.saveSeqUpdate({'/api/v2/test': 100000})
      assert os.path.exists(backupFile)

  def testSaveToJsonl(self, mockEnv, tempDir):
    """JSON Lines 저장 테스트"""
    with patch.object(GroupIBCollector, '_setupLogger'):
      collector = GroupIBCollector()
      collector.outputsDir = tempDir

      endpoint = '/api/v2/test'
      items = [
        {'id': 1, 'name': 'test1'},
        {'id': 2, 'name': 'test2'}
      ]
      seqUpdate = 12345

      result = collector.saveToJsonl(endpoint, items, seqUpdate)
      assert result is True

      # 파일 내용 확인
      filename = collector.urlToFilename(endpoint)
      filepath = os.path.join(tempDir, filename)
      assert os.path.exists(filepath)

      with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

      assert len(lines) == 2

      # 첫 번째 라인 검증
      firstRecord = json.loads(lines[0])
      assert firstRecord['endpoint'] == endpoint
      assert firstRecord['seqUpdate'] == seqUpdate
      assert firstRecord['data']['id'] == 1


if __name__ == '__main__':
  pytest.main([__file__, '-v'])
