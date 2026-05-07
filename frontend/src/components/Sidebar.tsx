"use client";

import { useState } from "react";
import { Send, RotateCcw, Loader2, ChevronDown, ChevronUp, Globe, Zap, Settings } from "lucide-react";

interface SidebarProps {
  title: string;
  content: string;
  onTitleChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  onExampleClick: (example: { title: string; content: string }) => void;
  loading: boolean;
}

const presetScenarios = [
  { label: "🌍 地缘冲突", title: "美国与伊朗爆发军事冲突，霍尔木兹海峡被封锁", category: "地缘政治" },
  { label: "🛢️ 原油减产", title: "OPEC+宣布大幅减产原油，每天减少500万桶", category: "大宗商品" },
  { label: "💻 科技制裁", title: "荷兰宣布禁止光刻机出口到中国", category: "科技制裁" },
  { label: "🚢 航运堵塞", title: "苏伊士运河因货轮搁浅再次堵塞", category: "航运" },
  { label: "🌱 碳中和政策", title: "欧盟通过碳中和法案，大幅提高碳排放成本", category: "政策" },
];

const exampleEvents = [
  { title: "美国与伊朗爆发军事冲突，霍尔木兹海峡被封锁", content: "据报道，美国和伊朗在波斯湾地区发生军事冲突，伊朗宣布封锁霍尔木兹海峡，禁止所有油轮通行。", category: "地缘政治" },
  { title: "OPEC+宣布大幅减产原油，每天减少500万桶", content: "石油输出国组织及其盟国(OPEC+)召开紧急会议，决定从下月开始大幅减产原油，日产量减少500万桶。", category: "大宗商品" },
  { title: "荷兰宣布禁止光刻机出口到中国", content: "荷兰政府宣布扩大光刻机出口管制范围，禁止ASML向中国出口更先进的DUV光刻机设备。", category: "科技制裁" },
];

const llmModels = [
  { value: "siliconflow", label: "SiliconFlow (DeepSeek)" },
  { value: "openai", label: "OpenAI GPT-4" },
  { value: "claude", label: "Anthropic Claude" },
  { value: "ollama", label: "Ollama (本地)" },
];

const marketRegions = [
  { value: "a-share", label: "A股" },
  { value: "us-stock", label: "美股" },
  { value: "all", label: "全市场" },
];

export function Sidebar({
  title,
  content,
  onTitleChange,
  onContentChange,
  onSubmit,
  onReset,
  onExampleClick,
  loading,
}: SidebarProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [llmEnabled, setLlmEnabled] = useState(true);
  const [selectedModel, setSelectedModel] = useState("siliconflow");
  const [selectedRegion, setSelectedRegion] = useState("all");
  const [kgDepth, setKgDepth] = useState(3);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim() && !loading) {
      onSubmit();
    }
  };

  return (
    <aside className="w-80 bg-slate-900 border-r border-slate-800 min-h-screen p-4 flex flex-col">
      <form onSubmit={handleSubmit} className="space-y-4 flex-1">
        {/* 新闻输入区 */}
        <div className="space-y-3">
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-slate-300 mb-1">
              事件标题 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              placeholder="输入事件标题..."
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder:text-slate-500 focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="content" className="block text-sm font-medium text-slate-300 mb-1">
              事件详情
              <span className="text-slate-500 font-normal ml-1">（可选）</span>
            </label>
            <textarea
              id="content"
              value={content}
              onChange={(e) => onContentChange(e.target.value)}
              placeholder="补充事件详细信息..."
              rows={3}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder:text-slate-500 resize-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              disabled={loading}
            />
          </div>
        </div>

        {/* 快捷场景按钮 */}
        <div>
          <p className="text-xs text-slate-500 mb-2">快捷场景</p>
          <div className="flex flex-wrap gap-2">
            {presetScenarios.map((scenario, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onExampleClick({ title: scenario.title, content: "" })}
                className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-slate-400 hover:bg-slate-700 hover:text-white transition-colors"
                disabled={loading}
              >
                {scenario.label}
              </button>
            ))}
          </div>
        </div>

        {/* 高级设置 */}
        <div className="border-t border-slate-800 pt-4">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center justify-between w-full text-sm text-slate-400 hover:text-white transition-colors"
          >
            <span className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              高级设置
            </span>
            {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showAdvanced && (
            <div className="mt-4 space-y-4">
              {/* LLM 模型选择 */}
              <div>
                <label className="block text-xs text-slate-500 mb-1">LLM 模型</label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:ring-2 focus:ring-primary/50"
                  disabled={loading}
                >
                  {llmModels.map((model) => (
                    <option key={model.value} value={model.value}>{model.label}</option>
                  ))}
                </select>
              </div>

              {/* LLM 开关 */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">启用 LLM 推理</span>
                <button
                  type="button"
                  onClick={() => setLlmEnabled(!llmEnabled)}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    llmEnabled ? "bg-primary" : "bg-slate-700"
                  }`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    llmEnabled ? "translate-x-6" : "translate-x-0.5"
                  }`} />
                </button>
              </div>

              {/* 知识图谱深度 */}
              <div>
                <label className="block text-xs text-slate-500 mb-1">
                  知识图谱深度: {kgDepth}
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={kgDepth}
                  onChange={(e) => setKgDepth(parseInt(e.target.value))}
                  className="w-full accent-primary"
                  disabled={loading}
                />
              </div>

              {/* 市场区域 */}
              <div>
                <label className="block text-xs text-slate-500 mb-1">市场区域</label>
                <div className="flex gap-2">
                  {marketRegions.map((region) => (
                    <button
                      key={region.value}
                      type="button"
                      onClick={() => setSelectedRegion(region.value)}
                      className={`flex-1 px-2 py-1 rounded text-xs transition-colors ${
                        selectedRegion === region.value
                          ? "bg-primary text-white"
                          : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                      }`}
                      disabled={loading}
                    >
                      {region.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 按钮区 */}
        <div className="pt-4 space-y-3">
          <button
            type="submit"
            disabled={!title.trim() || loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-white font-medium rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                分析中...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                开始分析
              </>
            )}
          </button>

          <button
            type="button"
            onClick={onReset}
            disabled={loading || (!title && !content)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-slate-700 text-slate-400 font-medium rounded-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            重置
          </button>
        </div>
      </form>

      {/* 示例事件列表 */}
      <div className="mt-6 pt-4 border-t border-slate-800">
        <p className="text-xs text-slate-500 mb-2">示例事件（点击使用）</p>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {exampleEvents.map((example, i) => (
            <button
              key={i}
              onClick={() => onExampleClick(example)}
              className="w-full text-left p-2 bg-slate-800/50 rounded hover:bg-slate-800 transition-colors"
              disabled={loading}
            >
              <p className="text-xs text-slate-300 line-clamp-2">{example.title}</p>
              <p className="text-xs text-slate-500 mt-1">{example.category}</p>
            </button>
          ))}
        </div>
      </div>

      {/* 风险提示 */}
      <div className="mt-6 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
        <p className="text-xs text-slate-500 text-center">
          ⚠️ 本系统仅供辅助参考，不构成投资建议
        </p>
      </div>
    </aside>
  );
}