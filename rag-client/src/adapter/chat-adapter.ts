import type { ChatModelAdapter } from "@assistant-ui/react";
import { useChatSessionStore } from "@/stores/chatSessionStore";
import { usePersonaStore } from "@/stores/personaStore";
import type { Source } from "@/types/sources";

const API_URL = "http://localhost:8000/chat";
const SOURCES_SENTINEL = "[SOURCES]";

interface BackendMessage {
  role: string;
  content: string;
}

export const chatModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const store = useChatSessionStore.getState();
    let sessionId = store.activeSessionId;

    if (!sessionId) {
      sessionId = store.createSession();
    }

    const chatHistory: BackendMessage[] = messages.map((m) => ({
      role: m.role,
      content:
        m.content
          .filter((part) => part.type === "text")
          .map((part) => part.text)
          .join("") || "",
    }));

    yield { content: [{ type: "text" as const, text: "" }] };

    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_history: chatHistory,
        persona: usePersonaStore.getState().selectedPersona,
      }),
      signal: abortSignal,
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let text = "";
    let sources: Source[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const sentinelIdx = chunk.indexOf(SOURCES_SENTINEL);

      if (sentinelIdx !== -1) {
        text += chunk.slice(0, sentinelIdx);
        try {
          sources = JSON.parse(chunk.slice(sentinelIdx + SOURCES_SENTINEL.length));
        } catch {
          sources = [];
        }
      } else {
        text += chunk;
      }

      yield { content: [{ type: "text" as const, text }] };
    }

    yield {
      content: [
        { type: "text" as const, text },
        ...(sources.length > 0
          ? [{ type: "data" as const, name: "sources", data: sources }]
          : []),
      ],
    };

    useChatSessionStore
      .getState()
      .updateSessionMessages(sessionId, [
        ...chatHistory,
        { role: "assistant", content: text, sources },
      ]);
  },
};
