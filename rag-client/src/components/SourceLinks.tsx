import { ExternalLinkIcon, FileTextIcon } from "lucide-react";
import type { FC } from "react";
import type { Source } from "@/types/sources";

interface SourceLinksProps {
  sources: Source[];
}

export const SourceLinks: FC<SourceLinksProps> = ({ sources }) => {
  if (sources.length === 0) return null;

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {sources.map((source, i) =>
        source.type === "article" ? (
          <a
            key={i}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-1.5 rounded-lg border border-border bg-muted px-2.5 py-1.5 text-[11px] font-medium text-muted-foreground shadow-sm transition-all hover:border-ring/40 hover:bg-muted hover:text-foreground hover:shadow-md"
          >
            <ExternalLinkIcon className="size-3 shrink-0 opacity-60 transition-opacity group-hover:opacity-100" />
            <span>{source.label}</span>
          </a>
        ) : (
          <span
            key={i}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-muted/60 px-2.5 py-1.5 text-[11px] font-medium text-muted-foreground/60 shadow-sm"
          >
            <FileTextIcon className="size-3 shrink-0 opacity-50" />
            <span>{source.label}</span>
          </span>
        )
      )}
    </div>
  );
};
