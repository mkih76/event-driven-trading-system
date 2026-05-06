"use client";

import { useState, useEffect } from "react";
import { useAnalysis, useExamples } from "@/hooks/useAnalysis";
import { EventInput } from "@/components/EventInput";
import { AnalysisResult } from "@/components/AnalysisResult";
import { Header } from "@/components/Header";
import { ExampleList } from "@/components/ExampleList";

export default function Home() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const { examples, fetchExamples } = useExamples();
  const { loading, error, result, currentStep, stepMessage, analyze, analyzeStream, clearResult } = useAnalysis();

  useEffect(() => {
    fetchExamples();
  }, [fetchExamples]);

  const handleAnalyze = async (useStream: boolean = false) => {
    if (!title.trim()) return;

    if (useStream) {
      await analyzeStream(title, content);
    } else {
      await analyze(title, content);
    }
  };

  const handleExampleClick = (example: { title: string; content: string }) => {
    setTitle(example.title);
    setContent(example.content);
  };

  const handleReset = () => {
    setTitle("");
    setContent("");
    clearResult();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Header />

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {/* 输入区域 */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8 animate-fade-in">
          <h2 className="text-xl font-semibold mb-4 text-slate-800">
            输入事件
          </h2>
          <EventInput
            title={title}
            content={content}
            onTitleChange={setTitle}
            onContentChange={setContent}
            onSubmit={() => handleAnalyze(true)}
            onReset={handleReset}
            loading={loading}
          />
        </div>

        {/* 示例事件 */}
        {!result && !loading && (
          <div className="mb-8 animate-fade-in">
            <h3 className="text-lg font-medium mb-3 text-slate-700">
              示例事件（点击使用）
            </h3>
            <ExampleList
              examples={examples}
              onSelect={handleExampleClick}
            />
          </div>
        )}

        {/* 加载状态 */}
        {loading && (
          <div className="bg-white rounded-xl shadow-lg p-8 mb-8 animate-fade-in">
            <div className="flex flex-col items-center justify-center gap-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
              </div>
              <div className="text-center">
                <p className="text-lg font-medium text-slate-800">
                  {stepMessage || "正在分析..."}
                </p>
                <div className="flex items-center gap-2 mt-3 justify-center">
                  {[1, 2, 3].map((step) => (
                    <div
                      key={step}
                      className={`w-24 h-2 rounded-full transition-colors ${
                        currentStep >= step
                          ? "bg-primary"
                          : "bg-slate-200"
                      }`}
                    />
                  ))}
                </div>
                <p className="text-sm text-slate-500 mt-2">
                  Step {currentStep} / 3 - LLM 推理中
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 错误状态 */}
        {error && (
          <div className="bg-destructive/10 border border-destructive/30 rounded-xl p-6 mb-8 animate-fade-in">
            <p className="text-destructive font-medium">分析出错</p>
            <p className="text-destructive/80 text-sm mt-1">{error}</p>
          </div>
        )}

        {/* 分析结果 */}
        {result && !loading && (
          <AnalysisResult result={result} />
        )}
      </main>

      {/* 底部信息 */}
      <footer className="text-center py-6 text-sm text-slate-500">
        <p>事件驱动交易分析系统 v1.0</p>
        <p className="mt-1">Powered by LLM + 产业链传导模型</p>
      </footer>
    </div>
  );
}