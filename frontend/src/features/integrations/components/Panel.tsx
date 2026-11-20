import type { HTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { useCardSurfaceStyle, useSurfaceTokens } from "@/core/styles/surfaceTokens";

/**
 * A titled section on the HMS card surface -- the same gradient, border,
 * shadow, 16px radius and title treatment as the dashboard panels
 * (RecentActivityPanel, AlertsPanel). Integration-local on purpose: it reuses
 * the shared surface tokens and changes no global style.
 */
export const Panel = ({
  id,
  title,
  description,
  actions,
  children,
  className,
  ...rest
}: {
  id: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
} & Omit<HTMLAttributes<HTMLElement>, "title">) => {
  const surface = useCardSurfaceStyle();
  const { titleColor, textMuted } = useSurfaceTokens();
  return (
    // A <div role="region">, like the dashboard panels' <div>, so the global
    // card rules in index.css render it exactly as they render those panels.
    <div
      role="region"
      aria-labelledby={id}
      className={cn("min-w-0 rounded-[16px] p-4 sm:p-5", className)}
      style={surface}
      {...rest}
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 id={id} className="text-base font-medium leading-6" style={{ color: titleColor }}>
            {title}
          </h2>
          {description ? (
            <p className="mt-0.5 text-xs leading-5" style={{ color: textMuted }}>
              {description}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {children}
    </div>
  );
};

/** A heading for a row of KPI tiles, which sit directly on the page as on the HMS dashboard. */
export const SectionHeading = ({ id, title, description }: { id: string; title: string; description?: ReactNode }) => {
  const { titleColor, textMuted } = useSurfaceTokens();
  return (
    <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <h2 id={id} className="text-base font-medium leading-6" style={{ color: titleColor }}>
        {title}
      </h2>
      {description ? (
        <p className="text-xs leading-5" style={{ color: textMuted }}>
          {description}
        </p>
      ) : null}
    </div>
  );
};

/** Secondary text in panel colour. */
export const Muted = ({ children, className }: { children: ReactNode; className?: string }) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <p className={cn("text-xs leading-5", className)} style={{ color: textMuted }}>
      {children}
    </p>
  );
};

/** The outline link button used in panel headers and footers. */
export const PanelLink = ({ to, children }: { to: string; children: ReactNode }) => (
  <Link
    to={to}
    className="inline-flex items-center gap-1 whitespace-nowrap rounded-lg border border-border bg-background/60 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
  >
    {children}
    <ArrowRight className="h-3.5 w-3.5" aria-hidden />
  </Link>
);
