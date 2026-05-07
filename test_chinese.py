import json
import urllib.request

data = json.dumps({
    "title": "OPEC+宣布大幅减产原油",
    "content": "石油输出国组织及其盟国(OPEC+)召开紧急会议，决定从下月开始大幅减产原油，日产量减少500万桶。",
    "use_cache": False
}, ensure_ascii=False).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8080/api/v1/analyze',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print("Success:", result.get('success'))
        if result.get('error'):
            print("Error:", result['error'])
        else:
            print("Event type:", result['data']['event_analysis']['event_type'])
            print("Signals count:", len(result['data']['signals']))
except urllib.error.HTTPError as e:
    print('HTTP Error:', e.read().decode('utf-8'))
except Exception as e:
    print('Error:', e)
