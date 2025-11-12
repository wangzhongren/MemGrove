# chat_agent.py
import openai
from memory_tree import MemoryTree
from memory_agent import MemoryAgent

class ChatAgent:
    def __init__(self, tree: MemoryTree, model="qwen3", base_url=None, api_key=None):
        self.tree = tree
        self.memory_agent = MemoryAgent(tree, model, base_url, api_key)
        self.model = model
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self.messages = [{"role": "system", "content": (
            "你是智能助手，拥有永久记忆能力。\n"
            "1. 所有回答都应基于用户的长期记忆和当前对话上下文。\n"
            "2. 如果记忆中没有相关信息，请如实回答“我不记得”或“不知道”。\n"
            "3. 不要编造信息。"
        )}]

    def chat(self, user_input: str) -> str:
        # === 第一步：决定是否存储新记忆 ===
        if self.memory_agent.maybe_remember(user_input):
            self.memory_agent.classify_and_store(user_input)

        # === 第二步：主动检索可能相关的记忆（预测式）===
        relevant_memory = self.memory_agent.search_memory(user_input)
        
        # === 第三步：构造带记忆上下文的消息 ===
        messages_for_reply = self.messages.copy()
        if relevant_memory and relevant_memory != "无相关记忆。":
            messages_for_reply.append({
                "role": "system",
                "content": f"相关记忆：\n{relevant_memory}"
            })
        messages_for_reply.append({"role": "user", "content": user_input})

        # === 第四步：生成最终回答 ===
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages_for_reply
        )
        final_reply = response.choices[0].message.content or "好的。"

        # === 第五步：更新对话历史（不包含临时 system 记忆）===
        self.messages.append({"role": "user", "content": user_input})
        self.messages.append({"role": "assistant", "content": final_reply})
        return final_reply