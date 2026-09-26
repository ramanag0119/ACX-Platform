/**
 * The one place a service request's status becomes a colour.
 *
 *   Pending              -> yellow   (raised, nobody on it yet)
 *   Assigned             -> blue     (someone owns it)
 *   In Progress          -> blue     (owned and underway)
 *   Completed            -> green    (done)
 *   Canceled             -> gray     (closed without being done)
 *
 * Written because the Room Details dialog rendered EVERY service request with
 * the same green "completed" badge, hardcoded on the element. A pending request
 * and a cancelled one both read as done -- the status text was correct while the
 * colour beside it said the opposite, which is worse than showing no colour at
 * all.
 *
 * Keyed by `service_status.status_name` as the API returns it, never by the
 * row's id: `services.py` happens to seed these as 1-5 today and nothing in the
 * schema promises that order. Matching is case- and space-insensitive so
 * "In Progress" and "in_progress" land on the same entry. A
 * status this map does not know falls back to neutral rather than borrowing
 * another status's meaning, so a status added to the table later shows up
 * uncoloured instead of silently claiming to be complete.
 *
 * This mirrors roomStatus.ts deliberately -- same lookup shape, same neutral
 * fallback, same "no new design token" rule.
 */

/** Filled `<Badge variant="secondary">` classes, light and dark. */
const STATUS_BADGE_CLASS: Record<string, string> = {
    pending:
        "bg-yellow-100 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400",
    assigned:
        "bg-blue-100 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400",
    "in progress":
        "bg-blue-100 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400",
    completed:
        "bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400",
    canceled:
        "bg-gray-100 text-gray-600 hover:bg-gray-100 dark:bg-slate-800/60 dark:text-slate-400",
    /** The API's spelling is "Canceled"; accept the British one too. */
    cancelled:
        "bg-gray-100 text-gray-600 hover:bg-gray-100 dark:bg-slate-800/60 dark:text-slate-400",
};

/** Used for an unrecognised status name and for a request carrying none. */
const NEUTRAL_BADGE_CLASS =
    "bg-muted text-muted-foreground hover:bg-muted dark:bg-slate-800/60 dark:text-slate-400";

/** Collapses casing, underscores and stray spacing before the lookup. */
const normalise = (statusName: string) =>
    statusName.trim().toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ");

export const serviceStatusBadgeClass = (statusName: string | null | undefined) =>
    (statusName && STATUS_BADGE_CLASS[normalise(statusName)]) || NEUTRAL_BADGE_CLASS;
