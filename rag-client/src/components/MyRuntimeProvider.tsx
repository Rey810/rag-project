import { chatModelAdapter } from "@/adapter/chat-adapter";
import { useChatSessionStore } from "@/stores/chatSessionStore";
import { AssistantRuntimeProvider, useLocalRuntime } from "@assistant-ui/react";
import { useMemo, type ReactNode } from "react";

export function MyRuntimeProvider({ children }: { children: ReactNode }) {
  const activeSessionId = useChatSessionStore((s) => s.activeSessionId);
  const sessions = useChatSessionStore((s) => s.sessions);

  const initialMessages = useMemo(() => {
    const session = sessions.find((s) => s.id === activeSessionId);
    if (!session || session.messages.length === 0) return [];

    return session.messages.map((m) => ({
      role: m.role as "user" | "assistant",
      content: [{ type: "text" as const, text: m.content }],
    }));
    // Only compute on mount (key-based remounting handles session switches)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runtimeOptions = useMemo(() => ({ initialMessages }), [initialMessages]);
  const runtime = useLocalRuntime(chatModelAdapter, runtimeOptions);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}
