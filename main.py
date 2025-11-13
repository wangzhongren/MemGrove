# main.py
from memory_tree import MemoryTree
from chat_agent import ChatAgent
import json
import os

# ===== 配置区（请根据你的模型部署方式修改）=====
MODEL_NAME = "qwen3-max"  # 或 qwen-max, llama3, gemma 等
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # DashScope 兼容 API 地址
API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 建议通过环境变量设置

# MODEL_NAME = "qwen3:latest"  # 或 qwen-max, llama3, gemma 等
# BASE_URL = "http://localhost:11434/v1";
# API_KEY = "ollama"

if not API_KEY:
    raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量")

# 初始化记忆树和对话代理
tree = MemoryTree()
chat = ChatAgent(tree, model=MODEL_NAME, base_url=BASE_URL, api_key=API_KEY)

print("MemGrove 已启动！🌱")
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
