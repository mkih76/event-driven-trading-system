"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import type { TransmissionStep } from "@/types";
import { ZoomIn, ZoomOut, RotateCcw, Info } from "lucide-react";

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
  midY: number;
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

// 放大状态
interface ZoomState {
  scale: number;
  translateX: number;
  translateY: number;
}

export function TransmissionGraph({ steps, affectedIndustries }: TransmissionGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<number | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [showInfoPanel, setShowInfoPanel] = useState(false);
  const [zoom, setZoom] = useState<ZoomState>({ scale: 1, translateX: 0, translateY: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const isDragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  // 计算节点和边的位置信息
  const { nodes, edges, baseWidth, baseHeight } = useMemo(() => {
    if (steps.length === 0) return { nodes: [], edges: [], baseWidth: 700, baseHeight: 300 };

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
      const midY = (from.y + to.y) / 2;
      const dx = Math.abs(to.x - from.x);
      return {
        index: i,
        step,
        from,
        to,
        midX,
        midY,
        path: `M ${from.x} ${from.y} C ${from.x + dx * 0.4} ${from.y}, ${to.x - dx * 0.4} ${to.y}, ${to.x} ${to.y}`,
        isPositive: step.impact_score > 0,
        isNegative: step.impact_score < 0,
      };
    }).filter((e): e is EdgeData => e !== null);

    return { nodes: positions, edges: edgeData, baseWidth: width, baseHeight: height };
  }, [steps]);

  // 缩放控制
  const handleZoom = useCallback((delta: number) => {
    setZoom(prev => ({
      ...prev,
      scale: Math.min(Math.max(prev.scale + delta, 0.5), 3)
    }));
  }, []);

  const handleReset = useCallback(() => {
    setZoom({ scale: 1, translateX: 0, translateY: 0 });
  }, []);

  const handleFit = useCallback(() => {
    setZoom({ scale: 1, translateX: 0, translateY: 0 });
  }, []);

  // 拖拽支持
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      isDragging.current = true;
      lastPos.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging.current) {
      const dx = e.clientX - lastPos.current.x;
      const dy = e.clientY - lastPos.current.y;
      setZoom(prev => ({
        ...prev,
        translateX: prev.translateX + dx,
        translateY: prev.translateY + dy
      }));
      lastPos.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  // 滚轮缩放
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    handleZoom(delta);
  };

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

  // 选中节点的详细信息
  const selectedNodeInfo = useMemo(() => {
    if (!selectedNode) return null;
    const inEdges = edges.filter(e => e.step.to_industry === selectedNode);
    const outEdges = edges.filter(e => e.step.from_industry === selectedNode);
    return { inEdges, outEdges };
  }, [selectedNode, edges]);

  // 选中的边信息
  const selectedEdgeInfo = useMemo(() => {
    if (hoveredEdge === null) return null;
    return edges.find(e => e.index === hoveredEdge);
  }, [hoveredEdge, edges]);

  return (
    <div className="relative">
      {/* 缩放控制按钮 */}
      <div className="absolute top-2 right-2 flex items-center gap-1 bg-slate-800/90 rounded-lg p-1 z-20">
        <button
          onClick={() => handleZoom(0.2)}
          className="p-1.5 hover:bg-slate-700 rounded text-slate-300 transition-colors"
          title="放大"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <span className="text-xs text-slate-400 px-1 min-w-[40px] text-center">
          {Math.round(zoom.scale * 100)}%
        </span>
        <button
          onClick={() => handleZoom(-0.2)}
          className="p-1.5 hover:bg-slate-700 rounded text-slate-300 transition-colors"
          title="缩小"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-slate-600 mx-0.5" />
        <button
          onClick={handleReset}
          className="p-1.5 hover:bg-slate-700 rounded text-slate-300 transition-colors"
          title="重置视图"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        <button
          onClick={() => setShowInfoPanel(!showInfoPanel)}
          className={`p-1.5 hover:bg-slate-700 rounded transition-colors ${showInfoPanel ? 'text-primary' : 'text-slate-300'}`}
          title="图例说明"
        >
          <Info className="w-4 h-4" />
        </button>
      </div>

      {/* SVG 图谱 */}
      <svg
        ref={svgRef}
        width="100%"
        height={Math.max(300, nodes.length > 0 ? Math.max(...nodes.map((n) => n.y)) + 60 : 300)}
        viewBox={`0 0 ${baseWidth} ${baseHeight}`}
        className="overflow-visible cursor-grab active:cursor-grabbing select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <g transform={`translate(${zoom.translateX}, ${zoom.translateY}) scale(${zoom.scale})`}>
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
            {/* 选中节点高亮效果 */}
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 边 */}
          {edges.map((edge) => {
            if (!edge) return null;
            const markerId = hoveredEdge === edge.index ? "url(#arrowhead-orange)" : edge.isPositive ? "url(#arrowhead-green)" : edge.isNegative ? "url(#arrowhead-red)" : "url(#arrowhead)";
            const isHighlighted = hoveredEdge === edge.index || hoveredNode === edge.step.from_industry || hoveredNode === edge.step.to_industry;
            const isNodeSelected = selectedNode && (edge.step.from_industry === selectedNode || edge.step.to_industry === selectedNode);
            return (
              <g key={edge.index}>
                {/* 选中时添加光晕 */}
                {isNodeSelected && (
                  <path
                    d={edge.path}
                    fill="none"
                    stroke={edgeColor(edge)}
                    strokeWidth={6}
                    opacity={0.3}
                    filter="url(#glow)"
                  />
                )}
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

          {/* 节点 */}
          {nodes.map((node) => {
            const isHighlighted = hoveredNode === node.id || selectedNode === node.id;
            const outgoingEdges = edges.filter(e => e.step.from_industry === node.id);
            const isSelected = selectedNode === node.id;

            return (
              <g key={node.id} className="cursor-pointer" onMouseEnter={(e) => handleNodeHover(node.id, e)} onMouseLeave={clearHover} onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)}>
                {/* 选中时添加光晕 */}
                {isSelected && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={32}
                    fill={roleColors[node.role]}
                    opacity={0.3}
                    filter="url(#glow)"
                  />
                )}
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
        </g>
      </svg>

      {/* 工具提示 */}
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
        <div className="flex items-center gap-2 text-slate-500 ml-4 border-l border-slate-700 pl-4">
          <span>拖拽平移</span>
          <span>滚轮缩放</span>
          <span>点击节点查看详情</span>
        </div>
      </div>

      {/* 节点详情面板 */}
      {selectedNode && selectedNodeInfo && (
        <div className="absolute bottom-4 left-4 right-4 bg-slate-800/95 backdrop-blur rounded-lg p-4 shadow-xl z-30 border border-slate-700">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">{selectedNode}</h3>
              <p className="text-sm text-slate-400">
                入度: {selectedNodeInfo.inEdges.length} · 出度: {selectedNodeInfo.outEdges.length}
              </p>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-4">
            {/* 入边 */}
            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-2">上游传导</h4>
              {selectedNodeInfo.inEdges.length > 0 ? (
                <div className="space-y-1">
                  {selectedNodeInfo.inEdges.map(edge => (
                    <div key={edge.index} className="text-sm bg-slate-700/50 rounded px-2 py-1">
                      <span className="text-primary">{edge.step.from_industry}</span>
                      <span className="text-slate-500 mx-1">→</span>
                      <span className="text-slate-300">{edge.step.relation_type}</span>
                      <span className="text-slate-500 text-xs ml-2">{(edge.step.transmission_rate * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">无上游传导</p>
              )}
            </div>
            {/* 出边 */}
            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-2">下游传导</h4>
              {selectedNodeInfo.outEdges.length > 0 ? (
                <div className="space-y-1">
                  {selectedNodeInfo.outEdges.map(edge => (
                    <div key={edge.index} className="text-sm bg-slate-700/50 rounded px-2 py-1">
                      <span className="text-slate-300">{edge.step.relation_type}</span>
                      <span className="text-slate-500 mx-1">→</span>
                      <span className="text-blue-400">{edge.step.to_industry}</span>
                      <span className="text-slate-500 text-xs ml-2">{(edge.step.transmission_rate * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">无下游传导</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 说明面板 */}
      {showInfoPanel && (
        <div className="absolute top-12 right-12 bg-slate-800/95 backdrop-blur rounded-lg p-4 shadow-xl z-30 border border-slate-700 max-w-xs">
          <h4 className="text-sm font-semibold text-white mb-3">图谱交互说明</h4>
          <div className="space-y-2 text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <span className="bg-slate-700 px-2 py-0.5 rounded">点击节点</span>
              <span>查看上下游传导详情</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="bg-slate-700 px-2 py-0.5 rounded">悬停边/节点</span>
              <span>显示详细信息</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="bg-slate-700 px-2 py-0.5 rounded">拖拽画布</span>
              <span>平移视图</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="bg-slate-700 px-2 py-0.5 rounded">滚轮</span>
              <span>缩放视图 (50%-300%)</span>
            </div>
            <div className="border-t border-slate-700 pt-2 mt-2">
              <p className="text-slate-400 mb-1">节点颜色含义:</p>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500"></span>起点</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span>中间</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>终点</span>
              </div>
            </div>
            <div className="border-t border-slate-700 pt-2 mt-2">
              <p className="text-slate-400 mb-1">边的颜色:</p>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-green-500"></span>利好</span>
                <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-red-500"></span>利空</span>
                <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-slate-400"></span>中性</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}