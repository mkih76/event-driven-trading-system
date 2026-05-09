"use client";

import { useState, useEffect } from "react";
import { Clock, Wifi, WifiOff, Loader2 } from "lucide-react";
import { useAnalysis } from "@/hooks/useAnalysis";

export function Header() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const { result, loading } = useAnalysis();
  const [llmStatus, setLlmStatus] = useState<"connected" | "degraded" | "unknown">("unknown");

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 定期健康检查
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/health', { cache: 'no-store' });
        if (res.ok) {
          setLlmStatus("connected");
        } else {
          setLlmStatus("degraded");
        }
      } catch {
        setLlmStatus("degraded");
      }
    };

    // 首次检查
    checkHealth();

    // 每30秒检查一次
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // 根据结果判断LLM状态
    if (result) {
      setLlmStatus("connected");
    } else if (loading) {
      setLlmStatus("unknown");
    }
  }, [result, loading]);

  const formatTime = (date: Date) => {
    return date.toLocaleString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      weekday: "short",
    });
  };

  return (
    <header className="bg-slate-900 border-b border-slate-700 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-3 max-w-7xl">
        <div className="flex items-center justify-between">
          {/* 左侧：系统名称和Logo */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/20 rounded-lg">
              <svg
                className="w-6 h-6 text-primary"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">
                事件驱动交易分析终端
              </h1>
              <p className="text-xs text-slate-400">
                Event-Driven Trading Analysis
              </p>
            </div>
          </div>

          {/* 中间：实时时钟 */}
          <div className="hidden md:flex flex-col items-center">
            <div className="flex items-center gap-2 text-white">
              <Clock className="w-4 h-4 text-slate-400" />
              <span className="text-2xl font-mono font-semibold">
                {formatTime(currentTime)}
              </span>
            </div>
            <div className="text-xs text-slate-400">{formatDate(currentTime)}</div>
          </div>

          {/* 右侧：状态指示 */}
          <div className="flex items-center gap-4">
            {/* LLM状态 */}
            <div className="flex items-center gap-2">
              {llmStatus === "connected" ? (
                <>
                  <Wifi className="w-4 h-4 text-green-400" />
                  <span className="text-xs text-green-400">LLM 已连接</span>
                </>
              ) : llmStatus === "degraded" ? (
                <>
                  <WifiOff className="w-4 h-4 text-yellow-400" />
                  <span className="text-xs text-yellow-400">规则模式</span>
                </>
              ) : (
                <>
                  <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                  <span className="text-xs text-slate-400">连接中...</span>
                </>
              )}
            </div>

            {/* 数据源状态 */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              </div>
              <span className="text-xs text-slate-400">数据源正常</span>
            </div>

            {/* 版本标签 */}
            <div className="hidden lg:flex items-center gap-2">
              <span className="px-2 py-1 bg-primary/20 text-primary text-xs font-medium rounded">
                LLM 驱动
              </span>
              <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-medium rounded">
                v1.0
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}