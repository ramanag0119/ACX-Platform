/**
 * Selectors behind the dashboard's Average Energy Consumption card.
 *
 * The source is GET /energy-stats/summary, which performs SUM and COUNT only.
 * Turning a bucket into a plotted point -- its axis wording, its rounding and
 * the divide-by-zero guard on the average -- is defined here so the chart
 * cannot grow a second, differing copy of it.
 *
 * NO UNIT IS APPLIED HERE. `energy_stat` has no unit column; the API resolves
 * `energy_unit` from `device_param` and the chart appends it at render time, so
 * these selectors deal in bare numbers and must not label, convert, cost or
 * carbon-weight them. There is no efficiency or baseline figure to report.
 */

import type { EnergySummaryBucket } from "@/lib/api/types";

export type EnergyGrouping = "hour" | "day";

export interface EnergyPoint {
  /** Axis label. */
  name: string;
  /** Spelled out bucket, used in the tooltip. */
  fullName: string;
  /** The stored SUM for the bucket. */
  totalEnergy: number;
  /** That SUM divided by the stored COUNT - a presentation division. */
  avgPerReading: number;
  /** The stored COUNT, the divisor behind `avgPerReading`. */
  readingCount: number;
}

const round = (value: number, decimals = 3) => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
};

/**
 * Axis and tooltip wording for one bucket. `bucket_label` is used whenever the
 * backend supplies one; the fallbacks only cover the null case.
 */
const describeBucket = (
  bucket: EnergySummaryBucket,
  grouping: EnergyGrouping,
  bucketCount: number,
): { name: string; fullName: string } => {
  const at = new Date(bucket.bucket);
  const parsed = !Number.isNaN(at.getTime());

  if (!parsed) {
    const raw = bucket.bucket_label ?? bucket.bucket;
    return { name: raw, fullName: raw };
  }

  if (grouping === "hour") {
    return {
      name: bucket.bucket_label ?? at.toLocaleTimeString([], { hour: "2-digit", hour12: false }),
      fullName: at.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        hour12: false,
      }),
    };
  }

  // A week's worth of days reads best as weekdays; longer spans need the date.
  const shortDay =
    bucketCount <= 7
      ? at.toLocaleDateString([], { weekday: "short" })
      : at.toLocaleDateString([], { month: "short", day: "numeric" });

  return {
    name: bucket.bucket_label ?? shortDay,
    fullName: at.toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" }),
  };
};

export const toEnergyPoints = (
  buckets: EnergySummaryBucket[],
  grouping: EnergyGrouping,
): EnergyPoint[] =>
  buckets.map((bucket) => ({
    ...describeBucket(bucket, grouping, buckets.length),
    totalEnergy: round(bucket.total_energy_consumed),
    avgPerReading:
      bucket.reading_count > 0 ? round(bucket.total_energy_consumed / bucket.reading_count) : 0,
    readingCount: bucket.reading_count,
  }));
