import { PersonaAvatar } from "@/components/PersonaAvatar";
import { cn } from "@/lib/utils";
import { PERSONAS, usePersonaStore } from "@/stores/personaStore";
import { CheckIcon, ChevronUpIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export const PersonaSidebarDropdown = () => {
  const selectedPersona = usePersonaStore((s) => s.selectedPersona);
  const setSelectedPersona = usePersonaStore((s) => s.setSelectedPersona);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const currentPersona = PERSONAS.find((p) => p.id === selectedPersona)!;

  // Close on outside click
  useEffect(() => {
    if (!open) return;

    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      {/* Dropdown menu — opens upward */}
      {open && (
        <div className="absolute bottom-full left-0 right-0 mb-1 rounded-lg border border-sidebar-border bg-sidebar shadow-lg">
          {PERSONAS.map((persona) => {
            const isSelected = persona.id === selectedPersona;

            return (
              <button
                key={persona.id}
                type="button"
                onClick={() => {
                  setSelectedPersona(persona.id);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors",
                  "hover:bg-sidebar-accent",
                  "first:rounded-t-lg last:rounded-b-lg",
                  isSelected && "text-terracotta",
                )}
              >
                <PersonaAvatar personaId={persona.id} className="size-6 shrink-0" />
                <span className="truncate font-medium">{persona.name}</span>
                {isSelected && <CheckIcon className="ml-auto size-4 shrink-0" />}
              </button>
            );
          })}
        </div>
      )}

      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
      >
        <PersonaAvatar personaId={selectedPersona} className="size-6 shrink-0" />
        <span className="truncate font-medium">{currentPersona.name}</span>
        <ChevronUpIcon
          className={cn(
            "ml-auto size-4 shrink-0 text-sidebar-foreground/50 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>
    </div>
  );
};
