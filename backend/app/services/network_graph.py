"""
产业链传导网络可视化服务
使用 pyvis 生成交互式网络图
"""
import json
from typing import List, Optional
from pathlib import Path

try:
    from pyvis.network import Network
    import networkx as nx
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    nx = None

from ..schemas.models import TransmissionChainResult, TransmissionStep


class NetworkGraphGenerator:
    """生成交互式产业链传导网络图"""

    def __init__(self):
        self.pyvis_available = PYVIS_AVAILABLE

    def generate_html(
        self,
        transmission: TransmissionChainResult,
        event_title: str = "事件传导网络"
    ) -> str:
        """
        生成交互式 HTML 网络图

        Args:
            transmission: 传导分析结果
            event_title: 事件标题

        Returns:
            HTML 字符串
        """
        if not self.pyvis_available:
            return self._generate_fallback_html(transmission, event_title)

        # 创建 Pyvis 网络
        net = Network(
            height="500px",
            width="100%",
            bgcolor="#1e293b",
            font_color="white",
            directed=True,
            notebook=False,
            select_menu=True
        )

        # 设置物理引擎参数使布局更美观
        net.set_options("""
        {
            "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 4,
                "font": {
                    "size": 14,
                    "color": "white"
                }
            },
            "edges": {
                "color": {
                    "inherit": true
                },
                "arrows": {
                    "to": {
                        "enabled": true,
                        "scaleFactor": 0.5
                    }
                },
                "smooth": {
                    "enabled": true,
                    "type": "continuous"
                }
            },
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 150,
                    "springConstant": 0.08
                },
                "maxVelocity": 50,
                "solver": "forceAtlas2Based",
                "timestep": 0.35,
                "stabilization": {
                    "iterations": 150
                }
            }
        }
        """)

        # 添加节点和边
        all_industries = set()
        for step in transmission.transmission_chain:
            all_industries.add(step.from_industry)
            all_industries.add(step.to_industry)

        # 添加所有行业节点
        for industry in all_industries:
            if industry in [s.from_industry for s in transmission.transmission_chain[:1]]:
                color = "#f97316"  # 起始节点 - 橙色
            elif industry in [s.to_industry for s in transmission.transmission_chain[-1:]]:
                color = "#3b82f6"  # 终端节点 - 蓝色
            else:
                color = "#22c55e"  # 中间节点 - 绿色

            net.add_node(
                industry,
                label=industry,
                title=f"行业: {industry}",
                color=color,
                size=30
            )

        # 添加边
        for step in transmission.transmission_chain:
            if step.impact_score > 0:
                edge_color = "#22c55e"  # 正向影响 - 绿色
            elif step.impact_score < 0:
                edge_color = "#ef4444"  # 负向影响 - 红色
            else:
                edge_color = "#94a3b8"  # 中性 - 灰色

            width = 1 + step.transmission_rate * 5

            net.add_edge(
                step.from_industry,
                step.to_industry,
                title=f"{step.relation_type}\n传导率: {step.transmission_rate*100:.0f}%\n滞后: {step.time_lag_days}天\n影响分: {step.impact_score:.1f}",
                color=edge_color,
                width=width,
                arrows="to"
            )

        return net.generate_html()

    def _generate_fallback_html(
        self,
        transmission: TransmissionChainResult,
        event_title: str
    ) -> str:
        """当 pyvis 不可用时生成简单的 SVG/HTML 回退"""
        nodes = []
        edges = []

        all_industries = []
        for step in transmission.transmission_chain:
            if step.from_industry not in all_industries:
                all_industries.append(step.from_industry)
            if step.to_industry not in all_industries:
                all_industries.append(step.to_industry)

        y_pos = 50
        x_step = 200
        start_x = 50

        for i, industry in enumerate(all_industries):
            x = start_x + (i % 4) * x_step
            y = y_pos + (i // 4) * 100
            nodes.append(f'''
                <circle cx="{x}" cy="{y}" r="25" fill="#3b82f6" stroke="white" stroke-width="2"/>
                <text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="12">{industry}</text>
            ''')

        for step in transmission.transmission_chain:
            from_idx = all_industries.index(step.from_industry)
            to_idx = all_industries.index(step.to_industry)

            from_x = start_x + (from_idx % 4) * x_step
            from_y = y_pos + (from_idx // 4) * 100
            to_x = start_x + (to_idx % 4) * x_step
            to_y = y_pos + (to_idx // 4) * 100

            color = "#22c55e" if step.impact_score > 0 else "#ef4444" if step.impact_score < 0 else "#94a3b8"

            edges.append(f'''
                <line x1="{from_x}" y1="{from_y}" x2="{to_x}" y2="{to_y}" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"/>
            ''')

        return f'''
        <svg width="100%" height="400" viewBox="0 0 800 400" style="background: #1e293b;">
            <defs>
                <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8"/>
                </marker>
            </defs>
            {''.join(nodes)}
            {''.join(edges)}
        </svg>
        '''

    def generate_json(self, transmission: TransmissionChainResult) -> dict:
        """生成网络图的 JSON 表示（供前端使用）"""
        nodes = []
        edges = []

        all_industries = {}
        for i, step in enumerate(transmission.transmission_chain):
            if step.from_industry not in all_industries:
                all_industries[step.from_industry] = len(all_industries)
            if step.to_industry not in all_industries:
                all_industries[step.to_industry] = len(all_industries)

        for industry, idx in all_industries.items():
            first_industries = [s.from_industry for s in transmission.transmission_chain[:1]]
            last_industries = [s.to_industry for s in transmission.transmission_chain[-1:]]

            if industry in first_industries:
                role = "source"
                color = "#f97316"
            elif industry in last_industries:
                role = "target"
                color = "#3b82f6"
            else:
                role = "intermediate"
                color = "#22c55e"

            nodes.append({
                "id": idx,
                "label": industry,
                "role": role,
                "color": color
            })

        for step in transmission.transmission_chain:
            edges.append({
                "from": all_industries[step.from_industry],
                "to": all_industries[step.to_industry],
                "relation": step.relation_type,
                "transmission_rate": step.transmission_rate,
                "time_lag_days": step.time_lag_days,
                "impact_score": step.impact_score,
                "description": step.description
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_industries": len(all_industries),
            "total_edges": len(edges)
        }


_graph_generator: Optional[NetworkGraphGenerator] = None


def get_network_graph_generator() -> NetworkGraphGenerator:
    """获取网络图生成器实例"""
    global _graph_generator
    if _graph_generator is None:
        _graph_generator = NetworkGraphGenerator()
    return _graph_generator