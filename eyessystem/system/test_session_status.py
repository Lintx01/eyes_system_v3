"""测试会话状态获取API"""
import requests

case_id = 'CCC7D361F8'
url = f'http://127.0.0.1:8000/api/clinical/get-progress/{case_id}/'

print(f"请求URL: {url}")

try:
    response = requests.get(url)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.json()}")
except Exception as e:
    print(f"错误: {e}")
