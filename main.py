# main.py
from memory_tree import MemoryTree
from chat_agent import ChatAgent
import json
import os

# ===== 配置区（请根据你的 Qwen3 部署方式修改）=====
MODEL_NAME = "qwen3-max"  # 或 qwen-max, qwen-plus 等
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # DashScope 兼容 API 地址
API_KEY = "sk-97650777219a49a19c80c1c9791da101"  # 建议通过环境变量设置

if not API_KEY:
    raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量")

# 初始化记忆树和对话代理
tree = MemoryTree()
chat = ChatAgent(tree, model=MODEL_NAME, base_url=BASE_URL, api_key=API_KEY)

print("智能记忆对话系统已启动！（使用 Qwen3 模型，无 function calling）")
print("输入 'tree' 查看记忆树，'exit' 退出。")

while True:
    user = input("\n你: ").strip()
    if user == "exit":
        break
    if user == "tree":
        print(json.dumps(tree.get_full_tree(), ensure_ascii=False, indent=2))
        continue
    
    reply = chat.chat(user)
    print(f"助手: {reply}")