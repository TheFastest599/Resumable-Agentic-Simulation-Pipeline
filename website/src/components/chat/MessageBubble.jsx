"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const mdComponents = {
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline text-blue-600 hover:text-blue-800"
    >
      {children}
    </a>
  ),
  code: ({ className, children }) => {
    const isBlock = /language-/.test(className ?? "") || String(children).includes("\n");
    return isBlock ? (
      <pre className="bg-muted p-3 rounded text-sm font-mono overflow-x-auto my-2">
        <code className={className}>{children}</code>
      </pre>
    ) : (
      <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono">{children}</code>
    );
  },
  p: ({ children }) => <div className="mb-2 last:mb-0">{children}</div>,
  ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="text-sm border-collapse w-full">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border px-2 py-1 bg-muted text-left font-medium">{children}</th>
  ),
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
};

export default function MessageBubble({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-lg px-4 py-3 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-card border text-card-foreground"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {content || "…"}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
