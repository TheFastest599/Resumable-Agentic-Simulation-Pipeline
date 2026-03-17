"use client";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function ToolCallIndicator({ tools }) {
  if (!tools || tools.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mb-2">
      {tools.map((name, i) => (
        <Badge key={i} variant="secondary" className="flex items-center gap-1 text-xs">
          <Loader2 className="h-3 w-3 animate-spin" />
          {name}
        </Badge>
      ))}
    </div>
  );
}
