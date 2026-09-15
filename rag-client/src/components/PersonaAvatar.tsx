import type { PersonaId } from "@/stores/personaStore";
import { cn } from "@/lib/utils";

import justTheAnswerSvg from "@/assets/just_the_answer.svg";
import explainSimplySvg from "@/assets/explain_simply.svg";
import giveMeDetailSvg from "@/assets/give_me_detail.svg";
import eminemJpg from "@/assets/eminem.jpg";

const AVATAR_MAP: Record<PersonaId, string> = {
  just_the_answer: justTheAnswerSvg,
  explain_simply: explainSimplySvg,
  give_me_detail: giveMeDetailSvg,
  eminem: eminemJpg,
};

// Photo avatars are square images; round them so they sit alongside the illustrated SVGs.
const PHOTO_PERSONAS: ReadonlySet<PersonaId> = new Set<PersonaId>(["eminem"]);

const ALT_MAP: Record<PersonaId, string> = {
  just_the_answer: "Just Answers avatar",
  explain_simply: "Explain Simply avatar",
  give_me_detail: "Get Technical avatar",
  eminem: "Eminem avatar",
};

interface PersonaAvatarProps {
  personaId: PersonaId;
  className?: string;
}

export const PersonaAvatar = ({ personaId, className }: PersonaAvatarProps) => {
  return (
    <img
      src={AVATAR_MAP[personaId]}
      alt={ALT_MAP[personaId]}
      className={cn(className, PHOTO_PERSONAS.has(personaId) && "rounded-full object-cover")}
    />
  );
};
