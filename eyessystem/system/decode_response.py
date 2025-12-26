"""解码诊断选项API响应"""
import json

response_json = '{"success": true, "data": {"diagnosis_options": [{"id": 11, "name": "\\u7cd6\\u5c3f\\u75c5\\u89c6\\u7f51\\u819c\\u75c5\\u53d8", "description": "", "difficulty": "medium"}, {"id": 12, "name": "\\u89c6\\u7f51\\u819c\\u52a8\\u8109\\u963b\\u585e", "description": "", "difficulty": "medium"}, {"id": 16, "name": "\\u8001\\u5e74\\u6027\\u767d\\u5185\\u969c", "description": "", "difficulty": "medium"}], "total_count": 3}, "message": "\\u8bca\\u65ad\\u9009\\u9879\\u83b7\\u53d6\\u6210\\u529f"}'

data = json.loads(response_json)
print(json.dumps(data, ensure_ascii=False, indent=2))
