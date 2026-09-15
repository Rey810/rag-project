import { useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useAccessCodeStore } from "@/stores/accessCodeStore";

const AUTH_CHECK_URL = "/auth/check";

export function AccessGate({ children }: { children: ReactNode }) {
  const accessCode = useAccessCodeStore((s) => s.accessCode);
  const setAccessCode = useAccessCodeStore((s) => s.setAccessCode);

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (accessCode) {
    return <>{children}</>;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = code.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(AUTH_CHECK_URL, {
        headers: { Authorization: `Bearer ${trimmed}` },
      });

      if (response.status === 204 || response.ok) {
        setAccessCode(trimmed);
        return;
      }

      if (response.status === 401) {
        setError("That access code is not valid.");
        return;
      }

      setError("Something went wrong. Please try again.");
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex h-dvh items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm rounded-[14px] border border-border bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-medium text-foreground">AllanClear</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter your access code to continue.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-2">
          <label
            htmlFor="access-code"
            className="text-sm font-medium text-foreground"
          >
            Access code
          </label>
          <input
            id="access-code"
            type="password"
            autoComplete="current-password"
            autoFocus
            value={code}
            onChange={(e) => setCode(e.target.value)}
            aria-invalid={error !== null}
            aria-describedby={error ? "access-code-error" : undefined}
            className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm outline-none transition-all placeholder:text-muted-foreground/60 focus-visible:border-ring/50 focus-visible:ring-2 focus-visible:ring-ring/15 aria-invalid:border-destructive/50"
          />

          {error && (
            <p id="access-code-error" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button
            type="submit"
            size="lg"
            disabled={submitting || code.trim().length === 0}
            className="mt-2 w-full"
          >
            {submitting ? "Checking..." : "Continue"}
          </Button>
        </form>
      </div>
    </div>
  );
}
