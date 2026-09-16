import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * The one page heading every HMS module renders.
 *
 * WHY THIS EXISTS. The heading used to be pinned by a global rule in
 * index.css that matched on document structure:
 *
 *     .hms-content .animate-fade-in > h1:first-child,
 *     .hms-content .animate-fade-in > :first-child:has(h1)
 *
 * That rule styled whatever happened to be first inside the page, so a page
 * only floated its heading by accident of markup. It missed Services Tracking
 * outright, whose first child is a dialog rather than the heading, and it
 * could not reach the two pages that were using `page-header` / `page-title`
 * -- class names that are not defined anywhere in the stylesheet, so those
 * headings rendered as unstyled browser defaults.
 *
 * The bar now lives on explicit classes this component owns
 * (`.hms-page-header*`, see index.css), so a page gets the standard header
 * because it renders this component, not because its markup matched a
 * selector.
 *
 * IT IS A STICKY BAR, NOT AN OVERLAY. `position: sticky` keeps the element in
 * normal flow, so it occupies real layout space and content begins below it
 * rather than underneath it. It paints a SOLID surface -- an earlier version
 * used `backdrop-filter: blur()`, which washed out the KPI cards as they
 * scrolled beneath. Nothing behind this bar is dimmed, blurred or overlapped.
 *
 * `.hms-content` in AppLayout is the single scroll container for every page,
 * which is what makes plain `position: sticky` work here.
 *
 * STRUCTURE. One row, fixed height, space-between:
 *
 *     [ leading? ][ title / subtitle ]            [ actions ]
 *
 * The identity block truncates with an ellipsis rather than wrapping, so the
 * bar can never grow to a second or third line and shift the page below it.
 */
interface PageHeaderProps {
  /** The module name, e.g. "Ticket Management". Rendered as the page's only h1. */
  title: string;
  /**
   * Optional control placed BEFORE the title, for a view that is navigated
   * into rather than selected from the sidebar -- in practice a back button.
   */
  leading?: ReactNode;
  /**
   * One secondary line under the title. Keep it to a SINGLE line: the bar is a
   * fixed height and this text is clipped with an ellipsis, so a `<br />` here
   * would simply lose the second half. Join a descriptor and a tagline with a
   * separator instead.
   */
  description?: ReactNode;
  /**
   * Controls pinned to the right of the title -- only ever the page's OWN
   * existing controls. The stylesheet puts them on one 36px baseline; it does
   * not add any.
   */
  actions?: ReactNode;
  /** Escape hatch for a page that needs one extra utility. Used sparingly. */
  className?: string;
}

export const PageHeader = ({
  title,
  leading,
  description,
  actions,
  className,
}: PageHeaderProps) => (
  <div className={cn("hms-page-header", className)}>
    <div className="hms-page-header__identity">
      {leading ? <div className="hms-page-header__leading">{leading}</div> : null}
      <div className="hms-page-header__text">
        <h1 className="hms-page-header__title">{title}</h1>
        {description ? (
          <p className="hms-page-header__subtitle">{description}</p>
        ) : null}
      </div>
    </div>
    {actions ? <div className="hms-page-header__actions">{actions}</div> : null}
  </div>
);
