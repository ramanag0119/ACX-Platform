/**
 * The one place a room's occupancy status becomes a colour.
 *
 *   Available   -> green
 *   Occupied    -> red
 *   Allotted    -> yellow
 *   Unavailable -> blue
 *
 * Keyed by `amenity_status.amenity_status_name` as the API returns it, never by
 * the row's id: `amenity_status` ids happen to be 0-3 today and nothing in the
 * schema promises that, so a lookup on the id would silently mis-colour if the
 * table were ever reordered. A status name this map does not know -- including
 * a room with no status at all -- falls back to neutral rather than borrowing
 * another status's colour.
 *
 * Three renderings of the same four colours, because the module draws status
 * three ways and they must not drift apart:
 *
 *   badgeClass  outline badges (the room list, the Room Details header)
 *   textClass   a status rendered as plain text in a detail row
 *   color       a raw value for SVG / chart fills and legend swatches
 *   tint        the filled room tiles on the status board
 *
 * Every value is an existing Tailwind palette step (green/red/yellow/blue 500
 * and friends); no new design token, CSS variable or theme entry is introduced.
 */

import {
    KNOWN_AMENITY_STATUSES,
    ROOM_STATUS,
    type AmenityStatusName,
} from "@/lib/api/types";

/**
 * Re-exported so this module is a one-stop import for the status vocabulary.
 * The names themselves are declared once, in lib/api/types, beside the other
 * lookup-table constants -- this file owns the COLOURS, not the vocabulary.
 */
export { KNOWN_AMENITY_STATUSES, ROOM_STATUS };
export type RoomStatusName = AmenityStatusName;

interface RoomStatusStyle {
    /** Outline `<Badge>` classes, light and dark. */
    badgeClass: string;
    /** Text-only rendering, light and dark. */
    textClass: string;
    /** Raw colour for chart fills, SVG strokes and legend swatches. */
    color: string;
    /** Filled tile: background per theme, plus its border and text colour. */
    tint: { light: string; dark: string; border: string; text: string };
}

const STATUS_STYLE: Record<AmenityStatusName, RoomStatusStyle> = {
    [ROOM_STATUS.AVAILABLE]: {
        badgeClass:
            "border-green-500 text-green-600 dark:text-green-400 dark:border-green-500/60 dark:bg-green-950/30",
        textClass: "text-green-600 dark:text-green-400",
        color: "#22C55E",
        tint: { light: "#DCFCE7", dark: "#12341f", border: "#22C55E", text: "#065F46" },
    },
    [ROOM_STATUS.OCCUPIED]: {
        badgeClass:
            "border-red-500 text-red-600 dark:text-red-400 dark:border-red-500/60 dark:bg-red-950/30",
        textClass: "text-red-600 dark:text-red-400",
        color: "#EF4444",
        tint: { light: "#FEE2E2", dark: "#3d1f1f", border: "#EF4444", text: "#7F1D1D" },
    },
    [ROOM_STATUS.ALLOTTED]: {
        badgeClass:
            "border-yellow-500 text-yellow-600 dark:text-yellow-400 dark:border-yellow-500/60 dark:bg-yellow-950/30",
        textClass: "text-yellow-600 dark:text-yellow-400",
        color: "#EAB308",
        tint: { light: "#FEF9C3", dark: "#3a3512", border: "#EAB308", text: "#713F12" },
    },
    [ROOM_STATUS.UNAVAILABLE]: {
        badgeClass:
            "border-blue-500 text-blue-600 dark:text-blue-400 dark:border-blue-500/60 dark:bg-blue-950/30",
        textClass: "text-blue-600 dark:text-blue-400",
        color: "#3B82F6",
        tint: { light: "#DBEAFE", dark: "#12294a", border: "#3B82F6", text: "#1E3A8A" },
    },
};

/** Used for an unrecognised status name and for a room carrying none. */
const NEUTRAL: RoomStatusStyle = {
    badgeClass:
        "border-gray-400 text-gray-500 dark:text-gray-400 dark:border-gray-600 dark:bg-slate-800/40",
    textClass: "text-muted-foreground",
    color: "#94A3B8",
    tint: { light: "#F1F5F9", dark: "#1e293b", border: "#94A3B8", text: "#334155" },
};

export const STATUS_ID_TO_NAME: Record<number, AmenityStatusName> = {
    0: ROOM_STATUS.AVAILABLE,
    1: ROOM_STATUS.OCCUPIED,
    2: ROOM_STATUS.UNAVAILABLE,
    3: ROOM_STATUS.ALLOTTED,
};

export const normalizeAmenityStatusName = (
    statusName: string | null | undefined,
    statusId?: number | null,
): AmenityStatusName | null => {
    if (typeof statusId === "number" && statusId in STATUS_ID_TO_NAME) {
        return STATUS_ID_TO_NAME[statusId];
    }
    if (!statusName) return null;
    const trimmed = statusName.trim().toLowerCase();
    for (const name of KNOWN_AMENITY_STATUSES) {
        if (name.toLowerCase() === trimmed) {
            return name;
        }
    }
    return null;
};

const styleOf = (statusName: string | null | undefined, statusId?: number | null) => {
    const normalized = normalizeAmenityStatusName(statusName, statusId);
    return (normalized && STATUS_STYLE[normalized]) || NEUTRAL;
};

