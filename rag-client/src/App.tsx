import { ChatSidebar } from "@/components/ChatSidebar";
import { MyRuntimeProvider } from "@/components/MyRuntimeProvider";
import { Thread } from "@/components/assistant-ui/thread";
import { useChatSessionStore } from "@/stores/chatSessionStore";
import { PanelLeftIcon } from "lucide-react";
import { useEffect, useState } from "react";

function App() {
  const activeSessionId = useChatSessionStore((s) => s.activeSessionId);
  const createSession = useChatSessionStore((s) => s.createSession);

  useEffect(() => {
    if (!activeSessionId) {
      createSession();
    }
  }, [activeSessionId, createSession]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-dvh">
      <ChatSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile header with sidebar toggle */}
        <header className="flex h-14 shrink-0 items-center border-b border-border/50 bg-background/80 px-4 backdrop-blur-md sm:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Open sidebar"
          >
            <PanelLeftIcon className="size-5" />
          </button>
        </header>

        <main className="flex-1 overflow-hidden">
          <MyRuntimeProvider key={activeSessionId ?? "new"}>
            <Thread />
          </MyRuntimeProvider>
        </main>
      </div>
    </div>
  );
}

export default App;
