"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SentimentMeterProps {
  sentiment: number; // -1.0 to 1.0
}

export function SentimentMeter({ sentiment }: SentimentMeterProps) {
  const percentage = ((sentiment + 1) / 2) * 100; // 转换为 0-100%

  const getSentimentLabel = () => {
    if (sentiment > 0.5) return "极度利好";
    if (sentiment > 0.2) return "利好";
    if (sentiment > -0.2) return "中性";
    if (sentiment > -0.5) return "利空";
    return "极度利空";
  };

  const getSentimentColor = () => {
    if (sentiment > 0.2) return "#10B981"; // positive green
    if (sentiment < -0.2) return "#EF4444"; // negative red
    return "#6B7280"; // neutral gray
  };

  const getSentimentIcon = () => {
    if (sentiment > 0.2) return <TrendingUp className="w-6 h-6" />;
    if (sentiment < -0.2) return <TrendingDown className="w-6 h-6" />;
    return <Minus className="w-6 h-6" />;
  };

  return (
    <div className="relative">
      {/* 背景条 */}
      <div className="h-8 bg-gradient-to-r from-red-500 via-gray-400 to-green-500 rounded-full relative overflow-hidden">
        {/* 渐变遮罩让它看起来更柔和 */}
        <div className="absolute inset-0 bg-gradient-to-b from-white/20 to-transparent"></div>
      </div>

      {/* 指示器 */}
      <div
        className="absolute top-0 w-1 h-8 bg-slate-900 rounded-full transform -translate-x-1/2 transition-all duration-500"
        style={{ left: `${percentage}%` }}
      >
        {/* 指示器三角 */}
        <div
          className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-6 border-l-transparent border-r-transparent"
          style={{
            borderTopColor: getSentimentColor(),
          }}
        ></div>
      </div>

      {/* 刻度标签 */}
      <div className="flex justify-between mt-2 text-xs text-slate-500">
        <span>-1.0 (极度利空)</span>
        <span>0 (中性)</span>
        <span>+1.0 (极度利好)</span>
      </div>

      {/* 当前值显示 */}
      <div
        className="flex items-center justify-center gap-2 mt-4 py-2 px-4 rounded-lg transition-colors"
        style={{
          backgroundColor: `${getSentimentColor()}15`,
          color: getSentimentColor(),
        }}
      >
        {getSentimentIcon()}
        <span className="font-bold text-lg">
          {sentiment > 0 ? "+" : ""}
          {sentiment.toFixed(2)}
        </span>
        <span className="font-medium">— {getSentimentLabel()}</span>
      </div>
    </div>
  );
}