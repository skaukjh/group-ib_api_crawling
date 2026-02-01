"""
API 인증 테스트 스크립트
"""

import base64
import requests
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()
username = os.getenv('username')
api_key = os.getenv('api_key')

print(f"Username: {username}")
print(f"API Key: {api_key[:10]}...")

# Base64 인코딩
auth_string = f"{username}:{api_key}"
auth_bytes = auth_string.encode("ascii")
auth_b64 = base64.b64encode(auth_bytes)
auth_b64_str = auth_b64.decode("ascii")

print(f"\nBase64 인코딩 결과: {auth_b64_str[:20]}...")

# 헤더 생성
headers = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54",
  "Authorization": f"Basic {auth_b64_str}",
  "Accept": "*/*"
}

# 인증 테스트
print("\n=== 인증 테스트 ===")
auth_url = "https://tap.group-ib.com/api/v2/user/granted_collections"
print(f"URL: {auth_url}")

try:
  response = requests.get(auth_url, headers=headers, timeout=30)
  print(f"상태 코드: {response.status_code}")
  print(f"응답 헤더: {dict(response.headers)}")

  if response.status_code == 200:
    print("\n[OK] 인증 성공!")
    print(f"응답: {response.text[:200]}")
  else:
    print(f"\n[FAIL] 인증 실패")
    print(f"응답: {response.text[:500]}")

except Exception as e:
  print(f"\n[ERROR] 오류 발생: {e}")

# 첫 번째 엔드포인트 테스트
print("\n\n=== 첫 번째 엔드포인트 테스트 ===")
test_url = "https://tap.group-ib.com/api/v2/apt/threat_actor/updated"
params = {'limit': '10'}
print(f"URL: {test_url}")
print(f"Params: {params}")

try:
  response = requests.get(test_url, headers=headers, params=params, timeout=30)
  print(f"상태 코드: {response.status_code}")

  if response.status_code == 200:
    print("\n[OK] 데이터 수집 성공!")
    data = response.json()
    print(f"응답 키: {list(data.keys())}")
    if 'seqUpdate' in data:
      print(f"seqUpdate: {data['seqUpdate']}")
    print(f"응답 일부: {str(data)[:300]}")
  else:
    print(f"\n[FAIL] 데이터 수집 실패")
    print(f"응답: {response.text[:500]}")

except Exception as e:
  print(f"\n[ERROR] 오류 발생: {e}")
