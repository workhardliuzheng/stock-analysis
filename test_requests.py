import requests
import json

# 直接测试requests的json参数序列化
payload_simple = {
    'receive_id': 'test123',
    'receive_id_type': 'open_id',
    'msg_type': 'text',
    'content': json.dumps({'text': 'test'})
}

# 尝试1: 使用json参数
print("=== Test 1: Using json parameter ===")
try:
    # 构建请求但不发送
    req = requests.Request('POST', 'https://httpbin.org/post', json=payload_simple)
    prepared = req.prepare()
    print('Body:', prepared.body)
    print('Content-Type:', prepared.headers.get('Content-Type'))
except Exception as e:
    print('Error:', e)

# 尝试2: 使用data参数手动序列化
print("\n=== Test 2: Using data parameter ===")
try:
    req = requests.Request('POST', 'https://httpbin.org/post', 
                          data=json.dumps(payload_simple),
                          headers={'Content-Type': 'application/json'})
    prepared = req.prepare()
    print('Body:', prepared.body)
    print('Content-Type:', prepared.headers.get('Content-Type'))
except Exception as e:
    print('Error:', e)
