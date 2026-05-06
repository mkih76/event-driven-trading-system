"use client";

import { Zap } from "lucide-react";

export function Header() {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4 max-w-6xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Zap className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              事件驱动交易分析系统
            </h1>
            <p className="text-sm text-slate-500">
              Event-Driven Trading Analysis
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-medium rounded-full">
              LLM 驱动
            </span>
            <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
              Beta
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}