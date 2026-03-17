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

    // Record where this turn starts before appending anything
    const turnStartIdx = useChatStore.getState().messages.length;

    // Optimistic user message
    store.appendMessage({ role: "user", content: message, id: crypto.randomUUID() });
    store.setIsStreaming(true);
    store.setIsTyping(true);
    store.clearTools();

    // Assistant placeholder is added on the first token so tool cards appear above it
    let assistantAdded = false;
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
            if (!assistantAdded) {
              store.setIsTyping(false);
              store.appendMessage({ role: "assistant", content: event.content, id: crypto.randomUUID() });
              assistantAdded = true;
            } else {
              store.updateLastAssistant(event.content);
            }
          } else if (event.type === "tool_start") {
            store.addTool(event.name);
            store.addToolMessage(event.name, event.input, turnStartIdx);
          } else if (event.type === "tool_end") {
            store.removeTool(event.name);
            store.resolveToolMessage(event.name, event.output);
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
      // Remove empty assistant placeholder if it was added but has no content
      if (assistantAdded) {
        store.setMessages(
          useChatStore.getState().messages.filter(
            (m) => !(m.role === "assistant" && m.content === "")
          )
        );
      }
    } finally {
      store.setIsStreaming(false);
      store.setIsTyping(false);
      store.clearTools();
    }
  };

  return { sendMessage };
}
