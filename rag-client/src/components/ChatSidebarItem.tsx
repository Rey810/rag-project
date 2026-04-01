import { cn } from "@/lib/utils";
import type { ChatSession } from "@/stores/chatSessionStore";
import { Trash2Icon } from "lucide-react";
import type { FC } from "react";

interface ChatSidebarItemProps {
  session: ChatSession;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

export const ChatSidebarItem: FC<ChatSidebarItemProps> = ({
  session,
  isActive,
  onSelect,
  onDelete,
}) => {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent/50",
      )}
    >
      <span className="min-w-0 flex-1 truncate">
        {session.title || "New Chat"}
      </span>
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.stopPropagation();
            onDelete();
          }
        }}
        className="shrink-0 rounded p-1 opacity-0 transition-opacity hover:bg-sidebar-accent group-hover:opacity-100"
        aria-label="Delete chat"
      >
        <Trash2Icon className="size-3.5" />
      </span>
    </button>
  );
};
