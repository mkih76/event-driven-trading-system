"use client";

import { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Building2,
  History,
} from "lucide-react";
import type { FullAnalysis, StockSignal } from "@/types";
import { TransmissionChain } from "./TransmissionChain";
import { SentimentMeter } from "./SentimentMeter";

interface AnalysisResultProps {
  result: FullAnalysis;
}

export function AnalysisResult({ result }: AnalysisResultProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["overview", "chain", "signals"])
  );

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const eventAnalysis = result.event_analysis;
  const transmission = result.transmission;
  const signals = result.signals || [];

  const sentimentColor =
    eventAnalysis.sentiment > 0
      ? "text-positive"
      : eventAnalysis.sentiment < 0
      ? "text-negative"
      : "text-neutral";

  const sentimentBg =
    eventAnalysis.sentiment > 0
      ? "bg-positive"
      : eventAnalysis.sentiment < 0
      ? "bg-negative"
      : "bg-neutral";

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 原始输入 */}
      <div className="bg-slate-800 text-white rounded-xl p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5" />
          <div>
            <p className="text-sm text-slate-400">分析事件</p>
            <p className="font-medium mt-1">{result.input_title}</p>
          </div>
        </div>
      </div>

      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* 事件类型 */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-sm text-slate-500 mb-1">事件类型</p>
          <p className="text-lg font-semibold text-slate-800">
            {eventAnalysis.event_type}
          </p>
        </div>

        {/* 情绪值 */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-sm text-slate-500 mb-1">市场情绪</p>
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${sentimentColor}`}>
              {eventAnalysis.sentiment > 0 ? "+" : ""}
              {eventAnalysis.sentiment.toFixed(2)}
            </span>
            <span className={`w-2 h-2 rounded-full ${sentimentBg}`}></span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {eventAnalysis.event_intensity}影响
          </p>
        </div>

        {/* 核心实体 */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-sm text-slate-500 mb-1">涉及实体</p>
          <div className="flex flex-wrap gap-1">
            {eventAnalysis.core_entities?.slice(0, 3).map((entity, i) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded"
              >
                {entity}
              </span>
            ))}
            {(eventAnalysis.core_entities?.length || 0) > 3 && (
              <span className="text-xs text-slate-400">
                +{(eventAnalysis.core_entities?.length || 0) - 3}
              </span>
            )}
          </div>
        </div>

        {/* 处理时间 */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-sm text-slate-500 mb-1">处理耗时</p>
          <p className="text-lg font-semibold text-slate-800">
            {result.processing_time_ms || "< 1000"} ms
          </p>
          <p className="text-xs text-slate-400 mt-1">LLM 推理完成</p>
        </div>
      </div>

      {/* 情绪仪表盘 */}
      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-slate-800">
          事件情绪分析
        </h3>
        <SentimentMeter sentiment={eventAnalysis.sentiment} />
        <p className="text-center text-slate-600 mt-4">
          {eventAnalysis.summary}
        </p>
      </div>

      {/* 直接影响行业 */}
      <div className="bg-white rounded-xl shadow">
        <button
          onClick={() => toggleSection("overview")}
          className="w-full p-6 flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold text-slate-800">
            直接受影响行业
          </h3>
          {expandedSections.has("overview") ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>
        {expandedSections.has("overview") && (
          <div className="px-6 pb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {eventAnalysis.direct_impacts.map((impact, i) => (
                <div
                  key={i}
                  className={`p-4 rounded-lg border ${
                    impact.impact_direction === "利好"
                      ? "border-positive/30 bg-positive/5"
                      : impact.impact_direction === "利空"
                      ? "border-negative/30 bg-negative/5"
                      : "border-slate-200 bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-slate-800">
                      {impact.industry}
                    </span>
                    {impact.impact_direction === "利好" ? (
                      <TrendingUp className="w-4 h-4 text-positive" />
                    ) : impact.impact_direction === "利空" ? (
                      <TrendingDown className="w-4 h-4 text-negative" />
                    ) : (
                      <span className="w-4 h-4 text-neutral">-</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        impact.impact_direction === "利好"
                          ? "bg-positive text-white"
                          : impact.impact_direction === "利空"
                          ? "bg-negative text-white"
                          : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {impact.impact_direction}
                    </span>
                    <span className="text-slate-500">
                      {impact.impact_magnitude}影响
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-1">
                    <span className="text-xs text-slate-400">影响分数:</span>
                    <span
                      className={`text-sm font-medium ${
                        impact.impact_score > 0
                          ? "text-positive"
                          : impact.impact_score < 0
                          ? "text-negative"
                          : "text-slate-500"
                      }`}
                    >
                      {impact.impact_score > 0 ? "+" : ""}
                      {impact.impact_score.toFixed(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 产业链传导链 */}
      <div className="bg-white rounded-xl shadow">
        <button
          onClick={() => toggleSection("chain")}
          className="w-full p-6 flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold text-slate-800">
            产业链传导路径
          </h3>
          {expandedSections.has("chain") ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>
        {expandedSections.has("chain") && (
          <div className="px-6 pb-6">
            <TransmissionChain steps={transmission.transmission_chain} />

            {/* 受影响行业汇总 */}
            <div className="mt-6 p-4 bg-slate-50 rounded-lg">
              <p className="text-sm font-medium text-slate-700 mb-2">
                <Building2 className="w-4 h-4 inline mr-1" />
                所有受影响行业 ({transmission.affected_industries.length} 个)
              </p>
              <div className="flex flex-wrap gap-2">
                {transmission.affected_industries.map((industry, i) => (
                  <span
                    key={i}
                    className="px-3 py-1 bg-white border border-slate-200 rounded-full text-sm text-slate-700"
                  >
                    {industry}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 交易信号 */}
      <div className="bg-white rounded-xl shadow">
        <button
          onClick={() => toggleSection("signals")}
          className="w-full p-6 flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold text-slate-800">
            交易信号 ({signals.length} 个)
          </h3>
          {expandedSections.has("signals") ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>
        {expandedSections.has("signals") && (
          <div className="px-6 pb-6 space-y-4">
            {signals.map((signal, i) => (
              <SignalCard key={i} signal={signal} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SignalCard({ signal }: { signal: StockSignal }) {
  const isBuy = signal.signal_type === "BUY";
  const isSell = signal.signal_type === "SELL";
  const hasBacktestRef = signal.backtest_reference && signal.backtest_reference.has_historical_reference;

  return (
    <div
      className={`p-5 rounded-lg border ${
        isBuy
          ? "border-positive/30 bg-positive/5"
          : isSell
          ? "border-negative/30 bg-negative/5"
          : "border-slate-200 bg-slate-50"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className={`px-3 py-1 rounded font-bold text-white ${
              isBuy ? "bg-positive" : isSell ? "bg-negative" : "bg-neutral"
            }`}
          >
            {signal.signal_type}
          </div>
          <div>
            <p className="font-semibold text-slate-800">
              {signal.stock_name}
            </p>
            <p className="text-sm text-slate-500">{signal.stock_code}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1">
            <CheckCircle2 className="w-4 h-4 text-primary" />
            <span className="font-bold text-slate-800">
              {signal.confidence}%
            </span>
          </div>
          <p className="text-xs text-slate-400">置信度</p>
        </div>
      </div>

      <p className="text-sm text-slate-600 mb-3">{signal.entry_rationale}</p>

      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1 text-slate-500">
          <ArrowRight className="w-3 h-3" />
          传导深度: {signal.chain_depth}
        </div>
        <div className="flex items-center gap-1 text-slate-500">
          <Clock className="w-3 h-3" />
          影响分: {signal.impact_score > 0 ? "+" : ""}
          {signal.impact_score}
        </div>
      </div>

      {/* 历史回测参考 */}
      {hasBacktestRef && (
        <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-medium text-blue-700">历史回测参考</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-slate-500">相似事件:</span>
              <span className="ml-1 text-slate-700 font-medium">
                {signal.backtest_reference?.best_match?.title?.slice(0, 15) || "无"}
                {(signal.backtest_reference?.best_match?.title?.length || 0) > 15 ? "..." : ""}
              </span>
            </div>
            <div>
              <span className="text-slate-500">相似度:</span>
              <span className="ml-1 text-slate-700 font-medium">
                {(signal.backtest_reference?.best_match?.similarity_score || 0) * 100}%
              </span>
            </div>
            <div>
              <span className="text-slate-500">历史胜率:</span>
              <span className={`ml-1 font-medium ${
                (signal.backtest_reference?.historical_win_rate || 0) >= 0.7
                  ? "text-green-600"
                  : (signal.backtest_reference?.historical_win_rate || 0) >= 0.5
                  ? "text-yellow-600"
                  : "text-red-600"
              }`}>
                {((signal.backtest_reference?.historical_win_rate || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div>
              <span className="text-slate-500">调整后置信度:</span>
              <span className={`ml-1 font-medium ${
                (signal.backtest_reference?.confidence_change || 0) > 0
                  ? "text-green-600"
                  : (signal.backtest_reference?.confidence_change || 0) < 0
                  ? "text-red-600"
                  : "text-slate-700"
              }`}>
                {signal.backtest_reference?.adjusted_confidence?.toFixed(0) || signal.confidence}%
              </span>
            </div>
          </div>
          {signal.backtest_reference?.backtest_evaluation?.actual_outcome && (
            <p className="text-xs text-slate-600 mt-2 pt-2 border-t border-blue-200">
              历史结果: {signal.backtest_reference?.backtest_evaluation?.actual_outcome}
            </p>
          )}
        </div>
      )}

      {(signal.risk_factors || []).length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-200">
          <p className="text-xs font-medium text-slate-500 mb-1">风险因素</p>
          <div className="flex flex-wrap gap-1">
            {signal.risk_factors.map((risk, i) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded"
              >
                {risk}
              </span>
            ))}
          </div>
        </div>
      )}

      {(signal.related_stocks || []).length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-slate-500 mb-1">相关股票</p>
          <div className="flex flex-wrap gap-1">
            {signal.related_stocks.map((stock, i) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded"
              >
                {stock}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}