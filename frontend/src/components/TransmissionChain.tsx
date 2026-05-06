"use client";

import { ArrowRight, Clock, Zap } from "lucide-react";
import type { TransmissionStep } from "@/types";

interface TransmissionChainProps {
  steps: TransmissionStep[];
}

export function TransmissionChain({ steps }: TransmissionChainProps) {
  if (steps.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        暂无传导链数据
      </div>
    );
  }

  const getRelationColor = (relationType: string) => {
    if (relationType.includes("成本") || relationType.includes("供给")) {
      return "border-orange-300 bg-orange-50";
    }
    if (relationType.includes("需求")) {
      return "border-blue-300 bg-blue-50";
    }
    if (relationType.includes("替代")) {
      return "border-purple-300 bg-purple-50";
    }
    return "border-slate-300 bg-slate-50";
  };

  const getImpactColor = (score: number) => {
    if (score > 5) return "text-positive";
    if (score < -5) return "text-negative";
    return "text-neutral";
  };

  return (
    <div className="relative">
      {/* 传导链可视化 */}
      <div className="flex flex-col gap-3">
        {steps.map((step, index) => (
          <div key={index} className="flex items-start gap-3">
            {/* 步骤序号 */}
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold text-sm">
              {step.step}
            </div>

            {/* 传导节点 */}
            <div className="flex-1">
              <div className={`p-4 rounded-lg border-2 ${getRelationColor(step.relation_type)} transition-all`}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800">
                      {step.from_industry}
                    </span>
                    <ArrowRight className="w-4 h-4 text-slate-400" />
                    <span className="font-semibold text-slate-800">
                      {step.to_industry}
                    </span>
                  </div>
                  <div className={`font-bold ${getImpactColor(step.impact_score)}`}>
                    {step.impact_score > 0 ? "+" : ""}
                    {step.impact_score.toFixed(1)}
                  </div>
                </div>

                <div className="flex items-center gap-4 text-sm text-slate-600 mb-2">
                  <span className="px-2 py-0.5 bg-white rounded border border-slate-200">
                    {step.relation_type}
                  </span>
                  <span className="flex items-center gap-1">
                    <Zap className="w-3 h-3" />
                    传导率: {(step.transmission_rate * 100).toFixed(0)}%
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    滞后: {step.time_lag_days}天
                  </span>
                </div>

                <p className="text-sm text-slate-500 italic">
                  {step.description}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 传导图示 */}
      <div className="mt-6 p-4 bg-slate-50 rounded-lg">
        <p className="text-xs font-medium text-slate-500 mb-2">传导路径图</p>
        <div className="flex items-center flex-wrap gap-2">
          {steps.map((step, index) => (
            <div key={index} className="flex items-center">
              <span className="px-3 py-1 bg-white border border-slate-300 rounded text-sm font-medium text-slate-700">
                {step.from_industry}
              </span>
              {index < steps.length - 1 && (
                <div className="flex items-center px-2">
                  <div className="w-8 h-0.5 bg-slate-300"></div>
                  <ArrowRight className="w-3 h-3 text-slate-400 -ml-1" />
                </div>
              )}
            </div>
          ))}
          {steps.length > 0 && (
            <>
              <ArrowRight className="w-4 h-4 text-slate-400" />
              <span className="px-3 py-1 bg-white border border-slate-300 rounded text-sm font-medium text-slate-700">
                {steps[steps.length - 1].to_industry}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}