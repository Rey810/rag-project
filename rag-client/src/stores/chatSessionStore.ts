import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Source } from "@/types/sources";

export interface BackendMessage {
  role: string;
  content: string;
  sources?: Source[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: BackendMessage[];
  createdAt: number;
  updatedAt: number;
}

interface ChatSessionState {
  sessions: ChatSession[];
  activeSessionId: string | null;

  createSession: () => string;
  deleteSession: (id: string) => void;
  switchSession: (id: string) => void;
  updateSessionMessages: (id: string, messages: BackendMessage[]) => void;
}

const LEGACY_KEY = "allanclear-chat";

function migrateLegacyData(): ChatSession | null {
  try {
    const raw = localStorage.getItem(LEGACY_KEY);
    if (!raw) return null;
    const messages: BackendMessage[] = JSON.parse(raw);
    if (!Array.isArray(messages) || messages.length === 0) return null;

    const firstUserMsg = messages.find((m) => m.role === "user");
    const title = firstUserMsg
      ? firstUserMsg.content.slice(0, 40)
      : "New Chat";
    const now = Date.now();

    const session: ChatSession = {
      id: crypto.randomUUID(),
      title,
      messages,
      createdAt: now,
      updatedAt: now,
    };

    localStorage.removeItem(LEGACY_KEY);
    return session;
  } catch {
    return null;
  }
}

export const useChatSessionStore = create<ChatSessionState>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,

      createSession: () => {
        const id = crypto.randomUUID();
        const now = Date.now();
        const session: ChatSession = {
          id,
          title: "New Chat",
          messages: [],
          createdAt: now,
          updatedAt: now,
        };
        set((state) => ({
          sessions: [session, ...state.sessions],
          activeSessionId: id,
        }));
        return id;
      },

      deleteSession: (id: string) => {
        const { activeSessionId, sessions } = get();
        const remaining = sessions.filter((s) => s.id !== id);
        let newActiveId = activeSessionId;

        if (activeSessionId === id) {
          newActiveId = remaining.length > 0 ? remaining[0].id : null;
        }

        set({
          sessions: remaining,
          activeSessionId: newActiveId,
        });
      },

      switchSession: (id: string) => {
        set({ activeSessionId: id });
      },

      updateSessionMessages: (id: string, messages: BackendMessage[]) => {
        set((state) => ({
          sessions: state.sessions.map((s) => {
            if (s.id !== id) return s;

            let title = s.title;
            if (title === "New Chat") {
              const firstUserMsg = messages.find((m) => m.role === "user");
              if (firstUserMsg) {
                title = firstUserMsg.content.slice(0, 40);
              }
            }

            return {
              ...s,
              title,
              messages,
              updatedAt: Date.now(),
            };
          }),
        }));
      },
    }),
    {
      name: "allanclear-sessions",
      onRehydrateStorage: () => (state) => {
        if (!state) return;

        const legacy = migrateLegacyData();
        if (legacy) {
          state.sessions = [legacy, ...state.sessions];
          if (!state.activeSessionId) {
            state.activeSessionId = legacy.id;
          }
        }
      },
    },
  ),
);
