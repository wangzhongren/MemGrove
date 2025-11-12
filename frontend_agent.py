# frontend_agent.py

import os
from openai import OpenAI
from memory_tree_agent import MemoryTreeAgent


class FrontendAgent:
    def __init__(self, memory_agent: MemoryTreeAgent):
        self.memory = memory_agent
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("请设置环境变量 OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

    def _parse_intent_with_llm(self, natural_language: str) -> dict:
        """
        使用 LLM 解析用户意图，返回结构化指令：
        {
            "action": "store" | "recall",
            "path": str (optional),
            "value": str (optional),
            "query_data": {
                "type": "exact" | "keyword",
                "path": str (optional),
                "keyword": str (optional)
            } (仅 recall 时存在)
        }
        """
        prompt = f"""你是一个记忆系统代理。请将用户的自然语言请求转换为以下 JSON 格式：

- 如果是存储请求（如“记住...”、“保存...”），输出：{{"action": "store", "path": "...", "value": "..."}}
- 如果是任何类型的回忆请求（如“查询...”、“搜索...”、“找一下...”），输出：{{"action": "recall", "query_data": {{"type": "...", ...}}}}

其中 query_data 的规则：
- 精确路径回忆：{{"type": "exact", "path": "/user/name"}}
- 关键词回忆：{{"type": "keyword", "keyword": "AI"}}

用户输入：{natural_language}

只输出 JSON，不要任何其他内容。"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个精准的记忆操作代理，只输出指定 JSON。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=250
        )

        try:
            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except Exception as e:
            raise ValueError(f"LLM 返回格式错误: {e}")

    def query(self, natural_language: str) -> str:
        try:
            intent = self._parse_intent_with_llm(natural_language)
            action = intent.get("action")

            if action == "store":
                path = intent.get("path", "").strip()
                value = intent.get("value", "").strip()
                if not path or not value:
                    return "❌ LLM 解析失败：缺少 path 或 value"
                self.memory.store(path, value)
                return f"✅ 已记住：{path} = {value}"

            elif action == "recall":
                query_data = intent.get("query_data")
                if not isinstance(query_data, dict):
                    return "❌ LLM 解析失败：query_data 格式错误"
                
                # 将结构化查询数据传递给记忆代理进行统一回忆
                results = self.memory.recall(query_data)
                
                if not results:
                    return "❌ 未找到相关记忆"
                
                # 格式化回忆结果
                if query_data.get("type") == "exact":
                    return f"🔍 回忆结果：{results[0]['value']}"
                else:  # keyword
                    lines = [f"- {r['path']}: {r['value']}" for r in results]
                    return "🔍 回忆结果：\n" + "\n".join(lines)

            else:
                return "🤖 无法识别的操作类型"

        except Exception as e:
            return f"❌ 处理失败：{str(e)}"