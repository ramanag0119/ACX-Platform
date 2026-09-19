import { useMemo } from "react";

import { useTheme } from "@/core/contexts/ThemeContext";

/**
 * The colour tokens for the raised "card" surface used by the dashboard and
 * occupancy widgets.
 *
 * WHY THIS EXISTS. The same nine literals -- the panel gradient, its border,
 * the title and muted text colours, the select and tooltip chrome and the drop
 * shadow -- had been copy-pasted into nine components. Re-theming meant finding
 * and editing all nine, and they had already drifted: the light-mode muted text
 * was `#5E5A7A` in five of them and `#8A86A8` in the other two, so the same
 * semantic role rendered in two different colours on one screen.
 *
 * Both values are kept below, but as two NAMED roles rather than one role with
 * two spellings. `textMuted` is the secondary text on a card; `textSubtle` is
 * the lighter grade the room/floor pickers use for their supporting lines.
 * Naming them separately preserves what is on screen today while making the
 * distinction deliberate and reviewable in one file.
 *
 * These stay TypeScript rather than CSS custom properties because Recharts
 * takes its `stroke` and `fill` as prop values, not as styles it can inherit.
 */
export interface SurfaceTokens {
  /** Card background. */
  cardBg: string;
  /** Full `border` shorthand for a card. */
  cardBorder: string;
  /** Card drop shadow. */
  cardShadow: string;
  /** Headings and primary figures on a card. */
  titleColor: string;
  /** Secondary text on a card: legends, captions, subtitles. */
  textMuted: string;
  /** The lighter secondary grade used by the building/floor/room pickers. */
  textSubtle: string;
  /** Background for a `<select>` or similar inline control on a card. */
  controlBg: string;
  /** Full `border` shorthand for that control. */
  controlBorder: string;
  /** Recharts tooltip background. */
  tooltipBg: string;
  /** Full `border` shorthand for the Recharts tooltip. */
  tooltipBorder: string;
  /** Recharts cartesian grid stroke. */
  gridStroke: string;
}

const DARK: SurfaceTokens = {
  cardBg: "linear-gradient(180deg, #1e2233, #1a1e30)",
  cardBorder: "1px solid rgba(255,255,255,0.07)",
  cardShadow: "0 8px 24px rgba(17,12,46,0.12)",
  titleColor: "#dde2ed",
  textMuted: "#8b95a9",
  textSubtle: "#8b95a9",
  controlBg: "#252a3e",
  controlBorder: "1px solid rgba(255,255,255,0.1)",
  tooltipBg: "#1e2233",
  tooltipBorder: "1px solid rgba(255,255,255,0.1)",
  gridStroke: "rgba(255,255,255,0.06)",
};

const LIGHT: SurfaceTokens = {
  cardBg: "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))",
  cardBorder: "1px solid rgba(124,92,255,0.12)",
  cardShadow: "0 8px 24px rgba(17,12,46,0.12)",
  titleColor: "#1F1B3A",
  textMuted: "#5E5A7A",
  textSubtle: "#8A86A8",
  controlBg: "#FFFFFF",
  controlBorder: "1px solid rgba(124,92,255,0.12)",
  tooltipBg: "#FFFFFF",
  tooltipBorder: "1px solid rgba(124,92,255,0.12)",
  gridStroke: "rgba(124,92,255,0.1)",
};

/** The card tokens for the active theme. */
export const useSurfaceTokens = (): SurfaceTokens => {
  const { isDark } = useTheme();
  return isDark ? DARK : LIGHT;
};

/**
 * The three properties every card shell sets, ready to spread into `style`.
 * Memoised because it is a fresh object each render otherwise, which would
 * defeat `React.memo` on any card that takes it as a prop.
 */
export const useCardSurfaceStyle = () => {
  const tokens = useSurfaceTokens();
  return useMemo(
    () => ({
      background: tokens.cardBg,
      border: tokens.cardBorder,
      boxShadow: tokens.cardShadow,
    }),
    [tokens],
  );
};
