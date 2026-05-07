"use client";

import { useState, useMemo } from "react";
import type { TransmissionStep } from "@/types";

interface TransmissionGraphProps {
  steps: TransmissionStep[];
  affectedIndustries: string[];
}

interface NodePosition {
  id: string;
  label: string;
  x: number;
  y: number;
  role: "source" | "target" | "intermediate";
}

interface EdgeData {
  index: number;
  step: TransmissionStep;
  from: NodePosition;
  to: NodePosition;
  midX: number;
  path: string;
  isPositive: boolean;
  isNegative: boolean;
}

interface TooltipData {
  type: "node" | "edge";
  x: number;
  y: number;
  content: {
    title: string;
    details: { label: string; value: string }[];
  };
}

export function TransmissionGraph({ steps, affectedIndustries }: TransmissionGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<number | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    if (steps.length === 0) return { nodes: [], edges: [] };

    const nodeMap = new Map<string, { layer: number; index: number }>();
    const firstFrom = steps[0].from_industry;
    nodeMap.set(firstFrom, { layer: 0, index: 0 });

    const layers: Map<number, string[]> = new Map();
    layers.set(0, [firstFrom]);

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      const fromLayer = nodeMap.get(step.from_industry)?.layer ?? 0;
      const toLayer = fromLayer + 1;

      if (!nodeMap.has(step.to_industry)) {
        nodeMap.set(step.to_industry, { layer: toLayer, index: 0 });
        if (!layers.has(toLayer)) layers.set(toLayer, []);
        layers.get(toLayer)!.push(step.to_industry);
      }
    }

    for (const [layer, nodeList] of Array.from(layers.entries())) {
      for (const node of nodeList) {
        const entry = nodeMap.get(node)!;
        entry.index = nodeList.indexOf(node);
      }
    }

    const layerCount = layers.size;
    const width = 700;
    const height = Math.max(300, layerCount * 120);

    const positions: NodePosition[] = [];
    for (const [nodeId, { layer, index }] of Array.from(nodeMap.entries())) {
      const layerNodes = layers.get(layer) || [];
      const layerHeight = layerNodes.length * 80;
      const startY = (height - layerHeight) / 2;
      positions.push({
        id: nodeId,
        label: nodeId,
        x: 60 + layer * ((width - 120) / Math.max(layerCount - 1, 1)),
        y: startY + index * 80 + 40,
        role: layer === 0 ? "source" : layer === layerCount - 1 ? "target" : "intermediate",
      });
    }

    const nodeMap2 = new Map(positions.map((n) => [n.id, n]));

    const edgeData: EdgeData[] = steps.map((step, i) => {
      const from = nodeMap2.get(step.from_industry);
      const to = nodeMap2.get(step.to_industry);
      if (!from || !to) return null;
      const midX = (from.x + to.x) / 2;
      const dx = Math.abs(to.x - from.x);
      return {
        index: i,
        step,
        from,
        to,
        midX,
        path: `M ${from.x} ${from.y} C ${from.x + dx * 0.4} ${from.y}, ${to.x - dx * 0.4} ${to.y}, ${to.x} ${to.y}`,
        isPositive: step.impact_score > 0,
        isNegative: step.impact_score < 0,
      };
    }).filter((e): e is EdgeData => e !== null);

    return { nodes: positions, edges: edgeData };
  }, [steps]);

  const handleNodeHover = (nodeId: string, event: React.MouseEvent) => {
    setHoveredNode(nodeId);
    const rect = (event.target as SVGElement).getBoundingClientRect();
    const svgRect = (event.target as SVGElement).ownerSVGElement?.getBoundingClientRect();
    if (svgRect) {
      setTooltip({
        type: "node",
        x: rect.left - svgRect.left + rect.width / 2,
        y: rect.top - svgRect.top - 10,
        content: {
          title: nodeId,
          details: [
            { label: "节点角色", value: nodeId === steps[0]?.from_industry ? "起点" : nodes.length > 0 && nodeId === nodes[nodes.length - 1]?.id ? "终点" : "中间节点" },
            { label: "影响分数", value: steps.find(s => s.to_industry === nodeId || s.from_industry === nodeId)?.impact_score?.toFixed(1) || "0" }
          ]
        }
      });
    }
  };

  const handleEdgeHover = (edge: EdgeData, event: React.MouseEvent) => {
    setHoveredEdge(edge.index);
    const rect = (event.target as SVGElement).getBoundingClientRect();
    const svgRect = (event.target as SVGElement).ownerSVGElement?.getBoundingClientRect();
    if (svgRect) {
      setTooltip({
        type: "edge",
        x: edge.midX,
        y: (edge.from.y + edge.to.y) / 2 - 20,
        content: {
          title: `${edge.step.from_industry} → ${edge.step.to_industry}`,
          details: [
            { label: "传导类型", value: edge.step.relation_type },
            { label: "传导率", value: `${(edge.step.transmission_rate * 100).toFixed(0)}%` },
            { label: "时滞", value: `${edge.step.time_lag_days}天` },
            { label: "影响分数", value: edge.step.impact_score > 0 ? `+${edge.step.impact_score.toFixed(1)}` : edge.step.impact_score.toFixed(1) },
            { label: "影响程度", value: edge.step.impact_magnitude }
          ]
        }
      });
    }
  };

  const clearHover = () => {
    setHoveredNode(null);
    setHoveredEdge(null);
    setTooltip(null);
  };

  if (steps.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        暂无传导数据
      </div>
    );
  }

  const roleColors = {
    source: "#f97316",
    target: "#3b82f6",
    intermediate: "#22c55e",
  };

  const edgeColor = (edge: EdgeData) => {
    if (hoveredEdge === edge.index) return "#f97316";
    if (edge.isPositive) return "#22c55e";
    if (edge.isNegative) return "#ef4444";
    return "#94a3b8";
  };

  return (
    <div className="relative">
      <svg
        width="100%"
        height={Math.max(300, nodes.length > 0 ? Math.max(...nodes.map((n) => n.y)) + 60 : 300)}
        viewBox={`0 0 700 ${Math.max(300, nodes.length > 0 ? Math.max(...nodes.map((n) => n.y)) + 60 : 300)}`}
        className="overflow-visible"
      >
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
          </marker>
          <marker id="arrowhead-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#22c55e" />
          </marker>
          <marker id="arrowhead-red" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
          </marker>
          <marker id="arrowhead-orange" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#f97316" />
          </marker>
        </defs>

        {edges.map((edge) => {
          if (!edge) return null;
          const markerId = hoveredEdge === edge.index ? "url(#arrowhead-orange)" : edge.isPositive ? "url(#arrowhead-green)" : edge.isNegative ? "url(#arrowhead-red)" : "url(#arrowhead)";
          const isHighlighted = hoveredEdge === edge.index || hoveredNode === edge.step.from_industry || hoveredNode === edge.step.to_industry;
          return (
            <g key={edge.index}>
              <path
                d={edge.path}
                fill="none"
                stroke={edgeColor(edge)}
                strokeWidth={isHighlighted ? 3 : 1.5 + (edge.step.transmission_rate || 0.5) * 2}
                markerEnd={markerId}
                className="transition-all duration-200 cursor-pointer"
                onMouseEnter={(e) => handleEdgeHover(edge, e)}
                onMouseLeave={clearHover}
                opacity={hoveredNode && !isHighlighted ? 0.3 : 0.85}
              />
              <text x={edge.midX} y={(edge.from.y + edge.to.y) / 2 - 8} textAnchor="middle" fontSize="11" fill={edgeColor(edge)} className="pointer-events-none select-none">
                {edge.step.relation_type} · {(edge.step.transmission_rate * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}

        {nodes.map((node) => {
          const isHighlighted = hoveredNode === node.id || selectedNode === node.id;
          const outgoingEdges = edges.filter(e => e.step.from_industry === node.id);

          return (
            <g key={node.id} className="cursor-pointer" onMouseEnter={(e) => handleNodeHover(node.id, e)} onMouseLeave={clearHover} onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)}>
              <circle
                cx={node.x}
                cy={node.y}
                r={isHighlighted ? 28 : 24}
                fill={roleColors[node.role]}
                opacity={hoveredNode && !isHighlighted ? 0.5 : 1}
                stroke={isHighlighted ? "#fff" : "transparent"}
                strokeWidth={isHighlighted ? 2 : 0}
                className="transition-all duration-200"
              />
              <text x={node.x} y={node.y + 40} textAnchor="middle" fontSize="12" fill="#e2e8f0" fontWeight="500">
                {node.label}
              </text>
              {outgoingEdges.length > 0 && (
                <text x={node.x + 20} y={node.y - 15} fontSize="10" fill="#94a3b8">
                  ↓{outgoingEdges.length}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {tooltip && (
        <div
          className="absolute bg-slate-800 text-white p-3 rounded-lg shadow-lg z-50 text-sm min-w-[180px]"
          style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}
        >
          <div className="font-semibold mb-2 border-b border-slate-600 pb-1">{tooltip.content.title}</div>
          <div className="space-y-1">
            {tooltip.content.details.map((d, i) => (
              <div key={i} className="flex justify-between gap-4">
                <span className="text-slate-400">{d.label}:</span>
                <span className="font-medium">{d.value}</span>
              </div>
            ))}
          </div>
          <div className="absolute left-1/2 -bottom-2 transform -translate-x-1/2 border-8 border-transparent border-t-slate-800" />
        </div>
      )}

      <div className="flex items-center gap-6 mt-4 justify-center text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: "#f97316" }} />
          <span>起点行业</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: "#22c55e" }} />
          <span>中间行业</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: "#3b82f6" }} />
          <span>终端行业</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-1.5 bg-green-500 rounded" />
          <span>利好传导</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-1.5 bg-red-500 rounded" />
          <span>利空传导</span>
        </div>
      </div>
    </div>
  );
}