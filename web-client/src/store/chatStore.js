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
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], content: msgs[i].content + chunk };
          break;
        }
      }
      return { messages: msgs };
    }),

  isStreaming: false,
  setIsStreaming: (v) => set({ isStreaming: v }),

  isTyping: false,
  setIsTyping: (v) => set({ isTyping: v }),

  activeTools: [],
  addTool: (name) => set((s) => ({ activeTools: [...s.activeTools, name] })),
  removeTool: (name) =>
    set((s) => ({ activeTools: s.activeTools.filter((t) => t !== name) })),
  clearTools: () => set({ activeTools: [] }),

  // Persistent tool call history in the message list
  addToolMessage: (name, input, turnStartIdx) =>
    set((s) => {
      const msgs = [...s.messages];
      const toolMsg = { id: crypto.randomUUID(), role: "tool", name, input, output: null, done: false };
      // Only look for an assistant bubble within the current turn (at or after turnStartIdx)
      let insertIdx = msgs.length;
      for (let i = msgs.length - 1; i >= (turnStartIdx ?? 0); i--) {
        if (msgs[i].role === "assistant") { insertIdx = i; break; }
      }
      msgs.splice(insertIdx, 0, toolMsg);
      return { messages: msgs };
    }),
  resolveToolMessage: (name, output) =>
    set((s) => {
      const msgs = [...s.messages];
      // find last unresolved tool message with this name
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "tool" && msgs[i].name === name && !msgs[i].done) {
          msgs[i] = { ...msgs[i], output, done: true };
          break;
        }
      }
      return { messages: msgs };
    }),
}));

export default useChatStore;
