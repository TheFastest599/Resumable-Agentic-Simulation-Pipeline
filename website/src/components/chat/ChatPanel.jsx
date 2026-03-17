"use client";
import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import MessageBubble from "./MessageBubble";
import ToolCallIndicator from "./ToolCallIndicator";
import useChatStore from "@/store/chatStore";
import { useStream } from "@/hooks/useStream";

export default function ChatPanel({ conversationId }) {
  const { messages, isStreaming, activeTools } = useChatStore();
  const { sendMessage } = useStream();
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeTools]);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || isStreaming) return;
    setInput("");
    sendMessage(msg, conversationId);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Messages — scrollable area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <p className="text-center text-muted-foreground text-sm pt-20">
              Start a conversation — ask the agent to run simulations.
            </p>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
          ))}
          {isStreaming && activeTools.length > 0 && (
            <div className="flex justify-start">
              <div className="max-w-[75%]">
                <ToolCallIndicator tools={activeTools} />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar — fixed at bottom */}
      <div className="border-t px-4 py-3">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the agent to run simulations…"
            className="resize-none min-h-11 max-h-40"
            rows={1}
            disabled={isStreaming}
          />
          <Button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            size="icon"
            className="shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
