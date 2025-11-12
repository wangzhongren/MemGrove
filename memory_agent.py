# memory_agent.py
import openai
import json
from memory_tree import MemoryTree

class MemoryAgent:
    def __init__(self, tree: MemoryTree, model="qwen3", base_url=None, api_key=None):
        self.tree = tree
        self.model = model
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key)

    def maybe_remember(self, user_input: str) -> bool:
        """
        让 LLM 判断：这条用户输入是否包含值得长期记忆的信息？
        返回 True 表示应该记忆，False 表示忽略。
        """
        prompt = f"""
你是一个记忆过滤器。请判断以下用户输入是否包含**值得存入长期记忆**的信息。

值得记忆的信息包括：
- 个人信息（姓名、年龄、住址、联系方式等）
- 重要经历（项目、旅行、学习、工作等）
- 偏好与习惯（喜欢的食物、运动、书籍等）
- 具体事实或计划（“我下周去上海”、“我买了 MacBook”）

不值得记忆的内容：
- 问候语（“你好”、“谢谢”）
- 临时性对话（“在吗？”、“帮我查一下”）
- 模糊或无实质信息的句子

用户输入：
"{user_input}"

请严格返回 JSON：
{{"should_remember": true | false}}
"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            decision = json.loads(resp.choices[0].message.content)
            return bool(decision.get("should_remember", False))
        except Exception:
            return False

    def classify_and_store(self, user_input: str) -> str:
        """仅在 should_remember=True 时调用"""
        all_categories = self.tree.get_all_nodes_for_classification()
        
        prompt = f"""
你是一个智能记忆路由系统。用户输入了一段**值得记忆**的信息，请决定如何存储。

用户输入：
"{user_input}"

可用的分类路径：
{json.dumps(all_categories, ensure_ascii=False, indent=2)}

请返回 JSON：
{{
  "action": "attach" | "create",
  "target_id": "node_id 或 null",
  "new_category": "新分类名 或 null",
  "summary": "记忆摘要（<15字）"
}}
"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            decision = json.loads(resp.choices[0].message.content)

            if decision["action"] == "create" and decision.get("new_category"):
                parent_id = "root"
                new_id = self.tree.create_subcategory(parent_id, decision["new_category"])
                final_id = self.tree.add_memory(decision["summary"], new_id)
            else:
                target_id = decision.get("target_id") or "root"
                if target_id not in self.tree.nodes:
                    target_id = "root"
                final_id = self.tree.add_memory(decision["summary"], target_id)

            self.tree.nodes[final_id].touch()
            return f"记忆已存：{decision['summary']}"
        except Exception:
            final_id = self.tree.add_memory(f"[原始] {user_input}", "root")
            self.tree.nodes[final_id].touch()
            return f"记忆已存（默认）：{user_input[:20]}..."

    def search_memory(self, query: str) -> str:
        """
        使用 LLM 从扁平化的记忆视图中检索最相关内容。
        """
        flat_memories = self.tree.get_flat_memory_view()
        
        if not flat_memories:
            return "无相关记忆。"

        # 构造紧凑的 key-value 列表
        memories_text = "\n".join([
            f"{i+1}. [{entry['path']}] {entry['content']}"
            for i, entry in enumerate(flat_memories)
        ])

        prompt = f"""
你是一个智能记忆助手。请根据用户的问题，从以下记忆库中选择**最相关的1-2条**信息。

用户问题：
"{query}"

记忆库（编号. [路径] 内容）：
{memories_text}

请返回 JSON：
{{"selected": [1, 3]}}  // 选中的编号列表，从1开始
如果无相关记忆，返回：{{"selected": []}}
"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(resp.choices[0].message.content)
            indices = result.get("selected", [])
            
            snippets = []
            for idx in indices:
                if 1 <= idx <= len(flat_memories):
                    entry = flat_memories[idx - 1]
                    snippets.append(f"{entry['path']}: {entry['content']}")
            
            return "\n".join(snippets) if snippets else "无相关记忆。"
        except Exception:
            return "无相关记忆。"