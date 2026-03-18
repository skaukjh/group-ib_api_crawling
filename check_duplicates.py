import json
from collections import defaultdict
import os
import sys

outputsDir = r"D:\99. Project\TI\Crawler\외부 인텔리전스 서비스\group-ib_api_crawling-main(2603_정상동작)\group-ib_api_crawling-main\data\outputs"
results = {}

for filename in sorted(os.listdir(outputsDir)):
    if not filename.endswith('.jsonl'):
        continue
    
    filepath = os.path.join(outputsDir, filename)
    id_list = []
    seq_updates = defaultdict(int)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    data = record.get('data', {})
                    
                    # 고유 ID 추출
                    record_id = data.get('id') or data.get('hash')
                    seq = record.get('seqUpdate')
                    
                    if record_id:
                        id_list.append(record_id)
                        seq_updates[seq] += 1
                except:
                    pass
        
        # 중복 확인
        if id_list:
            unique_count = len(set(id_list))
            total_count = len(id_list)
            
            if unique_count < total_count:
                duplicate_ratio = ((total_count - unique_count) / total_count) * 100
                results[filename] = {
                    'total': total_count,
                    'unique': unique_count,
                    'duplicates': total_count - unique_count,
                    'ratio': f"{duplicate_ratio:.1f}%",
                    'seqUpdate_dist': dict(seq_updates)
                }
    except Exception as e:
        pass

# 결과 출력
if results:
    print("=" * 70)
    print("중복 데이터가 발견된 엔드포인트")
    print("=" * 70)
    for filename, data in results.items():
        print(f"\n📄 {filename}")
        print(f"   총 레코드: {data['total']}개")
        print(f"   고유 레코드: {data['unique']}개")
        print(f"   중복: {data['duplicates']}개 ({data['ratio']})")
        print(f"   seqUpdate 분포:")
        for seq in sorted(data['seqUpdate_dist'].keys()):
            print(f"     - {seq}: {data['seqUpdate_dist'][seq]}개")
else:
    print("✓ 모든 엔드포인트에서 중복 데이터 없음")
