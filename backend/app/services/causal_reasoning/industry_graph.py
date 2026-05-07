"""
产业链知识图谱
使用 networkx 构建确定性产业链关系，作为 LLM 推理的约束骨架
"""
import json
import os
import logging
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

logger = logging.getLogger(__name__)

# 图谱数据路径（可配置）
GRAPH_DATA_PATH = os.getenv("KNOWLEDGE_GRAPH_JSON_PATH", os.path.join(os.path.dirname(__file__), "graph_data.json"))
# 自动重载间隔（秒），0 表示不自动重载
AUTO_RELOAD_INTERVAL = int(os.getenv("KNOWLEDGE_GRAPH_RELOAD_INTERVAL", "0"))


@dataclass
class PathResult:
    """路径搜索结果"""
    path: List[str]
    total_rate: float
    total_lag_days: int
    edges: List[Dict[str, Any]]
    confidence: float


@dataclass
class GraphNode:
    """图谱节点"""
    id: str
    name: str
    aliases: List[str]
    category: str
    is_tradeable: bool
    related_etf: List[str] = None
    a_share: List[str] = None
    us_stock: List[str] = None


@dataclass
class GraphEdge:
    """图谱边"""
    from_node: str
    to_node: str
    relation_type: str
    transmission_rate: float
    time_lag_days: int
    confidence: float
    description: str


