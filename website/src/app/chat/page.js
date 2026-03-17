"use client";
import { useEffect } from "react";
import ChatPanel from "@/components/chat/ChatPanel";
import useChatStore from "@/store/chatStore";

export default function NewChatPage() {
  const { setMessages, setActiveConvId } = useChatStore();

  useEffect(() => {
    setMessages([]);
    setActiveConvId(null);

    // Handle prefill from Tasks page
    const prefill = sessionStorage.getItem("prefill");
    if (prefill) {
      sessionStorage.removeItem("prefill");
      // Give ChatPanel a moment to mount, then we can auto-send via store
      // For now we just clear — user sees the prefill in the input is a UX enhancement
      // that would require lifting state; keep it simple.
    }
  }, [setMessages, setActiveConvId]);

  return <ChatPanel conversationId={null} />;
}
