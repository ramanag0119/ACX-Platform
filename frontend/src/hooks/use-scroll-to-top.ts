import { useEffect } from "react";

/**
 * Return the page's scroll container to the top whenever `dependency` changes.
 *
 * WHY THIS EXISTS. Pagination controls sit at the BOTTOM of a long table, so
 * using them means scrolling down first. Changing page swapped the rows but
 * left the scroll offset exactly where it was, which put both the new page's
 * first rows and the sticky page header above the fold -- from the operator's
 * seat the header had simply vanished and the list appeared to start mid-way
 * through. Nothing in the app moved the scroll position, on any page.
 *
 * `.hms-content` (AppLayout) is the single scroll container for every screen;
 * the window itself does not scroll, so `window.scrollTo` would do nothing
 * here. The element is looked up per call rather than held in a ref so this
 * stays a drop-in one-liner for a page that already owns its pagination state.
 *
 * Runs on mount too. That is a no-op -- the container is already at the top --
 * and it keeps the effect free of a "first render" flag that would have to be
 * kept correct.
 */
export const useScrollToTop = (dependency: unknown) => {
  useEffect(() => {
    const container = document.querySelector(".hms-content");
    if (!container) return;

    // Honour the OS setting: an involuntary smooth scroll is exactly the kind
    // of motion `prefers-reduced-motion` exists to suppress.
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    container.scrollTo({ top: 0, behavior: prefersReducedMotion ? "auto" : "smooth" });
  }, [dependency]);
};

/**
 * Bring a panel on the CURRENT page into view, clear of the sticky header.
 *
 * Used by dashboard KPI tiles whose detail lives in a panel further down the
 * same page rather than on a route of its own -- Device alerts is counted in
 * the KPI row and listed in the Alerts panel below it.
 *
 * `scrollIntoView` is not enough on its own: the page header is sticky and
 * 74px tall, so a panel aligned to the top of the scrollport lands underneath
 * it. The offset is read from `--hms-header-height` rather than repeated here,
 * so it follows the header if that ever changes.
 */
/** Styled in index.css; kept in step with the timeout below. */
const PANEL_FLASH_CLASS = "hms-panel-flash";
const PANEL_FLASH_MS = 1600;

export const scrollPanelIntoView = (elementId: string) => {
  const container = document.querySelector<HTMLElement>(".hms-content");
  const target = document.getElementById(elementId);
  if (!container || !target) return;

  const headerHeight =
    parseInt(
      getComputedStyle(container).getPropertyValue("--hms-header-height"),
      10,
    ) || 0;

  // Rect deltas rather than `offsetTop`: the panel's offsetParent is not
  // necessarily the scroll container, so offsetTop can be measured from the
  // wrong box.
  const delta =
    target.getBoundingClientRect().top - container.getBoundingClientRect().top;

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  container.scrollTo({
    // 12px of breathing room so the panel does not sit flush against the bar.
    top: Math.max(0, container.scrollTop + delta - headerHeight - 12),
    behavior: prefersReducedMotion ? "auto" : "smooth",
  });

  /*
    Scrolling alone does not say WHICH panel answered the click -- several
    cards sit in view at once, so the jump is ambiguous. A brief outline names
    the target, then gets out of the way.

    Re-adding the class needs the previous animation cleared first, otherwise
    clicking the same tile twice does nothing: the class is already present, so
    no animation restarts. Removing it and forcing a reflow restarts it.
  */
  target.classList.remove(PANEL_FLASH_CLASS);
  void target.offsetWidth;
  target.classList.add(PANEL_FLASH_CLASS);
  window.setTimeout(
    () => target.classList.remove(PANEL_FLASH_CLASS),
    PANEL_FLASH_MS,
  );
};
