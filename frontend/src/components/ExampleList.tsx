"use client";

import type { ExampleEvent } from "@/types";

interface ExampleListProps {
  examples: ExampleEvent[];
  onSelect: (example: ExampleEvent) => void;
}

export function ExampleList({ examples, onSelect }: ExampleListProps) {
  if (!examples || examples.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {examples.map((example, index) => (
        <button
          key={index}
          onClick={() => onSelect(example)}
          className="text-left p-4 bg-white rounded-lg border border-slate-200 hover:border-primary/50 hover:shadow-md transition-all group"
        >
          <div className="flex items-start gap-2">
            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs font-medium rounded group-hover:bg-primary/10 group-hover:text-primary transition-colors">
              {example.category}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-700 line-clamp-3 group-hover:text-slate-900">
            {example.title}
          </p>
        </button>
      ))}
    </div>
  );
}