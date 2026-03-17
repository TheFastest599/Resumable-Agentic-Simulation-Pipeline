import { create } from "zustand";

const useChatStore = create((set) => ({
  activeConvId: null,
  setActiveConvId: (id) => set({ activeConvId: id }),

  messages: [],
  setMessages: (messages) => set({ messages }),
  appendMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAssistant: (chunk) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + chunk };
      }
      return { messages: msgs };
    }),

  isStreaming: false,
  setIsStreaming: (v) => set({ isStreaming: v }),

  activeTools: [],
  addTool: (name) => set((s) => ({ activeTools: [...s.activeTools, name] })),
  removeTool: (name) =>
    set((s) => ({ activeTools: s.activeTools.filter((t) => t !== name) })),
  clearTools: () => set({ activeTools: [] }),
}));

export default useChatStore;
