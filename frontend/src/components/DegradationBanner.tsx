"use client";

import { AlertTriangle, X } from "lucide-react";
import { useState } from "react";

interface DegradationBannerProps {
  message: string;
}

export function DegradationBanner({ message }: DegradationBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="bg-yellow-900/30 border border-yellow-600/50 rounded-lg p-4 mb-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
        <div>
          <p className="text-yellow-200 font-medium">当前使用规则模式</p>
          <p className="text-yellow-300/80 text-sm mt-0.5">{message}</p>
        </div>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="p-1 hover:bg-yellow-900/50 rounded transition-colors"
      >
        <X className="w-4 h-4 text-yellow-400" />
      </button>
    </div>
  );
}