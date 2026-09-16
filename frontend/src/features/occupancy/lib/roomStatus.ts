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

const styleOf = (statusName: string | null | undefined) =>
    (statusName && STATUS_STYLE[statusName as AmenityStatusName]) || NEUTRAL;

export const roomStatusBadgeClass = (statusName: string | null | undefined) =>
    styleOf(statusName).badgeClass;

export const roomStatusTextClass = (statusName: string | null | undefined) =>
    styleOf(statusName).textClass;

export const roomStatusColor = (statusName: string | null | undefined) =>
    styleOf(statusName).color;

export const roomStatusTint = (statusName: string | null | undefined) =>
    styleOf(statusName).tint;
