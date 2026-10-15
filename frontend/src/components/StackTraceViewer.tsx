'use client';

import React, { useState } from 'react';
import { Copy, Check, FileCode } from 'lucide-react';

interface StackTraceViewerProps {
  stackTrace?: string | null;
  maxHeight?: string;
}

export function StackTraceViewer({ stackTrace, maxHeight = '400px' }: StackTraceViewerProps) {
  const [copied, setCopied] = useState(false);

  if (!stackTrace || !stackTrace.trim()) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs font-mono text-slate-500 italic flex items-center gap-2">
        <FileCode className="h-4 w-4 text-slate-600" />
        No stack trace captured for this event.
      </div>
    );
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(stackTrace);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const lines = stackTrace.split('\n');

  return (
    <div className="rounded-xl border border-slate-800 bg-[#070b12] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800/80 bg-slate-950/80 text-xs font-mono text-slate-400">
        <div className="flex items-center gap-2">
          <FileCode className="h-3.5 w-3.5 text-blue-400" />
          <span>Normalized Traceback ({lines.length} lines)</span>
        </div>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-800/80 hover:bg-slate-750 text-slate-300 hover:text-white transition text-[11px]"
          title="Copy stack trace"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <div
        className="overflow-auto p-4 text-xs font-mono text-slate-300 leading-relaxed"
        style={{ maxHeight }}
      >
        <pre className="m-0 select-text whitespace-pre-wrap break-all">
          {lines.map((line, idx) => {
            const isFile = line.includes('File "') || line.includes(' at ');
            const isException =
              line.includes('Error:') ||
              line.includes('Exception:') ||
              line.match(/^[A-Z][A-Za-z0-9_]*Error/);

            let lineClass = 'text-slate-300';
            if (isFile) {
              lineClass = 'text-blue-300/90 font-medium';
            } else if (isException) {
              lineClass = 'text-rose-400 font-semibold';
            } else if (line.trim().startsWith('Traceback')) {
              lineClass = 'text-slate-500 font-semibold';
            }

            return (
              <div key={idx} className="flex hover:bg-slate-900/50 px-1 -mx-1 rounded">
                <span className="w-8 shrink-0 text-slate-600 select-none text-right pr-3 text-[11px]">
                  {idx + 1}
                </span>
                <span className={lineClass}>{line}</span>
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
