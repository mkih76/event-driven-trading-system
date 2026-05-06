"use client";

import { Send, RotateCcw, Loader2 } from "lucide-react";

interface EventInputProps {
  title: string;
  content: string;
  onTitleChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  loading: boolean;
}

export function EventInput({
  title,
  content,
  onTitleChange,
  onContentChange,
  onSubmit,
  onReset,
  loading,
}: EventInputProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim() && !loading) {
      onSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="title"
          className="block text-sm font-medium text-slate-700 mb-1"
        >
          事件标题 <span className="text-destructive">*</span>
        </label>
        <input
          type="text"
          id="title"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="例如：美国与伊朗爆发军事冲突，霍尔木兹海峡被封锁"
          className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors text-slate-800 placeholder:text-slate-400"
          disabled={loading}
        />
      </div>

      <div>
        <label
          htmlFor="content"
          className="block text-sm font-medium text-slate-700 mb-1"
        >
          事件详情
          <span className="text-slate-400 font-normal ml-2">（可选）</span>
        </label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => onContentChange(e.target.value)}
          placeholder="补充事件的详细信息..."
          rows={4}
          className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors text-slate-800 placeholder:text-slate-400 resize-none"
          disabled={loading}
        />
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={!title.trim() || loading}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white font-medium rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              分析中...
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              开始分析
            </>
          )}
        </button>

        <button
          type="button"
          onClick={onReset}
          disabled={loading || (!title && !content)}
          className="flex items-center gap-2 px-4 py-3 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          重置
        </button>

        <div className="ml-auto text-sm text-slate-500">
          按 Enter 快速提交
        </div>
      </div>
    </form>
  );
}