/**
 * The contract between a status shown somewhere and the room list that details
 * it.
 *
 * The Occupancy Statistics donut writes `?status=` and the Occupancy screen
 * reads it. Those are two files with no compiler-visible link between them: the
 * param name was a bare string on each side, so renaming it in one place would
 * have broken the drill-through silently -- the link would still navigate, the
 * screen would still render, and the filter would simply be ignored. Naming it
 * once is what makes that a build error instead of a quiet regression.
 *
 * The status travels as its `amenity_status_name`, not its id. That is what the
 * Occupancy screen's own filter is keyed on, and an `amenity_status` row id is a
 * lookup-table detail that nothing should pin into a URL a user can bookmark.
 */

/** The route that lists rooms, and this panel's detail view. */
export const OCCUPANCY_PATH = "/occupancy";

/** The query key carrying a status name into that route's filter. */
export const STATUS_QUERY_PARAM = "status";

/** The query key carrying in-house occupancy filtering into that route. */
export const IS_OCCUPIED_QUERY_PARAM = "is_occupied";

/**
 * Link to the room list filtered to one status.
 *
 * Encoded, because a status name is display text from the lookup table rather
 * than a slug -- a row named "Under maintenance" or one holding an `&` has to
 * survive the round trip.
 */
export const statusDetailPath = (statusName: string) =>
    `${OCCUPANCY_PATH}?${STATUS_QUERY_PARAM}=${encodeURIComponent(statusName)}&amenity_category=room`;

/**
 * Link to the room list filtered to active in-house occupancy (Room in House).
 */
export const inHouseDetailPath = () =>
    `${OCCUPANCY_PATH}?${IS_OCCUPIED_QUERY_PARAM}=true&amenity_category=room`;

