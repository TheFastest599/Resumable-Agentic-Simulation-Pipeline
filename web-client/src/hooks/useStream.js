"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import useChatStore from "@/store/chatStore";

const STREAM_URL = "http://localhost:8000/agent/chat/stream";

export function useStream() {
  const router = useRouter();
  const qc = useQueryClient();
  const store = useChatStore();

  const sendMessage = async (message, conversationId) => {
    if (store.isStreaming) return;

    // Optimistic user message
    store.appendMessage({ role: "user", content: message, id: crypto.randomUUID() });
    // Empty assistant placeholder
    store.appendMessage({ role: "assistant", content: "", id: crypto.randomUUID() });
    store.setIsStreaming(true);
    store.clearTools();

    let finalConvId = conversationId;

    try {
      const res = await fetch(STREAM_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: conversationId ?? null,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop(); // keep incomplete trailing chunk

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data: ")) continue;
          let event;
          try {
            event = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (event.type === "token") {
            store.updateLastAssistant(event.content);
          } else if (event.type === "tool_start") {
            store.addTool(event.name);
          } else if (event.type === "tool_end") {
            store.removeTool(event.name);
          } else if (event.type === "done") {
            finalConvId = event.conversation_id;
            store.setActiveConvId(finalConvId);
            qc.invalidateQueries({ queryKey: ["jobs"] });
            // Only refetch conversation list when a new conversation was created
            if (!conversationId) {
              qc.invalidateQueries({ queryKey: ["conversations"] });
              router.replace(`/chat/${finalConvId}`);
            }
          } else if (event.type === "error") {
            toast.error(event.message ?? "Agent error");
          }
        }
      }
    } catch (err) {
      toast.error(err.message ?? "Stream failed");
      // Remove empty assistant placeholder on error
      store.setMessages(store.messages.slice(0, -1));
    } finally {
      store.setIsStreaming(false);
      store.clearTools();
    }
  };

  return { sendMessage };
}
