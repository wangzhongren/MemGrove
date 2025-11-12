# memory_tree.py
import json
import time
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

class MemoryNode(BaseModel):
    id: str
    name: str
    content: str = ""
    parent_id: Optional[str] = None
    children: Dict[str, 'MemoryNode'] = {}
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0

    def touch(self):
        self.last_accessed = time.time()
        self.access_count += 1

class MemoryTree:
    def __init__(self, schema_path: str = "schema.json", save_path: str = "memory_tree.json"):
        self.save_path = save_path
        self.nodes: Dict[str, MemoryNode] = {}
        
        # 尝试从持久化文件加载
        if os.path.exists(self.save_path):
            self._load_from_file()
        else:
            # 首次启动：从 schema 初始化
            self._load_initial_schema(schema_path)
            self._assign_ids(self.root, None)
            self.save_to_file()  # 保存初始结构

    def _load_initial_schema(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.root = self._dict_to_node("root", "ROOT", data["root"])
        self.nodes["root"] = self.root

    def _dict_to_node(self, node_id: str, name: str, data: Dict) -> MemoryNode:
        node = MemoryNode(id=node_id, name=name, created_at=time.time(), last_accessed=time.time())
        for k, v in data.items():
            child_id = f"{node_id}:{k}"
            child = self._dict_to_node(child_id, k, v)
            node.children[k] = child
            self.nodes[child_id] = child
        return node

    def _assign_ids(self, node: MemoryNode, parent_id: Optional[str]):
        node.parent_id = parent_id
        self.nodes[node.id] = node
        for child in node.children.values():
            self._assign_ids(child, node.id)

    def _load_from_file(self):
        """从 JSON 文件加载记忆树"""
        with open(self.save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建所有节点
        self.nodes = {}
        for node_id, node_data in data["nodes"].items():
            # 移除 children 字段（稍后重建）
            children_data = node_data.pop("children", {})
            node = MemoryNode(**node_data)
            self.nodes[node_id] = node
        
        # 重建父子关系
        for node_id, node_data in data["nodes"].items():
            parent_id = self.nodes[node_id].parent_id
            if parent_id and parent_id in self.nodes:
                self.nodes[parent_id].children[node_id] = self.nodes[node_id]
        
        self.root = self.nodes["root"]

    def save_to_file(self):
        """将记忆树保存到 JSON 文件"""
        # 转换所有节点为 dict
        nodes_dict = {}
        for node_id, node in self.nodes.items():
            node_dict = node.model_dump()
            # 移除 children 引用，避免循环
            node_dict["children"] = {}
            nodes_dict[node_id] = node_dict
        
        data = {
            "nodes": nodes_dict,
            "root_id": "root"
        }
        
        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def find_best_node(self, text: str) -> List[Dict[str, Any]]:
        candidates = []
        def dfs(node: MemoryNode, path: List[str]):
            if node.id == "root": 
                path = []
            score = self._simple_match_score(text, node.name + " " + node.content)
            if score > 0.3:
                candidates.append({
                    "node_id": node.id,
                    "path": " -> ".join(path + [node.name]),
                    "score": score,
                    "has_content": bool(node.content.strip())
                })
            for name, child in node.children.items():
                dfs(child, path + [node.name])
        dfs(self.root, [])
        return sorted(candidates, key=lambda x: -x["score"])[:3]

    def _simple_match_score(self, text: str, target: str) -> float:
        text, target = text.lower(), target.lower()
        if len(target) < 2: return 0
        overlap = len(set(text.split()) & set(target.split()))
        return overlap / max(len(text.split()), 1)

    def add_memory(self, content: str, parent_id: str) -> str:
        if parent_id not in self.nodes:
            return f"父节点 {parent_id} 不存在"
        node_id = f"{parent_id}:mem{int(time.time()*1000)}"
        node = MemoryNode(
            id=node_id, name="记忆", content=content,
            parent_id=parent_id, created_at=time.time(), last_accessed=time.time()
        )
        parent = self.nodes[parent_id]
        parent.children[node_id] = node
        self.nodes[node_id] = node
        self.save_to_file()  # 持久化
        return node_id

    def create_subcategory(self, parent_id: str, category_name: str) -> str:
        if parent_id not in self.nodes:
            return "父节点不存在"
        child_id = f"{parent_id}:{category_name}"
        if child_id in self.nodes:
            return "分类已存在"
        node = MemoryNode(id=child_id, name=category_name, parent_id=parent_id,
                          created_at=time.time(), last_accessed=time.time())
        self.nodes[parent_id].children[child_id] = node
        self.nodes[child_id] = node
        self.save_to_file()  # 持久化
        return child_id

    def get_full_tree(self) -> Dict:
        return self._node_to_dict(self.root)

    def _node_to_dict(self, node: MemoryNode) -> Dict:
        return {
            "name": node.name,
            "content": node.content,
            "meta": {
                "id": node.id,
                "access_count": node.access_count,
                "last_accessed": datetime.fromtimestamp(node.last_accessed).isoformat()
            },
            "children": {k: self._node_to_dict(v) for k, v in node.children.items()}
        }

    def get_all_nodes_for_classification(self) -> List[Dict[str, str]]:
        """
        返回所有可用于挂载新记忆的分类节点（排除 name='记忆' 的叶子记忆节点）
        """
        candidates = []
        def dfs(node: MemoryNode, path: List[str]):
            if node.id == "root":
                current_path = []
            else:
                current_path = path + [node.name]
            # 只收录非“记忆”节点（即分类节点）
            if node.name != "记忆":
                candidates.append({
                    "node_id": node.id,
                    "path": " -> ".join(current_path) if current_path else "ROOT"
                })
            for child in node.children.values():
                dfs(child, current_path)
        dfs(self.root, [])
        return candidates

    def get_flat_memory_view(self) -> List[Dict[str, str]]:
        """
        返回扁平化的记忆视图，仅包含有内容的记忆节点。
        格式：[{"path": "个人信息 -> 基本信息", "content": "张三"}, ...]
        """
        flat_memories = []
        for node in self.nodes.values():
            if node.name == "记忆" and node.content.strip():
                # 构建完整路径
                path_parts = []
                current = node
                while current and current.id != "root":
                    if current.name != "记忆":  # 跳过"记忆"本身，保留分类名
                        path_parts.append(current.name)
                    current = self.nodes.get(current.parent_id)
                path_parts.reverse()
                full_path = " -> ".join(path_parts) if path_parts else "未分类"
                flat_memories.append({
                    "path": full_path,
                    "content": node.content.strip()
                })
        return flat_memories