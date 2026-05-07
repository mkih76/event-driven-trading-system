"""
动态知识图谱扩展模块
从分析结果中自动学习新的产业链关系、事件模式和行业模式
"""
import json
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredRelationship:
    """新发现的关系"""
    from_industry: str
    to_industry: str
    relation_type: str
    evidence_count: int
    transmission_rate: float
    time_lag_days: int
    confidence: float
    last_observed: str
    evidence: List[str]


@dataclass
class DiscoveredEventPattern:
    """新发现的事件模式"""
    pattern_name: str
    trigger_keywords: List[str]
    primary_impacts: List[str]
    sentiment_factor: float
    typical_depth: int
    discovery_count: int
    last_observed: str


@dataclass
class DiscoveredNode:
    """新发现的节点"""
    id: str
    name: str
    aliases: List[str]
    category: str
    discovery_method: str  # "llm_inference", "pattern_learning", "user_feedback"
    confidence: float
    related_existing_nodes: List[str]
    last_updated: str


class DynamicGraphLearner:
    """
    动态图谱学习器
    从分析结果中学习新的产业链关系和事件模式
    """

    def __init__(self, base_graph_path: str, auto_save: bool = True):
        self.base_graph_path = base_graph_path
        self.auto_save = auto_save
        self._lock = threading.RLock()

        # 动态发现的存储
        self._discovered_relationships: Dict[str, DiscoveredRelationship] = {}
        self._discovered_patterns: Dict[str, DiscoveredEventPattern] = {}
        self._discovered_nodes: Dict[str, DiscoveredNode] = {}

        # 行业别名到标准名称的映射
        self._alias_to_standard: Dict[str, str] = {}

        # 关系计数器（用于计算置信度）
        self._relationship_counts: Dict[str, int] = defaultdict(int)

        # 加载基础图谱
        self._load_base_graph()

    def _load_base_graph(self):
        """加载基础图谱，构建别名映射"""
        try:
            with open(self.base_graph_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 构建别名映射
            for node in data.get("industries", []):
                self._alias_to_standard[node["name"]] = node["id"]
                for alias in node.get("aliases", []):
                    self._alias_to_standard[alias] = node["id"]

            logger.info(f"基础图谱加载完成，别名映射: {len(self._alias_to_standard)} 条")
        except Exception as e:
            logger.warning(f"加载基础图谱失败: {e}，将从头开始学习")

    def _get_relationship_key(self, from_node: str, to_node: str, relation_type: str) -> str:
        """生成关系唯一键"""
        return f"{from_node}|{to_node}|{relation_type}"

    def _standardize_industry_name(self, name: str) -> Optional[str]:
        """将行业名称标准化"""
        name_lower = name.lower().strip()

        # 直接查找
        if name_lower in self._alias_to_standard:
            return self._alias_to_standard[name_lower]

        # 模糊匹配
        for alias, std_id in self._alias_to_standard.items():
            if name_lower in alias.lower() or alias.lower() in name_lower:
                return std_id

        return None

    async def learn_from_analysis(
        self,
        event_type: str,
        core_entities: List[str],
        direct_impacts: List[Dict[str, Any]],
        transmission_chain: List[Dict[str, Any]],
        sentiment: float
    ):
        """
        从分析结果中学习

        Args:
            event_type: 事件类型
            core_entities: 核心实体列表
            direct_impacts: 直接影响列表 [{"industry": "...", "direction": "...", "magnitude": "..."}]
            transmission_chain: 传导链 [{"from": "...", "to": "...", "relation_type": "...", "time_lag_days": ...}]
            sentiment: 情绪值
        """
        with self._lock:
            # 1. 学习传导关系
            await self._learn_relationships(transmission_chain)

            # 2. 学习事件模式
            await self._learn_event_pattern(
                event_type, core_entities, direct_impacts, sentiment
            )

            # 3. 学习新节点
            await self._learn_new_nodes(core_entities, direct_impacts)

            # 自动保存
            if self.auto_save:
                await self.save_discoveries()

    async def _learn_relationships(
        self,
        transmission_chain: List[Dict[str, Any]]
    ):
        """从传导链学习新关系"""
        for step in transmission_chain:
            from_ind = step.get("from_industry", "")
            to_ind = step.get("to_industry", "")
            relation_type = step.get("relation_type", "成本传导")
            time_lag = step.get("time_lag_days", 7)
            transmission_rate = step.get("transmission_rate", 0.5)

            if not from_ind or not to_ind:
                continue

            # 标准化
            from_std = self._standardize_industry_name(from_ind)
            to_std = self._standardize_industry_name(to_ind)

            if not from_std or not to_std:
                # 可能发现新节点
                if not from_std:
                    self._add_potential_node(from_ind)
                if not to_std:
                    self._add_potential_node(to_ind)
                continue

            key = self._get_relationship_key(from_std, to_std, relation_type)

            if key in self._discovered_relationships:
                # 更新现有关系
                rel = self._discovered_relationships[key]
                rel.evidence_count += 1
                rel.last_observed = datetime.now().isoformat()
                # 增量更新传导率和时滞
                rel.transmission_rate = (rel.transmission_rate * (rel.evidence_count - 1) + transmission_rate) / rel.evidence_count
                rel.time_lag_days = int((rel.time_lag_days * (rel.evidence_count - 1) + time_lag) / rel.evidence_count)
                # 更新置信度
                rel.confidence = min(0.5 + rel.evidence_count * 0.1, 0.95)
            else:
                # 新关系
                self._discovered_relationships[key] = DiscoveredRelationship(
                    from_industry=from_std,
                    to_industry=to_std,
                    relation_type=relation_type,
                    evidence_count=1,
                    transmission_rate=transmission_rate,
                    time_lag_days=time_lag,
                    confidence=0.5,
                    last_observed=datetime.now().isoformat(),
                    evidence=[]
                )

            self._relationship_counts[key] += 1
            logger.debug(f"学习到关系: {from_std} -> {to_std} ({relation_type})")

    async def _learn_event_pattern(
        self,
        event_type: str,
        core_entities: List[str],
        direct_impacts: List[Dict[str, Any]],
        sentiment: float
    ):
        """从事件分析中学习事件模式"""
        # 提取关键词
        keywords = []
        for entity in core_entities:
            keywords.extend(entity.split())

        # 提取受影响行业
        impacted = [imp.get("industry", "") for imp in direct_impacts if imp.get("industry")]

        # 标准化行业
        impacted_std = []
        for ind in impacted:
            std = self._standardize_industry_name(ind)
            if std:
                impacted_std.append(std)
            else:
                impacted_std.append(ind)

        pattern_key = f"{event_type}|{'_'.join(keywords[:3])}"

        if pattern_key in self._discovered_patterns:
            pattern = self._discovered_patterns[pattern_key]
            pattern.discovery_count += 1
            pattern.last_observed = datetime.now().isoformat()

            # 增量更新情感因子
            pattern.sentiment_factor = (pattern.sentiment_factor * (pattern.discovery_count - 1) + sentiment) / pattern.discovery_count

            # 扩展影响行业
            for ind in impacted_std:
                if ind not in pattern.primary_impacts:
                    pattern.primary_impacts.append(ind)
        else:
            self._discovered_patterns[pattern_key] = DiscoveredEventPattern(
                pattern_name=event_type,
                trigger_keywords=keywords[:5],
                primary_impacts=impacted_std[:5],
                sentiment_factor=sentiment,
                typical_depth=3,
                discovery_count=1,
                last_observed=datetime.now().isoformat()
            )

        logger.debug(f"学习到事件模式: {event_type}")

    async def _learn_new_nodes(
        self,
        core_entities: List[str],
        direct_impacts: List[Dict[str, Any]]
    ):
        """学习可能的新节点"""
        all_entities = set(core_entities)

        for imp in direct_impacts:
            if imp.get("industry"):
                all_entities.add(imp.get("industry"))

        for entity in all_entities:
            # 检查是否已存在
            std = self._standardize_industry_name(entity)
            if std:
                continue

            # 检查是否已发现
            self._add_potential_node(entity)

    def _add_potential_node(self, name: str):
        """添加潜在新节点"""
        node_id = self._generate_node_id(name)

        if node_id not in self._discovered_nodes:
            self._discovered_nodes[node_id] = DiscoveredNode(
                id=node_id,
                name=name,
                aliases=[],
                category="待分类",
                discovery_method="inference",
                confidence=0.3,
                related_existing_nodes=[],
                last_updated=datetime.now().isoformat()
            )
            logger.info(f"发现潜在新节点: {name}")

    def _generate_node_id(self, name: str) -> str:
        """生成节点ID"""
        import hashlib
        clean_name = ''.join(c for c in name if c.isalnum())
        short_hash = hashlib.md5(clean_name.encode()).hexdigest()[:6]
        return f"dynamic_{short_hash}"

    async def save_discoveries(self, output_path: str = None):
        """保存发现的知识"""
        if output_path is None:
            output_path = self.base_graph_path.replace('.json', '_discoveries.json')

        discoveries = {
            "last_updated": datetime.now().isoformat(),
            "discovered_relationships": [asdict(r) for r in self._discovered_relationships.values()],
            "discovered_patterns": [asdict(p) for p in self._discovered_patterns.values()],
            "discovered_nodes": [asdict(n) for n in self._discovered_nodes.values()]
        }

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(discoveries, f, ensure_ascii=False, indent=2)
            logger.info(f"发现知识已保存: {output_path}")
        except Exception as e:
            logger.error(f"保存失败: {e}")

    async def load_discoveries(self, path: str = None):
        """加载已发现的知识"""
        if path is None:
            path = self.base_graph_path.replace('.json', '_discoveries.json')

        try:
            with open(path, 'r', encoding='utf-8') as f:
                discoveries = json.load(f)

            # 恢复关系
            for rel_data in discoveries.get("discovered_relationships", []):
                rel = DiscoveredRelationship(**rel_data)
                key = self._get_relationship_key(rel.from_industry, rel.to_industry, rel.relation_type)
                self._discovered_relationships[key] = rel

            # 恢复模式
            for pattern_data in discoveries.get("discovered_patterns", []):
                pattern = DiscoveredEventPattern(**pattern_data)
                pattern_key = f"{pattern.pattern_name}|{'_'.join(pattern.trigger_keywords[:3])}"
                self._discovered_patterns[pattern_key] = pattern

            # 恢复节点
            for node_data in discoveries.get("discovered_nodes", []):
                node = DiscoveredNode(**node_data)
                self._discovered_nodes[node.id] = node

            logger.info(f"发现知识已加载: {len(self._discovered_relationships)} 关系, {len(self._discovered_patterns)} 模式, {len(self._discovered_nodes)} 节点")

        except FileNotFoundError:
            logger.info("未找到已保存的发现知识，将从头开始学习")
        except Exception as e:
            logger.warning(f"加载失败: {e}")

    def get_dynamic_relationships(self, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """获取动态发现的关系"""
        return [
            {
                "from": rel.from_industry,
                "to": rel.to_industry,
                "relation_type": rel.relation_type,
                "transmission_rate": rel.transmission_rate,
                "time_lag_days": rel.time_lag_days,
                "confidence": rel.confidence,
                "evidence_count": rel.evidence_count
            }
            for rel in self._discovered_relationships.values()
            if rel.confidence >= min_confidence
        ]

    def get_dynamic_patterns(self) -> Dict[str, Any]:
        """获取动态发现的事件模式"""
        return {
            key: {
                "pattern_name": p.pattern_name,
                "primary_impacts": p.primary_impacts,
                "sentiment_factor": p.sentiment_factor,
                "discovery_count": p.discovery_count
            }
            for key, p in self._discovered_patterns.items()
        }

    def get_potential_nodes(self) -> List[Dict[str, Any]]:
        """获取潜在的新节点（需要人工确认）"""
        return [
            {
                "id": node.id,
                "name": node.name,
                "category": node.category,
                "confidence": node.confidence,
                "discovery_method": node.discovery_method
            }
            for node in self._discovered_nodes.values()
            if node.confidence < 0.7  # 置信度不高的需要人工审核
        ]

    def merge_to_graph(self, output_path: str = None) -> str:
        """
        将动态学习的内容合并到基础图谱

        Returns:
            合并后的图谱文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.base_graph_path.replace('.json', f'_merged_{timestamp}.json')

        try:
            # 读取原始图谱
            with open(self.base_graph_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)

            # 合并新节点
            existing_ids = {n["id"] for n in graph_data.get("industries", [])}
            for node in self._discovered_nodes.values():
                if node.id not in existing_ids and node.confidence >= 0.7:
                    graph_data["industries"].append({
                        "id": node.id,
                        "name": node.name,
                        "aliases": node.aliases,
                        "category": node.category,
                        "is_tradeable": False,
                        "source": "dynamic_learning"
                    })

            # 合并新关系
            existing_edges = {
                (e["from"], e["to"], e["relation_type"])
                for e in graph_data.get("relationships", [])
            }
            for rel in self._discovered_relationships.values():
                key = (rel.from_industry, rel.to_industry, rel.relation_type)
                if key not in existing_edges and rel.confidence >= 0.6:
                    graph_data["relationships"].append({
                        "from": rel.from_industry,
                        "to": rel.to_industry,
                        "relation_type": rel.relation_type,
                        "transmission_rate": rel.transmission_rate,
                        "time_lag_days": rel.time_lag_days,
                        "confidence": rel.confidence,
                        "source": "dynamic_learning"
                    })

            # 保存
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)

            logger.info(f"图谱已合并保存: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"合并失败: {e}")
            return ""

    def get_statistics(self) -> Dict[str, Any]:
        """获取学习统计"""
        return {
            "total_relationships_learned": len(self._discovered_relationships),
            "total_patterns_learned": len(self._discovered_patterns),
            "potential_nodes_discovered": len(self._discovered_nodes),
            "high_confidence_relationships": sum(1 for r in self._discovered_relationships.values() if r.confidence >= 0.7),
            "confirmed_nodes": sum(1 for n in self._discovered_nodes.values() if n.confidence >= 0.7)
        }


# 全局实例
_dynamic_learner: Optional[DynamicGraphLearner] = None


def get_dynamic_learner() -> DynamicGraphLearner:
    """获取动态学习器实例"""
    global _dynamic_learner

    if _dynamic_learner is None:
        from .industry_graph import GRAPH_DATA_PATH
        _dynamic_learner = DynamicGraphLearner(GRAPH_DATA_PATH)

    return _dynamic_learner
