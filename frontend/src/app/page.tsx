"use client";

import { useState } from "react";
import { useAnalysis } from "@/hooks/useAnalysis";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { DegradationBanner } from "@/components/DegradationBanner";
import { TransmissionGraph } from "@/components/TransmissionGraph";

export default function Home() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [selectedTab, setSelectedTab] = useState("summary");
  const { loading, error, result, currentStep, stepMessage, analyze, analyzeStream, clearResult } = useAnalysis();
  const [degradationMessage, setDegradationMessage] = useState<string | null>(null);

  const handleAnalyze = async (useStream: boolean = false) => {
    if (!title.trim()) return;

    setDegradationMessage(null);

    if (useStream) {
      await analyzeStream(title, content);
    } else {
      const apiResponse = await analyze(title, content);
      if (apiResponse?.degradation_message) {
        setDegradationMessage(apiResponse.degradation_message);
      }
    }
  };

  const handleExampleClick = (example: { title: string; content: string }) => {
    setTitle(example.title);
    setContent(example.content);
  };

  const handleReset = () => {
    setTitle("");
    setContent("");
    setDegradationMessage(null);
    clearResult();
  };

  const tabs = [
    { id: "summary", label: "📋 事件摘要", icon: "📋" },
    { id: "chain", label: "🕸️ 传导图谱", icon: "🕸️" },
    { id: "details", label: "🔗 传导明细", icon: "🔗" },
    { id: "history", label: "📊 历史回测", icon: "📊" },
    { id: "signals", label: "💡 交易建议", icon: "💡" },
  ];

  return (
    <div className="min-h-screen bg-slate-950">
      <Header />

      <div className="flex">
        {/* 左侧边栏 */}
        <Sidebar
          title={title}
          content={content}
          onTitleChange={setTitle}
          onContentChange={setContent}
          onSubmit={() => handleAnalyze(true)}
          onReset={handleReset}
          onExampleClick={handleExampleClick}
          loading={loading}
        />

        {/* 右侧主区域 */}
        <main className="flex-1 p-6 overflow-auto">
          {/* 降级提示横幅 */}
          {degradationMessage && (
            <DegradationBanner message={degradationMessage} />
          )}

          {/* 加载状态 */}
          {loading && (
            <div className="bg-slate-900 rounded-xl p-8 mb-6 border border-slate-800">
              <div className="flex flex-col items-center justify-center gap-4">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
                  <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div className="text-center">
                  <p className="text-lg font-medium text-white">
                    {stepMessage || "正在分析..."}
                  </p>
                  <div className="flex items-center gap-2 mt-3 justify-center">
                    {[1, 2, 3].map((step) => (
                      <div
                        key={step}
                        className={`w-24 h-2 rounded-full transition-colors ${
                          currentStep >= step
                            ? "bg-primary"
                            : "bg-slate-700"
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-sm text-slate-400 mt-2">
                    Step {currentStep} / 3 - LLM 推理中
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 错误状态 */}
          {error && (
            <div className="bg-red-900/20 border border-red-800 rounded-xl p-6 mb-6">
              <p className="text-red-400 font-medium">分析出错</p>
              <p className="text-red-400/80 text-sm mt-1">{error}</p>
            </div>
          )}

          {/* 分析结果 */}
          {result && !loading && (
            <div className="space-y-6">
              {/* Tab 导航 */}
              <div className="flex gap-2 overflow-x-auto pb-2">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setSelectedTab(tab.id)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                      selectedTab === tab.id
                        ? "bg-primary text-white"
                        : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab 内容 */}
              <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
                {selectedTab === "summary" && (
                  <SummaryTab result={result} />
                )}
                {selectedTab === "chain" && (
                  <ChainTab result={result} />
                )}
                {selectedTab === "details" && (
                  <DetailsTab result={result} />
                )}
                {selectedTab === "history" && (
                  <HistoryTab result={result} />
                )}
                {selectedTab === "signals" && (
                  <SignalsTab result={result} />
                )}
              </div>
            </div>
          )}

          {/* 空状态 */}
          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-96 text-slate-500">
              <svg
                className="w-24 h-24 mb-4 text-slate-700"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1"
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              <p className="text-lg">输入事件开始分析</p>
              <p className="text-sm mt-1">或从左侧边栏选择示例事件</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// Tab 组件
function SummaryTab({ result }: { result: any }) {
  const eventAnalysis = result.event_analysis;

  return (
    <div className="space-y-6">
      {/* 原始输入 */}
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <p className="text-sm text-slate-400">分析事件</p>
            <p className="font-medium text-white mt-1">{result.input_title}</p>
          </div>
        </div>
      </div>

      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-lg p-5">
          <p className="text-sm text-slate-400 mb-1">事件类型</p>
          <p className="text-lg font-semibold text-white">{eventAnalysis.event_type}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-5">
          <p className="text-sm text-slate-400 mb-1">市场情绪</p>
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${
              eventAnalysis.sentiment > 0 ? "text-green-400" : eventAnalysis.sentiment < 0 ? "text-red-400" : "text-slate-400"
            }`}>
              {eventAnalysis.sentiment > 0 ? "+" : ""}{eventAnalysis.sentiment.toFixed(2)}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">{eventAnalysis.event_intensity}影响</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-5">
          <p className="text-sm text-slate-400 mb-1">涉及实体</p>
          <div className="flex flex-wrap gap-1">
            {eventAnalysis.core_entities?.slice(0, 3).map((entity: string, i: number) => (
              <span key={i} className="px-2 py-0.5 bg-primary/20 text-primary text-xs rounded">
                {entity}
              </span>
            ))}
          </div>
        </div>
        <div className="bg-slate-800 rounded-lg p-5">
          <p className="text-sm text-slate-400 mb-1">处理耗时</p>
          <p className="text-lg font-semibold text-white">{result.processing_time_ms || "< 1000"} ms</p>
          <p className="text-xs text-slate-400 mt-1">LLM 推理完成</p>
        </div>
      </div>

      {/* 情绪仪表 */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">事件情绪分析</h3>
        <div className="flex items-center justify-center py-8">
          <div className="relative w-64 h-8 bg-slate-700 rounded-full">
            <div
              className={`absolute top-0 h-8 rounded-full transition-all ${
                eventAnalysis.sentiment > 0 ? "bg-green-500" : eventAnalysis.sentiment < 0 ? "bg-red-500" : "bg-slate-500"
              }`}
              style={{ width: `${50 + eventAnalysis.sentiment * 50}%` }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-sm font-medium text-white">
                {eventAnalysis.sentiment > 0 ? "利好" : eventAnalysis.sentiment < 0 ? "利空" : "中性"}
              </span>
            </div>
          </div>
        </div>
        <p className="text-center text-slate-400 mt-4">{eventAnalysis.summary}</p>
      </div>

      {/* 直接影响行业 */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">直接受影响行业</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {eventAnalysis.direct_impacts.map((impact: any, i: number) => (
            <div
              key={i}
              className={`p-4 rounded-lg border ${
                impact.impact_direction === "利好"
                  ? "border-green-500/30 bg-green-500/5"
                  : impact.impact_direction === "利空"
                  ? "border-red-500/30 bg-red-500/5"
                  : "border-slate-600 bg-slate-800"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-white">{impact.industry}</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  impact.impact_direction === "利好" ? "bg-green-500 text-white" :
                  impact.impact_direction === "利空" ? "bg-red-500 text-white" : "bg-slate-600 text-white"
                }`}>
                  {impact.impact_direction}
                </span>
              </div>
              <div className="text-sm text-slate-400">影响程度: {impact.impact_magnitude}</div>
              <div className="text-sm text-slate-400">影响分数: {impact.impact_score > 0 ? "+" : ""}{impact.impact_score.toFixed(1)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChainTab({ result }: { result: any }) {
  const transmission = result.transmission;
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white">产业链传导路径</h3>
      <div className="bg-slate-800 rounded-lg p-6">
        <TransmissionGraph
          steps={transmission.transmission_chain}
          affectedIndustries={transmission.affected_industries}
        />
      </div>
    </div>
  );
}

function DetailsTab({ result }: { result: any }) {
  const transmission = result.transmission;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white">传导链条明细</h3>
      <div className="space-y-4">
        {transmission.transmission_chain.map((step: any, i: number) => (
          <div key={i} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center font-bold">
                {step.step}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">{step.from_industry}</span>
                  <span className="text-slate-400">→</span>
                  <span className="font-semibold text-white">{step.to_industry}</span>
                </div>
                <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                  <span className="px-2 py-1 bg-slate-700 rounded">{step.relation_type}</span>
                  <span>传导率: {(step.transmission_rate * 100).toFixed(0)}%</span>
                  <span>滞后: {step.time_lag_days}天</span>
                  <span className={step.impact_score > 0 ? "text-green-400" : "text-red-400"}>
                    影响分: {step.impact_score > 0 ? "+" : ""}{step.impact_score.toFixed(1)}
                  </span>
                </div>
                <p className="text-slate-500 mt-2 text-sm italic">{step.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 受影响行业汇总 */}
      <div className="bg-slate-800 rounded-lg p-6">
        <p className="text-sm font-medium text-slate-300 mb-3">所有受影响行业 ({transmission.affected_industries.length} 个)</p>
        <div className="flex flex-wrap gap-2">
          {transmission.affected_industries.map((industry: string, i: number) => (
            <span key={i} className="px-3 py-1 bg-slate-700 border border-slate-600 rounded-full text-sm text-slate-300">
              {industry}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function HistoryTab({ result }: { result: any }) {
  const { event_analysis, signals } = result;

  // 基于事件情绪生成模拟的历史影响曲线
  const sentiment = event_analysis?.sentiment ?? 0;
  const isPositive = sentiment >= 0;

  const mockData = [
    { day: "事件前", impact: 0 },
    { day: "T+1天", impact: sentiment * 5 },
    { day: "T+3天", impact: sentiment * 8 },
    { day: "T+7天", impact: sentiment * 12 },
    { day: "T+14天", impact: sentiment * 15 },
    { day: "T+30天", impact: sentiment * 13 },
    { day: "T+60天", impact: sentiment * 10 },
  ];

  const maxImpact = Math.max(...mockData.map((d) => Math.abs(d.impact)), 1);
  const svgHeight = 180;
  const svgWidth = 560;
  const padding = 40;
  const chartWidth = svgWidth - padding * 2;
  const chartHeight = svgHeight - padding * 2;

  const points = mockData.map((d, i) => {
    const x = padding + (i / (mockData.length - 1)) * chartWidth;
    const y = padding + chartHeight / 2 - (d.impact / maxImpact) * (chartHeight / 2);
    return { x, y, ...d };
  });

  const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaD = pathD + ` L ${points[points.length - 1].x} ${padding + chartHeight} L ${points[0].x} ${padding + chartHeight} Z`;

  const color = isPositive ? "#10B981" : "#EF4444";

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white">历史影响回测（基于类似事件统计）</h3>

      {/* 图表 */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-slate-400">
            参考历史同类事件传导时间线（模拟数据，仅供参考）
          </p>
          <span
            className="text-xs px-2 py-1 rounded"
            style={{ background: `${color}20`, color }}
          >
            {isPositive ? "利好型事件" : "利空型事件"}
          </span>
        </div>

        <svg width="100%" viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="overflow-visible">
          {/* 零线 */}
          <line
            x1={padding}
            y1={padding + chartHeight / 2}
            x2={svgWidth - padding}
            y2={padding + chartHeight / 2}
            stroke="#334155"
            strokeWidth="1"
            strokeDasharray="4 4"
          />

          {/* 面积填充 */}
          <path d={areaD} fill={color} opacity="0.1" />

          {/* 折线 */}
          <path d={pathD} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />

          {/* 数据点 */}
          {points.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r="4" fill={color} />
              <text
                x={p.x}
                y={svgHeight - 8}
                textAnchor="middle"
                fontSize="11"
                fill="#64748b"
              >
                {p.day}
              </text>
              <text
                x={p.x}
                y={p.y - 10}
                textAnchor="middle"
                fontSize="10"
                fill={color}
              >
                {p.impact > 0 ? "+" : ""}{p.impact.toFixed(1)}
              </text>
            </g>
          ))}
        </svg>

        <p className="text-center text-xs text-slate-500 mt-2">
          Y轴：相对影响分数（+为利好，-为利空）| 仅供参考，不构成投资建议
        </p>
      </div>

      {/* 统计摘要 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-sm text-slate-400 mb-1">情绪评估</p>
          <p className={`text-xl font-bold ${isPositive ? "text-green-400" : "text-red-400"}`}>
            {isPositive ? "利好" : "利空"} ({sentiment > 0 ? "+" : ""}{sentiment.toFixed(2)})
          </p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-sm text-slate-400 mb-1">峰值时间</p>
          <p className="text-xl font-bold text-white">T+14天</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-sm text-slate-400 mb-1">传导周期</p>
          <p className="text-xl font-bold text-white">~60天</p>
        </div>
      </div>

      {/* 信号列表摘要 */}
      {signals && signals.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-sm font-medium text-slate-300 mb-3">推荐股票（按置信度排序）</p>
          <div className="space-y-2">
            {[...signals]
              .sort((a, b) => b.confidence - a.confidence)
              .slice(0, 5)
              .map((s: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-bold text-white ${
                        s.signal_type === "BUY" ? "bg-green-500" : "bg-red-500"
                      }`}
                    >
                      {s.signal_type}
                    </span>
                    <span className="text-slate-300">{s.stock_name}</span>
                    <span className="text-slate-500 text-xs">{s.stock_code}</span>
                  </div>
                  <span className="text-slate-400">{s.confidence}%</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SignalsTab({ result }: { result: any }) {
  const signals = result.signals || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">交易建议 ({signals.length} 个)</h3>
        <div className="flex gap-2">
          <button className="px-3 py-1 bg-slate-700 text-slate-300 text-sm rounded hover:bg-slate-600">
            按得分排序
          </button>
          <button className="px-3 py-1 bg-slate-700 text-slate-300 text-sm rounded hover:bg-slate-600">
            按置信度排序
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {signals.map((signal: any, i: number) => (
          <div
            key={i}
            className={`p-5 rounded-lg border ${
              signal.signal_type === "BUY"
                ? "border-green-500/30 bg-green-500/5"
                : signal.signal_type === "SELL"
                ? "border-red-500/30 bg-red-500/5"
                : "border-slate-600 bg-slate-800"
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`px-3 py-1 rounded font-bold text-white ${
                  signal.signal_type === "BUY" ? "bg-green-500" : signal.signal_type === "SELL" ? "bg-red-500" : "bg-slate-500"
                }`}>
                  {signal.signal_type}
                </div>
                <div>
                  <p className="font-semibold text-white">{signal.stock_name}</p>
                  <p className="text-sm text-slate-400">{signal.stock_code}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-white">{signal.confidence}%</p>
                <p className="text-xs text-slate-400">置信度</p>
              </div>
            </div>

            <p className="text-sm text-slate-400 mb-3">{signal.entry_rationale}</p>

            <div className="flex items-center gap-4 text-sm text-slate-400 mb-3">
              <span>传导深度: {signal.chain_depth}</span>
              <span className={signal.impact_score > 0 ? "text-green-400" : "text-red-400"}>
                影响分: {signal.impact_score > 0 ? "+" : ""}{signal.impact_score}
              </span>
            </div>

            {(signal.risk_factors || []).length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-700">
                <p className="text-xs font-medium text-slate-500 mb-2">风险因素</p>
                <div className="flex flex-wrap gap-1">
                  {signal.risk_factors.map((risk: string, i: number) => (
                    <span key={i} className="px-2 py-0.5 bg-slate-700 text-slate-400 text-xs rounded">
                      {risk}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(signal.related_stocks || []).length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium text-slate-500 mb-2">相关股票</p>
                <div className="flex flex-wrap gap-1">
                  {signal.related_stocks.map((stock: string, i: number) => (
                    <span key={i} className="px-2 py-0.5 bg-primary/20 text-primary text-xs rounded">
                      {stock}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}