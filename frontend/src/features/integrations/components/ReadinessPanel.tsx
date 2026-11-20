import type { ReadinessBlock } from "@/lib/api/integrations";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { readinessRows } from "../lib/presentation";
import { Panel } from "./Panel";
import { StatusBadge } from "./StatusBadge";

/**
 * The eight readiness dimensions, each with its own status. They are listed
 * side by side on purpose and never folded into one verdict: a synthetic PASS
 * says nothing about vendor validation, and neither says the system is ready
 * for production.
 */
export const ReadinessPanel = ({
  id,
  readiness,
  title = "Readiness",
}: {
  id: string;
  readiness: ReadinessBlock;
  title?: string;
}) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <Panel
      id={id}
      title={title}
      description="Each dimension is tracked separately. Decision references (HF-xx) are from the HTNG / FIAS decision register; statuses are read-only here."
    >
      <ul className="divide-y divide-border/60" aria-label={title}>
        {readinessRows(readiness).map((row) => (
          <li key={row.key} className="py-2.5" data-dimension={row.key}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm" style={{ color: textMuted }}>{row.label}</span>
              <StatusBadge status={row.status} />
            </div>
            {row.details.length || row.note ? (
              <div className="mt-1.5 flex min-w-0 flex-wrap gap-1.5 text-xs" style={{ color: textMuted }}>
                {row.details.map((d) => (
                  <span key={d} className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] text-foreground/80">
                    {d}
                  </span>
                ))}
                {row.note ? <span className="min-w-0 basis-full break-words leading-5">{row.note}</span> : null}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </Panel>
  );
};
