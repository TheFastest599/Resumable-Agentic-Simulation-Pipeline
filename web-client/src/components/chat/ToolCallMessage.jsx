"use client";
import { useState } from "react";
import { ChevronDown, ChevronRight, Loader2, Wrench } from "lucide-react";

function JsonBlock({ value }) {
  let parsed = value;
  if (typeof value === "string") {
    try { parsed = JSON.parse(value); } catch { /* keep as string */ }
  }
  return (
    <pre className="text-xs bg-muted rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
      {typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2)}
    </pre>
  );
}

export default function ToolCallMessage({ name, input, output, done }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="my-1 rounded-lg border bg-muted/40 text-sm overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-muted/60 transition-colors"
      >
        <Wrench className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <span className="font-mono font-medium text-xs">{name}</span>
        {!done && (
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground ml-1" />
        )}
        <span className="ml-auto text-muted-foreground">
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </span>
      </button>

      {/* Expandable details */}
      {open && (
        <div className="px-3 pb-3 space-y-2 border-t">
          {input !== undefined && input !== null && (
            <div className="pt-2">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Input</p>
              <JsonBlock value={input} />
            </div>
          )}
          {done && output !== undefined && output !== null && (
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Output</p>
              <JsonBlock value={output} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