export const roomStatusBadgeClass = (statusName: string | null | undefined, statusId?: number | null) =>
    styleOf(statusName, statusId).badgeClass;

export const roomStatusTextClass = (statusName: string | null | undefined, statusId?: number | null) =>
    styleOf(statusName, statusId).textClass;

export const roomStatusColor = (statusName: string | null | undefined, statusId?: number | null) =>
    styleOf(statusName, statusId).color;

export const roomStatusTint = (statusName: string | null | undefined, statusId?: number | null) =>
    styleOf(statusName, statusId).tint;

/**
 * Display label for an `amenity_condition` name.
 *
 * The stored vocabulary is the backend's (Dirty, Low battery, Under
 * maintenance, Sanitation, Ready for occupant) and is NOT changed here --
 * filters, writes and the condition picker all still work on the stored value.
 * This maps the stored name to the wording operators use, in ONE place, so the
 * room list, the dashboard tiles and the conditions dialog cannot disagree.
 *
 * Matching is case-insensitive on the stored name; anything without an entry
 * falls through unchanged, so a condition added to the table later shows its
 * real name rather than vanishing.
 */
/**
 * Display label for an `amenity_condition` record or name.
 * Authoritative display names come directly from the database via the API (display_name).
 * If display_name is absent, falls back to the condition name.
 */
export const conditionLabel = (
  conditionOrName:
    | { display_name?: string | null; name?: string | null }
    | string
    | null
    | undefined,
): string => {
  if (!conditionOrName) return "";
  if (typeof conditionOrName === "object") {
    return (
      conditionOrName.display_name?.trim() ||
      conditionOrName.name?.trim() ||
      ""
    );
  }
  return conditionOrName.trim();
};

export const READY_CONDITION_ID = 5;
export const BLOCKING_CONDITION_IDS = new Set([1, 3, 4]);

export const READY_CONDITION_NAMES = new Set([
  "ready for occupant",
  "ready to occupy",
]);

export const BLOCKING_CONDITION_NAMES = new Set([
  "dirty",
  "need maintenance",
  "under maintenance",
  "sanitation",
]);

export interface ConditionLookupItem {
  id: number;
  name: string;
  display_name?: string | null;
}

export const isReadyCondition = (
  idOrName: number | string,
  conditions?: ConditionLookupItem[],
): boolean => {
  if (typeof idOrName === "number") {
    if (idOrName === READY_CONDITION_ID) return true;
    const found = conditions?.find((c) => c.id === idOrName);
    return found ? READY_CONDITION_NAMES.has(found.name.trim().toLowerCase()) : false;
  }
  return READY_CONDITION_NAMES.has(idOrName.trim().toLowerCase());
};

export const isBlockingCondition = (
  idOrName: number | string,
  conditions?: ConditionLookupItem[],
): boolean => {
  if (typeof idOrName === "number") {
    if (BLOCKING_CONDITION_IDS.has(idOrName)) return true;
    const found = conditions?.find((c) => c.id === idOrName);
    return found ? BLOCKING_CONDITION_NAMES.has(found.name.trim().toLowerCase()) : false;
  }
  return BLOCKING_CONDITION_NAMES.has(idOrName.trim().toLowerCase());
};

/**
 * Computes the next set of selected condition IDs when toggling a condition ID.
 *
 * Compatibility rules:
 * 1. If unchecking: simply removes it.
 * 2. If checking Ready to Occupy: removes any blocking conditions (Dirty/Need Maintenance,
 *    Under maintenance, Sanitation), while preserving independent conditions (e.g. Low battery).
 * 3. If checking a blocking condition: removes Ready to Occupy, while preserving independent
 *    conditions and other compatible blocking conditions.
 * 4. If checking an independent condition (e.g. Low battery): preserves all existing selections.
 */
export const getNextConditionIds = (
  toggledId: number,
  currentIds: number[],
  conditions?: ConditionLookupItem[],
): number[] => {
  if (currentIds.includes(toggledId)) {
    return currentIds.filter((id) => id !== toggledId);
  }

  if (isReadyCondition(toggledId, conditions)) {
    const withoutBlocking = currentIds.filter((id) => !isBlockingCondition(id, conditions));
    return [...withoutBlocking, toggledId];
  }

  if (isBlockingCondition(toggledId, conditions)) {
    const withoutReady = currentIds.filter((id) => !isReadyCondition(id, conditions));
    return [...withoutReady, toggledId];
  }

  return [...currentIds, toggledId];
};

/**
 * Validates whether the given condition IDs contain contradictory conditions.
 */
export const validateConditions = (
  conditionIds: number[],
  conditions?: ConditionLookupItem[],
): { valid: boolean; error?: string } => {
  const hasReady = conditionIds.some((id) => isReadyCondition(id, conditions));
  const blockingIds = conditionIds.filter((id) => isBlockingCondition(id, conditions));

  if (hasReady && blockingIds.length > 0) {
    const blockingNames = blockingIds
      .map((id) => {
        const found = conditions?.find((c) => c.id === id);
        return conditionLabel(found ?? `Condition ${id}`);
      })
      .join(", ");
    return {
      valid: false,
      error: `Ready to occupy cannot coexist with blocking condition(s): ${blockingNames}.`,
    };
  }

  return { valid: true };
};

