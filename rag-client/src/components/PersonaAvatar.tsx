import type { PersonaId } from "@/stores/personaStore";

import justTheAnswerSvg from "@/assets/just_the_answer.svg";
import explainSimplySvg from "@/assets/explain_simply.svg";
import giveMeDetailSvg from "@/assets/give_me_detail.svg";

const AVATAR_MAP: Record<PersonaId, string> = {
  just_the_answer: justTheAnswerSvg,
  explain_simply: explainSimplySvg,
  give_me_detail: giveMeDetailSvg,
};

const ALT_MAP: Record<PersonaId, string> = {
  just_the_answer: "Just Answers avatar",
  explain_simply: "Explain Simply avatar",
  give_me_detail: "Get Technical avatar",
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
      className={className}
    />
  );
};
