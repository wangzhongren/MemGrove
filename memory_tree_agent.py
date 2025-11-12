# memory_tree_agent.py

class MemoryNode:
    def __init__(self, key: str, value: str = "", parent=None):
        self.key = key
        self.value = value
        self.parent = parent
        self.children = {}

    def add_child(self, key: str, value: str = ""):
        if key not in self.children:
            self.children[key] = MemoryNode(key=key, value=value, parent=self)
        return self.children[key]

    def get_child(self, key: str):
        return self.children.get(key)

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "children": {k: v.to_dict() for k, v in self.children.items()}
        }

    @classmethod
    def from_dict(cls, data: dict, parent=None):
        node = cls(key=data["key"], value=data.get("value", ""), parent=parent)
        for k, v in data.get("children", {}).items():
            node.children[k] = cls.from_dict(v, parent=node)
        return node


class MemoryTreeAgent:
    def __init__(self):
        self.root = MemoryNode(key="root")

    def store(self, path: str, value: str):
        keys = [k for k in path.strip("/").split("/") if k]
        current = self.root
        for key in keys:
            current = current.add_child(key)
        current.value = value

    def retrieve(self, path: str) -> str:
        keys = [k for k in path.strip("/").split("/") if k]
        current = self.root
        for key in keys:
            current = current.get_child(key)
            if current is None:
                return ""
        return current.value

    def search_by_keyword(self, keyword: str) -> list:
        results = []
        stack = [self.root]
        while stack:
            node = stack.pop()
            if keyword.lower() in node.value.lower() or keyword.lower() in node.key.lower():
                # Reconstruct full path
                path_parts = []
                tmp = node
                while tmp.parent:
                    path_parts.append(tmp.key)
                    tmp = tmp.parent
                path = "/" + "/".join(reversed(path_parts))
                results.append({"path": path, "value": node.value})
            stack.extend(node.children.values())
        return results

    def recall(self, query_data: dict) -> list:
        """
        统一回忆接口：接收结构化查询数据，执行记忆检索
        支持两种模式：
        - 精确路径查询: {"type": "exact", "path": "/user/name"}
        - 关键词搜索: {"type": "keyword", "keyword": "AI"}
        """
        recall_type = query_data.get("type")
        
        if recall_type == "exact":
            path = query_data.get("path", "")
            value = self.retrieve(path)
            if value:
                return [{"path": path, "value": value}]
            else:
                return []
                
        elif recall_type == "keyword":
            keyword = query_data.get("keyword", "")
            return self.search_by_keyword(keyword)
            
        else:
            raise ValueError(f"不支持的回忆类型: {recall_type}")

    def save_to_file(self, filepath: str):
        import json
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.root.to_dict(), f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str):
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.root = MemoryNode.from_dict(data)