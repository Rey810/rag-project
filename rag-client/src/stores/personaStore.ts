import { create } from "zustand";
import { persist } from "zustand/middleware";

export type PersonaId = "just_the_answer" | "explain_simply" | "give_me_detail" | "eminem";

export interface Persona {
  id: PersonaId;
  name: string;
  description: string;
}

export const PERSONAS: Persona[] = [
  { id: "just_the_answer", name: "Just Answers", description: "Quick and direct" },
  { id: "explain_simply", name: "Explain Simply", description: "Clear and jargon-free" },
  { id: "give_me_detail", name: "Get Technical", description: "In-depth analysis" },
  { id: "eminem", name: "Eminem", description: "Explicit. Unfiltered." },
];

interface PersonaState {
  selectedPersona: PersonaId;
  setSelectedPersona: (id: PersonaId) => void;
}

export const usePersonaStore = create<PersonaState>()(
  persist(
    (set) => ({
      selectedPersona: "just_the_answer",
      setSelectedPersona: (id: PersonaId) => set({ selectedPersona: id }),
    }),
    {
      name: "allanclear-persona",
    },
  ),
);
