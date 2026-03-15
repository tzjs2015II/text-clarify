#!/usr/bin/env python3
import requests
import json

payload = {
    "model": "qwen3.5-27b-text",
    "prompt": "你好",
    "stream": False,
    "think": False,
    "options": {
        "num_predict": 100
    }
}

print("发送请求 (think=False)...")
try:
    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json=payload,
        timeout=120
    )
    
    print(f"状态码: {response.status_code}")
    print(f"响应长度: {len(response.content)} 字节")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print(f"\n响应文本: '{result.get('response', '')}'")
    else:
        print(f"错误: {response.text}")
except Exception as e:
    print(f"错误: {e}")