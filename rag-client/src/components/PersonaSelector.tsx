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
    <div className="flex w-full items-center justify-center gap-[1.44rem]">
      {PERSONAS.map((persona) => {
        const isSelected = persona.id === selectedPersona;

        return (
          <button
            key={persona.id}
            type="button"
            onClick={() => handleSelect(persona.id)}
            className={cn(
              // Base styles — all cards always have border-2 to prevent layout shift
              "relative flex cursor-pointer items-center rounded-[14px] border-2 bg-white transition-all",
              // Desktop: always expanded
              "sm:flex-1 sm:gap-[0.86rem] sm:px-[1.15rem] sm:py-[0.86rem]",
              // Mobile: collapsed = avatar-only square, expanded = full card
              isSelected
                ? "flex-1 gap-[0.86rem] px-[1.15rem] py-[0.86rem]"
                : "w-[4rem] shrink-0 justify-center p-[0.72rem] sm:w-auto sm:justify-start sm:p-0 sm:px-[1.15rem] sm:py-[0.86rem]",
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
                isSelected ? "size-[3.16rem] sm:size-[3.45rem]" : "size-[2.59rem] sm:size-[3.45rem]",
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
                  "truncate text-[17px] font-semibold sm:text-[1.15rem]",
                  isSelected ? "text-terracotta" : "text-[#1A1A1A]",
                )}
              >
                {persona.name}
              </div>
              <div className="truncate text-[15px] text-[#999]">
                {persona.description}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};
