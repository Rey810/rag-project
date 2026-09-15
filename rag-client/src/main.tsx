import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AccessGate } from "@/components/AccessGate";
import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TooltipProvider>
      <AccessGate>
        <App />
      </AccessGate>
    </TooltipProvider>
  </StrictMode>,
);
