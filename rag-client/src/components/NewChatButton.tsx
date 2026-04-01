import { useChatSessionStore } from "@/stores/chatSessionStore";
import { Button } from "@/components/ui/button";
import { SquarePenIcon } from "lucide-react";
import type { FC } from "react";

export const NewChatButton: FC = () => {
  const createSession = useChatSessionStore((s) => s.createSession);

  const handleNewChat = () => {
    createSession();
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleNewChat}
      className="gap-1.5 text-muted-foreground transition-colors hover:text-foreground"
    >
      <SquarePenIcon className="size-4" />
      New Chat
    </Button>
  );
};
