import { PersonaAvatar } from "@/components/PersonaAvatar";
import { cn } from "@/lib/utils";
import { PERSONAS, usePersonaStore } from "@/stores/personaStore";
import type { PersonaId } from "@/stores/personaStore";

interface PersonaSelectorProps {
  selected?: PersonaId;
  onSelect?: (persona: PersonaId) => void;
}

export const PersonaSelector = ({ selected, onSelect }: PersonaSelectorProps) => {
  const storeSelected = usePersonaStore((s) => s.selectedPersona);
  const storeSetSelected = usePersonaStore((s) => s.setSelectedPersona);

  const selectedPersona = selected ?? storeSelected;
  const handleSelect = onSelect ?? storeSetSelected;

  return (
    <div className="flex w-full items-center justify-center gap-5">
      {PERSONAS.map((persona) => {
        const isSelected = persona.id === selectedPersona;

        return (
          <button
            key={persona.id}
            type="button"
            onClick={() => handleSelect(persona.id)}
            className={cn(
              // Base styles — all cards always have border-2 to prevent layout shift
              "relative flex cursor-pointer items-center rounded-[12px] border-2 bg-white transition-all",
              // Desktop: always expanded
              "sm:flex-1 sm:gap-3 sm:px-4 sm:py-3",
              // Mobile: collapsed = avatar-only square, expanded = full card
              isSelected
                ? "flex-1 gap-3 px-4 py-3"
                : "w-14 shrink-0 justify-center p-2.5 sm:w-auto sm:justify-start sm:p-0 sm:px-4 sm:py-3",
              // Border color + opacity for selection state
              isSelected
                ? "border-terracotta"
                : "border-transparent opacity-50 hover:opacity-75 hover:shadow-sm",
              // Transitions
              "duration-300 ease-in-out sm:duration-200",
            )}
            aria-pressed={isSelected}
          >
            {/* Avatar */}
            <div
              className={cn(
                "shrink-0",
                isSelected ? "size-11 sm:size-12" : "size-9 sm:size-12",
              )}
            >
              <PersonaAvatar personaId={persona.id} className="size-full" />
            </div>

            {/* Text — always visible on desktop, only when selected on mobile */}
            <div
              className={cn(
                "min-w-0 text-left",
                // Mobile: hide text for unselected, show for selected
                isSelected
                  ? "opacity-100 transition-opacity duration-200 delay-100"
                  : "hidden opacity-0 sm:block sm:opacity-100",
              )}
            >
              <div
                className={cn(
                  "truncate text-[15px] font-semibold sm:text-base",
                  isSelected ? "text-terracotta" : "text-[#1A1A1A]",
                )}
              >
                {persona.name}
              </div>
              <div className="truncate text-[13px] text-[#999]">
                {persona.description}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};
