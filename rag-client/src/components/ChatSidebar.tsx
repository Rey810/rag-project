import { ChatSidebarItem } from "@/components/ChatSidebarItem";
import { PersonaSidebarDropdown } from "@/components/PersonaSidebarDropdown";
import { useChatSessionStore } from "@/stores/chatSessionStore";
import { PanelLeftCloseIcon, SquarePenIcon } from "lucide-react";
import type { FC } from "react";

interface ChatSidebarProps {
  open: boolean;
  onClose: () => void;
}

export const ChatSidebar: FC<ChatSidebarProps> = ({ open, onClose }) => {
  const sessions = useChatSessionStore((s) => s.sessions);
  const sortedSessions = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt);
  const activeSessionId = useChatSessionStore((s) => s.activeSessionId);
  const createSession = useChatSessionStore((s) => s.createSession);
  const switchSession = useChatSessionStore((s) => s.switchSession);
  const deleteSession = useChatSessionStore((s) => s.deleteSession);

  const handleNewChat = () => {
    createSession();
  };

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/30 sm:hidden"
          onClick={onClose}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
          }}
          role="button"
          tabIndex={0}
          aria-label="Close sidebar"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-200 sm:relative sm:z-auto sm:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full sm:translate-x-0"
        }`}
      >
        {/* Sidebar header */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-sidebar-border px-4">
          <h1 className="text-base font-semibold tracking-tight text-sidebar-foreground">
            Allan<span className="text-accent">Clear</span>
          </h1>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={handleNewChat}
              className="rounded-md p-1.5 text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
              aria-label="New chat"
            >
              <SquarePenIcon className="size-4" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground sm:hidden"
              aria-label="Close sidebar"
            >
              <PanelLeftCloseIcon className="size-4" />
            </button>
          </div>
        </div>

        {/* Chat list */}
        <nav className="flex-1 overflow-y-auto p-2">
          <div className="flex flex-col gap-0.5">
            {sortedSessions.map((session) => (
              <ChatSidebarItem
                key={session.id}
                session={session}
                isActive={session.id === activeSessionId}
                onSelect={() => switchSession(session.id)}
                onDelete={() => deleteSession(session.id)}
              />
            ))}
          </div>
          {sortedSessions.length === 0 && (
            <p className="px-3 py-4 text-center text-sm text-sidebar-foreground/50">
              No chats yet
            </p>
          )}
        </nav>

        {/* Persona selector */}
        <div className="shrink-0 border-t border-sidebar-border p-3">
          <PersonaSidebarDropdown />
        </div>
      </aside>
    </>
  );
};