class IndustryKnowledgeGraph:
    """产业链知识图谱（支持动态重载）"""

    def __init__(self, graph_data_path: str = None):
        self.graph_data_path = graph_data_path or GRAPH_DATA_PATH
        self._graph = None
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._name_to_id: Dict[str, str] = {}  # 名称/别名 -> id 映射
        self._initialized = False
        self._last_load_time = 0
        self._last_mtime = 0

    def _should_reload(self) -> bool:
        """检查是否需要重新加载（文件变更或自动重载周期到达）"""
        if not self._initialized:
            return True
        # 根据文件修改时间重载
        if os.path.exists(self.graph_data_path):
            current_mtime = os.path.getmtime(self.graph_data_path)
            if current_mtime != self._last_mtime:
                logger.info(f"图谱文件 {self.graph_data_path} 已修改，触发重载")
                return True
        # 自动周期重载
        if AUTO_RELOAD_INTERVAL > 0:
            if time.time() - self._last_load_time > AUTO_RELOAD_INTERVAL:
                logger.info(f"自动重载间隔 {AUTO_RELOAD_INTERVAL}s 到期，触发重载")
                return True
        return False

    def _load_data(self) -> bool:
        """加载图谱数据（自动检测重载）"""
        if not self._should_reload():
            return True

        try:
            with open(self.graph_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 清空现有数据
            self._nodes.clear()
            self._edges.clear()
            self._name_to_id.clear()
            self._graph = None

            # 加载节点
            for node_data in data.get("industries", []):
                node = GraphNode(
                    id=node_data["id"],
                    name=node_data["name"],
                    aliases=node_data.get("aliases", []),
                    category=node_data.get("category", ""),
                    is_tradeable=node_data.get("is_tradeable", False),
                    related_etf=node_data.get("related_etf", []),
                    a_share=node_data.get("a_share", []),
                    us_stock=node_data.get("us_stock", [])
                )
                self._nodes[node.id] = node

                # 建立名称映射
                self._name_to_id[node.name] = node.id
                for alias in node.aliases:
                    self._name_to_id[alias] = node.id

            # 加载边
            for edge_data in data.get("relationships", []):
                edge = GraphEdge(
                    from_node=edge_data["from"],
                    to_node=edge_data["to"],
                    relation_type=edge_data["relation_type"],
                    transmission_rate=edge_data.get("transmission_rate", 0.5),
                    time_lag_days=edge_data.get("time_lag_days", 7),
                    confidence=edge_data.get("confidence", 0.8),
                    description=edge_data.get("description", "")
                )
                self._edges.append(edge)

            self._initialized = True
            self._last_load_time = time.time()
            if os.path.exists(self.graph_data_path):
                self._last_mtime = os.path.getmtime(self.graph_data_path)
            logger.info(f"图谱数据加载完成: {len(self._nodes)} 节点, {len(self._edges)} 边")
            # 重新构建 networkx 图
            self.build_graph()
            return True

        except Exception as e:
            logger.error(f"加载图谱数据失败: {e}")
            return False

    def reload_from_json(self, json_data: dict) -> bool:
        """
        从给定的 JSON 字典重新加载图谱数据（用于 API 动态更新）

        Args:
            json_data: 包含 "industries" 和 "relationships" 的字典

        Returns:
            是否成功
        """
        try:
            # 清空现有数据
            self._nodes.clear()
            self._edges.clear()
            self._name_to_id.clear()
            self._graph = None

            # 加载节点
            for node_data in json_data.get("industries", []):
                node = GraphNode(
                    id=node_data["id"],
                    name=node_data["name"],
                    aliases=node_data.get("aliases", []),
                    category=node_data.get("category", ""),
                    is_tradeable=node_data.get("is_tradeable", False),
                    related_etf=node_data.get("related_etf", []),
                    a_share=node_data.get("a_share", []),
                    us_stock=node_data.get("us_stock", [])
                )
                self._nodes[node.id] = node
                self._name_to_id[node.name] = node.id
                for alias in node.aliases:
                    self._name_to_id[alias] = node.id

            # 加载边
            for edge_data in json_data.get("relationships", []):
                edge = GraphEdge(
                    from_node=edge_data["from"],
                    to_node=edge_data["to"],
                    relation_type=edge_data["relation_type"],
                    transmission_rate=edge_data.get("transmission_rate", 0.5),
                    time_lag_days=edge_data.get("time_lag_days", 7),
                    confidence=edge_data.get("confidence", 0.8),
                    description=edge_data.get("description", "")
                )
                self._edges.append(edge)

            self._initialized = True
            self._last_load_time = time.time()
            # 保存到文件（可选）
            try:
                with open(self.graph_data_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                self._last_mtime = os.path.getmtime(self.graph_data_path)
            except Exception as e:
                logger.warning(f"保存图谱文件失败: {e}")
            self.build_graph()
            logger.info(f"图谱动态重载完成: {len(self._nodes)} 节点, {len(self._edges)} 边")
            return True

        except Exception as e:
            logger.error(f"动态重载图谱失败: {e}")
            return False

    def build_graph(self) -> Optional[Any]:
        """构建 networkx 有向图"""
        if not self._load_data():
            return None

        if not NETWORKX_AVAILABLE:
            logger.warning("networkx 未安装，使用简化模式")
            return None

        self._graph = nx.DiGraph()

        # 添加节点
        for node_id, node in self._nodes.items():
            self._graph.add_node(
                node_id,
                name=node.name,
                category=node.category,
                is_tradeable=node.is_tradeable
            )

        # 添加边
        for edge in self._edges:
            self._graph.add_edge(
                edge.from_node,
                edge.to_node,
                relation_type=edge.relation_type,
                transmission_rate=edge.transmission_rate,
                time_lag_days=edge.time_lag_days,
                confidence=edge.confidence,
                description=edge.description
            )

        logger.info(f"networkx 图谱构建完成: {self._graph.number_of_nodes()} 节点, {self._graph.number_of_edges()} 边")
        return self._graph

    def add_dynamic_relationships(self, dynamic_relationships: List[Dict[str, Any]]):
        """
        添加动态学习的关系到图谱

        Args:
            dynamic_relationships: 动态发现的关系列表
        """
        if not dynamic_relationships:
            return

        if self._graph is None:
            self.build_graph()

        for rel in dynamic_relationships:
            from_id = rel.get("from")
            to_id = rel.get("to")

            if not from_id or not to_id:
                continue

            # 添加节点（如果不存在）
            if from_id not in self._graph:
                self._graph.add_node(from_id, name=from_id, category="动态学习", is_tradeable=False)
            if to_id not in self._graph:
                self._graph.add_node(to_id, name=to_id, category="动态学习", is_tradeable=False)

            # 添加边（使用更新版本的参数）
            if self._graph.has_edge(from_id, to_id):
                # 更新现有边
                existing = self._graph.edges[from_id, to_id]
                new_confidence = max(existing.get("confidence", 0.5), rel.get("confidence", 0.5))
                new_rate = (existing.get("transmission_rate", 0.5) + rel.get("transmission_rate", 0.5)) / 2
                self._graph.edges[from_id, to_id]["confidence"] = new_confidence
                self._graph.edges[from_id, to_id]["transmission_rate"] = new_rate
            else:
                # 添加新边
                self._graph.add_edge(
                    from_id,
                    to_id,
                    relation_type=rel.get("relation_type", "成本传导"),
                    transmission_rate=rel.get("transmission_rate", 0.5),
                    time_lag_days=rel.get("time_lag_days", 7),
                    confidence=rel.get("confidence", 0.5),
                    description=f"动态学习发现 (证据数: {rel.get('evidence_count', 1)})"
                )

        logger.info(f"动态关系已添加: {len(dynamic_relationships)} 条")

    @property
    def graph(self) -> Optional[Any]:
        """获取图谱对象"""
        if self._graph is None:
            self.build_graph()
        return self._graph

    @property
    def nodes(self) -> Dict[str, GraphNode]:
        """获取所有节点"""
        self._load_data()
        return self._nodes

    @property
    def edges(self) -> List[GraphEdge]:
        """获取所有边"""
        self._load_data()
        return self._edges

    def match_nodes(self, entities: List[str]) -> List[str]:
        """
        将实体列表匹配到图谱节点

        Args:
            entities: 从事件中提取的核心实体列表

        Returns:
            匹配到的图谱节点 ID 列表
        """
        self._load_data()

        matched_ids = []
        for entity in entities:
            entity_lower = entity.lower()

            # 精确匹配名称和别名
            for name, node_id in self._name_to_id.items():
                if name.lower() in entity_lower or entity_lower in name.lower():
                    if node_id not in matched_ids:
                        matched_ids.append(node_id)

        return matched_ids

    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点详细信息"""
        self._load_data()

        if node_id not in self._nodes:
            return None

        node = self._nodes[node_id]
        return {
            "id": node.id,
            "name": node.name,
            "category": node.category,
            "is_tradeable": node.is_tradeable,
            "related_etf": node.related_etf or [],
            "a_share": node.a_share or [],
            "us_stock": node.us_stock or [],
            "out_edges": self._get_out_edges(node_id),
            "in_edges": self._get_in_edges(node_id)
        }

    def _get_out_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """获取节点的出边"""
        return [
            {
                "to": e.to_node,
                "to_name": self._nodes.get(e.to_node, type('', (), {'name': e.to_node})()).name if e.to_node in self._nodes else e.to_node,
                "relation_type": e.relation_type,
                "transmission_rate": e.transmission_rate,
                "time_lag_days": e.time_lag_days
            }
            for e in self._edges
            if e.from_node == node_id
        ]

    def _get_in_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """获取节点的入边"""
        return [
            {
                "from": e.from_node,
                "from_name": self._nodes.get(e.from_node, type('', (), {'name': e.from_node})()).name if e.from_node in self._nodes else e.from_node,
                "relation_type": e.relation_type,
                "transmission_rate": e.transmission_rate,
                "time_lag_days": e.time_lag_days
            }
            for e in self._edges
            if e.to_node == node_id
        ]

    def get_affected_paths(
        self,
        start_nodes: List[str],
        depth: int = 3
    ) -> List[PathResult]:
        """
        BFS 遍历获取从起始节点开始的所有受影响路径

        Args:
            start_nodes: 起始节点 ID 列表
            depth: 最大深度

        Returns:
            路径结果列表
        """
        if self.graph is None:
            return []

        results = []
        visited_paths = set()  # 避免重复路径

        for start in start_nodes:
            if start not in self.graph:
                continue

            # BFS
            queue = [(start, [start], 1.0, 0, [])]  # (current_node, path, total_rate, total_lag, edges)

            while queue:
                current, path, total_rate, total_lag, edges = queue.pop(0)

                if len(path) - 1 >= depth:
                    continue

                for successor in self.graph.successors(current):
                    if successor in path:  # 避免循环
                        continue

                    edge_data = self.graph.edges[current, successor]
                    new_rate = total_rate * edge_data['transmission_rate']
                    new_lag = total_lag + edge_data['time_lag_days']

                    new_path = path + [successor]
                    new_edges = edges + [{
                        'from': current,
                        'to': successor,
                        'relation_type': edge_data['relation_type'],
                        'transmission_rate': edge_data['transmission_rate'],
                        'time_lag_days': edge_data['time_lag_days'],
                        'confidence': edge_data['confidence']
                    }]

                    # 创建路径签名
                    path_signature = '->'.join(new_path)
                    if path_signature not in visited_paths:
                        visited_paths.add(path_signature)

                        results.append(PathResult(
                            path=new_path,
                            total_rate=new_rate,
                            total_lag_days=new_lag,
                            edges=new_edges,
                            confidence=min(edge_data['confidence'], 0.95)
                        ))

                    queue.append((successor, new_path, new_rate, new_lag, new_edges))

        # 按传导系数排序
        results.sort(key=lambda x: x.total_rate, reverse=True)
        return results

    def get_graph_constraints(
        self,
        start_nodes: List[str],
        depth: int = 3,
        max_paths: int = 10
    ) -> str:
        """
        获取格式化的图谱约束字符串，用于注入 LLM prompt

        Args:
            start_nodes: 起始节点列表
            depth: 最大深度
            max_paths: 最大路径数

        Returns:
            格式化的约束字符串
        """
        paths = self.get_affected_paths(start_nodes, depth)

        if not paths:
            return ""

        constraints_parts = ["=== 产业链知识图谱约束 ==="]
        constraints_parts.append(f"已知传导路径 (共 {len(paths)} 条，显示前 {max_paths} 条):\n")

        for i, path_result in enumerate(paths[:max_paths]):
            # 获取节点名称
            node_names = []
            for node_id in path_result.path:
                if node_id in self._nodes:
                    node_names.append(self._nodes[node_id].name)
                else:
                    node_names.append(node_id)

            path_str = " → ".join(node_names)

            constraints_parts.append(
                f"{i+1}. {path_str}\n"
                f"   累积传导率: {path_result.total_rate:.1%}, "
                f"累积时滞: {path_result.total_lag_days}天, "
                f"置信度: {path_result.confidence:.0%}"
            )

            # 详细边信息
            for edge in path_result.edges:
                from_name = self._nodes.get(edge['from'], type('', (), {'name': edge['from']})()).name if edge['from'] in self._nodes else edge['from']
                to_name = self._nodes.get(edge['to'], type('', (), {'name': edge['to']})()).name if edge['to'] in self._nodes else edge['to']
                constraints_parts.append(
                    f"   - {from_name} → {to_name}: "
                    f"{edge['relation_type']}, "
                    f"传导率 {edge['transmission_rate']:.0%}, "
                    f"滞后 {edge['time_lag_days']}天"
                )

        return "\n".join(constraints_parts)

    def get_tradeable_stocks(self, node_id: str) -> Dict[str, List[str]]:
        """获取节点的可交易标的"""
        self._load_data()

        if node_id not in self._nodes:
            return {}

        node = self._nodes[node_id]
        result = {}

        if node.a_share:
            result["a_share"] = node.a_share
        if node.us_stock:
            result["us_stock"] = node.us_stock
        if node.related_etf:
            result["etf"] = node.related_etf

        return result

    def find_similar_industries(self, node_id: str, limit: int = 3) -> List[str]:
        """查找相似行业的节点"""
        self._load_data()

        if node_id not in self._nodes:
            return []

        target = self._nodes[node_id]

        # 基于共享的出边/入边找相似
        target_out = {e.to_node for e in self._edges if e.from_node == node_id}
        target_in = {e.from_node for e in self._edges if e.to_node == node_id}

        similarities = []
        for other_id, other_node in self._nodes.items():
            if other_id == node_id:
                continue

            other_out = {e.to_node for e in self._edges if e.from_node == other_id}
            other_in = {e.from_node for e in self._edges if e.to_node == other_id}

            # Jaccard 相似度
            out_jaccard = len(target_out & other_out) / len(target_out | other_out) if target_out | other_out else 0
            in_jaccard = len(target_in & other_in) / len(target_in | other_in) if target_in | other_in else 0

            similarity = (out_jaccard + in_jaccard) / 2
            if similarity > 0:
                similarities.append((other_id, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return [sid for sid, _ in similarities[:limit]]

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        self._load_data()

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "categories": list(set(n.category for n in self._nodes.values())),
            "tradeable_nodes": sum(1 for n in self._nodes.values() if n.is_tradeable),
            "avg_degree": sum(self.graph.out_degree(n) + self.graph.in_degree(n) for n in self._nodes) / len(self._nodes) if self._nodes else 0
        }


# 全局图谱实例
_kg_instance: Optional[IndustryKnowledgeGraph] = None


def get_industry_graph() -> IndustryKnowledgeGraph:
    """获取知识图谱实例"""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = IndustryKnowledgeGraph()
    return _kg_instance
