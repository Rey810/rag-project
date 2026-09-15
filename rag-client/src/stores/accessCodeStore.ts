import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AccessCodeState {
  accessCode: string | null;
  setAccessCode: (code: string) => void;
  clearAccessCode: () => void;
}

export const useAccessCodeStore = create<AccessCodeState>()(
  persist(
    (set) => ({
      accessCode: null,
      setAccessCode: (code: string) => set({ accessCode: code }),
      clearAccessCode: () => set({ accessCode: null }),
    }),
    {
      name: "allanclear-access-code",
    },
  ),
);

/** Authorization header for backend requests, empty when no code is stored. */
export function authHeaders(): Record<string, string> {
  const code = useAccessCodeStore.getState().accessCode;
  return code ? { Authorization: `Bearer ${code}` } : {};
}
